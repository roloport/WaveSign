"""WaveSign integration layer.

This module provides the interface to WaveSign's invisible signature technology.
It handles embedding ABV data into credential images and verifying them.

In production, this connects to WaveSign's signing/verification API.
This implementation provides a self-contained reference that uses WaveSign's
core principles: physics-based signal embedding with dual-layer verification.
"""

from __future__ import annotations

import hashlib
import hmac
import struct
from io import BytesIO

import numpy as np
from PIL import Image


class WaveSignError(Exception):
    """Errors from WaveSign operations."""


class WaveSignEngine:
    """Interface to WaveSign's invisible signature technology.

    Provides two operations:
    1. sign() — embed invisible payload into an image
    2. verify() — extract and validate the payload from a signed image

    The signing process:
    - Generates a content signature from the image's signal structure + key
    - Computes a block-level integrity hash of the pixel data
    - Embeds the payload into the image's least-significant signal components
      with magnitude calibrated to be imperceptible (target PSNR > 40 dB)
    """

    # Block size for integrity hashing (matches WaveSign's block-level approach)
    BLOCK_SIZE = 8

    def __init__(self, key: str | bytes) -> None:
        if isinstance(key, str):
            key = key.encode()
        self._key = key
        self._derived_key = hashlib.sha256(b"wavesign.key.v1" + key).digest()

    def sign(self, image: Image.Image, payload: bytes) -> tuple[Image.Image, bytes]:
        """Embed an invisible payload into an image.

        Args:
            image: The source image (RGB).
            payload: Arbitrary bytes to embed (typically ABV + metadata).

        Returns:
            (signed_image, verify_data): The signed image and verification sidecar.
        """
        img_array = np.array(image.convert("RGB"), dtype=np.float64)

        # Embed payload into image signal
        signed_array = self._embed_payload(img_array, payload)

        # Quantize to uint8 now — this is the actual image that will be stored.
        # All hashes must be computed on the quantized version to ensure
        # the round-trip through PNG save/load produces identical values.
        signed_uint8 = np.clip(signed_array, 0, 255).astype(np.uint8)
        final_array = signed_uint8.astype(np.float64)

        # Layer 1: Content signature — derived from image signal + key
        content_sig = self._content_signature(final_array)

        # Layer 2: Integrity hash — block-level pixel fingerprint of signed image
        integrity_hash = self._integrity_hash(final_array)

        # Build verify sidecar
        verify_data = self._build_verify_data(payload, content_sig, integrity_hash)

        signed_image = Image.fromarray(signed_uint8)
        return signed_image, verify_data

    def verify(self, image: Image.Image, verify_data: bytes) -> tuple[bool, bytes]:
        """Verify a signed image and extract the payload.

        Args:
            image: The potentially signed image.
            verify_data: The verification sidecar from signing.

        Returns:
            (is_valid, payload): Whether verification passed, and the extracted payload.
        """
        img_array = np.array(image.convert("RGB"), dtype=np.float64)

        # Parse verify data
        parsed = self._parse_verify_data(verify_data)
        if parsed is None:
            return False, b""

        original_payload, expected_content_sig, expected_integrity = parsed

        # Check Layer 2: Integrity hash
        current_integrity = self._integrity_hash(img_array)
        if not hmac.compare_digest(current_integrity, expected_integrity):
            return False, b""

        # Check Layer 1: Content signature
        current_content_sig = self._content_signature(img_array)
        if not hmac.compare_digest(current_content_sig, expected_content_sig):
            return False, b""

        # Extract and verify embedded payload
        extracted = self._extract_payload(img_array, len(original_payload))
        if extracted != original_payload:
            return False, b""

        return True, original_payload

    def _content_signature(self, img_array: np.ndarray) -> bytes:
        """Compute content signature from image signal structure + key.

        This is WaveSign Layer 1: the signature depends on both the image
        content and the secret key, making it non-transferable.
        """
        # Downsample to capture signal structure, not pixel-level noise
        h, w = img_array.shape[:2]
        block_h, block_w = h // self.BLOCK_SIZE, w // self.BLOCK_SIZE
        if block_h == 0 or block_w == 0:
            block_h, block_w = max(block_h, 1), max(block_w, 1)

        blocks = img_array[: block_h * self.BLOCK_SIZE, : block_w * self.BLOCK_SIZE]
        blocks = blocks.reshape(block_h, self.BLOCK_SIZE, block_w, self.BLOCK_SIZE, -1)
        signal = blocks.mean(axis=(1, 3))  # Block-level averages

        signal_bytes = signal.astype(np.float32).tobytes()
        return hmac.new(self._derived_key, signal_bytes, hashlib.sha256).digest()

    def _integrity_hash(self, img_array: np.ndarray) -> bytes:
        """Compute block-level integrity hash.

        This is WaveSign Layer 2: a pixel fingerprint that detects any
        modification to the image after signing.
        """
        raw = np.clip(img_array, 0, 255).astype(np.uint8).tobytes()
        return hashlib.sha256(self._derived_key + raw).digest()

    def _embed_payload(self, img_array: np.ndarray, payload: bytes) -> np.ndarray:
        """Embed payload bits into the image using LSB encoding.

        Uses a pseudo-random embedding pattern seeded by the key to spread
        the payload across the image, making it invisible and hard to locate
        without the key. Operates in uint8 space for exact PNG round-trip.
        """
        result = np.clip(img_array, 0, 255).astype(np.uint8).copy()
        h, w, c = result.shape

        # Generate embedding positions from key
        rng = np.random.RandomState(
            int.from_bytes(self._derived_key[:4], "big") & 0x7FFFFFFF
        )

        # Convert payload to bit array (with length prefix)
        payload_with_len = struct.pack(">I", len(payload)) + payload
        bits = np.unpackbits(np.frombuffer(payload_with_len, dtype=np.uint8))

        # Check capacity
        total_pixels = h * w * c
        if len(bits) > total_pixels // 8:
            raise WaveSignError(
                f"Payload too large ({len(payload)} bytes) for image size ({h}x{w})"
            )

        positions = rng.permutation(total_pixels)[: len(bits)]
        flat = result.reshape(-1)

        for i, bit in enumerate(bits):
            pos = positions[i]
            val = int(flat[pos])
            # Set LSB to the bit value
            flat[pos] = np.uint8((val & 0xFE) | int(bit))

        return result.astype(np.float64)

    def _extract_payload(self, img_array: np.ndarray, expected_len: int) -> bytes:
        """Extract embedded payload from a signed image via LSB decoding."""
        arr = np.clip(img_array, 0, 255).astype(np.uint8)
        h, w, c = arr.shape

        rng = np.random.RandomState(
            int.from_bytes(self._derived_key[:4], "big") & 0x7FFFFFFF
        )

        # Extract length prefix (4 bytes = 32 bits) + payload
        total_bits = (4 + expected_len) * 8
        total_pixels = h * w * c
        positions = rng.permutation(total_pixels)[:total_bits]
        flat = arr.reshape(-1)

        bits = np.zeros(total_bits, dtype=np.uint8)
        for i in range(total_bits):
            bits[i] = flat[positions[i]] & 1

        extracted_bytes = np.packbits(bits).tobytes()
        extracted_len = struct.unpack(">I", extracted_bytes[:4])[0]
        if extracted_len != expected_len:
            return b""
        return extracted_bytes[4 : 4 + expected_len]

    def _build_verify_data(
        self, payload: bytes, content_sig: bytes, integrity_hash: bytes
    ) -> bytes:
        """Build verification sidecar."""
        # Format: version(1) + payload_len(4) + payload + content_sig(32) + integrity(32) + mac(32)
        version = struct.pack("B", 1)
        payload_len = struct.pack(">I", len(payload))
        body = version + payload_len + payload + content_sig + integrity_hash
        mac = hmac.new(self._derived_key, body, hashlib.sha256).digest()
        return body + mac

    def _parse_verify_data(self, data: bytes) -> tuple[bytes, bytes, bytes] | None:
        """Parse and validate verification sidecar."""
        if len(data) < 1 + 4 + 32 + 32 + 32:
            return None

        version = data[0]
        if version != 1:
            return None

        payload_len = struct.unpack(">I", data[1:5])[0]
        body_end = 5 + payload_len + 32 + 32
        if len(data) < body_end + 32:
            return None

        body = data[:body_end]
        received_mac = data[body_end : body_end + 32]
        expected_mac = hmac.new(self._derived_key, body, hashlib.sha256).digest()
        if not hmac.compare_digest(received_mac, expected_mac):
            return None

        payload = data[5 : 5 + payload_len]
        content_sig = data[5 + payload_len : 5 + payload_len + 32]
        integrity_hash = data[5 + payload_len + 32 : 5 + payload_len + 64]

        return payload, content_sig, integrity_hash
