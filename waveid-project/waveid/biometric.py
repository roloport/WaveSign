"""Agent Biometric Vector (ABV) extraction and comparison.

The ABV is the agent's computational fingerprint — a fixed-length vector
derived from model identity, behavioral signature, system context, and
inference trace. It serves the same role as a human fingerprint: intrinsic,
unique, and hard to forge.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ABV is 256 bits = 32 bytes
ABV_LENGTH = 32

# Behavioral signature is a 64-dim statistical profile
BEHAVIORAL_DIM = 64


@dataclass(frozen=True)
class ModelMetadata:
    """Immutable model identity descriptor."""

    model_id: str
    version: str
    architecture: str = ""

    def fingerprint(self) -> bytes:
        """SHA-256 hash of model identity fields."""
        payload = f"{self.model_id}|{self.version}|{self.architecture}"
        return hashlib.sha256(payload.encode()).digest()


@dataclass(frozen=True)
class SystemContext:
    """Agent's system configuration that shapes its behavior."""

    system_prompt: str
    tool_config: dict[str, Any] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)

    def context_hash(self) -> bytes:
        """SHA-256 hash of the system context."""
        prompt_bytes = self.system_prompt.encode()
        tool_bytes = str(sorted(self.tool_config.items())).encode()
        perm_bytes = ",".join(sorted(self.permissions)).encode()
        combined = prompt_bytes + b"|" + tool_bytes + b"|" + perm_bytes
        return hashlib.sha256(combined).digest()


@dataclass(frozen=True)
class AgentBiometricVector:
    """The agent's computational fingerprint.

    A 32-byte vector that uniquely identifies an agent based on its
    model, behavior, context, and inference characteristics.
    """

    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != ABV_LENGTH:
            raise ValueError(f"ABV must be {ABV_LENGTH} bytes, got {len(self.data)}")

    def hex(self) -> str:
        return self.data.hex()

    def similarity(self, other: AgentBiometricVector) -> float:
        """Compute cosine similarity between two ABVs.

        Returns a value between -1.0 and 1.0. Identical agents produce 1.0.
        Different agents produce values near 0.0.
        """
        a = np.frombuffer(self.data, dtype=np.uint8).astype(np.float64)
        b = np.frombuffer(other.data, dtype=np.uint8).astype(np.float64)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentBiometricVector):
            return NotImplemented
        # Constant-time comparison to prevent timing attacks
        return hmac_compare(self.data, other.data)


def hmac_compare(a: bytes, b: bytes) -> bool:
    """Constant-time byte comparison."""
    import hmac

    return hmac.compare_digest(a, b)


class BiometricExtractor:
    """Extracts Agent Biometric Vectors from agent characteristics.

    The extractor combines four biometric factors into a single ABV:
    1. Model fingerprint (DNA) — identity of the model itself
    2. Behavioral signature (handwriting) — statistical response patterns
    3. System context hash (voice) — configuration fingerprint
    4. Inference trace (gait) — computational timing/entropy patterns
    """

    # Domain separation tags to prevent cross-factor collisions
    _DOMAIN_MODEL = b"waveid.model.v1"
    _DOMAIN_BEHAVIOR = b"waveid.behavior.v1"
    _DOMAIN_CONTEXT = b"waveid.context.v1"
    _DOMAIN_INFERENCE = b"waveid.inference.v1"
    _DOMAIN_FINAL = b"waveid.abv.v1"

    def __init__(self, salt: bytes = b"") -> None:
        """Initialize extractor with optional salt for additional entropy."""
        self._salt = salt

    def extract(
        self,
        model: ModelMetadata,
        context: SystemContext,
        behavioral_profile: np.ndarray | None = None,
        inference_trace: np.ndarray | None = None,
    ) -> AgentBiometricVector:
        """Extract a complete ABV from all biometric factors.

        Args:
            model: Model identity metadata.
            context: System configuration.
            behavioral_profile: Statistical profile from challenge responses.
                Shape: (BEHAVIORAL_DIM,) float64 array. If None, uses zeros.
            inference_trace: Entropy/timing profile from inference.
                Shape: (BEHAVIORAL_DIM,) float64 array. If None, uses zeros.

        Returns:
            A 32-byte AgentBiometricVector.
        """
        # Factor 1: Model fingerprint
        model_fp = self._domain_hash(self._DOMAIN_MODEL, model.fingerprint())

        # Factor 2: Behavioral signature
        if behavioral_profile is not None:
            behavior_bytes = behavioral_profile.astype(np.float64).tobytes()
        else:
            behavior_bytes = np.zeros(BEHAVIORAL_DIM, dtype=np.float64).tobytes()
        behavior_fp = self._domain_hash(self._DOMAIN_BEHAVIOR, behavior_bytes)

        # Factor 3: System context
        context_fp = self._domain_hash(self._DOMAIN_CONTEXT, context.context_hash())

        # Factor 4: Inference trace
        if inference_trace is not None:
            trace_bytes = inference_trace.astype(np.float64).tobytes()
        else:
            trace_bytes = np.zeros(BEHAVIORAL_DIM, dtype=np.float64).tobytes()
        trace_fp = self._domain_hash(self._DOMAIN_INFERENCE, trace_bytes)

        # Combine all factors with domain separation
        combined = model_fp + behavior_fp + context_fp + trace_fp
        abv_bytes = self._domain_hash(self._DOMAIN_FINAL, combined)

        return AgentBiometricVector(data=abv_bytes)

    def _domain_hash(self, domain: bytes, data: bytes) -> bytes:
        """Domain-separated SHA-256 hash."""
        h = hashlib.sha256()
        h.update(domain)
        h.update(struct.pack(">I", len(domain)))
        h.update(self._salt)
        h.update(data)
        return h.digest()


class BehavioralProfiler:
    """Computes behavioral fingerprints from challenge-response pairs.

    Given an agent's responses to a standardized challenge set, this extracts
    a compact statistical profile that characterizes the agent's behavior.
    """

    def profile_from_responses(self, responses: list[str]) -> np.ndarray:
        """Extract a behavioral profile from challenge responses.

        The profile captures:
        - Response length distribution (moments)
        - Character frequency distribution
        - Vocabulary richness metrics
        - Structural patterns (punctuation, whitespace ratios)

        Returns:
            A (BEHAVIORAL_DIM,) float64 array.
        """
        features: list[float] = []

        # Response length statistics
        lengths = [len(r) for r in responses]
        features.extend(self._moments(lengths))  # 4 values

        # Word count statistics
        word_counts = [len(r.split()) for r in responses]
        features.extend(self._moments(word_counts))  # 4 values

        # Average word length per response
        avg_word_lens = []
        for r in responses:
            words = r.split()
            avg_word_lens.append(np.mean([len(w) for w in words]) if words else 0.0)
        features.extend(self._moments(avg_word_lens))  # 4 values

        # Character class ratios (computed per response, then aggregated)
        alpha_ratios = []
        digit_ratios = []
        punct_ratios = []
        upper_ratios = []
        for r in responses:
            n = max(len(r), 1)
            alpha_ratios.append(sum(c.isalpha() for c in r) / n)
            digit_ratios.append(sum(c.isdigit() for c in r) / n)
            punct_ratios.append(sum(not c.isalnum() and not c.isspace() for c in r) / n)
            upper_ratios.append(sum(c.isupper() for c in r) / n)
        features.extend(self._moments(alpha_ratios))   # 4 values
        features.extend(self._moments(digit_ratios))    # 4 values
        features.extend(self._moments(punct_ratios))    # 4 values
        features.extend(self._moments(upper_ratios))    # 4 values

        # Sentence count statistics
        sentence_counts = []
        for r in responses:
            count = sum(1 for c in r if c in ".!?")
            sentence_counts.append(max(count, 1))
        features.extend(self._moments(sentence_counts))  # 4 values

        # Unique word ratio (vocabulary richness)
        vocab_ratios = []
        for r in responses:
            words = r.lower().split()
            vocab_ratios.append(len(set(words)) / max(len(words), 1))
        features.extend(self._moments(vocab_ratios))  # 4 values

        # Newline density
        newline_ratios = [r.count("\n") / max(len(r), 1) for r in responses]
        features.extend(self._moments(newline_ratios))  # 4 values

        # Pad or truncate to BEHAVIORAL_DIM
        profile = np.zeros(BEHAVIORAL_DIM, dtype=np.float64)
        n = min(len(features), BEHAVIORAL_DIM)
        profile[:n] = features[:n]

        # Fill remaining dimensions with hash-derived features for stability
        if n < BEHAVIORAL_DIM:
            concat = "||".join(responses).encode()
            h = hashlib.sha256(concat).digest()
            remaining = BEHAVIORAL_DIM - n
            hash_features = np.frombuffer(h, dtype=np.uint8)[:remaining].astype(np.float64) / 255.0
            profile[n : n + len(hash_features)] = hash_features

        return profile

    @staticmethod
    def _moments(values: list[float]) -> list[float]:
        """Compute mean, std, skewness proxy, and kurtosis proxy."""
        arr = np.array(values, dtype=np.float64)
        if len(arr) == 0:
            return [0.0, 0.0, 0.0, 0.0]
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        if std == 0:
            return [mean, 0.0, 0.0, 0.0]
        centered = arr - mean
        skew = float(np.mean(centered**3) / std**3)
        kurt = float(np.mean(centered**4) / std**4 - 3.0)
        return [mean, std, skew, kurt]
