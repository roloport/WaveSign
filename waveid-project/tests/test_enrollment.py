"""Tests for the full enrollment and authentication flow."""

import pytest

from waveid.auth import AuthLevel
from waveid.authority import WaveIDAuthority
from waveid.challenge import ChallengeResponse
from waveid.verifier import WaveIDVerifier
from PIL import Image
from io import BytesIO


WAVESIGN_KEY = "test-authority-key"


def _make_responses(challenge, prefix="Agent response to"):
    """Generate mock agent responses for a challenge set."""
    return {
        p.prompt_id: f"{prefix} {p.prompt_id}: {p.text[:50]}... "
        f"This is a detailed answer with reasoning and explanation."
        for p in challenge.prompts
    }


@pytest.fixture
def authority():
    return WaveIDAuthority(wavesign_key=WAVESIGN_KEY)


class TestEnrollmentFlow:
    def test_full_enrollment(self, authority):
        # Step 1: Begin enrollment
        challenge = authority.begin_enrollment()
        assert len(challenge.prompts) == 16
        assert not challenge.is_expired

        # Step 2: Agent responds
        response = ChallengeResponse(
            challenge_nonce=challenge.nonce,
            responses=_make_responses(challenge),
            model_metadata={"model": "claude-opus-4-6", "version": "2026-03"},
        )

        # Step 3: Complete enrollment
        result = authority.complete_enrollment(
            challenge=challenge,
            response=response,
            agent_name="TestAgent",
            issuer="TestOrg",
            scope=["read", "write"],
        )

        assert result.agent_id.startswith("waveid:testagent:")
        assert result.credential_png[:4] == b"\x89PNG"
        assert len(result.verify_data) > 0
        assert authority.is_enrolled(result.agent_id)

    def test_enrollment_rejects_missing_responses(self, authority):
        challenge = authority.begin_enrollment()
        response = ChallengeResponse(
            challenge_nonce=challenge.nonce,
            responses={"R01": "only one response"},
            model_metadata={"model": "test", "version": "1"},
        )
        with pytest.raises(ValueError, match="Missing response"):
            authority.complete_enrollment(
                challenge=challenge,
                response=response,
                agent_name="Bad",
                issuer="Test",
            )

    def test_enrollment_rejects_reused_nonce(self, authority):
        challenge = authority.begin_enrollment()
        response = ChallengeResponse(
            challenge_nonce=challenge.nonce,
            responses=_make_responses(challenge),
            model_metadata={"model": "test", "version": "1"},
        )

        # First enrollment succeeds
        authority.complete_enrollment(
            challenge=challenge, response=response,
            agent_name="A", issuer="T",
        )

        # Second attempt with same nonce fails
        with pytest.raises(ValueError, match="Unknown"):
            authority.complete_enrollment(
                challenge=challenge, response=response,
                agent_name="B", issuer="T",
            )

    def test_revoke(self, authority):
        challenge = authority.begin_enrollment()
        response = ChallengeResponse(
            challenge_nonce=challenge.nonce,
            responses=_make_responses(challenge),
            model_metadata={"model": "test", "version": "1"},
        )
        result = authority.complete_enrollment(
            challenge=challenge, response=response,
            agent_name="Revokable", issuer="T",
        )
        assert authority.is_enrolled(result.agent_id)
        assert authority.revoke(result.agent_id)
        assert not authority.is_enrolled(result.agent_id)


class TestL1Verification:
    def test_credential_only_verification(self, authority):
        # Enroll agent
        challenge = authority.begin_enrollment()
        response = ChallengeResponse(
            challenge_nonce=challenge.nonce,
            responses=_make_responses(challenge),
            model_metadata={"model": "claude-opus-4-6", "version": "2026-03"},
        )
        enrollment = authority.complete_enrollment(
            challenge=challenge, response=response,
            agent_name="VerifyMe", issuer="TestOrg", scope=["read"],
        )

        # Verify credential (L1)
        verifier = WaveIDVerifier(
            wavesign_key=WAVESIGN_KEY,
            get_enrolled_abv=authority.get_enrolled_abv,
        )
        result = verifier.verify_credential_only(
            credential_image=enrollment.credential.image,
            verify_data=enrollment.verify_data,
            agent_id=enrollment.agent_id,
        )

        assert result.authenticated
        assert result.level == AuthLevel.L1_CREDENTIAL
        assert result.credential_valid
