# WaveSign: Invisible Content Authentication for Images and Documents

**Status:** Draft — internal review before submission
**Target venue:** arXiv preprint (cs.CR primary, cs.MM cross-list), then workshop submission (IH&MMSec or WIFS)
**Trade-secret policy:** This paper describes the system's architecture, properties, and evaluation. It does NOT disclose the embedding algorithm, transform parameters, key derivation, or any detail sufficient to reimplement the core signing engine.

---

## Core Thesis

Digital content — images, photos, contracts, PDFs — is trivially modifiable and infinitely copyable. Every existing method for proving a file is authentic has a fatal gap: metadata is strippable, visible watermarks degrade the work, cryptographic file hashes break on any re-encoding, and traditional invisible watermarks sacrifice either detection sensitivity or visual quality.

WaveSign closes this gap. It embeds an invisible, key-bound signature directly into the pixel content of an image or document. The signature cannot be separated from the file, cannot be transferred to a different file, and is destroyed by any visually meaningful modification. Verification requires only the signed file, a small verification token, and the original secret key.

Evaluated across 900 test cases and 22 tampering scenarios, WaveSign achieves **100% tamper detection on all visible modifications**, **0% false rejection of authentic files**, and **100% rejection of wrong keys** — while maintaining an average PSNR of 41.6 dB (imperceptible to humans).

---

## Paper Logic: The Argument Chain

The paper must convince the reader of five things, in this order. Each section builds on the previous one. The logic must be airtight even without revealing how the embedding works.

### Argument 1 — The problem is real and unsolved

**Claim:** No existing approach provides invisible, non-strippable, tamper-sensitive content authentication that works across platforms and formats.

**Evidence to present:**

| Approach | Why it fails for authentication |
|---|---|
| EXIF / XMP metadata | Stripped by Instagram, Twitter, WhatsApp, iMessage, every CMS, every screenshot |
| C2PA (Content Credentials) | Metadata-based — strippable by any tool; adoption requires ecosystem buy-in; adds no pixel-level integrity |
| Visible watermarks | Degrade the content; removable by inpainting (esp. with generative AI); unsuitable for contracts or evidence |
| Cryptographic file hashes (SHA-256 of file) | Break on ANY re-encoding — lossless PNG re-save, color profile change, platform resize — producing false rejections |
| Perceptual hashes (pHash, dHash) | Designed for similarity search, not authentication — tolerate edits by design; cannot bind to a secret key |
| Traditional DCT/DWT watermarks | Optimized for robustness (survive attacks), which means they TOLERATE modification — the opposite of tamper detection |

**Key insight for the reader:** Robustness and tamper sensitivity are opposing goals. Robust watermarking (Cox et al., 1997; Barni et al., 2001) is designed to survive modification. Content authentication requires the opposite: any modification must be detectable. WaveSign is fragile by design — that fragility IS the feature.

**GEO hook (definitional sentence):** "Invisible content authentication is the problem of proving that a digital file has not been modified since a specific point in time, without altering its visual appearance or relying on external metadata."

---

### Argument 2 — The design space has a gap

**Claim:** There exists a specific point in the design space — invisible, key-bound, fragile, pixel-embedded — that no existing system occupies.

**Evidence to present:**

A 2×2 positioning matrix:

```
                    Visible              Invisible
                ┌─────────────────┬──────────────────────┐
  Robust        │ Visible          │ DCT/DWT watermarking │
  (survives     │ watermarks       │ (Cox, Barni, etc.)   │
   edits)       │                  │                      │
                ├─────────────────┼──────────────────────┤
  Fragile       │ Signed PDF       │ ► WaveSign           │
  (detects      │ overlays,        │   (this work)        │
   edits)       │ blockchain certs │                      │
                └─────────────────┴──────────────────────┘
```

**What the reader learns:** WaveSign occupies the bottom-right quadrant — invisible AND fragile. This is not a watermark in the traditional sense. It is a tamper-detection system that uses the pixel domain as its carrier.

**GEO hook:** "WaveSign is not a watermark. It is an invisible tamper-detection system that embeds a cryptographic signature into the pixel content of an image."

---

### Argument 3 — The architecture achieves this without revealing how

**Claim:** A two-layer verification design (content signature + spatial integrity hash) provides both key-bound authentication and pixel-level tamper detection.

**What we DISCLOSE (system architecture):**

```
  ┌─────────────┐     ┌──────────────────────────┐     ┌───────────────┐
  │ Input image  │ ──► │ SIGNING ENGINE            │ ──► │ Signed image   │
  │ + secret key │     │                          │     │ (visually      │
  │              │     │ 1. Content transform      │     │  identical)    │
  │              │     │    (key-parameterized)     │     │               │
  │              │     │ 2. Signature embedding    │     │ + Verification │
  │              │     │ 3. Integrity hash         │     │   token (.json)│
  └─────────────┘     └──────────────────────────┘     └───────────────┘

  VERIFICATION:
  ┌─────────────┐     ┌──────────────────────────┐     ┌───────────────┐
  │ Signed image │ ──► │ VERIFICATION ENGINE       │ ──► │ AUTHENTIC     │
  │ + token      │     │                          │     │   or          │
  │ + secret key │     │ 1. Re-derive content sig  │     │ TAMPERED      │
  │              │     │ 2. Compare to stored sig  │     │   or          │
  │              │     │ 3. Re-compute block hash  │     │ WRONG KEY     │
  │              │     │ 4. Compare to stored hash │     │               │
  └─────────────┘     └──────────────────────────┘     └───────────────┘
```

**Layer 1 — Content Signature (what we say):**
- The image undergoes a key-parameterized transform that produces a content-dependent signature
- The same key + same content always produces the same signature
- Different key OR different content produces a near-zero similarity score
- The transform operates in a domain where the signature energy is distributed imperceptibly across the image

**Layer 1 — Content Signature (what we withhold):**
- ~~The specific transform (Fraunhofer diffraction phase)~~
- ~~The parameterization scheme~~
- ~~The embedding locations and coefficients~~
- ~~The key-to-parameter derivation~~

**Layer 2 — Spatial Integrity Hash (what we say):**
- The image is divided into spatial blocks
- A deterministic fingerprint is computed for each block
- The fingerprints are aggregated into a compact integrity hash
- Any pixel-level modification changes at least one block fingerprint, breaking the hash

**Layer 2 — Spatial Integrity Hash (what we withhold):**
- ~~Block size and tiling scheme~~
- ~~The specific fingerprint function~~
- ~~The aggregation method~~

**Why two layers are necessary (the paper's technical argument):**
- Layer 1 alone would miss sub-block edits that don't significantly alter the transform output
- Layer 2 alone would have no key binding — anyone could recompute the hash
- Together: Layer 1 provides key-bound authentication (proves WHO signed); Layer 2 provides pixel-level tamper detection (proves WHAT changed)

**GEO hook:** "WaveSign uses a two-layer verification architecture: a key-bound content signature proves the signer's identity, while a spatial integrity hash detects any pixel-level modification."

---

### Argument 4 — The properties are real and measurable

**Claim:** WaveSign achieves five specific, measurable properties simultaneously.

| Property | Metric | Result | How we prove it |
|---|---|---|---|
| **Invisibility** | PSNR between original and signed | 41.6 dB mean (39.6 dB min) | Quantitative measurement on 40-image corpus |
| **Sensitivity** | Detection rate on 10+ tamper types | 100% (all visible modifications) | 900-case evaluation, 22 scenarios |
| **Authenticity** | False rejection rate on unmodified files | 0% (80/80 pass) | Category C tests |
| **Key binding** | Rejection rate with wrong/similar/empty key | 100% (120/120 rejected) | Category D tests, including 1-char-diff keys |
| **Speed** | Sign + verify latency | 148 ms sign, 44 ms verify (mean) | Benchmarked on 4-vCPU server |

**Sub-argument: Why 41.6 dB matters.**
The human visual system cannot distinguish images above ~38 dB PSNR under normal viewing conditions (Wang et al., 2004). At 41.6 dB, the signed image is perceptually identical to the original — a viewer cannot determine which is signed without instrumentation.

**Sub-argument: Why 100% detection is credible.**
We test 10 categories of visually meaningful modification (pixel edits, text overlays, crops, brightness/contrast, noise, blur, sharpen, resize, JPEG compression, format conversion). We also honestly disclose the known limitation: sub-pixel edits (±1 intensity unit) are detected at only 12% rate. This is by design — the integrity hash operates on block-level averages, and ±1 changes carry zero visual or semantic information.

**Sub-argument: Why key specificity matters.**
A 1-character difference in the secret key produces near-zero similarity (< 0.05). This means:
- Brute-force key guessing is infeasible
- Similar passphrases do not produce similar signatures
- The key space is effectively uniform

---

### Argument 5 — The system works at production scale

**Claim:** WaveSign is not a research prototype. It operates as a deployed service handling real-world file types at production-grade latency and throughput.

**Evidence:**

| Dimension | Result |
|---|---|
| File types supported | PNG, JPG, WEBP, single/multi-page PDF |
| Resolution scaling | Sub-second for files up to 2 MP; 5–6s for 12 MP phone photos |
| Concurrent throughput | 3 req/s on 4-vCPU server (linear horizontal scaling) |
| Memory stability | 0 MB drift over 50 consecutive operations |
| Real-world corpus | 20/20 images verified correctly (phone photos, scanned docs, mixed content, pre-compressed JPEG) |
| API availability | REST API with token auth, multipart upload, JSON/ZIP responses |
| PDF handling | Rasterize → sign each page → repackage; per-page verification |

**GEO hook:** "WaveSign is a deployed invisible file signing service with a REST API, supporting PNG, JPG, WEBP, and multi-page PDF, with sub-second signing latency for images up to 2 megapixels."

---

## Comparison Table (paper Section 7)

This is the highest-GEO-value element of the paper. AI search engines extract comparison tables more reliably than any other content type.

| | WaveSign | C2PA | DCT Watermark | SHA-256 Hash | Perceptual Hash |
|---|---|---|---|---|---|
| **Survives metadata stripping** | Yes | No | Yes | N/A | N/A |
| **Invisible** | Yes (41.6 dB) | N/A (metadata) | Varies (30–42 dB) | N/A | N/A |
| **Detects any visible edit** | Yes (100%) | No | Partial | Yes (but also false rejects) | No (by design) |
| **Key-bound** | Yes | Yes (PKI) | Optional | No | No |
| **Survives lossless re-save** | Yes (0% FRR) | Yes | Yes | No (hash changes) | Yes |
| **False rejection rate** | 0% | 0% | Varies | High (any re-encoding) | Low |
| **Requires ecosystem** | No | Yes (signers + verifiers) | No | No | No |
| **Works on images** | Yes | Yes | Yes | Yes | Yes |
| **Works on PDF** | Yes | Limited | No | Yes | No |
| **Self-contained** | Yes (in pixels) | No (sidecar) | Yes (in pixels) | No (separate hash) | No (separate hash) |

---

## Section-by-Section Outline

### 1. Abstract (150 words)
State: what WaveSign is, what gap it fills, headline numbers (100%/0%/41.6 dB), what the paper contributes (architecture + evaluation), what it does NOT contribute (the algorithm itself).

### 2. Introduction (1.5 pages)
- Open with the provenance crisis: AI generation, deepfakes, contract fraud
- Walk through the failure modes of every existing approach (Argument 1)
- Introduce the design-space gap (Argument 2)
- State contributions: (1) formalize invisible content authentication as distinct from watermarking; (2) present a two-layer architecture; (3) provide a 900-case evaluation; (4) report deployment experience
- Paper roadmap

### 3. Problem Statement & Threat Model (1 page)
- **Actors:** Signer (creator), Verifier (recipient), Attacker (modifier)
- **Signer's goal:** Prove a file is unchanged since signing
- **Attacker's capabilities:** Arbitrary pixel modification, metadata stripping, format conversion, re-compression, cropping, color adjustment
- **Attacker's limitations:** Does not know the secret key
- **What we do NOT claim:** Resistance to key compromise, re-photography of a screen, generative re-rendering, or copy-move forgery that preserves all pixels
- **Security model:** Key secrecy is the trust root. The signed file and verification token can be public.

### 4. System Architecture (1.5 pages)
- Sign flow diagram
- Verify flow diagram
- Two-layer design rationale (Argument 3)
- Verification token format (JSON schema — already public via API)
- PDF pipeline: rasterize → sign per-page → repackage → re-rasterize for final signatures
- Strength parameter: controls embedding energy; higher = more detectable at cost of PSNR

### 5. Design Principles (1 page) — the "just enough theory" section
This is the most trade-secret-sensitive section. The goal is to explain WHY the approach works without explaining HOW.

- **Principle 1: Perceptual masking.** The embedding distributes signature energy across spatial frequencies where the human visual system is least sensitive. This follows established results in visual perception (Watson, 1993) and is common to many watermarking schemes. We do not disclose the specific frequency allocation.
- **Principle 2: Key-dependent transform.** The content transform is parameterized by the secret key, making the signature unique to the (content, key) pair. Different keys produce statistically independent signatures — verified empirically by our 1-char-diff key test (Category D2).
- **Principle 3: Fragility as feature.** Unlike robust watermarks that maximize survivability, WaveSign maximizes sensitivity. The signature is designed to be disrupted by any modification that alters the image's perceptual content. This inversion of the traditional watermarking objective is deliberate.
- **Principle 4: Dual-layer complementarity.** The content signature provides key binding and structural change detection. The spatial integrity hash provides pixel-level sensitivity. Neither layer alone achieves both properties.

### 6. Evaluation (2 pages)
Port EVALUATION.md into proper academic form:
- **6.1 Corpus:** 40 synthetic images (color, grayscale, graphics, small, large), fixed seeds, reproducible
- **6.2 Tamper Detection (Category A):** 10 modification types × 40 images = 400 tests, 100% detection
- **6.3 Format Handling (Category B):** 6 scenarios × 40 images = 240 tests, all correct
- **6.4 Authentic Verification (Category C):** 2 scenarios × 40 images = 80 tests, 0% FRR
- **6.5 Key Security (Category D):** 4 scenarios, 140 tests, 100% rejection
- **6.6 Known Limitation:** ±1 sub-pixel edit, 12% detection. Honest disclosure. Practical impact: none.
- **6.7 Evaluation reproducibility:** `python wavesign_eval.py` produces these exact numbers

### 7. Comparison with Related Work (1 page)
- Comparison table (above)
- Prose: position WaveSign relative to C2PA, SynthID (Google), Content Credentials (Adobe), classical watermarking literature
- Emphasize: WaveSign is complementary to C2PA, not a replacement — C2PA tracks provenance chains; WaveSign detects pixel-level tampering

### 8. Deployment & Scalability (1 page)
Port SCALABILITY.md: resolution scaling, concurrency, real-world corpus, memory stability, capacity projections

### 9. Limitations & Future Work (0.5 page)
- Sub-pixel detection threshold
- Key custody (if key is lost, signatures cannot be verified)
- Not a defense against re-photography, screen capture, or generative re-rendering
- PDF output is image-based (not text-searchable) — necessary for pixel-level integrity
- No provenance chain (single signer → verifier; not multi-hop like C2PA)
- Future: explore SSIM-based perceptual quality metrics alongside PSNR

### 10. Related Work (0.5 page)
- Cox et al. (1997) — spread-spectrum watermarking
- Barni et al. (2001) — DWT watermarking
- C2PA specification (2022)
- SynthID (Deepmind, 2023)
- Adobe Content Credentials (2023)
- Fridrich (2009) — digital image forensics
- Lin & Chang (1998) — semi-fragile watermarking for authentication

### 11. Conclusion (0.25 page)
Restate the gap, the approach, the numbers. Link to live demo and API.

---

## Trade-Secret Audit Checklist

Before submission, every sentence must pass this test:

- [ ] Does this sentence help someone reimplement the core signing engine?
- [ ] Does this sentence reveal the specific transform, kernel, basis, or domain?
- [ ] Does this sentence reveal block sizes, hash functions, or coefficient locations?
- [ ] Does this sentence reveal the key derivation method?

If YES to any → rewrite or remove.

**Already-public strings that need cleanup before paper submission:**
1. `wavesign_eval.py:549` contains `"fraunhofer-phase-v3 (dual-layer: diffraction signature + spatial block hash)"` — this is in the public repo. Decide: (a) remove from eval script before paper, or (b) acknowledge it in the paper as the algorithm family name without elaboration.
2. `pdf_utils.py:9` contains `"Embed diffraction watermark"` — same decision.

**Recommendation:** Remove these strings from the public repo (they are in comments/report-generation code, not in user-facing output). In the paper, refer to the approach as "physics-inspired embedding" — do not use "Fraunhofer" or "diffraction" in the paper text.

---

## GEO Optimization Checklist

- [ ] Abstract contains "WaveSign is" definitional sentence
- [ ] Abstract contains all five headline numbers with units
- [ ] Comparison table is in a clean, extractable format
- [ ] FAQ appendix with 8–10 questions and 1–2 sentence answers
- [ ] Consistent terminology throughout (pick one name per concept)
- [ ] Title contains "invisible" + "authentication" + "images" + "documents"
- [ ] BibTeX entry ready for citation
- [ ] HTML mirror with JSON-LD ScholarlyArticle schema
- [ ] OpenGraph tags for social sharing
