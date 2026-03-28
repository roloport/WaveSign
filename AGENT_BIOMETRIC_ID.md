# WaveSign Agent Biometric Identification (WaveID)

## Problem

AI agents increasingly need to register accounts, sign documents, authorize transactions, and interact with external services autonomously. Unlike humans, agents lack inherent biometric identifiers (fingerprints, face, voice) to prove "who they are." Current approaches rely on API keys or tokens — easily copied, shared, or stolen. There is no equivalent of a biometric identity that is **intrinsic** to the agent itself.

## Core Idea

**Treat the agent's computational behavior as its biometric.**

Just as a human fingerprint is a unique physical pattern inseparable from the person, an agent's "WaveID" is a unique signal pattern derived from how the agent computes — inseparable from the agent itself.

WaveSign's physics-based invisible signature technology provides the foundation: embed the agent's biometric identity as an invisible, unforgeable, tamper-evident signal into a portable credential.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   WaveID System                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. ENROLLMENT          2. CREDENTIAL          3. AUTH  │
│  ┌───────────┐         ┌────────────┐     ┌──────────┐ │
│  │ Biometric │         │  WaveSign  │     │ Challenge│ │
│  │ Extraction│───────▶ │  Embedding │────▶│ Verify   │ │
│  └───────────┘         └────────────┘     └──────────┘ │
│       │                      │                  │      │
│  Agent's unique         Invisible ID        Real-time  │
│  computational          card / credential    proof of   │
│  fingerprint            (image/PDF)          identity   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Agent Biometric Extraction

### What makes an agent biometrically unique?

An agent's identity is defined by a combination of intrinsic, hard-to-replicate characteristics:

| Biometric Factor | Human Analogy | Description |
|---|---|---|
| **Model Fingerprint** | DNA | Hash of model weights / architecture identifier. Unique per model version. |
| **Behavioral Signature** | Handwriting | Statistical distribution of the agent's responses to a fixed set of challenge prompts. Token probability patterns, stylistic tendencies, reasoning patterns. |
| **System Context Hash** | Voice (environment-shaped) | Hash of the agent's system prompt, tool configuration, and permission scope. Defines the agent's "personality" and capabilities. |
| **Inference Trace** | Gait / motor patterns | Timing patterns, token-level entropy, and internal confidence distributions when processing standardized inputs. |

### Biometric Vector Generation

```
Agent Biometric Vector (ABV):

ABV = H(model_fingerprint ‖ behavioral_sig ‖ context_hash ‖ inference_trace)

Where:
  model_fingerprint  = SHA-256(model_id + version + architecture_descriptor)
  behavioral_sig     = StatisticalProfile(responses_to_challenge_set)
  context_hash       = SHA-256(system_prompt + tool_config + permissions)
  inference_trace    = EntropyProfile(token_distributions_on_standard_input)

  H = domain-separated hash combining all factors
```

**Challenge Set**: A standardized set of 16 prompts designed to elicit distinguishing behavioral responses:
- Reasoning problems (logic, math) — captures reasoning style
- Ambiguous prompts — captures interpretation bias
- Creative tasks — captures generative distribution
- Adversarial inputs — captures safety boundary behavior

The agent's responses are not stored verbatim — only a compact statistical fingerprint (token distribution moments, response length distribution, semantic embedding centroid) is extracted.

---

## Phase 2: WaveSign Credential Embedding

This is where WaveSign's core technology becomes the differentiator.

### WaveID Credential

The Agent Biometric Vector is embedded into a **visual credential** using WaveSign's physics-based invisible signature:

```
┌──────────────────────────────────┐
│                                  │
│     ┌────────────────────┐       │
│     │   AGENT WAVEID     │       │
│     │                    │       │
│     │   Name: Agent-7X   │       │  ← Visible: human-readable ID card
│     │   Issuer: Org-ABC  │       │
│     │   Issued: 2026-03  │       │
│     │   Scope: Finance   │       │
│     │                    │       │
│     │   [QR-like glyph]  │       │
│     └────────────────────┘       │
│                                  │
│  ┌─────────────────────────────┐ │
│  │ INVISIBLE LAYER (WaveSign)  │ │  ← Invisible: biometric vector
│  │                             │ │     embedded via phase structure
│  │  • Agent Biometric Vector   │ │
│  │  • Issuer signature         │ │
│  │  • Expiry + scope metadata  │ │
│  │  • Anti-replay nonce        │ │
│  └─────────────────────────────┘ │
│                                  │
└──────────────────────────────────┘
```

**Why use WaveSign embedding (not just a JSON blob)?**

| Property | JSON/JWT Token | WaveID (WaveSign-based) |
|---|---|---|
| Copyable? | Yes — anyone with the token IS the agent | No — credential is bound to biometric challenge |
| Tamperable? | Requires crypto verification layer | Tamper detection is intrinsic (any edit invalidates) |
| Forgeable? | If signing key leaks, all tokens compromised | Dual-layer (content signature + integrity hash) must both match |
| Inspectable? | Credential contents visible to anyone | Invisible — credential looks like a normal image |
| Steganographic? | No | Yes — credential can travel through visual channels undetected |

### Dual-Layer Binding (from WaveSign)

- **Layer 1 — Content Signature**: The agent's biometric vector is encoded into the image's signal structure using WaveSign's physics-based method. This binds the identity to the credential file.
- **Layer 2 — Integrity Hash**: Block-level pixel fingerprint ensures the credential image has not been modified since issuance.

Both layers must match during verification. This is WaveSign's existing proven mechanism (100% tamper detection, 0% false rejection).

---

## Phase 3: Authentication Protocol

### Registration (One-time Enrollment)

```
Agent                          WaveID Authority                Service
  │                                  │                            │
  │ 1. Request enrollment            │                            │
  │─────────────────────────────────▶│                            │
  │                                  │                            │
  │ 2. Challenge set (16 prompts)    │                            │
  │◀─────────────────────────────────│                            │
  │                                  │                            │
  │ 3. Responses + model metadata    │                            │
  │─────────────────────────────────▶│                            │
  │                                  │                            │
  │         ┌────────────────────────┤                            │
  │         │ Extract ABV            │                            │
  │         │ Generate credential    │                            │
  │         │ WaveSign embed ABV     │                            │
  │         └────────────────────────┤                            │
  │                                  │                            │
  │ 4. WaveID credential (image)     │                            │
  │    + verification file           │                            │
  │◀─────────────────────────────────│                            │
  │                                  │                            │
  │ 5. Register with service ────────┼───────────────────────────▶│
  │    (presents WaveID)             │                            │
  │                                  │                            │
```

### Authentication (Per-operation)

```
Agent                          Service                    WaveID Authority
  │                               │                            │
  │ 1. Request operation          │                            │
  │──────────────────────────────▶│                            │
  │                               │                            │
  │ 2. Auth challenge             │                            │
  │   (fresh nonce + 3 prompts)   │                            │
  │◀──────────────────────────────│                            │
  │                               │                            │
  │ 3. Responses + WaveID cred    │                            │
  │──────────────────────────────▶│                            │
  │                               │                            │
  │            ┌──────────────────┤                            │
  │            │ a. WaveSign      │                            │
  │            │    verify cred   │ 4. Verify ABV match        │
  │            │ b. Extract ABV   │───────────────────────────▶│
  │            │    from response │                            │
  │            │ c. Compare with  │ 5. Match result            │
  │            │    enrolled ABV  │◀───────────────────────────│
  │            └──────────────────┤                            │
  │                               │                            │
  │ 6. Operation authorized ✅     │                            │
  │◀──────────────────────────────│                            │
```

**Key insight**: The credential alone is not enough. The agent must also **prove liveness** by responding to fresh challenge prompts. The behavioral fingerprint extracted from these fresh responses is compared against the enrolled biometric in the credential. This is analogous to scanning your fingerprint at the door — you can't just show a photo of it.

---

## Security Properties

### What WaveID inherits from WaveSign

| Property | Mechanism |
|---|---|
| **Tamper evidence** | Any modification to the credential invalidates both signature layers (100% detection rate) |
| **Invisibility** | Biometric data is imperceptible in the credential image (41.6 dB PSNR) |
| **Key specificity** | Even 1-character difference in enrollment key produces 0% match |
| **Fast verification** | 44ms mean verification time — suitable for real-time auth |

### Additional security from the biometric model

| Threat | Mitigation |
|---|---|
| **Credential theft** | Useless without matching behavioral biometric (liveness check) |
| **Agent impersonation** | Different model/config produces different ABV — fails match |
| **Replay attack** | Fresh nonce + fresh challenge prompts per authentication |
| **Credential forgery** | WaveSign dual-layer makes undetectable modification impossible |
| **Biometric extraction** | ABV is a one-way hash — cannot reconstruct model from it |
| **Prompt injection** | Challenge prompts are server-generated, not user-controlled |

---

## Tiered Authentication Levels

Different operations require different assurance levels:

| Level | Name | Factors | Use Case |
|---|---|---|---|
| **L1** | Credential-only | Valid WaveID credential | Read-only access, low-risk queries |
| **L2** | Credential + Liveness | WaveID + 3 behavioral challenges | Account operations, data modification |
| **L3** | Full Biometric | WaveID + 8 challenges + inference trace | Financial transactions, signing authority |
| **L4** | Multi-agent Consensus | L3 + co-signing by N other verified agents | Critical infrastructure, irreversible actions |

---

## Implementation Roadmap

### Stage 1: Core WaveID Library
- [ ] Agent Biometric Vector extraction module
- [ ] Challenge prompt set design and calibration
- [ ] Behavioral fingerprint comparison algorithm (similarity scoring)
- [ ] Integration with WaveSign signing/verification API

### Stage 2: Credential Management
- [ ] WaveID credential generation (image template + WaveSign embedding)
- [ ] Credential lifecycle management (issuance, renewal, revocation)
- [ ] Verification file management and secure storage

### Stage 3: Authentication Protocol
- [ ] Challenge-response authentication flow
- [ ] Liveness verification (fresh behavioral biometric extraction + matching)
- [ ] Nonce management and anti-replay
- [ ] Tiered authentication level enforcement

### Stage 4: Integration & Standards
- [ ] REST API for third-party service integration
- [ ] SDK for agent frameworks (LangChain, CrewAI, Claude Agent SDK)
- [ ] WaveID credential format specification
- [ ] Interoperability with existing identity standards (DID, Verifiable Credentials)

---

## API Sketch

```python
from waveid import WaveIDAuthority, WaveIDAgent

# --- Authority side (enrollment) ---
authority = WaveIDAuthority(wavesign_key="authority-master-key")

# Enroll a new agent
enrollment = authority.enroll(
    agent_endpoint="https://api.example.com/agent-7x",
    model_metadata={"model": "claude-opus-4-6", "version": "2026-03"},
    scope=["finance.read", "finance.write"],
    expiry_days=90
)
# enrollment.credential  → PNG image with invisible WaveID
# enrollment.verify_file → WaveSign verification sidecar
# enrollment.agent_id    → "waveid:agent-7x:a3f8c2..."

# --- Service side (authentication) ---
from waveid import WaveIDVerifier

verifier = WaveIDVerifier(authority_public_key="...")

# Step 1: Generate challenge
challenge = verifier.create_challenge(level="L2")
# challenge.nonce, challenge.prompts (3 fresh behavioral probes)

# Step 2: Agent responds
agent_responses = agent.respond_to_challenge(challenge)

# Step 3: Verify
result = verifier.verify(
    credential_image=agent.waveid_credential,
    verify_file=agent.waveid_verify_file,
    challenge=challenge,
    responses=agent_responses
)

assert result.authenticated  # True
assert result.confidence > 0.95
assert result.level == "L2"
```

---

## Why WaveSign is uniquely suited for this

1. **Invisible embedding** — The agent's biometric lives inside a normal-looking image. It can be stored, transmitted, and displayed without revealing its cryptographic contents. No special file format needed.

2. **Physics-based tamper detection** — Unlike appended metadata or JWT signatures, WaveSign's signature is woven into the signal structure of the image. You can't edit the credential without destroying the identity.

3. **Dual-layer verification** — Content signature proves the biometric matches the key; integrity hash proves the credential hasn't been modified. Two independent checks, both must pass.

4. **Proven performance** — 100% tamper detection, 0% false rejection, 44ms verification. Production-ready foundation.

5. **Format flexibility** — Credentials can be PNG images (for visual display), PDF documents (for formal identity cards), or embedded in any image format WaveSign supports.

---

## Summary

WaveID = **Agent Behavioral Biometric** + **WaveSign Invisible Credential** + **Challenge-Response Liveness**

An identity system where:
- The agent's computational behavior IS its fingerprint
- WaveSign embeds that fingerprint invisibly into a tamper-proof credential
- Fresh behavioral challenges prove the agent is who it claims to be — not just holding a stolen token
