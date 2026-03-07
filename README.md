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

## License

MIT
