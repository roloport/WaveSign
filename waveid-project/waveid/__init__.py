"""WaveID — Agent Biometric Identification System.

Computational fingerprints for AI agents, powered by WaveSign.
"""

from waveid.biometric import AgentBiometricVector, BiometricExtractor
from waveid.authority import WaveIDAuthority
from waveid.verifier import WaveIDVerifier
from waveid.credential import WaveIDCredential
from waveid.challenge import ChallengeSet, ChallengeResponse
from waveid.auth import AuthLevel, AuthResult

__version__ = "0.1.0"

__all__ = [
    "AgentBiometricVector",
    "BiometricExtractor",
    "WaveIDAuthority",
    "WaveIDVerifier",
    "WaveIDCredential",
    "ChallengeSet",
    "ChallengeResponse",
    "AuthLevel",
    "AuthResult",
]
