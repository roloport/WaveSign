"""
WaveSign Live API Benchmark
============================
Hits the deployed REST API with real HTTP requests to prove scalability,
correctness, and concurrent throughput.

  T1 — Latency by File Size   : E2E latency (sign) across 5 image sizes
  T2 — Concurrent Throughput  : req/s and latency percentiles at 1/2/4 workers
  T3 — Sign→Verify Roundtrip  : Full correctness check across 4 image types
  T4 — Sustained Load         : 20 consecutive requests, detect latency drift

Usage:
  export WS_API_KEY="your-token"
  python wavesign_api_bench.py

Output:
  Console tables + API_BENCHMARK.md + api_benchmark_raw.json
"""

import io, json, os, sys, time, zipfile
import numpy as np
from PIL import Image, ImageDraw
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import median, quantiles

try:
    import requests
except ImportError:
    sys.exit("requests not installed — run: pip install requests")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

BASE_URL = "https://roseluo-wavesign-api.hf.space"
SECRET   = "wavesign-bench-2026"

API_KEY = os.environ.get("WS_API_KEY", "")
if not API_KEY:
    sys.exit(
        "\n[ERROR] WS_API_KEY environment variable is not set.\n"
        "  export WS_API_KEY='your-api-token'\n"
        "  then re-run:  python wavesign_api_bench.py\n"
    )

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# ─────────────────────────────────────────
# IMAGE GENERATORS  (standalone copies)
# ─────────────────────────────────────────

def make_image_at_size(w, h, seed=0):
    rng = np.random.default_rng(seed)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for c in range(3):
        base = rng.integers(40, 200)
        arr[:, :, c] = np.clip(
            np.linspace(base, base + 60, w)[None, :] +
            rng.integers(-20, 20, (h, w)), 0, 255
        ).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def make_phone_photo(seed=0):
    w, h = 3024, 4032
    rng  = np.random.default_rng(seed)
    arr  = np.zeros((h, w, 3), dtype=np.uint8)
    for c in range(3):
        base  = rng.integers(40, 180)
        horiz = np.linspace(base, base + rng.integers(30, 80), w)
        vert  = np.linspace(0, rng.integers(10, 40), h)
        arr[:, :, c] = np.clip(horiz[None, :] + vert[:, None], 0, 255).astype(np.uint8)
    noise = rng.integers(-15, 15, (h, w, 3))
    arr   = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def make_scanned_doc(seed=0):
    w, h = 2480, 3508
    rng  = np.random.default_rng(seed)
    base = rng.integers(230, 250)
    arr  = np.full((h, w), base, dtype=np.uint8)
    arr  = np.clip(arr.astype(np.int16) + rng.integers(-3, 3, (h, w)), 0, 255).astype(np.uint8)
    for row in range(120, h - 120, 22):
        line_len = rng.integers(w // 3, w - 100)
        darkness = rng.integers(10, 50)
        arr[row:row+3, 80:80+line_len] = darkness
    return Image.fromarray(arr, "L").convert("RGB")


def make_mixed_content(seed=0):
    w, h = 1920, 1080
    rng  = np.random.default_rng(seed)
    arr  = np.zeros((h, w, 3), dtype=np.uint8)
    split = int(w * 0.65)
    for c in range(3):
        arr[:, :split, c] = rng.integers(60, 200, (h, split))
    arr[:, split:, :] = rng.integers(20, 80, 3)
    img  = Image.fromarray(arr, "RGB")
    draw = ImageDraw.Draw(img)
    for i in range(5):
        draw.text((split + 20, 80 + i * 60), f"Line {i+1} content", fill=(240, 240, 240))
    return img


def make_compressed(seed=0):
    w, h = 1280, 720
    rng  = np.random.default_rng(seed)
    arr  = rng.integers(30, 220, (h, w, 3), dtype=np.uint8)
    img  = Image.fromarray(arr, "RGB")
    buf  = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def img_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────

def warmup():
    """Ensure the Space is warm. Retries up to 4× with backoff."""
    print("Warming up API Space …", end=" ", flush=True)
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=30)
            if r.status_code == 200:
                print("ready.\n")
                return
        except requests.exceptions.RequestException:
            pass
        wait = 2 ** (attempt + 1)
        print(f"retrying in {wait}s …", end=" ", flush=True)
        time.sleep(wait)
    sys.exit("\n[ERROR] API did not respond after 4 warmup attempts. Check the Space status.")


def api_sign(png_bytes, key=SECRET, timeout=90):
    """POST /sign → returns (status_code, elapsed_ms, zip_bytes_or_None)."""
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{BASE_URL}/sign",
            headers=HEADERS,
            files={"file": ("img.png", png_bytes, "image/png")},
            data={"key": key},
            timeout=timeout,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            return r.status_code, elapsed_ms, r.content
        return r.status_code, elapsed_ms, None
    except requests.exceptions.RequestException as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return 0, elapsed_ms, None


def api_verify(signed_bytes, sig_bytes, key=SECRET, timeout=60):
    """POST /verify → returns (status_code, elapsed_ms, result_dict_or_None)."""
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
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            return r.status_code, elapsed_ms, r.json()
        return r.status_code, elapsed_ms, None
    except requests.exceptions.RequestException as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return 0, elapsed_ms, None


def unzip_sign_response(zip_bytes):
    """Extract signed PNG + sig.json from ZIP response."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        signed_name = next((n for n in names if n.startswith("signed")), names[0])
        sig_name    = next((n for n in names if n.endswith(".json")), None)
        signed_bytes = z.read(signed_name)
        sig_bytes    = z.read(sig_name) if sig_name else None
    return signed_bytes, sig_bytes


def pct(values, p):
    """Return p-th percentile of a list."""
    if not values:
        return 0
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    return sorted_v[min(idx, len(sorted_v) - 1)]


# ─────────────────────────────────────────
# PRINTING
# ─────────────────────────────────────────

SEP = "─" * 64

def hdr(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ─────────────────────────────────────────
# T1 — LATENCY BY FILE SIZE
# ─────────────────────────────────────────

def run_t1():
    hdr("T1  Latency by File Size  (sequential, 3-run median)")
    sizes = [
        ("256×256",   256,  256),
        ("640×480",   640,  480),
        ("1024×768",  1024, 768),
        ("1280×720",  1280, 720),
        ("1920×1080", 1920, 1080),
    ]
    print(f"  {'Size':<12} {'MP':>6}  {'sign_ms':>9}  {'status':>7}")
    print(f"  {'-'*12} {'-'*6}  {'-'*9}  {'-'*7}")

    rows = []
    for label, w, h in sizes:
        png = img_to_png_bytes(make_image_at_size(w, h))
        mp  = round(w * h / 1e6, 2)
        times = []
        status = "—"
        for run in range(3):
            code, ms, zb = api_sign(png)
            if code == 200:
                times.append(ms)
                status = "200 OK"
            else:
                status = f"ERR {code}"
        med = round(median(times)) if times else "FAIL"
        print(f"  {label:<12} {mp:>6.2f}  {str(med)+' ms':>9}  {status:>7}")
        rows.append({"size": label, "mp": mp, "sign_ms_median": med, "status": status})

    return rows


# ─────────────────────────────────────────
# T2 — CONCURRENT THROUGHPUT
# ─────────────────────────────────────────

def run_t2():
    hdr("T2  Concurrent Throughput  (1280×720, 12 tasks each level)")
    png       = img_to_png_bytes(make_image_at_size(1280, 720))
    TASKS     = 12
    WORKERS   = [1, 2, 4]

    print(f"  {'Workers':>8}  {'req/s':>7}  {'p50':>7}  {'p95':>7}  {'p99':>7}  {'errors':>7}")
    print(f"  {'-'*8}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*7}")

    rows = []
    for nw in WORKERS:
        latencies = []
        errors    = 0
        t_wall0   = time.perf_counter()

        def _worker(_):
            code, ms, _ = api_sign(png)
            return code, ms

        with ThreadPoolExecutor(max_workers=nw) as ex:
            futs = [ex.submit(_worker, i) for i in range(TASKS)]
            for fut in as_completed(futs):
                code, ms = fut.result()
                if code == 200:
                    latencies.append(ms)
                else:
                    errors += 1

        wall_s    = time.perf_counter() - t_wall0
        throughput = round(TASKS / wall_s, 2)
        p50 = round(pct(latencies, 50))
        p95 = round(pct(latencies, 95))
        p99 = round(pct(latencies, 99))

        print(f"  {nw:>8}  {throughput:>7.2f}  {p50:>5} ms  {p95:>5} ms  {p99:>5} ms  {errors:>7}")
        rows.append({"workers": nw, "req_s": throughput,
                     "p50_ms": p50, "p95_ms": p95, "p99_ms": p99,
                     "tasks": TASKS, "errors": errors})

    return rows


# ─────────────────────────────────────────
# T3 — END-TO-END SIGN → VERIFY ROUNDTRIP
# ─────────────────────────────────────────

def run_t3():
    hdr("T3  End-to-End Roundtrip  (sign → unzip → verify)")
    corpus = [
        ("phone_photo",   make_image_at_size(1920, 1080, seed=0)),  # downsized for speed
        ("scanned_doc",   make_image_at_size(1240, 1754, seed=1)),  # A4 half-res
        ("mixed_content", make_mixed_content(seed=2)),
        ("compressed",    make_compressed(seed=3)),
    ]

    print(f"  {'Type':<16} {'roundtrip_ms':>13}  {'sign_ms':>8}  {'verify_ms':>10}  {'verdict':<28}  {'sim':>5}")
    print(f"  {'-'*16} {'-'*13}  {'-'*8}  {'-'*10}  {'-'*28}  {'-'*5}")

    rows = []
    all_valid = True
    for label, img in corpus:
        png = img_to_png_bytes(img)
        t_total = time.perf_counter()

        # Sign
        code, sign_ms, zip_bytes = api_sign(png)
        if code != 200 or zip_bytes is None:
            print(f"  {label:<16} {'SIGN FAILED':>13}")
            rows.append({"type": label, "error": f"sign HTTP {code}"})
            all_valid = False
            continue

        # Unzip
        try:
            signed_bytes, sig_bytes = unzip_sign_response(zip_bytes)
        except Exception as e:
            print(f"  {label:<16} {'UNZIP FAILED':>13}")
            rows.append({"type": label, "error": str(e)})
            all_valid = False
            continue

        # Verify
        vcode, verify_ms, result = api_verify(signed_bytes, sig_bytes)
        roundtrip_ms = round((time.perf_counter() - t_total) * 1000)

        if vcode != 200 or result is None:
            print(f"  {label:<16} {roundtrip_ms:>10} ms  {'VERIFY FAILED':>10}")
            rows.append({"type": label, "error": f"verify HTTP {vcode}"})
            all_valid = False
            continue

        is_valid = result.get("is_valid", False)
        verdict  = result.get("verdict", "—")
        sim      = result.get("similarity_score")
        sim_str  = f"{sim:.3f}" if sim is not None else "—"
        if not is_valid:
            all_valid = False

        print(f"  {label:<16} {roundtrip_ms:>10} ms  {round(sign_ms):>5} ms  {round(verify_ms):>7} ms  {verdict:<28}  {sim_str:>5}")
        rows.append({
            "type": label, "roundtrip_ms": roundtrip_ms,
            "sign_ms": round(sign_ms), "verify_ms": round(verify_ms),
            "is_valid": is_valid, "verdict": verdict, "similarity_score": sim,
        })

    print(f"\n  All roundtrips authentic: {'✓ YES' if all_valid else '✗ NO — check errors above'}")
    return rows


# ─────────────────────────────────────────
# T4 — SUSTAINED LOAD (20 requests)
# ─────────────────────────────────────────

def run_t4():
    hdr("T4  Sustained Load  (20 sequential sign requests, 1280×720)")
    png       = img_to_png_bytes(make_image_at_size(1280, 720))
    N         = 20
    latencies = []
    errors    = 0

    print(f"  {'Req':>5}  {'sign_ms':>9}  {'status':>8}")
    print(f"  {'-'*5}  {'-'*9}  {'-'*8}")

    for i in range(1, N + 1):
        code, ms, _ = api_sign(png)
        ms_r = round(ms)
        if code == 200:
            latencies.append(ms)
            status = "200 OK"
        else:
            errors += 1
            status = f"ERR {code}"
        print(f"  {i:>5}  {ms_r:>7} ms  {status:>8}")

    print()
    if latencies:
        p50 = round(pct(latencies, 50))
        p99 = round(pct(latencies, 99))
        drift_pct = round((p99 - p50) / p50 * 100, 1) if p50 else 0
        stability = "STABLE" if drift_pct < 100 else "DEGRADED"
        print(f"  p50: {p50} ms   p99: {p99} ms   drift: {drift_pct:+.1f}%   status: {stability}   errors: {errors}/{N}")
    else:
        p50, p99, drift_pct, stability = 0, 0, 0, "ALL FAILED"
        print(f"  All {N} requests failed.")

    return {
        "n": N, "errors": errors,
        "p50_ms": p50, "p99_ms": p99,
        "drift_pct": drift_pct, "stability": stability,
        "latencies_ms": [round(l) for l in latencies],
    }


# ─────────────────────────────────────────
# MARKDOWN REPORT
# ─────────────────────────────────────────

def write_report(t1, t2, t3, t4, run_date):
    lines = [
        "## WaveSign Live API Benchmark",
        "",
        f"**Date:** {run_date}  ",
        f"**Endpoint:** `{BASE_URL}`  ",
        "**Infrastructure:** Hugging Face Spaces (shared infrastructure, warm instance)  ",
        "",
        "---",
        "",
        "### T1 — Latency by File Size",
        "",
        "| Size | Megapixels | Sign latency (median 3 runs) | Status |",
        "|---|---|---|---|",
    ]
    for r in t1:
        ms = r["sign_ms_median"]
        lines.append(f"| {r['size']} | {r['mp']} MP | {ms} ms | {r['status']} |")

    lines += [
        "",
        "### T2 — Concurrent Throughput",
        "",
        "| Workers | Throughput | p50 | p95 | p99 | Errors |",
        "|---|---|---|---|---|---|",
    ]
    for r in t2:
        lines.append(
            f"| {r['workers']} | {r['req_s']} req/s | {r['p50_ms']} ms "
            f"| {r['p95_ms']} ms | {r['p99_ms']} ms | {r['errors']}/{r['tasks']} |"
        )

    lines += [
        "",
        "### T3 — End-to-End Roundtrip",
        "",
        "| Image Type | Roundtrip | Sign | Verify | Verdict | Similarity |",
        "|---|---|---|---|---|---|",
    ]
    for r in t3:
        if "error" in r:
            lines.append(f"| {r['type']} | ERROR | — | — | {r['error']} | — |")
        else:
            sim = f"{r['similarity_score']:.3f}" if r.get("similarity_score") is not None else "—"
            lines.append(
                f"| {r['type']} | {r['roundtrip_ms']} ms | {r['sign_ms']} ms "
                f"| {r['verify_ms']} ms | {r['verdict']} | {sim} |"
            )

    lines += [
        "",
        "### T4 — Sustained Load (20 requests)",
        "",
        f"| Metric | Value |",
        "|---|---|",
        f"| p50 latency | {t4['p50_ms']} ms |",
        f"| p99 latency | {t4['p99_ms']} ms |",
        f"| Latency drift (p99 vs p50) | {t4['drift_pct']:+.1f}% |",
        f"| Stability | {t4['stability']} |",
        f"| Errors | {t4['errors']}/{t4['n']} |",
        "",
        "---",
        "",
        "> Tested on Hugging Face Spaces shared infrastructure.",
        "> Cold start (first request after idle) is excluded; results reflect warm-instance performance.",
        "> For production SLA deployments, dedicated infrastructure is recommended.",
    ]

    report = "\n".join(lines)
    with open("API_BENCHMARK.md", "w") as f:
        f.write(report)
    print(f"\nReport written → API_BENCHMARK.md")
    return report


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    print("\nWaveSign Live API Benchmark")
    print(f"Target: {BASE_URL}\n")

    warmup()

    run_date = time.strftime("%Y-%m-%d")
    t1 = run_t1()
    t2 = run_t2()
    t3 = run_t3()
    t4 = run_t4()

    raw = {"date": run_date, "base_url": BASE_URL,
           "t1": t1, "t2": t2, "t3": t3, "t4": t4}
    with open("api_benchmark_raw.json", "w") as f:
        json.dump(raw, f, indent=2)
    print(f"Raw data written  → api_benchmark_raw.json")

    write_report(t1, t2, t3, t4, run_date)
    print("\nDone.\n")


if __name__ == "__main__":
    main()
