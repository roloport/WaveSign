# WaveSign 

**Invisible file signing and tamper detection for images and documents.**

Sign any image or PDF with an invisible signature. Share it. Verify it later — any modification, no matter how small, is detected instantly.

---

## Try It

🔗 **[wavesign.streamlit.app](https://phasesig-rbek68ksvn9aty6wize8wo.streamlit.app/)** *(replace with your live URL)*

---

## What It Does

- **Sign** — Upload an image or PDF, set a secret key, download a signed package
- **Verify** — Upload the signed file + verification file + key → instant ✅ or ❌
- **Invisible** — Signed files look identical to the originals
- **Sensitive** — Any edit after signing invalidates the signature

Supports PNG, JPG, WEBP, and multi-page PDF.

---

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

> **Note:** PDF support requires `poppler`. Install via `brew install poppler` (macOS) or `apt install poppler-utils` (Linux).

---

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → select `app.py` → Deploy
4. Add a `packages.txt` file with `poppler-utils` for PDF support

Live in ~2 minutes.

---

## Use Cases

- Contracts and documents — detect any edit after signing
- AI-generated images — prove a file is unmodified since export
- Creative work — sign before publishing, verify origin later
- Sensitive files — any modification immediately invalidates the signature

---

# WaveSign

WaveSign uses advanced **plane wave diffraction phase-shift technology** to embed cryptographic signatures into images and documents. The signature is mathematically integrated into the file's phase structure, making it completely invisible to the naked eye while ensuring robust authenticity.

## 📸 Invisible Signature Showcase

The primary advantage of WaveSign is its non-destructive nature. The signature does not degrade image quality or affect the readability of document text.

| Original (Before) | Signed (After) |
| :---: | :---: |
| ![Original Image](ppl.jpg) | ![Signed Image](signed_ppl.png) |

**Key Benefits:**
* **Invisible Protection:** No visible watermarks or artifacts.
* **Zero Quality Loss:** Ideal for high-resolution images and professional photography.
* **Text Integrity:** Document readability remains 100% intact for PDFs and scans.

## 🎥 User Guide

The following clips demonstrate the seamless workflow for protecting and verifying your files.

### 1. Signing Flow
Upload your file, enter your secret key, and the system generates a signed version instantly.

https://github.com/roloport/WaveSign/sign.mp4

### 2. Verification Flow
Confirm the integrity and origin of any signed file by uploading it with the corresponding secret key.

https://github.com/roloport/WaveSign/verify.mp4

---




## License

MIT
