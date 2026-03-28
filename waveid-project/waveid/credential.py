"""WaveID Credential — visual identity card with invisible biometric embedding.

A credential is a PNG image that looks like a human-readable ID card but
contains the agent's biometric vector invisibly embedded via WaveSign's
physics-based signature technology.
"""

from __future__ import annotations

import json
import struct
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from waveid.biometric import ABV_LENGTH, AgentBiometricVector


# Credential image dimensions
CREDENTIAL_WIDTH = 600
CREDENTIAL_HEIGHT = 380


@dataclass
class CredentialMetadata:
    """Human-readable metadata displayed on the credential card."""

    agent_name: str
    agent_id: str
    issuer: str
    scope: list[str]
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            self.expires_at = self.issued_at + 90 * 86400  # 90 days default

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_id": self.agent_id,
            "issuer": self.issuer,
            "scope": self.scope,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True).encode()


@dataclass
class WaveIDCredential:
    """A WaveID credential containing visible card + invisible biometric.

    The credential image is a standard PNG that can be stored, transmitted,
    and displayed normally. The invisible layer is embedded using WaveSign
    and contains the ABV, issuer signature, and metadata.
    """

    metadata: CredentialMetadata
    abv: AgentBiometricVector
    image: Image.Image | None = None
    verify_data: bytes = b""

    def generate_card_image(self) -> Image.Image:
        """Render the visible ID card image.

        This produces the visual layer of the credential — a clean,
        human-readable card. The invisible biometric embedding is applied
        separately by the WaveSign integration layer.
        """
        img = Image.new("RGB", (CREDENTIAL_WIDTH, CREDENTIAL_HEIGHT), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Card border
        draw.rectangle(
            [10, 10, CREDENTIAL_WIDTH - 10, CREDENTIAL_HEIGHT - 10],
            outline=(30, 60, 120),
            width=3,
        )

        # Header bar
        draw.rectangle(
            [10, 10, CREDENTIAL_WIDTH - 10, 70],
            fill=(30, 60, 120),
        )

        # Title
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except OSError:
            title_font = ImageFont.load_default()
            body_font = title_font
            small_font = title_font

        draw.text((30, 25), "WAVEID AGENT CREDENTIAL", fill=(255, 255, 255), font=title_font)

        # Agent info
        y = 90
        fields = [
            ("Agent", self.metadata.agent_name),
            ("ID", self.metadata.agent_id[:24] + "..."),
            ("Issuer", self.metadata.issuer),
            ("Scope", ", ".join(self.metadata.scope)),
            ("Issued", time.strftime("%Y-%m-%d", time.gmtime(self.metadata.issued_at))),
            ("Expires", time.strftime("%Y-%m-%d", time.gmtime(self.metadata.expires_at))),
        ]
        for label, value in fields:
            draw.text((30, y), f"{label}:", fill=(100, 100, 100), font=small_font)
            draw.text((120, y), value, fill=(30, 30, 30), font=body_font)
            y += 35

        # ABV fingerprint visualization (small grid in bottom-right)
        abv_bytes = self.abv.data
        grid_x, grid_y = CREDENTIAL_WIDTH - 140, CREDENTIAL_HEIGHT - 120
        draw.text((grid_x, grid_y - 18), "Biometric Hash", fill=(100, 100, 100), font=small_font)
        cell_size = 12
        for i in range(8):
            for j in range(4):
                idx = i * 4 + j
                if idx < len(abv_bytes):
                    val = abv_bytes[idx]
                    color = (
                        30 + int(val * 0.6),
                        60 + int(val * 0.4),
                        120 + int(val * 0.3),
                    )
                    # Clamp to valid RGB range
                    color = tuple(min(255, c) for c in color)
                    draw.rectangle(
                        [
                            grid_x + j * cell_size,
                            grid_y + i * cell_size,
                            grid_x + (j + 1) * cell_size - 1,
                            grid_y + (i + 1) * cell_size - 1,
                        ],
                        fill=color,
                    )

        self.image = img
        return img

    def to_png_bytes(self) -> bytes:
        """Export the credential card as PNG bytes."""
        if self.image is None:
            self.generate_card_image()
        buf = BytesIO()
        self.image.save(buf, format="PNG")
        return buf.getvalue()

    def build_verify_payload(self, authority_key: bytes) -> bytes:
        """Build the verification sidecar data.

        This contains everything needed to verify the credential:
        - ABV (encrypted with authority key)
        - Metadata
        - Integrity checksum

        In production, this would be handled by WaveSign's signing API.
        Here we build the payload structure that WaveSign would embed.
        """
        import hashlib
        import hmac

        # Structure: version(1) + abv(32) + metadata_len(4) + metadata + hmac(32)
        version = struct.pack("B", 1)
        metadata_bytes = self.metadata.to_bytes()
        metadata_len = struct.pack(">I", len(metadata_bytes))

        payload = version + self.abv.data + metadata_len + metadata_bytes
        mac = hmac.new(authority_key, payload, hashlib.sha256).digest()

        self.verify_data = payload + mac
        return self.verify_data

    @staticmethod
    def parse_verify_payload(data: bytes, authority_key: bytes) -> tuple[AgentBiometricVector, CredentialMetadata] | None:
        """Parse and verify a credential verification payload.

        Returns (ABV, metadata) if valid, None if tampered or invalid.
        """
        import hashlib
        import hmac

        if len(data) < 1 + ABV_LENGTH + 4 + 32:
            return None

        version = data[0]
        if version != 1:
            return None

        abv_data = data[1 : 1 + ABV_LENGTH]
        metadata_len = struct.unpack(">I", data[1 + ABV_LENGTH : 1 + ABV_LENGTH + 4])[0]

        payload_end = 1 + ABV_LENGTH + 4 + metadata_len
        if len(data) < payload_end + 32:
            return None

        payload = data[:payload_end]
        received_mac = data[payload_end : payload_end + 32]

        expected_mac = hmac.new(authority_key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(received_mac, expected_mac):
            return None

        metadata_bytes = data[1 + ABV_LENGTH + 4 : payload_end]
        metadata_dict = json.loads(metadata_bytes.decode())
        metadata = CredentialMetadata(**metadata_dict)
        abv = AgentBiometricVector(data=abv_data)

        return abv, metadata
