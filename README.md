# WaveSign

**Invisible file signing and tamper detection for images and documents.**

Sign any image or PDF with an invisible signature. Share it. Verify it later — any modification, no matter how small, is detected instantly.

---

## Try It

🔗 [Live Demo](https://phasesig-rbek68ksvn9aty6wize8wo.streamlit.app/)

---

## Evaluation Results

Tested across **900 cases, 22 scenarios**. Full results: [EVALUATION.md](./EVALUATION.md)

| Metric | Result |
|---|---|
| **Tamper Detection Rate** | **100%** on all visible modifications |
| **False Rejection Rate** | **0%** — no authentic file wrongly rejected |
| **Key Specificity** | **100%** — wrong, similar, and empty keys always rejected |
| **Signing time** | 148 ms mean |
| **Invisibility (PSNR)** | 41.6 dB mean — imperceptible |

---

## What It Does

- **Sign** — Upload an image or PDF, set a secret key, download a signed package
- **Verify** — Upload the signed file + verification file + key → instant ✅ or ❌
- **Invisible** — Signed files look identical to the originals
- **Sensitive** — Any edit after signing invalidates the signature

Supports PNG, JPG, WEBP, and multi-page PDF.

---

## Use Cases

- Contracts and documents — detect any edit after signing
- AI-generated images — prove a file is unmodified since export
- Creative work — sign before publishing, verify origin later
- Sensitive files — any modification immediately invalidates the signature

---

## How It Works

WaveSign uses a proprietary physics-based method to embed an invisible cryptographic signature directly into the file. The signature is bound to both the file content and your secret key — it cannot be transferred, forged, or separated from the file it protects.

**Two-layer verification:**
- **Content signature** — derived from the file's signal structure using your key
- **Integrity hash** — block-level pixel fingerprint detects any pixel-level change

Both layers must match for a file to verify as authentic.

---

## Demo

### Invisible Signature

The signed file is visually identical to the original.

| Original | Signed |
| :---: | :---: |
| <img src="assets/ppl.jpg" width="70%"/> | <img src="assets/signed_ppl.png" width="70%"/> |

| Original Document | Signed Document |
| :---: | :---: |
| <img src="assets/1page_contract.png" width="70%"/> | <img src="assets/wavesign_1page_contract.png" width="70%"/> |

### Workflow

**Signing** — Upload, set key, download signed package.

<img src="assets/sign.gif" width="50%"/>

**Verification** — Upload signed file + verification file + key → instant result.

<img src="assets/verify.gif" width="50%"/>

---

## License

See [LICENSE](./LICENSE)
