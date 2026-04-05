"""
WaveSign API Demo — End-to-End Workflow
========================================
Demonstrates the complete WaveSign sign → verify → tamper-detect → wrong-key
workflow.  Runs locally by default (core module), or against the live REST API.

Usage:
  python wavesign_api_demo.py              # local mode (default)
  python wavesign_api_demo.py --api        # remote API mode (needs WS_API_KEY)

Output files saved to demo_output/.
"""

import argparse
import io
import json
import os
import sys
import time
import zipfile

import numpy as np
from PIL import Image, ImageDraw

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR  = os.path.join(SCRIPT_DIR, "assets")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "demo_output")

SECRET    = "wavesign-demo-2026"
WRONG_KEY = "wrong-key-12345"

BASE_URL = "https://roseluo-wavesign-api.hf.space"

TOTAL_STEPS = 6
SEP = "=" * 60

# ─────────────────────────────────────────
# FORMATTING
# ─────────────────────────────────────────

def banner(mode):
    print(f"\n{SEP}")
    print("  WaveSign — Invisible Signing & Tamper Detection")
    print(f"  Mode  : {'LOCAL (core module)' if mode == 'local' else f'API ({BASE_URL})'}")
    print(f"  Key   : {SECRET!r}")
    print(SEP)


def step_header(n, title):
    print(f"\n{SEP}")
    print(f"  Step {n}/{TOTAL_STEPS}: {title}")
    print(SEP)


def ok(msg):
    print(f"  [PASS] {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")


def info(msg):
    print(f"  {msg}")


# ─────────────────────────────────────────
# IMAGE HELPERS
# ─────────────────────────────────────────

def make_test_image(w=800, h=600, seed=42):
    """Fallback synthetic gradient image if no asset available."""
    rng = np.random.default_rng(seed)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for c in range(3):
        base = rng.integers(40, 200)
        arr[:, :, c] = np.clip(
            np.linspace(base, base + 60, w)[None, :]
            + rng.integers(-20, 20, (h, w)),
            0, 255,
        ).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def load_demo_image():
    """Load a real asset photo, fall back to synthetic."""
    for name in ("ppl.jpg", "1page_contract.png"):
        path = os.path.join(ASSET_DIR, name)
        if os.path.isfile(path):
            img = Image.open(path).convert("RGB")
            info(f"Loaded asset: {name}  ({img.width}x{img.height})")
            return img, name
    img = make_test_image()
    info(f"Using synthetic image  ({img.width}x{img.height})")
    return img, "synthetic_800x600.png"


def img_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def tamper_pil(img):
    """Draw red 'EDITED' text — a visible tamper."""
    out = img.copy()
    draw = ImageDraw.Draw(out)
    draw.text((10, 10), "EDITED", fill=(255, 0, 0))
    return out


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────
# LOCAL-MODE BACKEND
# ─────────────────────────────────────────

def local_sign(img, key):
    """Sign using the core module directly. Returns (signed_img, sig_dict, mode, ms)."""
    from core import embed_watermark, sign_image, detect_mode
    t0 = time.perf_counter()
    mode = detect_mode(img)
    strength = 0.015 if mode == "color" else 0.03
    signed = embed_watermark(img, key, strength=strength, mode=mode)
    sig = sign_image(signed, key, mode=mode)
    ms = (time.perf_counter() - t0) * 1000
    return signed, sig, mode, ms


def local_verify(img, key, sig):
    """Verify using the core module directly. Returns (result_dict, ms)."""
    from core import verify_image
    t0 = time.perf_counter()
    result = verify_image(img, key, sig)
    ms = (time.perf_counter() - t0) * 1000
    return result, ms


def local_psnr(original, signed):
    from core import compute_psnr
    return compute_psnr(original, signed)


# ─────────────────────────────────────────
# API-MODE BACKEND
# ─────────────────────────────────────────

def _api_headers():
    api_key = os.environ.get("WS_API_KEY", "")
    if not api_key:
        sys.exit(
            "\n[ERROR] WS_API_KEY not set.  "
            "export WS_API_KEY='your-token' or use --local mode.\n"
        )
    return {"Authorization": f"Bearer {api_key}"}


def api_sign(png_bytes, key, timeout=90):
    import requests
    headers = _api_headers()
    t0 = time.perf_counter()
    r = requests.post(
        f"{BASE_URL}/sign", headers=headers,
        files={"file": ("img.png", png_bytes, "image/png")},
        data={"key": key}, timeout=timeout,
    )
    ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        return None, None, ms
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names = z.namelist()
        signed_name = next((n for n in names if n.startswith("signed")), names[0])
        sig_name = next((n for n in names if n.endswith(".json")), None)
        signed_bytes = z.read(signed_name)
        sig_bytes = z.read(sig_name) if sig_name else None
    return signed_bytes, sig_bytes, ms


def api_verify(signed_bytes, sig_bytes, key, timeout=60):
    import requests
    headers = _api_headers()
    t0 = time.perf_counter()
    r = requests.post(
        f"{BASE_URL}/verify", headers=headers,
        files={
            "file":     ("signed.png", signed_bytes, "image/png"),
            "sig_file": ("sig.json",   sig_bytes,    "application/json"),
        },
        data={"key": key}, timeout=timeout,
    )
    ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        return None, ms
    return r.json(), ms


# ─────────────────────────────────────────
# DEMO STEPS
# ─────────────────────────────────────────

def step_sign(mode, img, name):
    """Step 1+2: Load image & sign it."""
    step_header(1, "Sign Image")

    if mode == "local":
        signed_img, sig, det_mode, ms = local_sign(img, SECRET)
        psnr = local_psnr(img, signed_img)
        info(f"Detected mode : {det_mode}")
        info(f"Signing time  : {ms:.0f} ms")
        info(f"PSNR quality  : {psnr:.1f} dB  (>40 dB = invisible)")
        info(f"Signature hash: {sig.get('sig_hash', '?')[:32]}...")
        # Save outputs
        ensure_output_dir()
        signed_img.save(os.path.join(OUTPUT_DIR, "signed.png"))
        with open(os.path.join(OUTPUT_DIR, "sig.json"), "w") as f:
            json.dump(sig, f, indent=2)
        info(f"Saved: demo_output/signed.png, demo_output/sig.json")
        ok(f"Image signed  (PSNR {psnr:.1f} dB, {ms:.0f} ms)")
        return True, signed_img, sig
    else:
        png = img_to_png_bytes(img)
        signed_bytes, sig_bytes, ms = api_sign(png, SECRET)
        if signed_bytes is None:
            fail("Sign request failed")
            return False, None, None
        sig = json.loads(sig_bytes)
        info(f"Signing time  : {ms:.0f} ms")
        info(f"Signed file   : {len(signed_bytes):,} bytes")
        info(f"Signature     : {len(sig_bytes):,} bytes")
        ensure_output_dir()
        with open(os.path.join(OUTPUT_DIR, "signed.png"), "wb") as f:
            f.write(signed_bytes)
        with open(os.path.join(OUTPUT_DIR, "sig.json"), "w") as f:
            json.dump(sig, f, indent=2)
        info(f"Saved: demo_output/signed.png, demo_output/sig.json")
        ok(f"Image signed via API  ({ms:.0f} ms)")
        signed_img = Image.open(io.BytesIO(signed_bytes)).convert("RGB")
        return True, signed_img, sig


def step_verify_authentic(mode, signed_img, sig):
    """Step 2: Verify the unmodified signed image — should PASS."""
    step_header(2, "Verify Authentic File")
    info("Verifying signed image with correct key...")

    if mode == "local":
        result, ms = local_verify(signed_img, SECRET, sig)
    else:
        result, ms = api_verify(
            img_to_png_bytes(signed_img),
            json.dumps(sig).encode(), SECRET,
        )

    if result is None:
        fail("Verify request failed")
        return False

    is_valid = result.get("is_valid", False)
    verdict  = result.get("verdict", "AUTHENTIC" if is_valid else "?")
    score    = result.get("similarity_score", "?")
    info(f"Verdict          : {verdict}")
    info(f"Valid            : {is_valid}")
    info(f"Similarity score : {score}")
    info(f"Latency          : {ms:.0f} ms")

    if is_valid:
        ok("Signed file verified as AUTHENTIC")
        return True
    fail(f"Expected AUTHENTIC, got: {verdict}")
    return False


def step_tamper_detect(mode, signed_img, sig):
    """Step 3: Tamper the image, verify again — should FAIL."""
    step_header(3, "Tamper Detection")
    tampered = tamper_pil(signed_img)
    info("Applied tamper: red 'EDITED' text overlay at (10,10)")

    ensure_output_dir()
    tampered.save(os.path.join(OUTPUT_DIR, "tampered.png"))
    info("Saved: demo_output/tampered.png")

    if mode == "local":
        result, ms = local_verify(tampered, SECRET, sig)
    else:
        result, ms = api_verify(
            img_to_png_bytes(tampered),
            json.dumps(sig).encode(), SECRET,
        )

    if result is None:
        fail("Verify request failed")
        return False

    is_valid = result.get("is_valid", False)
    verdict  = result.get("verdict", "?")
    score    = result.get("similarity_score", "?")
    info(f"Verdict          : {verdict}")
    info(f"Valid            : {is_valid}")
    info(f"Similarity score : {score}")
    info(f"Latency          : {ms:.0f} ms")

    if not is_valid:
        ok("Tampering correctly detected — file rejected")
        return True
    fail("Tampered file was incorrectly accepted")
    return False


def step_wrong_key(mode, signed_img, sig):
    """Step 4: Verify with wrong key — should FAIL."""
    step_header(4, "Wrong Key Detection")
    info(f"Verifying with wrong key: {WRONG_KEY!r}")

    if mode == "local":
        result, ms = local_verify(signed_img, WRONG_KEY, sig)
    else:
        result, ms = api_verify(
            img_to_png_bytes(signed_img),
            json.dumps(sig).encode(), WRONG_KEY,
        )

    if result is None:
        fail("Verify request failed")
        return False

    is_valid = result.get("is_valid", False)
    verdict  = result.get("verdict", "?")
    info(f"Verdict : {verdict}")
    info(f"Valid   : {is_valid}")
    info(f"Latency : {ms:.0f} ms")

    if not is_valid:
        ok("Wrong key correctly rejected")
        return True
    fail("Wrong key was incorrectly accepted")
    return False


def step_real_asset(mode):
    """Step 5: Sign & verify a document image if available."""
    step_header(5, "Document Signing (Contract)")
    doc_path = os.path.join(ASSET_DIR, "1page_contract.png")
    if not os.path.isfile(doc_path):
        info("No document asset found — skipping")
        ok("Skipped (no asset)")
        return True

    doc = Image.open(doc_path).convert("RGB")
    info(f"Loaded: 1page_contract.png  ({doc.width}x{doc.height})")

    if mode == "local":
        signed_doc, sig, det_mode, ms = local_sign(doc, SECRET)
        psnr = local_psnr(doc, signed_doc)
        info(f"Detected mode : {det_mode}")
        info(f"Signing time  : {ms:.0f} ms")
        info(f"PSNR quality  : {psnr:.1f} dB")
        result, vms = local_verify(signed_doc, SECRET, sig)
    else:
        png = img_to_png_bytes(doc)
        signed_bytes, sig_bytes, ms = api_sign(png, SECRET)
        if signed_bytes is None:
            fail("Sign request failed")
            return False
        sig = json.loads(sig_bytes)
        info(f"Signing time  : {ms:.0f} ms")
        result, vms = api_verify(signed_bytes, sig_bytes, SECRET)

    if result is None:
        fail("Verify request failed")
        return False

    is_valid = result.get("is_valid", False)
    info(f"Verify result : {'AUTHENTIC' if is_valid else 'FAILED'}  ({vms:.0f} ms)")
    if is_valid:
        ok("Document signed and verified")
        return True
    fail("Document verification failed")
    return False


def step_summary(results):
    """Step 6: Print final summary."""
    step_header(6, "Summary")
    passed = 0
    for i, (name, ok_flag) in enumerate(results, 1):
        tag = "PASS" if ok_flag else "FAIL"
        print(f"  {i}. {name:28s} {tag}")
        passed += ok_flag
    total = len(results)
    print(f"\n  Result: {passed}/{total} passed")
    if passed == total:
        print("  All checks passed.")
    print(SEP)
    return passed == total


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WaveSign end-to-end demo")
    parser.add_argument(
        "--api", action="store_true",
        help="Use the remote REST API instead of the local core module",
    )
    args = parser.parse_args()
    run_mode = "api" if args.api else "local"

    banner(run_mode)

    # Load image
    img, img_name = load_demo_image()

    results = []

    # Step 1 — Sign
    passed, signed_img, sig = step_sign(run_mode, img, img_name)
    results.append(("Sign Image", passed))
    if not passed:
        info("\nSigning failed — cannot continue.")
        step_summary(results)
        return 1

    # Step 2 — Verify authentic
    passed = step_verify_authentic(run_mode, signed_img, sig)
    results.append(("Verify Authentic", passed))

    # Step 3 — Tamper detection
    passed = step_tamper_detect(run_mode, signed_img, sig)
    results.append(("Tamper Detection", passed))

    # Step 4 — Wrong key
    passed = step_wrong_key(run_mode, signed_img, sig)
    results.append(("Wrong Key Detection", passed))

    # Step 5 — Document asset
    passed = step_real_asset(run_mode)
    results.append(("Document Signing", passed))

    # Step 6 — Summary
    all_ok = step_summary(results)
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}")
        sys.exit(2)
