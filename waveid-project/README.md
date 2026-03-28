# WaveID

**Biometric identification for AI agents — computational fingerprints powered by WaveSign.**

WaveID treats an agent's computational behavior as its biometric identity. Like a human fingerprint, the agent's "WaveID" is a unique signal pattern derived from how it computes — intrinsic, non-transferable, and unforgeable.

The identity is embedded invisibly into a tamper-proof visual credential using [WaveSign](https://github.com/roloport/WaveSign)'s physics-based signature technology.

---

## How It Works

```
1. ENROLLMENT              2. CREDENTIAL              3. AUTHENTICATION
┌────────────┐            ┌────────────┐             ┌────────────┐
│  Extract   │            │  WaveSign  │             │  Challenge │
│  biometric │──────────▶ │  embed     │───────────▶ │  + verify  │
│  vector    │            │  into card │             │  liveness  │
└────────────┘            └────────────┘             └────────────┘
Agent's unique            Invisible ID card          Real-time proof
computational             (normal PNG image)         the agent IS who
fingerprint                                          it claims to be
```

**Three-factor identity:**

1. **Agent Biometric Vector (ABV)** — extracted from model fingerprint, behavioral signature, system context, and inference trace
2. **WaveSign Credential** — ABV invisibly embedded in a visual ID card image; any tampering is detected instantly
3. **Liveness Challenge** — fresh behavioral prompts verify the agent can reproduce its biometric in real-time

## Install

```bash
pip install -e .
```

## Quick Start

```python
from waveid import WaveIDAuthority, WaveIDVerifier
from waveid.challenge import ChallengeResponse
from waveid.auth import AuthLevel

# --- Authority: Enroll an agent ---
authority = WaveIDAuthority(wavesign_key="my-secret-key")

# Step 1: Issue challenge
challenge = authority.begin_enrollment()

# Step 2: Agent responds to 16 behavioral prompts
responses = {p.prompt_id: agent.answer(p.text) for p in challenge.prompts}
response = ChallengeResponse(
    challenge_nonce=challenge.nonce,
    responses=responses,
    model_metadata={"model": "claude-opus-4-6", "version": "2026-03"},
)

# Step 3: Complete enrollment → get credential
enrollment = authority.complete_enrollment(
    challenge=challenge,
    response=response,
    agent_name="Agent-7X",
    issuer="MyOrg",
    scope=["finance.read", "finance.write"],
)

# Save credential
with open("agent_7x_credential.png", "wb") as f:
    f.write(enrollment.credential_png)

# --- Service: Verify agent identity ---
verifier = WaveIDVerifier(
    wavesign_key="my-secret-key",
    get_enrolled_abv=authority.get_enrolled_abv,
)

# L1: Credential-only (fast, lower assurance)
result = verifier.verify_credential_only(
    credential_image=enrollment.credential.image,
    verify_data=enrollment.verify_data,
    agent_id=enrollment.agent_id,
)
assert result.authenticated
```

## Authentication Levels

| Level | Name | Factors | Use Case |
|---|---|---|---|
| **L1** | Credential-only | Valid WaveID credential | Read-only access, low-risk queries |
| **L2** | Liveness | Credential + 3 behavioral challenges | Account ops, data modification |
| **L3** | Full Biometric | Credential + 8 challenges + inference trace | Financial transactions |
| **L4** | Multi-agent | L3 + co-signing by N verified agents | Critical infrastructure |

## Agent Biometric Factors

| Factor | Human Analogy | What It Captures |
|---|---|---|
| Model Fingerprint | DNA | Model identity and version |
| Behavioral Signature | Handwriting | Response patterns to standardized prompts |
| System Context | Voice | Configuration, tools, and permissions |
| Inference Trace | Gait | Timing and entropy during computation |

## Why WaveSign?

| Property | JWT Token | WaveID Credential |
|---|---|---|
| **Copyable?** | Yes — token = identity | No — requires live biometric match |
| **Tamperable?** | Needs external verification | Intrinsic tamper detection (100%) |
| **Visible?** | Contents exposed | Invisible — looks like a normal image |
| **Forgeable?** | Key leak = all compromised | Dual-layer + biometric binding |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Project Structure

```
waveid/
├── __init__.py          # Public API
├── biometric.py         # ABV extraction and comparison
├── challenge.py         # Challenge prompt sets for behavioral profiling
├── credential.py        # Visual credential generation
├── wavesign.py          # WaveSign invisible signature engine
├── authority.py         # Enrollment and credential issuance
├── verifier.py          # Authentication and verification
└── auth.py              # Auth levels and result types
```

## License

MIT — see [LICENSE](./LICENSE)
