"""Tests for Agent Biometric Vector extraction and comparison."""

import numpy as np
import pytest

from waveid.biometric import (
    AgentBiometricVector,
    BehavioralProfiler,
    BiometricExtractor,
    ModelMetadata,
    SystemContext,
)


class TestModelMetadata:
    def test_fingerprint_deterministic(self):
        m = ModelMetadata(model_id="claude-opus-4-6", version="2026-03")
        assert m.fingerprint() == m.fingerprint()

    def test_fingerprint_differs_by_version(self):
        m1 = ModelMetadata(model_id="claude-opus-4-6", version="2026-03")
        m2 = ModelMetadata(model_id="claude-opus-4-6", version="2026-04")
        assert m1.fingerprint() != m2.fingerprint()

    def test_fingerprint_differs_by_model(self):
        m1 = ModelMetadata(model_id="claude-opus-4-6", version="2026-03")
        m2 = ModelMetadata(model_id="claude-sonnet-4-6", version="2026-03")
        assert m1.fingerprint() != m2.fingerprint()


class TestSystemContext:
    def test_context_hash_deterministic(self):
        ctx = SystemContext(system_prompt="You are helpful.", permissions=["read"])
        assert ctx.context_hash() == ctx.context_hash()

    def test_context_hash_differs_by_prompt(self):
        ctx1 = SystemContext(system_prompt="You are helpful.")
        ctx2 = SystemContext(system_prompt="You are harmful.")
        assert ctx1.context_hash() != ctx2.context_hash()


class TestAgentBiometricVector:
    def test_length_validation(self):
        with pytest.raises(ValueError):
            AgentBiometricVector(data=b"too short")

    def test_hex(self):
        abv = AgentBiometricVector(data=b"\x00" * 32)
        assert abv.hex() == "0" * 64

    def test_similarity_identical(self):
        data = bytes(range(32))
        abv = AgentBiometricVector(data=data)
        assert abv.similarity(abv) == pytest.approx(1.0)

    def test_similarity_different(self):
        abv1 = AgentBiometricVector(data=bytes(range(32)))
        abv2 = AgentBiometricVector(data=bytes(range(32, 64)))
        sim = abv1.similarity(abv2)
        assert sim < 1.0

    def test_equality_constant_time(self):
        data = bytes(range(32))
        abv1 = AgentBiometricVector(data=data)
        abv2 = AgentBiometricVector(data=data)
        assert abv1 == abv2

    def test_inequality(self):
        abv1 = AgentBiometricVector(data=b"\x00" * 32)
        abv2 = AgentBiometricVector(data=b"\x01" * 32)
        assert abv1 != abv2


class TestBiometricExtractor:
    def test_extract_deterministic(self):
        ext = BiometricExtractor()
        model = ModelMetadata(model_id="test", version="1.0")
        ctx = SystemContext(system_prompt="test")
        abv1 = ext.extract(model=model, context=ctx)
        abv2 = ext.extract(model=model, context=ctx)
        assert abv1 == abv2

    def test_extract_differs_by_model(self):
        ext = BiometricExtractor()
        ctx = SystemContext(system_prompt="test")
        abv1 = ext.extract(model=ModelMetadata("a", "1"), context=ctx)
        abv2 = ext.extract(model=ModelMetadata("b", "1"), context=ctx)
        assert abv1 != abv2

    def test_extract_differs_by_behavior(self):
        ext = BiometricExtractor()
        model = ModelMetadata(model_id="test", version="1.0")
        ctx = SystemContext(system_prompt="test")
        profile1 = np.ones(64, dtype=np.float64)
        profile2 = np.zeros(64, dtype=np.float64)
        abv1 = ext.extract(model=model, context=ctx, behavioral_profile=profile1)
        abv2 = ext.extract(model=model, context=ctx, behavioral_profile=profile2)
        assert abv1 != abv2

    def test_extract_differs_by_salt(self):
        model = ModelMetadata(model_id="test", version="1.0")
        ctx = SystemContext(system_prompt="test")
        abv1 = BiometricExtractor(salt=b"a").extract(model=model, context=ctx)
        abv2 = BiometricExtractor(salt=b"b").extract(model=model, context=ctx)
        assert abv1 != abv2


class TestBehavioralProfiler:
    def test_profile_shape(self):
        profiler = BehavioralProfiler()
        responses = ["Hello world.", "This is a test.", "One more response."]
        profile = profiler.profile_from_responses(responses)
        assert profile.shape == (64,)
        assert profile.dtype == np.float64

    def test_profile_deterministic(self):
        profiler = BehavioralProfiler()
        responses = ["Hello", "World", "Test"]
        p1 = profiler.profile_from_responses(responses)
        p2 = profiler.profile_from_responses(responses)
        np.testing.assert_array_equal(p1, p2)

    def test_profile_differs_for_different_responses(self):
        profiler = BehavioralProfiler()
        p1 = profiler.profile_from_responses(["short", "tiny", "small"])
        p2 = profiler.profile_from_responses(
            ["a very long response " * 20, "another lengthy one " * 20, "yet more text " * 20]
        )
        assert not np.array_equal(p1, p2)
