"""Tests for WaveID credential generation and verification."""

import time

import pytest

from waveid.biometric import AgentBiometricVector
from waveid.credential import CredentialMetadata, WaveIDCredential


@pytest.fixture
def sample_abv():
    return AgentBiometricVector(data=bytes(range(32)))


@pytest.fixture
def sample_metadata():
    return CredentialMetadata(
        agent_name="TestAgent",
        agent_id="waveid:testagent:abc123",
        issuer="TestOrg",
        scope=["read", "write"],
    )


@pytest.fixture
def authority_key():
    return b"test-authority-key-32-bytes!!!!!"


class TestCredentialMetadata:
    def test_default_expiry(self):
        meta = CredentialMetadata(
            agent_name="A", agent_id="id", issuer="I", scope=[]
        )
        assert meta.expires_at > meta.issued_at
        assert meta.expires_at - meta.issued_at == pytest.approx(90 * 86400, abs=1)

    def test_not_expired(self):
        meta = CredentialMetadata(
            agent_name="A",
            agent_id="id",
            issuer="I",
            scope=[],
            expires_at=time.time() + 3600,
        )
        assert not meta.is_expired

    def test_expired(self):
        meta = CredentialMetadata(
            agent_name="A",
            agent_id="id",
            issuer="I",
            scope=[],
            issued_at=time.time() - 7200,
            expires_at=time.time() - 3600,
        )
        assert meta.is_expired

    def test_round_trip_bytes(self, sample_metadata):
        data = sample_metadata.to_bytes()
        assert b"TestAgent" in data
        assert b"TestOrg" in data


class TestWaveIDCredential:
    def test_generate_card_image(self, sample_abv, sample_metadata):
        cred = WaveIDCredential(metadata=sample_metadata, abv=sample_abv)
        img = cred.generate_card_image()
        assert img.size == (600, 380)
        assert img.mode == "RGB"

    def test_to_png_bytes(self, sample_abv, sample_metadata):
        cred = WaveIDCredential(metadata=sample_metadata, abv=sample_abv)
        png = cred.to_png_bytes()
        assert png[:4] == b"\x89PNG"
        assert len(png) > 100

    def test_verify_payload_round_trip(self, sample_abv, sample_metadata, authority_key):
        cred = WaveIDCredential(metadata=sample_metadata, abv=sample_abv)
        payload = cred.build_verify_payload(authority_key)

        result = WaveIDCredential.parse_verify_payload(payload, authority_key)
        assert result is not None
        abv, meta = result
        assert abv == sample_abv
        assert meta.agent_name == "TestAgent"
        assert meta.agent_id == "waveid:testagent:abc123"

    def test_verify_payload_wrong_key(self, sample_abv, sample_metadata, authority_key):
        cred = WaveIDCredential(metadata=sample_metadata, abv=sample_abv)
        payload = cred.build_verify_payload(authority_key)

        result = WaveIDCredential.parse_verify_payload(payload, b"wrong-key-32-bytes!!!!!!!!!!!!!")
        assert result is None

    def test_verify_payload_tampered(self, sample_abv, sample_metadata, authority_key):
        cred = WaveIDCredential(metadata=sample_metadata, abv=sample_abv)
        payload = bytearray(cred.build_verify_payload(authority_key))
        payload[10] ^= 0xFF  # Flip a byte
        result = WaveIDCredential.parse_verify_payload(bytes(payload), authority_key)
        assert result is None
