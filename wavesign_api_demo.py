"""
WaveSign API Demo — End-to-End Workflow
========================================
Verifies the live WaveSign API and demonstrates a complete
sign → verify → tamper-detect → wrong-key-reject workflow.

Usage:
  export WS_API_KEY="your-token"
  python wavesign_api_demo.py

Steps:
  1. Health Check          — confirm API is reachable
  2. API Info              — display service metadata
  3. Sign Workflow         — generate image, sign via API
  4. Verify Authentic      — verify signed file (correct key)
  5. Tamper Detection      — modify signed image, expect rejection
  6. Wrong Key Detection   — verify with wrong key, expect rejection
"""

import io, json, os, sys, time, zipfile
import numpy as np
from PIL import Image, ImageDraw

try:
    import requests
except ImportError:
    sys.exit("requests not installed — run: pip install requests")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

BASE_URL  = "https://roseluo-wavesign-api.hf.space"
SECRET    = "wavesign-demo-2026"
WRONG_KEY = "wrong-key-12345"

API_KEY = os.environ.get("WS_API_KEY", "")
if not API_KEY:
    sys.exit(
        "\n[ERROR] WS_API_KEY environment variable is not set.\n"
        "  export WS_API_KEY='your-api-token'\n"
        "  then re-run:  python wavesign_api_demo.py\n"
    )

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

SEP = "=" * 60


def step_header(n, total, title):
    print(f"\n{SEP}")
    print(f"  Step {n}/{total}: {title}")
    print(SEP)


def ok(msg):
    print(f"  [PASS] {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")


def make_test_image(w=800, h=600, seed=42):
    """Generate a synthetic gradient image with noise."""
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


def img_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def tamper_image(png_bytes):
    """Draw red 'EDITED' text on the signed image — a visible tamper."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "EDITED", fill=(255, 0, 0))
    return img_to_png_bytes(img)


# ─────────────────────────────────────────
# API CALLERS
# ─────────────────────────────────────────

def api_sign(png_bytes, key=SECRET, timeout=90):
    """POST /sign → (status_code, elapsed_ms, zip_bytes | None)."""
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{BASE_URL}/sign",
            headers=HEADERS,
            files={"file": ("img.png", png_bytes, "image/png")},
            data={"key": key},
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            return r.status_code, elapsed, r.content
        return r.status_code, elapsed, None
    except requests.exceptions.RequestException:
        return 0, (time.perf_counter() - t0) * 1000, None


def api_verify(signed_bytes, sig_bytes, key=SECRET, timeout=60):
    """POST /verify → (status_code, elapsed_ms, result_dict | None)."""
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{BASE_URL}/verify",
            headers=HEADERS,
            files={
                "file":     ("signed.png", signed_bytes, "image/png"),
                "sig_file": ("sig.json",   sig_bytes,    "application/json"),
            },
            data={"key": key},
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            return r.status_code, elapsed, r.json()
        return r.status_code, elapsed, None
    except requests.exceptions.RequestException:
        return 0, (time.perf_counter() - t0) * 1000, None


def unzip_sign_response(zip_bytes):
    """Extract signed file + sig.json from ZIP response."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        signed_name = next((n for n in names if n.startswith("signed")), names[0])
        sig_name    = next((n for n in names if n.endswith(".json")), None)
        signed_bytes = z.read(signed_name)
        sig_bytes    = z.read(sig_name) if sig_name else None
    return signed_bytes, sig_bytes


# ─────────────────────────────────────────
# DEMO STEPS
# ─────────────────────────────────────────

TOTAL_STEPS = 6


def run_health_check():
    step_header(1, TOTAL_STEPS, "Health Check")
    try:
        t0 = time.perf_counter()
        r = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=30)
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200 and r.json().get("status") == "ok":
            ok(f"API is healthy  ({ms:.0f} ms)")
            return True, "healthy"
        fail(f"Unexpected response: {r.status_code} — {r.text}")
        return False, f"status {r.status_code}"
    except requests.exceptions.RequestException as e:
        fail(f"Could not reach API: {e}")
        return False, str(e)


def run_api_info():
    step_header(2, TOTAL_STEPS, "API Info")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=30)
        if r.status_code == 200:
            info = r.json()
            print(f"  Service : {info.get('service', '?')}")
            print(f"  Version : {info.get('version', '?')}")
            endpoints = info.get("endpoints", {})
            if endpoints:
                print("  Endpoints:")
                for path, desc in endpoints.items():
                    print(f"    {path:12s} — {desc}")
            ok("API info retrieved")
            return True, "ok"
        fail(f"Unexpected status {r.status_code}")
        return False, f"status {r.status_code}"
    except requests.exceptions.RequestException as e:
        fail(f"Request failed: {e}")
        return False, str(e)


def run_sign():
    step_header(3, TOTAL_STEPS, "Sign Workflow")
    img = make_test_image()
    png = img_to_png_bytes(img)
    print(f"  Generated test image: 800x600 ({len(png):,} bytes)")

    code, ms, zdata = api_sign(png, key=SECRET)
    if code != 200 or zdata is None:
        fail(f"Sign request failed (HTTP {code})")
        return False, None, None

    signed_bytes, sig_bytes = unzip_sign_response(zdata)
    if signed_bytes is None or sig_bytes is None:
        fail("Could not extract signed file or signature from ZIP")
        return False, None, None

    sig_meta = json.loads(sig_bytes)
    print(f"  Signed file : {len(signed_bytes):,} bytes")
    print(f"  Signature   : {len(sig_bytes):,} bytes  (mode: {sig_meta.get('mode', '?')})")
    print(f"  Latency     : {ms:.0f} ms")
    ok("Image signed successfully")
    return True, signed_bytes, sig_bytes


def run_verify_authentic(signed_bytes, sig_bytes):
    step_header(4, TOTAL_STEPS, "Verify Authentic")
    code, ms, result = api_verify(signed_bytes, sig_bytes, key=SECRET)
    if code != 200 or result is None:
        fail(f"Verify request failed (HTTP {code})")
        return False

    is_valid = result.get("is_valid", False)
    verdict  = result.get("verdict", "?")
    score    = result.get("similarity_score", "?")
    print(f"  Verdict          : {verdict}")
    print(f"  Valid            : {is_valid}")
    print(f"  Similarity Score : {score}")
    print(f"  Latency          : {ms:.0f} ms")

    if is_valid and "AUTHENTIC" in str(verdict).upper():
        ok("Signed file verified as AUTHENTIC")
        return True
    fail(f"Expected AUTHENTIC but got: {verdict}")
    return False


def run_tamper_detect(signed_bytes, sig_bytes):
    step_header(5, TOTAL_STEPS, "Tamper Detection")
    tampered = tamper_image(signed_bytes)
    print(f"  Tampered image: added red 'EDITED' text overlay")

    code, ms, result = api_verify(tampered, sig_bytes, key=SECRET)
    if code != 200 or result is None:
        fail(f"Verify request failed (HTTP {code})")
        return False

    is_valid = result.get("is_valid", False)
    verdict  = result.get("verdict", "?")
    score    = result.get("similarity_score", "?")
    print(f"  Verdict          : {verdict}")
    print(f"  Valid            : {is_valid}")
    print(f"  Similarity Score : {score}")
    print(f"  Latency          : {ms:.0f} ms")

    if not is_valid:
        ok("Tampering correctly detected")
        return True
    fail("Tampered file was incorrectly accepted as authentic")
    return False


def run_wrong_key(signed_bytes, sig_bytes):
    step_header(6, TOTAL_STEPS, "Wrong Key Detection")
    print(f"  Using wrong key: '{WRONG_KEY}'")

    code, ms, result = api_verify(signed_bytes, sig_bytes, key=WRONG_KEY)
    if code != 200 or result is None:
        fail(f"Verify request failed (HTTP {code})")
        return False

    is_valid = result.get("is_valid", False)
    verdict  = result.get("verdict", "?")
    print(f"  Verdict : {verdict}")
    print(f"  Valid   : {is_valid}")
    print(f"  Latency : {ms:.0f} ms")

    if not is_valid:
        ok("Wrong key correctly rejected")
        return True
    fail("Wrong key was incorrectly accepted")
    return False


# ─────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────

def print_summary(results):
    print(f"\n{SEP}")
    print("  DEMO SUMMARY")
    print(SEP)
    passed = 0
    for i, (name, ok_flag) in enumerate(results, 1):
        tag = "PASS" if ok_flag else "FAIL"
        print(f"  {i}. {name:24s} {tag}")
        passed += ok_flag
    total = len(results)
    print(f"\n  Overall: {passed}/{total} passed")
    print(SEP)
    return passed == total


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    print(f"\n{SEP}")
    print("  WaveSign API Demo")
    print(f"  Target: {BASE_URL}")
    print(SEP)

    results = []

    # Step 1 — Health Check
    passed, _ = run_health_check()
    results.append(("Health Check", passed))
    if not passed:
        print("\n  API is not reachable — aborting remaining steps.")
        print_summary(results)
        return 1

    # Step 2 — API Info
    passed, _ = run_api_info()
    results.append(("API Info", passed))

    # Step 3 — Sign
    passed, signed_bytes, sig_bytes = run_sign()
    results.append(("Sign Workflow", passed))
    if not passed:
        print("\n  Signing failed — skipping verification steps.")
        results += [
            ("Verify Authentic", False),
            ("Tamper Detection", False),
            ("Wrong Key Detection", False),
        ]
        print_summary(results)
        return 1

    # Step 4 — Verify Authentic
    passed = run_verify_authentic(signed_bytes, sig_bytes)
    results.append(("Verify Authentic", passed))

    # Step 5 — Tamper Detection
    passed = run_tamper_detect(signed_bytes, sig_bytes)
    results.append(("Tamper Detection", passed))

    # Step 6 — Wrong Key
    passed = run_wrong_key(signed_bytes, sig_bytes)
    results.append(("Wrong Key Detection", passed))

    all_ok = print_summary(results)
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
