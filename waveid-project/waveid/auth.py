"""Authentication levels and result types for WaveID."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class AuthLevel(IntEnum):
    """Tiered authentication levels.

    Higher levels require more biometric factors and provide stronger assurance.
    """

    L1_CREDENTIAL = 1       # Credential-only: valid WaveID credential
    L2_LIVENESS = 2         # Credential + 3 behavioral challenges
    L3_FULL_BIOMETRIC = 3   # Credential + 8 challenges + inference trace
    L4_MULTI_AGENT = 4      # L3 + co-signing by N other verified agents


# Similarity thresholds for each auth level
AUTH_THRESHOLDS: dict[AuthLevel, float] = {
    AuthLevel.L1_CREDENTIAL: 0.0,       # No behavioral check
    AuthLevel.L2_LIVENESS: 0.85,        # Moderate confidence
    AuthLevel.L3_FULL_BIOMETRIC: 0.92,  # High confidence
    AuthLevel.L4_MULTI_AGENT: 0.95,     # Very high confidence
}


@dataclass
class AuthResult:
    """Result of an authentication attempt."""

    authenticated: bool
    level: AuthLevel
    confidence: float = 0.0
    agent_id: str = ""
    credential_valid: bool = False
    biometric_match: bool = False
    reason: str = ""
    co_signers: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.authenticated

    def summary(self) -> str:
        status = "PASS" if self.authenticated else "FAIL"
        return (
            f"[{status}] Level={self.level.name} "
            f"confidence={self.confidence:.3f} "
            f"agent={self.agent_id} "
            f"reason={self.reason}"
        )
