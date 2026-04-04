"""
WaveSign Evaluation Suite
=========================
Generates synthetic test corpus, runs all test scenarios,
and produces a formatted evaluation report.

Categories:
  A — Pixel-Level Tampering (must be detected)
  B — Format & Platform Handling (must be detected)
  C — Authentic File Verification (must pass)
  D — Key Security (wrong key must fail)
"""

import sys
import os
import time
import json
import io
import hashlib
import textwrap
from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Import WaveSign core
sys.path.insert(0, os.path.dirname(__file__))
from core import (
    embed_watermark, sign_image, verify_image,
    detect_mode, compute_psnr
)


# ─────────────────────────────────────────
# TEST CORPUS GENERATION
# ─────────────────────────────────────────

def make_color_photo(w=800, h=600, seed=0):
    """Synthetic color image with gradients and shapes (simulates photo)."""
    rng = np.random.default_rng(seed)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    # Gradient background
    for c in range(3):
        base = rng.integers(30, 200)
        grad = np.linspace(base, base + rng.integers(20, 80), h).astype(np.uint8)
        arr[:, :, c] = grad[:, None]
    # Random rectangles
    for _ in range(15):
        x1, y1 = rng.integers(0, w-50), rng.integers(0, h-50)
        x2, y2 = x1 + rng.integers(20, 150), y1 + rng.integers(20, 150)
        color = rng.integers(0, 255, size=3)
        arr[y1:min(y2,h), x1:min(x2,w)] = color
    return Image.fromarray(arr, 'RGB')


def make_grayscale_doc(w=800, h=1000, seed=0):
    """Synthetic grayscale document (white bg, dark text-like patterns)."""
    rng = np.random.default_rng(seed)
    arr = np.full((h, w), 245, dtype=np.uint8)
    # Simulate text lines
    for row in range(40, h - 40, 18):
        line_len = rng.integers(w // 3, w - 40)
        arr[row:row+2, 40:40+line_len] = rng.integers(10, 60)
    return Image.fromarray(arr, 'L').convert('RGB')


def make_graphic(w=600, h=600, seed=0):
    """Simple graphic with shapes and flat colors."""
    img = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    rng = np.random.default_rng(seed)
    for _ in range(8):
        x1, y1 = rng.integers(0, w), rng.integers(0, h)
        x2, y2 = x1 + rng.integers(50, 200), y1 + rng.integers(50, 200)
        color = tuple(rng.integers(0, 255, size=3).tolist())
        draw.rectangle([x1, y1, x2, y2], fill=color)
    for _ in range(5):
        cx, cy = rng.integers(50, w-50), rng.integers(50, h-50)
        r = rng.integers(20, 100)
        color = tuple(rng.integers(0, 255, size=3).tolist())
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)
    return img


def make_small_image(seed=0):
    return make_color_photo(256, 256, seed)


def make_large_image(seed=0):
    return make_color_photo(1600, 1200, seed)


def generate_corpus(n_per_type=10):
    """Generate test corpus. Returns list of (image, label, seed)."""
    corpus = []
    for i in range(n_per_type):
        corpus.append((make_color_photo(seed=i), f"color_photo_{i}", i))
    for i in range(n_per_type):
        corpus.append((make_grayscale_doc(seed=100+i), f"grayscale_doc_{i}", 100+i))
    for i in range(n_per_type):
        corpus.append((make_graphic(seed=200+i), f"graphic_{i}", 200+i))
    for i in range(n_per_type // 2):
        corpus.append((make_small_image(seed=300+i), f"small_img_{i}", 300+i))
    for i in range(n_per_type // 2):
        corpus.append((make_large_image(seed=400+i), f"large_img_{i}", 400+i))
    return corpus


# ─────────────────────────────────────────
# TAMPERING FUNCTIONS
# ─────────────────────────────────────────

def tamper_single_pixel(img):
    """Change exactly 1 pixel visibly (±10 on each channel)."""
    arr = np.array(img)
    h, w = arr.shape[:2]
    y, x = h // 2, w // 2
    for c in range(arr.shape[2]):
        arr[y, x, c] = min(255, int(arr[y, x, c]) + 10)
    return Image.fromarray(arr, img.mode)


def tamper_single_pixel_minimal(img):
    """Change exactly 1 pixel by 1 unit (minimal edit)."""
    arr = np.array(img)
    h, w = arr.shape[:2]
    y, x = h // 2, w // 2
    arr[y, x, 0] = (int(arr[y, x, 0]) + 1) % 256
    return Image.fromarray(arr, img.mode)


def tamper_text_overlay(img):
    """Draw text on top of signed image."""
    out = img.copy()
    draw = ImageDraw.Draw(out)
    draw.text((10, 10), "EDITED", fill=(255, 0, 0))
    return out


def tamper_crop_5(img):
    """Crop 5% from each edge, then resize back to original dimensions."""
    w, h = img.size
    margin_w, margin_h = int(w * 0.05), int(h * 0.05)
    cropped = img.crop((margin_w, margin_h, w - margin_w, h - margin_h))
    return cropped.resize((w, h), Image.BILINEAR)


def tamper_crop_10(img):
    """Crop 10% from each edge, then resize back."""
    w, h = img.size
    margin_w, margin_h = int(w * 0.10), int(h * 0.10)
    cropped = img.crop((margin_w, margin_h, w - margin_w, h - margin_h))
    return cropped.resize((w, h), Image.BILINEAR)


def tamper_brightness(img, factor=1.1):
    """Adjust brightness by 10%."""
    arr = np.array(img).astype(np.float64)
    arr = np.clip(arr * factor, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, img.mode)


def tamper_contrast(img):
    """Slight contrast increase."""
    arr = np.array(img).astype(np.float64)
    mean = arr.mean()
    arr = np.clip((arr - mean) * 1.1 + mean, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, img.mode)


def tamper_noise_1pct(img):
    """Add Gaussian noise at 1% level."""
    arr = np.array(img).astype(np.float64)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 2.55, arr.shape)  # 1% of 255
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, img.mode)


def tamper_blur(img):
    """Mild Gaussian blur (radius 1)."""
    return img.filter(ImageFilter.GaussianBlur(radius=1))


def tamper_sharpen(img):
    """Sharpening filter."""
    return img.filter(ImageFilter.SHARPEN)


def tamper_resize_50(img):
    """Downscale to 50%, then back to original size."""
    w, h = img.size
    small = img.resize((w // 2, h // 2), Image.BILINEAR)
    return small.resize((w, h), Image.BILINEAR)


def tamper_jpeg_roundtrip(img, quality=75):
    """Save as JPEG then reload as PNG (lossy roundtrip)."""
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality)
    buf.seek(0)
    reloaded = Image.open(buf).convert('RGB')
    # Ensure same size
    if reloaded.size != img.size:
        reloaded = reloaded.resize(img.size, Image.BILINEAR)
    return reloaded


def tamper_jpeg_90(img):
    return tamper_jpeg_roundtrip(img, quality=90)


def tamper_jpeg_50(img):
    return tamper_jpeg_roundtrip(img, quality=50)


def tamper_screenshot_sim(img):
    """Simulate screenshot: save as JPEG q95, reload."""
    return tamper_jpeg_roundtrip(img, quality=95)


def tamper_format_roundtrip(img):
    """PNG -> JPEG -> PNG (lossy roundtrip via JPEG q85)."""
    return tamper_jpeg_roundtrip(img, quality=85)


def tamper_grayscale_convert(img):
    """Convert to grayscale and back to RGB."""
    return img.convert('L').convert('RGB')


def tamper_metadata_only(img):
    """Re-save PNG without pixel changes (test byte-level re-encode)."""
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Image.open(buf).convert('RGB')


# ─────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────

SECRET_KEY = "wavesign-eval-2026"
WRONG_KEY = "wrong-key-12345"
SIMILAR_KEY = "wavesign-eval-2027"  # 1 char diff
EMPTY_KEY = ""


class TestResult:
    def __init__(self, category, scenario, label, expected_valid, actual_valid,
                 similarity=None, spatial_match=None, elapsed_ms=None):
        self.category = category
        self.scenario = scenario
        self.label = label
        self.expected_valid = expected_valid
        self.actual_valid = actual_valid
        self.similarity = similarity
        self.spatial_match = spatial_match
        self.elapsed_ms = elapsed_ms
        self.correct = (expected_valid == actual_valid)


def run_tamper_test(category, scenario, img, sig, tamper_fn, results):
    """Sign is already done. Apply tamper, verify, collect result."""
    tampered = tamper_fn(img)
    t0 = time.perf_counter()
    vr = verify_image(tampered, SECRET_KEY, sig)
    elapsed = (time.perf_counter() - t0) * 1000
    results.append(TestResult(
        category=category, scenario=scenario, label=img._eval_label,
        expected_valid=False, actual_valid=vr["is_valid"],
        similarity=vr["similarity_score"], spatial_match=vr["spatial_hash_match"],
        elapsed_ms=elapsed
    ))


def run_authentic_test(category, scenario, img, sig, results, key=SECRET_KEY, expected=True):
    """Verify unmodified image with correct key."""
    t0 = time.perf_counter()
    vr = verify_image(img, key, sig)
    elapsed = (time.perf_counter() - t0) * 1000
    results.append(TestResult(
        category=category, scenario=scenario, label=img._eval_label,
        expected_valid=expected, actual_valid=vr["is_valid"],
        similarity=vr["similarity_score"], spatial_match=vr["spatial_hash_match"],
        elapsed_ms=elapsed
    ))


def run_all_tests():
    print("=" * 60)
    print("WaveSign Evaluation Suite")
    print("=" * 60)

    # Generate corpus
    print("\n[1/5] Generating test corpus...")
    corpus = generate_corpus(n_per_type=10)
    print(f"  {len(corpus)} test images generated")

    # Sign all images
    print("\n[2/5] Signing all images...")
    signed_pairs = []  # (watermarked_img, signature, original_label)
    sign_times = []
    psnr_values = []
    for img, label, seed in corpus:
        t0 = time.perf_counter()
        wm = embed_watermark(img, SECRET_KEY)
        sig = sign_image(wm, SECRET_KEY)
        sign_times.append((time.perf_counter() - t0) * 1000)
        psnr_values.append(compute_psnr(img, wm))
        wm._eval_label = label
        signed_pairs.append((wm, sig, label))
    print(f"  Signing: mean={np.mean(sign_times):.0f}ms, "
          f"max={np.max(sign_times):.0f}ms")
    finite_psnr = [p for p in psnr_values if p != float('inf')]
    if finite_psnr:
        print(f"  PSNR: mean={np.mean(finite_psnr):.1f}dB, "
              f"min={np.min(finite_psnr):.1f}dB")

    results = []

    # ── Category A: Pixel-Level Tampering ──
    print("\n[3/5] Running Category A — Pixel-Level Tampering...")
    tamper_scenarios_a = [
        ("A1: Single pixel edit (±10)", tamper_single_pixel),
        ("A1b: Single pixel edit (±1)", tamper_single_pixel_minimal),
        ("A2: Text overlay", tamper_text_overlay),
        ("A3: Crop 5%", tamper_crop_5),
        ("A4: Crop 10%", tamper_crop_10),
        ("A5: Brightness +10%", tamper_brightness),
        ("A6: Contrast adjust", tamper_contrast),
        ("A7: Noise 1%", tamper_noise_1pct),
        ("A8: Gaussian blur", tamper_blur),
        ("A9: Sharpen", tamper_sharpen),
        ("A10: Resize 50% roundtrip", tamper_resize_50),
    ]
    for scenario_name, tamper_fn in tamper_scenarios_a:
        for wm_img, sig, label in signed_pairs:
            run_tamper_test("A: Pixel Tampering", scenario_name,
                           wm_img, sig, tamper_fn, results)
    a_count = sum(1 for r in results if r.category.startswith("A"))
    a_correct = sum(1 for r in results if r.category.startswith("A") and r.correct)
    print(f"  {a_correct}/{a_count} correctly detected as tampered")

    # ── Category B: Format & Platform Handling ──
    print("\n[4/5] Running Category B — Format & Platform Handling...")
    tamper_scenarios_b = [
        ("B1: Screenshot sim (JPEG q95)", tamper_screenshot_sim),
        ("B2: Format roundtrip (PNG→JPG→PNG)", tamper_format_roundtrip),
        ("B3: JPEG 90%", tamper_jpeg_90),
        ("B4: JPEG 50%", tamper_jpeg_50),
        ("B5: Grayscale convert", tamper_grayscale_convert),
        ("B6: Metadata-only re-save", tamper_metadata_only),
    ]
    for scenario_name, tamper_fn in tamper_scenarios_b:
        for wm_img, sig, label in signed_pairs:
            if scenario_name == "B6: Metadata-only re-save":
                # Lossless re-save should preserve pixels
                tampered = tamper_fn(wm_img)
                t0 = time.perf_counter()
                vr = verify_image(tampered, SECRET_KEY, sig)
                elapsed = (time.perf_counter() - t0) * 1000
                results.append(TestResult(
                    category="B: Format Handling", scenario=scenario_name,
                    label=label,
                    expected_valid=True,
                    actual_valid=vr["is_valid"],
                    similarity=vr["similarity_score"],
                    spatial_match=vr["spatial_hash_match"],
                    elapsed_ms=elapsed
                ))
            elif scenario_name == "B5: Grayscale convert":
                # Grayscale docs are already grayscale — conversion is a no-op
                is_grayscale = "grayscale" in label
                tampered = tamper_fn(wm_img)
                t0 = time.perf_counter()
                vr = verify_image(tampered, SECRET_KEY, sig)
                elapsed = (time.perf_counter() - t0) * 1000
                results.append(TestResult(
                    category="B: Format Handling", scenario=scenario_name,
                    label=label,
                    expected_valid=is_grayscale,  # grayscale docs unchanged
                    actual_valid=vr["is_valid"],
                    similarity=vr["similarity_score"],
                    spatial_match=vr["spatial_hash_match"],
                    elapsed_ms=elapsed
                ))
            else:
                run_tamper_test("B: Format Handling", scenario_name,
                               wm_img, sig, tamper_fn, results)
    b_results = [r for r in results if r.category.startswith("B")]
    b_correct = sum(1 for r in b_results if r.correct)
    print(f"  {b_correct}/{len(b_results)} correct")

    # ── Category C: Authentic File Verification ──
    print("\n[5/5] Running Categories C & D...")
    for wm_img, sig, label in signed_pairs:
        # C1: Unmodified verify
        run_authentic_test("C: Authenticity", "C1: Unmodified verify",
                           wm_img, sig, results)
        # C2: Re-save PNG (lossless roundtrip)
        buf = io.BytesIO()
        wm_img.save(buf, format='PNG')
        buf.seek(0)
        reloaded = Image.open(buf).convert('RGB')
        reloaded._eval_label = label
        resig = sig  # same signature
        run_authentic_test("C: Authenticity", "C2: PNG re-save verify",
                           reloaded, resig, results)

    # ── Category D: Key Security ──
    for wm_img, sig, label in signed_pairs:
        # D1: Wrong key
        run_authentic_test("D: Key Security", "D1: Wrong key",
                           wm_img, sig, results, key=WRONG_KEY, expected=False)
        # D2: Similar key (1 char diff)
        run_authentic_test("D: Key Security", "D2: Similar key (1-char diff)",
                           wm_img, sig, results, key=SIMILAR_KEY, expected=False)
        # D3: Empty key
        run_authentic_test("D: Key Security", "D3: Empty key",
                           wm_img, sig, results, key=EMPTY_KEY, expected=False)

    # D4: Unsigned file (sign with one key, create fresh unsigned image, try verify)
    for i in range(min(20, len(signed_pairs))):
        wm_img, sig, label = signed_pairs[i]
        # Create a completely different image
        fresh = make_color_photo(seed=9000 + i)
        fresh._eval_label = f"unsigned_{i}"
        run_authentic_test("D: Key Security", "D4: Unsigned/different file",
                           fresh, sig, results, key=SECRET_KEY, expected=False)

    return results, sign_times, psnr_values


# ─────────────────────────────────────────
# REPORT GENERATION
# ─────────────────────────────────────────

def generate_report(results, sign_times, psnr_values):
    # Aggregate by scenario
    scenario_stats = defaultdict(lambda: {"total": 0, "correct": 0, "similarities": []})
    for r in results:
        key = (r.category, r.scenario)
        scenario_stats[key]["total"] += 1
        if r.correct:
            scenario_stats[key]["correct"] += 1
        if r.similarity is not None:
            scenario_stats[key]["similarities"].append(r.similarity)

    total = len(results)
    total_correct = sum(1 for r in results if r.correct)

    # Category aggregates
    cat_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in results:
        cat_stats[r.category]["total"] += 1
        if r.correct:
            cat_stats[r.category]["correct"] += 1

    # Metric calculations
    tamper_results = [r for r in results if r.expected_valid is False]
    authentic_results = [r for r in results if r.expected_valid is True]

    tdr = sum(1 for r in tamper_results if r.correct) / max(len(tamper_results), 1) * 100
    frr = sum(1 for r in authentic_results if not r.correct) / max(len(authentic_results), 1) * 100
    key_results = [r for r in results if r.category.startswith("D")]
    key_spec = sum(1 for r in key_results if r.correct) / max(len(key_results), 1) * 100

    verify_times = [r.elapsed_ms for r in results if r.elapsed_ms]
    finite_psnr = [p for p in psnr_values if p != float('inf')]

    # ── Build report ──
    lines = []
    lines.append("## WaveSign Evaluation Results\n")
    lines.append(f"**Date:** {time.strftime('%Y-%m-%d')}")
    lines.append(f"**Total test cases:** {total}")
    lines.append(f"**Overall accuracy:** {total_correct}/{total} "
                 f"({total_correct/total*100:.1f}%)\n")

    lines.append("### Headline Metrics\n")
    lines.append("| Metric | Value | Target |")
    lines.append("|---|---|---|")
    lines.append(f"| **Tamper Detection Rate (TDR)** | {tdr:.1f}% | 100% |")
    lines.append(f"| **False Rejection Rate (FRR)** | {frr:.1f}% | 0% |")
    lines.append(f"| **Key Specificity** | {key_spec:.1f}% | 100% |")
    lines.append("")

    lines.append("### Performance\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Signing time (mean) | {np.mean(sign_times):.0f} ms |")
    lines.append(f"| Signing time (max) | {np.max(sign_times):.0f} ms |")
    lines.append(f"| Verify time (mean) | {np.mean(verify_times):.0f} ms |")
    lines.append(f"| Verify time (max) | {np.max(verify_times):.0f} ms |")
    if finite_psnr:
        lines.append(f"| PSNR (mean) | {np.mean(finite_psnr):.1f} dB |")
        lines.append(f"| PSNR (min) | {np.min(finite_psnr):.1f} dB |")
    lines.append("")

    lines.append("### Results by Category\n")
    lines.append("| Category | Tests | Passed | Rate |")
    lines.append("|---|---|---|---|")
    for cat in ["A: Pixel Tampering", "B: Format Handling",
                "C: Authenticity", "D: Key Security"]:
        s = cat_stats.get(cat, {"total": 0, "correct": 0})
        rate = s["correct"] / max(s["total"], 1) * 100
        lines.append(f"| {cat} | {s['total']} | {s['correct']} | {rate:.1f}% |")
    lines.append("")

    lines.append("### Detailed Scenario Results\n")
    lines.append("| Category | Scenario | N | Correct | Rate | Avg Similarity |")
    lines.append("|---|---|---|---|---|---|")

    # Sort by category then scenario
    for (cat, scenario) in sorted(scenario_stats.keys()):
        s = scenario_stats[(cat, scenario)]
        rate = s["correct"] / s["total"] * 100
        sims = s["similarities"]
        avg_sim = f"{np.mean(sims):.4f}" if sims else "—"
        lines.append(f"| {cat} | {scenario} | {s['total']} | "
                     f"{s['correct']} | {rate:.0f}% | {avg_sim} |")
    lines.append("")

    # Interpretation
    lines.append("### Interpretation\n")
    if tdr == 100.0 and frr == 0.0 and key_spec == 100.0:
        lines.append("> **All tests passed.** Every pixel-level modification, "
                     "format conversion, and incorrect key was correctly detected. "
                     "Unmodified signed files verified successfully with zero false rejections.\n")
    else:
        if tdr < 100:
            lines.append(f"> **Tamper detection:** {tdr:.1f}% — "
                         f"some modifications were not detected.\n")
        if frr > 0:
            lines.append(f"> **False rejections:** {frr:.1f}% — "
                         f"some authentic files were incorrectly flagged.\n")
        if key_spec < 100:
            lines.append(f"> **Key specificity:** {key_spec:.1f}% — "
                         f"some wrong-key attempts were not rejected.\n")

    lines.append("### Methodology\n")
    lines.append("- **Corpus:** Synthetic images — color photos, grayscale documents, "
                 "graphics, small (256px) and large (1600px)")
    lines.append("- **Signing:** `embed_watermark` + `sign_image` with default "
                 "strength (0.03)")
    lines.append("- **Verification:** `verify_image` with default tolerance (0.05)")
    lines.append("- **All tests deterministic** — reproducible with fixed seeds")
    lines.append("- **Algorithm:** fraunhofer-phase-v3 (dual-layer: diffraction "
                 "signature + spatial block hash)")
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    results, sign_times, psnr_values = run_all_tests()
    report = generate_report(results, sign_times, psnr_values)

    # Print to console
    print("\n" + "=" * 60)
    print(report)

    # Save report
    report_path = os.path.join(os.path.dirname(__file__), "EVALUATION.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")

    # Save raw data
    raw = []
    for r in results:
        raw.append({
            "category": r.category,
            "scenario": r.scenario,
            "label": r.label,
            "expected_valid": r.expected_valid,
            "actual_valid": r.actual_valid,
            "correct": r.correct,
            "similarity": r.similarity,
            "spatial_match": r.spatial_match,
            "elapsed_ms": round(r.elapsed_ms, 2) if r.elapsed_ms else None
        })
    raw_path = os.path.join(os.path.dirname(__file__), "evaluation_raw.json")
    with open(raw_path, "w") as f:
        json.dump(raw, f, indent=2)
    print(f"Raw data saved to: {raw_path}")
