"""WaveID Verifier — authentication and identity verification.

The Verifier handles the authentication protocol:
1. Issue challenge (with fresh nonce)
2. Receive agent's responses + credential
3. Verify credential via WaveSign
4. Extract fresh behavioral biometric from responses
5. Compare against enrolled biometric
6. Return AuthResult
"""

from __future__ import annotations

import hashlib

import numpy as np

from waveid.auth import AUTH_THRESHOLDS, AuthLevel, AuthResult
from waveid.biometric import (
    AgentBiometricVector,
    BehavioralProfiler,
    BiometricExtractor,
    ModelMetadata,
    SystemContext,
)
from waveid.challenge import ChallengeResponse, ChallengeSet
from waveid.credential import WaveIDCredential
from waveid.wavesign import WaveSignEngine

from PIL import Image


class WaveIDVerifier:
    """Verifies agent identity through credential + behavioral biometric.

    Usage:
        verifier = WaveIDVerifier(
            wavesign_key="authority-key",
            get_enrolled_abv=authority.get_enrolled_abv,
        )

        # Step 1: Generate challenge
        challenge = verifier.create_challenge(level=AuthLevel.L2_LIVENESS)

        # Step 2: Agent responds
        response = ChallengeResponse(...)

        # Step 3: Verify
        result = verifier.verify(
            credential_image=signed_image,
            verify_data=verify_data,
            agent_id="waveid:agent-7x:a3f8c2...",
            challenge=challenge,
            response=response,
        )
    """

    def __init__(
        self,
        wavesign_key: str,
        get_enrolled_abv: callable = None,
    ) -> None:
        self._engine = WaveSignEngine(wavesign_key)
        self._authority_key = hashlib.sha256(wavesign_key.encode()).digest()
        self._profiler = BehavioralProfiler()
        self._extractor = BiometricExtractor()
        self._get_enrolled_abv = get_enrolled_abv

    def verify(
        self,
        credential_image: Image.Image,
        verify_data: bytes,
        agent_id: str,
        challenge: ChallengeSet | None = None,
        response: ChallengeResponse | None = None,
        level: AuthLevel = AuthLevel.L2_LIVENESS,
    ) -> AuthResult:
        """Perform full authentication verification.

        For L1 (credential-only), only credential_image and verify_data are needed.
        For L2+, challenge and response are also required for liveness check.
        """
        # Step 1: Verify credential via WaveSign
        ws_valid, ws_payload = self._engine.verify(credential_image, verify_data)
        if not ws_valid:
            return AuthResult(
                authenticated=False,
                level=level,
                agent_id=agent_id,
                credential_valid=False,
                reason="WaveSign credential verification failed — tampered or invalid",
            )

        # Step 2: Parse credential payload to get enrolled ABV
        parsed = WaveIDCredential.parse_verify_payload(ws_payload, self._authority_key)
        if parsed is None:
            return AuthResult(
                authenticated=False,
                level=level,
                agent_id=agent_id,
                credential_valid=False,
                reason="Credential payload parsing failed — invalid authority signature",
            )

        enrolled_abv, metadata = parsed

        # Check credential expiry
        if metadata.is_expired:
            return AuthResult(
                authenticated=False,
                level=level,
                agent_id=agent_id,
                credential_valid=False,
                reason="Credential has expired",
            )

        # Check agent ID matches
        if metadata.agent_id != agent_id:
            return AuthResult(
                authenticated=False,
                level=level,
                agent_id=agent_id,
                credential_valid=False,
                reason=f"Agent ID mismatch: credential={metadata.agent_id}, claimed={agent_id}",
            )

        # Cross-reference with authority registry if available
        if self._get_enrolled_abv is not None:
            registry_abv = self._get_enrolled_abv(agent_id)
            if registry_abv is None:
                return AuthResult(
                    authenticated=False,
                    level=level,
                    agent_id=agent_id,
                    credential_valid=True,
                    reason="Agent not found in enrollment registry",
                )
            if enrolled_abv != registry_abv:
                return AuthResult(
                    authenticated=False,
                    level=level,
                    agent_id=agent_id,
                    credential_valid=True,
                    reason="Credential ABV does not match registry — possible forgery",
                )

        # L1: Credential-only — done
        if level == AuthLevel.L1_CREDENTIAL:
            return AuthResult(
                authenticated=True,
                level=level,
                confidence=1.0,
                agent_id=agent_id,
                credential_valid=True,
                biometric_match=True,
                reason="Credential verified (L1)",
            )

        # L2+: Behavioral liveness check required
        if challenge is None or response is None:
            return AuthResult(
                authenticated=False,
                level=level,
                agent_id=agent_id,
                credential_valid=True,
                reason=f"Level {level.name} requires challenge-response, but none provided",
            )

        # Validate challenge freshness
        if challenge.is_expired:
            return AuthResult(
                authenticated=False,
                level=level,
                agent_id=agent_id,
                credential_valid=True,
                reason="Authentication challenge has expired",
            )

        if response.challenge_nonce != challenge.nonce:
            return AuthResult(
                authenticated=False,
                level=level,
                agent_id=agent_id,
                credential_valid=True,
                reason="Challenge nonce mismatch — possible replay attack",
            )

        # Extract fresh behavioral biometric from responses
        ordered_responses = []
        for prompt in challenge.prompts:
            resp_text = response.responses.get(prompt.prompt_id, "")
            if not resp_text:
                return AuthResult(
                    authenticated=False,
                    level=level,
                    agent_id=agent_id,
                    credential_valid=True,
                    reason=f"Missing response for prompt {prompt.prompt_id}",
                )
            ordered_responses.append(resp_text)

        fresh_profile = self._profiler.profile_from_responses(ordered_responses)

        # Re-extract ABV with fresh behavioral data and compare
        model = ModelMetadata(
            model_id=response.model_metadata.get("model", "unknown"),
            version=response.model_metadata.get("version", "unknown"),
        )
        context = SystemContext(system_prompt="")  # Context not available at auth time

        fresh_abv = self._extractor.extract(
            model=model,
            context=context,
            behavioral_profile=fresh_profile,
        )

        # Compute similarity between enrolled and fresh ABV
        similarity = enrolled_abv.similarity(fresh_abv)
        threshold = AUTH_THRESHOLDS[level]

        biometric_match = similarity >= threshold

        return AuthResult(
            authenticated=biometric_match,
            level=level,
            confidence=similarity,
            agent_id=agent_id,
            credential_valid=True,
            biometric_match=biometric_match,
            reason="Authentication successful" if biometric_match else f"Biometric similarity {similarity:.3f} below threshold {threshold:.3f}",
        )

    def verify_credential_only(
        self,
        credential_image: Image.Image,
        verify_data: bytes,
        agent_id: str,
    ) -> AuthResult:
        """Convenience method for L1 credential-only verification."""
        return self.verify(
            credential_image=credential_image,
            verify_data=verify_data,
            agent_id=agent_id,
            level=AuthLevel.L1_CREDENTIAL,
        )
