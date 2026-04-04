"""
WaveSign — PDF Support via Rasterization
-----------------------------------------
Pipeline:
  1. Rasterize original PDF pages at 300 DPI
  2. Embed diffraction watermark into each page image
  3. Repackage watermarked pages into a signed image-PDF
  4. Rasterize the signed PDF again — sign those final images
     (ensures verification always matches the exact output PDF pixels)

Output is an image-PDF (not text-searchable) — correct for tamper-evident signing.
"""

import io
from pdf2image import convert_from_bytes
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

from core import embed_watermark, sign_image, verify_image, detect_mode

DPI = 300


def pdf_to_images(pdf_bytes: bytes, dpi: int = DPI) -> list:
    """Rasterize all PDF pages. Returns list of PIL Images."""
    return convert_from_bytes(pdf_bytes, dpi=dpi)


def images_to_pdf(images: list) -> bytes:
    """Pack PIL Images into a single PDF. Each image fills its page."""
    buf = io.BytesIO()
    first_w, first_h = images[0].size
    c = rl_canvas.Canvas(buf, pagesize=(first_w * 72 / DPI, first_h * 72 / DPI))
    for img in images:
        w_px, h_px = img.size
        pw, ph = w_px * 72 / DPI, h_px * 72 / DPI
        c.setPageSize((pw, ph))
        img_buf = io.BytesIO()
        img.save(img_buf, format="PNG")
        img_buf.seek(0)
        c.drawImage(ImageReader(img_buf), 0, 0, width=pw, height=ph)
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def sign_pdf(pdf_bytes: bytes, secret: str, dpi: int = DPI, strength: float = 0.03):
    """
    Sign all pages of a PDF.

    Critical: signatures are computed from the FINAL rasterized output PDF,
    not from intermediate watermarked images. This ensures verify_pdf always
    produces matching results without round-trip pixel drift.

    Returns: (signed_pdf_bytes, signatures_list, n_pages)
    """
    # Step 1: rasterize original pages
    images = pdf_to_images(pdf_bytes, dpi=dpi)

    # Step 2: embed watermark into each page
    watermarked = []
    for img in images:
        mode = detect_mode(img)
        wm   = embed_watermark(img, secret, strength=strength, mode=mode)
        watermarked.append(wm)

    # Step 3: pack watermarked pages into signed PDF
    signed_pdf_bytes = images_to_pdf(watermarked)

    # Step 4: rasterize signed PDF — sign these exact pixels
    final_images = pdf_to_images(signed_pdf_bytes, dpi=dpi)
    n_pages      = len(final_images)
    sigs         = []
    for i, img in enumerate(final_images):
        sig              = sign_image(img, secret, mode='document')
        sig["page_index"] = i
        sigs.append(sig)

    return signed_pdf_bytes, sigs, n_pages


def verify_pdf(pdf_bytes: bytes, secret: str, signatures: list) -> list:
    """
    Verify all pages of a signed PDF against per-page signatures.
    Returns list of per-page result dicts with page_index key.
    """
    images  = pdf_to_images(pdf_bytes, dpi=DPI)
    results = []
    for i, (img, sig) in enumerate(zip(images, signatures)):
        result              = verify_image(img, secret, sig)
        result["page_index"] = i
        results.append(result)
    return results


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """Quick page count without rasterization."""
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
