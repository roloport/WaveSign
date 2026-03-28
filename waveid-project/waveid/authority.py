"""WaveID Authority — the enrollment and credential issuance service.

The Authority is responsible for:
1. Conducting enrollment (issuing challenge sets, collecting responses)
2. Extracting Agent Biometric Vectors
3. Generating WaveID credentials (image + verification sidecar)
4. Maintaining the enrollment registry
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from waveid.auth import AuthLevel
from waveid.biometric import (
    AgentBiometricVector,
    BehavioralProfiler,
    BiometricExtractor,
    ModelMetadata,
    SystemContext,
)
from waveid.challenge import (
    ChallengeResponse,
    ChallengeSet,
    create_auth_challenge,
    create_enrollment_challenge,
)
from waveid.credential import CredentialMetadata, WaveIDCredential
from waveid.wavesign import WaveSignEngine


@dataclass
class EnrollmentRecord:
    """Record of an enrolled agent."""

    agent_id: str
    agent_name: str
    abv: AgentBiometricVector
    model_metadata: dict[str, str]
    scope: list[str]
    enrolled_at: float
    expires_at: float
    credential_hash: str  # SHA-256 of the credential image


@dataclass
class EnrollmentResult:
    """Result of a successful enrollment."""

    agent_id: str
    credential: WaveIDCredential
    credential_png: bytes
    verify_data: bytes


class WaveIDAuthority:
    """Central authority for WaveID enrollment and credential issuance.

    Usage:
        authority = WaveIDAuthority(wavesign_key="my-secret-key")

        # Step 1: Get challenge set
        challenge = authority.begin_enrollment()

        # Step 2: Agent responds to challenges
        response = ChallengeResponse(
            challenge_nonce=challenge.nonce,
            responses={"R01": "The ball costs $0.05...", ...},
            model_metadata={"model": "claude-opus-4-6", "version": "2026-03"},
        )

        # Step 3: Complete enrollment
        result = authority.complete_enrollment(
            challenge=challenge,
            response=response,
            agent_name="Agent-7X",
            issuer="Org-ABC",
            scope=["finance.read", "finance.write"],
        )
        # result.credential_png → PNG bytes of the ID card
        # result.verify_data → verification sidecar
    """

    def __init__(self, wavesign_key: str, salt: bytes = b"") -> None:
        self._wavesign_key = wavesign_key
        self._engine = WaveSignEngine(wavesign_key)
        self._extractor = BiometricExtractor(salt=salt)
        self._profiler = BehavioralProfiler()
        self._registry: dict[str, EnrollmentRecord] = {}
        self._pending_challenges: dict[str, ChallengeSet] = {}

    def begin_enrollment(self) -> ChallengeSet:
        """Start the enrollment process by issuing a challenge set.

        Returns a ChallengeSet containing 16 prompts. The agent must respond
        to all prompts within the expiry window.
        """
        challenge = create_enrollment_challenge()
        self._pending_challenges[challenge.nonce] = challenge
        return challenge

    def complete_enrollment(
        self,
        challenge: ChallengeSet,
        response: ChallengeResponse,
        agent_name: str,
        issuer: str,
        scope: list[str] | None = None,
        expiry_days: int = 90,
        system_prompt: str = "",
        tool_config: dict[str, Any] | None = None,
        permissions: list[str] | None = None,
    ) -> EnrollmentResult:
        """Complete enrollment by processing challenge responses.

        Extracts the ABV, generates a credential, and registers the agent.
        """
        # Validate challenge
        if challenge.nonce not in self._pending_challenges:
            raise ValueError("Unknown or already-used challenge nonce")
        if challenge.is_expired:
            self._pending_challenges.pop(challenge.nonce, None)
            raise ValueError("Challenge has expired")

        # Validate responses cover all prompts
        for prompt in challenge.prompts:
            if prompt.prompt_id not in response.responses:
                raise ValueError(f"Missing response for prompt {prompt.prompt_id}")

        # Extract biometric
        model = ModelMetadata(
            model_id=response.model_metadata.get("model", "unknown"),
            version=response.model_metadata.get("version", "unknown"),
            architecture=response.model_metadata.get("architecture", ""),
        )
        context = SystemContext(
            system_prompt=system_prompt,
            tool_config=tool_config or {},
            permissions=permissions or [],
        )

        # Build behavioral profile from responses
        ordered_responses = [
            response.responses[p.prompt_id] for p in challenge.prompts
        ]
        behavioral_profile = self._profiler.profile_from_responses(ordered_responses)

        # Extract ABV
        abv = self._extractor.extract(
            model=model,
            context=context,
            behavioral_profile=behavioral_profile,
        )

        # Generate agent ID
        agent_id = f"waveid:{agent_name.lower().replace(' ', '-')}:{abv.hex()[:12]}"

        # Build credential
        scope = scope or []
        metadata = CredentialMetadata(
            agent_name=agent_name,
            agent_id=agent_id,
            issuer=issuer,
            scope=scope,
            expires_at=time.time() + expiry_days * 86400,
        )
        credential = WaveIDCredential(metadata=metadata, abv=abv)
        card_image = credential.generate_card_image()

        # Embed ABV into credential image via WaveSign
        payload = credential.build_verify_payload(
            authority_key=hashlib.sha256(self._wavesign_key.encode()).digest()
        )
        signed_image, verify_data = self._engine.sign(card_image, payload)
        credential.image = signed_image

        # Register
        import hashlib as hl

        credential_png = credential.to_png_bytes()
        record = EnrollmentRecord(
            agent_id=agent_id,
            agent_name=agent_name,
            abv=abv,
            model_metadata=response.model_metadata,
            scope=scope,
            enrolled_at=time.time(),
            expires_at=metadata.expires_at,
            credential_hash=hl.sha256(credential_png).hexdigest(),
        )
        self._registry[agent_id] = record

        # Clean up used challenge
        self._pending_challenges.pop(challenge.nonce, None)

        return EnrollmentResult(
            agent_id=agent_id,
            credential=credential,
            credential_png=credential_png,
            verify_data=verify_data,
        )

    def create_auth_challenge(self, level: AuthLevel = AuthLevel.L2_LIVENESS) -> ChallengeSet:
        """Create a challenge for authentication (not enrollment)."""
        challenge = create_auth_challenge(level=int(level))
        self._pending_challenges[challenge.nonce] = challenge
        return challenge

    def get_enrolled_abv(self, agent_id: str) -> AgentBiometricVector | None:
        """Look up an enrolled agent's ABV."""
        record = self._registry.get(agent_id)
        if record is None:
            return None
        if time.time() > record.expires_at:
            return None
        return record.abv

    def is_enrolled(self, agent_id: str) -> bool:
        record = self._registry.get(agent_id)
        return record is not None and time.time() <= record.expires_at

    def revoke(self, agent_id: str) -> bool:
        """Revoke an agent's enrollment."""
        if agent_id in self._registry:
            del self._registry[agent_id]
            return True
        return False

    @property
    def enrolled_count(self) -> int:
        return len(self._registry)
