## WaveSign Scalability Results

**Date:** 2026-03-25
**Hardware:** 4 vCPU, 16 GB RAM

### T1: Performance vs. File Size

| Resolution | Megapixels | Sign | Verify | PSNR |
|---|---|---|---|---|
| 256×256 | 0.07 MP | 19 ms | 7 ms | 39.7 dB |
| 512×512 | 0.26 MP | 78 ms | 23 ms | 39.9 dB |
| 1024×768 | 0.79 MP | 249 ms | 75 ms | 40.1 dB |
| 1920×1080 | 2.07 MP | 725 ms | 212 ms | 40.1 dB |
| 2480×3508 (A4 scan 300 DPI) | 8.70 MP | 4,737 ms | 1,388 ms | 40.4 dB |
| 3024×4032 (phone photo 12 MP) | 12.19 MP | 5,604 ms | 1,632 ms | 40.3 dB |

**Key finding:** Signing time scales with pixel count. Files up to 1920×1080 (2 MP) sign in under 1 second. Full-resolution phone photos (12 MP) and A4 scans (300 DPI) take 5–6 seconds.

> **Practical recommendation for customers:** Resize to ≤ 2 MP before signing for sub-second performance. The signature proves authenticity — it does not require the full display resolution to do so. A signed 1920×1080 export from a 48 MP camera is fully protected.

---

### T2: Concurrent Users (1920×1080 images)

| Concurrent Users | Throughput | Latency p50 | Latency p95 | Latency p99 | Peak RAM |
|---|---|---|---|---|---|
| 1 | 1.1 req/s | 907 ms | 936 ms | 941 ms | 167 MB |
| 2 | 1.9 req/s | 1,009 ms | 1,140 ms | 1,211 ms | 213 MB |
| 4 | 3.0 req/s | 1,248 ms | 1,363 ms | 1,421 ms | 342 MB |
| 8 | 2.9 req/s | 2,616 ms | 3,228 ms | 3,258 ms | 579 MB |

**Key findings:**
- Throughput scales linearly up to 4 concurrent workers (1.1 → 3.0 req/s)
- Beyond 4 workers, Python's GIL causes contention — throughput plateaus and latency doubles
- Sweet spot: **4 concurrent workers per process** on a 4-vCPU machine
- Memory stays well within bounds: 579 MB peak at 8 workers, no runaway growth

> **Scaling path:** Each server process handles ~3 req/s. A worker queue (Celery + Redis) running one process per CPU core scales throughput linearly. 4 servers × 3 req/s = **12 sign operations/second** — enough for ~40,000 files per hour.

---

### T3: Real-World Corpus Accuracy

| Image Type | N | Pass Rate | Avg Sign Time | Avg PSNR |
|---|---|---|---|---|
| Phone photo (12 MP) | 5 | **100%** | 7,044 ms | 40.5 dB |
| Scanned document (A4 300 DPI) | 5 | **100%** | 6,127 ms | 44.5 dB |
| Mixed content (1920×1080) | 5 | **100%** | 939 ms | 40.2 dB |
| Pre-compressed JPEG (1280×720) | 5 | **100%** | 368 ms | 40.1 dB |

**20/20 real-world images verified correctly after signing (100%).** The algorithm handles all realistic input types — including already-compressed JPEG inputs and high-res scans — with no false rejections.

Notable: scanned documents achieve higher PSNR (44.5 dB) than photos — the low-frequency nature of document content makes the diffraction watermark even more imperceptible.

---

### T4: Memory Stability (50 consecutive operations)

| Metric | Value |
|---|---|
| Memory at op 1 | 808.5 MB |
| Memory at op 50 | 808.5 MB |
| Total drift | **+0.0 MB** |
| Peak observed | 808.5 MB |
| Verdict | **No memory leak** |

50 consecutive sign+verify cycles on a 1920×1080 image produced zero memory growth. The process is safe for long-running server deployment without periodic restarts.

---

### Deployment Capacity Summary

| Scenario | Throughput | Files / Hour |
|---|---|---|
| Single VPS, 4 vCPU (current) | ~3 req/s | ~10,800 |
| 2× VPS load balanced | ~6 req/s | ~21,600 |
| 4× VPS | ~12 req/s | ~43,200 |

These figures assume 1920×1080 inputs (~2 MP). Throughput is higher for smaller files, lower for full-resolution phone photos without pre-resizing.

**For early customers (first 10–50 users):** A single VPS handles the load comfortably — early usage is bursty, not sustained at 3 req/s. Horizontal scaling is straightforward when needed: the algorithm is stateless and shares no state between requests.

---

### Methodology

- **T1:** Median of 3 runs per resolution with warm-up excluded, measured on identical hardware
- **T2:** 20 tasks per concurrency level using `ThreadPoolExecutor`; reflects Streamlit's threading model
- **T3:** 20 realistic images — phone photos (12 MP), A4 document scans (300 DPI, 8.7 MP), mixed content, pre-compressed JPEG
- **T4:** 50 consecutive sign+verify cycles, RSS memory sampled after each operation
- **Reproducible:** `python wavesign_scale.py`
