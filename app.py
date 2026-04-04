"""
WaveSign — Invisible File Authentication
UI matching wavesign_merged.html: cool blue, dot-grid, card layout, JetBrains Mono
"""

import streamlit as st
from PIL import Image
import json, io, zipfile
from core import sign_image, embed_watermark, verify_image, detect_mode
from pdf_utils import sign_pdf, verify_pdf, get_pdf_page_count

st.set_page_config(
    page_title="WaveSign — Invisible File Authentication",
    page_icon="🔏", layout="wide",
    initial_sidebar_state="collapsed"
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:          #f2f4f8;
  --white:       #ffffff;
  --surface:     #f8f9fc;
  --border:      #dde2ec;
  --border2:     #c4ccda;
  --accent:      #1a6cff;
  --accent-lt:   #eaf0ff;
  --accent-dk:   #0f4fd4;
  --ink:         #141c2e;
  --ink2:        #3d4f6a;
  --muted:       #7a8fa8;
  --muted2:      #aab8cc;
  --ok:          #00986a;
  --ok-bg:       #e6f6f1;
  --err:         #d42050;
  --err-bg:      #fce9ef;
  --warm:        #f5f0e8;
  --warm-bd:     #e8dfc8;
  --r:           8px;
  --rs:          5px;
}

html, body, [class*="css"] {
  font-family: 'Source Sans 3', sans-serif !important;
  background: var(--bg) !important;
  color: var(--ink);
  font-size: 15px;
  line-height: 1.6;
}

.stApp { background: var(--bg) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 48px 4rem !important; max-width: 960px !important; margin: 0 auto !important; }

/* dot grid */
.stApp::before {
  content: '';
  position: fixed; inset: 0;
  background-image: radial-gradient(circle, rgba(26,108,255,0.06) 1px, transparent 1px);
  background-size: 28px 28px;
  pointer-events: none; z-index: 0;
}

.ws-wrap {
  position: relative; z-index: 1;
  max-width: 100%; margin: 0 auto;
  padding: 0;
}

/* header */
.ws-hdr {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 36px; padding-bottom: 18px;
  border-bottom: 1px solid var(--border);
}
.logo { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; color: var(--ink); }
.logo span { color: var(--accent); }
.logo-tag {
  display: inline-block; margin-left: 8px;
  font-size: 10px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase;
  color: var(--muted); border: 1px solid var(--border2); background: var(--white);
  padding: 2px 7px; border-radius: 3px; vertical-align: middle; position: relative; top: -2px;
}
.hdr-status { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); font-weight: 500; }
.sdot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--ok);
  box-shadow: 0 0 0 2px rgba(0,152,106,0.2); display: inline-block;
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }

/* hero */
.hero {
  background: var(--white); border: 1px solid var(--border); border-radius: var(--r);
  padding: 40px 44px 36px; margin-bottom: 28px; text-align: center;
  box-shadow: 0 1px 4px rgba(20,28,46,0.06); position: relative; overflow: hidden;
}
.hero::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent), #55aaff 50%, var(--accent));
}
.hero-eye {
  font-size: 11px; font-weight: 600; letter-spacing: 3px; text-transform: uppercase;
  color: var(--accent); margin-bottom: 14px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.hero-eye::before, .hero-eye::after {
  content: ''; display: block; width: 28px; height: 1px; background: var(--accent); opacity: 0.4;
}
.hero-title { font-size: 32px; font-weight: 700; letter-spacing: -0.5px; color: var(--ink); line-height: 1.2; margin-bottom: 14px; }
.hero-div { width: 40px; height: 2px; background: linear-gradient(90deg, var(--accent), #55aaff); border-radius: 2px; margin: 0 auto 16px; }
.hero-sub { font-size: 16px; color: var(--ink2); max-width: 520px; margin: 0 auto; line-height: 1.7; }
.trust-row { display: flex; justify-content: center; gap: 10px; margin-top: 22px; flex-wrap: wrap; }
.trust-pill {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: var(--ink2);
  background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 5px 13px;
}

/* tabs */
.stTabs [data-baseweb="tab-list"] {
  background: var(--white) !important; border: 1px solid var(--border) !important;
  border-radius: var(--r) !important; padding: 5px !important; gap: 4px !important;
  box-shadow: 0 1px 3px rgba(20,28,46,0.05) !important; margin-bottom: 24px !important;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Source Sans 3', sans-serif !important;
  font-size: 13px !important; font-weight: 600 !important; color: var(--muted) !important;
  border-radius: 6px !important; padding: 10px 16px !important; background: transparent !important; border: none !important;
}
.stTabs [aria-selected="true"] {
  color: var(--accent) !important; background: var(--accent-lt) !important; font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 0 !important; }

/* step card */
.sc {
  background: var(--white); border: 1px solid var(--border); border-radius: var(--r);
  overflow: hidden; box-shadow: 0 1px 3px rgba(20,28,46,0.05); margin-bottom: 14px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.sc:hover { box-shadow: 0 3px 14px rgba(26,108,255,0.09); border-color: #b3caff; }
.sc-hd {
  display: flex; align-items: center; gap: 12px;
  padding: 13px 18px; border-bottom: 1px solid var(--border); background: var(--surface);
}
.sc-badge {
  width: 24px; height: 24px; border-radius: 50%; background: var(--accent-lt);
  border: 1.5px solid #b3caff; display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: var(--accent); flex-shrink: 0;
}
.sc-title { font-size: 13px; font-weight: 700; color: var(--ink); letter-spacing: 0.2px; text-transform: uppercase; }
.sc-body { padding: 20px; }

/* info box */
.ibox {
  background: var(--warm); border: 1px solid var(--warm-bd); border-radius: var(--rs);
  padding: 11px 14px; font-size: 13px; color: var(--ink2); margin-bottom: 14px; line-height: 1.55;
}

/* field label */
.flabel { font-size: 12px; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }

/* format badges */
.fmt-row { display: flex; gap: 6px; justify-content: center; margin-top: 14px; }
.fmt-badge {
  font-size: 10px; font-weight: 700; letter-spacing: 1px; color: var(--ink2);
  border: 1px solid var(--border2); background: var(--white); padding: 3px 9px; border-radius: 3px;
}

/* detect badge */
.dbadge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; border-radius: 20px; padding: 4px 12px; margin-top: 8px; }
.db-doc { background: var(--accent-lt); color: var(--accent); border: 1px solid #b3caff; }
.db-img { background: #fff8ec; color: #b06010; border: 1px solid #f0d090; }
.db-pdf { background: var(--ok-bg); color: var(--ok); border: 1px solid #90d8c0; }

/* inputs */
.stTextInput > div > div > input {
  background: var(--bg) !important; border: 1.5px solid var(--border2) !important;
  border-radius: var(--rs) !important; padding: 12px 14px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 13px !important; color: var(--ink) !important; letter-spacing: 1px !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(26,108,255,0.1) !important; background: var(--white) !important;
}

/* file uploader */
div[data-testid="stFileUploader"] { background: var(--surface) !important; border: 1.5px dashed var(--border2) !important; border-radius: var(--rs) !important; }
div[data-testid="stFileUploader"]:hover { border-color: var(--accent) !important; background: var(--accent-lt) !important; }

/* buttons */
.stButton > button {
  background: var(--accent) !important; color: white !important; border: none !important;
  border-radius: var(--rs) !important; font-family: 'Source Sans 3', sans-serif !important;
  font-size: 15px !important; font-weight: 700 !important; padding: 15px 20px !important;
  width: 100% !important; min-height: 50px !important;
  box-shadow: 0 2px 8px rgba(26,108,255,0.28) !important; transition: all 0.15s !important;
}
.stButton > button:hover { background: var(--accent-dk) !important; box-shadow: 0 4px 18px rgba(26,108,255,0.38) !important; transform: translateY(-1px) !important; }
.stDownloadButton > button {
  background: var(--accent) !important; color: white !important; border: none !important;
  border-radius: var(--rs) !important; font-size: 14px !important; font-weight: 700 !important;
  width: 100% !important; min-height: 46px !important; box-shadow: 0 2px 8px rgba(26,108,255,0.28) !important;
}
.stDownloadButton > button:hover { background: var(--accent-dk) !important; }

/* side cards */
.scard { background: var(--white); border: 1px solid var(--border); border-radius: var(--r); overflow: hidden; box-shadow: 0 1px 3px rgba(20,28,46,0.05); margin-bottom: 14px; }
.scard-hd { padding: 11px 16px; border-bottom: 1px solid var(--border); background: var(--surface); font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted); }
.scard-bd { padding: 14px 16px; }

/* metrics */
.mrow { display: flex; align-items: center; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid var(--border); }
.mrow:last-child { border-bottom: none; }
.mlbl { font-size: 12px; color: var(--muted); font-weight: 500; }
.mval { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; padding: 2px 9px; border-radius: 4px; }
.mv-ok  { color: var(--ok);  background: var(--ok-bg);  }
.mv-err { color: var(--err); background: var(--err-bg); }
.mv-neu { color: var(--muted); background: var(--surface); border: 1px solid var(--border); }

/* results */
.res-ok  { background: var(--ok-bg);  border: 1.5px solid #90d8c0; border-radius: var(--r); padding: 20px; text-align: center; margin-bottom: 14px; }
.res-err { background: var(--err-bg); border: 1.5px solid #f0a0b8; border-radius: var(--r); padding: 20px; text-align: center; margin-bottom: 14px; }
.res-icon  { font-size: 28px; margin-bottom: 8px; }
.res-title { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.res-sub   { font-family: 'JetBrains Mono', monospace; font-size: 11px; opacity: 0.75; }

/* ready */
.ready { display: flex; flex-direction: column; align-items: center; padding: 28px 10px; gap: 10px; text-align: center; }
.ready-lbl { font-size: 12px; font-weight: 600; color: var(--muted2); }

/* sig hash */
.sighash { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--accent); background: var(--accent-lt); border: 1px solid #b3caff; border-radius: var(--rs); padding: 8px 12px; word-break: break-all; line-height: 1.7; margin: 8px 0; }

/* how it works */
.how-step { display: flex; gap: 16px; align-items: flex-start; padding: 16px 0; border-bottom: 1px solid var(--border); }
.how-step:last-child { border-bottom: none; }
.how-num { font-size: 11px; font-weight: 700; color: var(--accent); background: var(--accent-lt); border: 1.5px solid #b3caff; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.how-title { font-size: 14px; font-weight: 700; color: var(--ink); margin-bottom: 4px; }
.how-desc  { font-size: 13px; color: var(--ink2); line-height: 1.55; }

.ucard { background: var(--surface); border: 1px solid var(--border); border-radius: var(--rs); padding: 12px 14px; margin-bottom: 8px; display: flex; gap: 12px; align-items: flex-start; }
.uicon  { font-size: 18px; line-height: 1; margin-top: 1px; }
.utitle { font-size: 13px; font-weight: 700; color: var(--ink); margin-bottom: 3px; }
.udesc  { font-size: 12px; color: var(--muted); line-height: 1.45; }

/* footer */
.ws-ftr { margin-top: 52px; padding-top: 18px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--muted); }
.ftr-links { display: flex; gap: 18px; }
.ftr-links a { color: var(--muted); text-decoration: none; font-weight: 500; }
.ftr-links a:hover { color: var(--ink2); }

@media(max-width:680px){
  .hero { padding: 28px 20px 24px; }
  .hero-title { font-size: 24px; }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ── wrapper + header ──────────────────────────────────────────────────
st.markdown("""
<div class="ws-wrap">
<div class="ws-hdr">
  <div>
    <span class="logo">Wave<span>Sign</span></span>
    <span class="logo-tag">Beta</span>
  </div>
  <div class="hdr-status"><span class="sdot"></span> System online</div>
</div>

<div class="hero">
  <div class="hero-eye">Invisible File Signing</div>
  <div class="hero-title">Protect your files with an invisible signature</div>
  <div class="hero-div"></div>
  <div class="hero-sub">Upload your file, set a secret key, and get a signed copy you can share.
  Anyone with the key can instantly verify the file is authentic and untampered.</div>
  <div class="trust-row">
    <div class="trust-pill">🔏 No accounts needed</div>
    <div class="trust-pill">🔑 Key never stored</div>
    <div class="trust-pill">⚡ Instant verification</div>
    <div class="trust-pill">🖼 Images &amp; PDFs</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔏  Sign a File", "🔍  Verify a File", "❓  How It Works", "⚡  API"])


# ══════════════════════════════════════════════════════════════════════
# TAB 1 — SIGN
# ══════════════════════════════════════════════════════════════════════
with tab1:
    L, R = st.columns([1, 0.56], gap="large")

    with L:
        # Step 1
        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">1</span>
          <span class="sc-title">Upload Your File</span>
        </div><div class="sc-body">
          <div class="ibox">Supports images (PNG, JPG, WEBP) and documents (PDF).</div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader("file", type=["png","jpg","jpeg","webp","pdf"],
                                    key="su", label_visibility="collapsed")

        _mode = None
        if uploaded:
            mb = uploaded.size / 1048576
            if mb > 20: st.warning(f"Large file ({mb:.1f} MB) — may be slow on free hosting.")
            elif mb > 8: st.info(f"{mb:.1f} MB — will take a few extra seconds.")

            if uploaded.name.lower().endswith(".pdf"):
                n = get_pdf_page_count(uploaded.getvalue())
                st.markdown(f'<span class="dbadge db-pdf">📑 PDF — {n} page{"s" if n!=1 else ""}</span>', unsafe_allow_html=True)
                _mode = "document"
            else:
                _m = detect_mode(Image.open(io.BytesIO(uploaded.getvalue())))
                _mode = _m
                if _m == "color":
                    st.markdown('<span class="dbadge db-img">🖼️ Color image</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="dbadge db-doc">📄 Document</span>', unsafe_allow_html=True)

        st.markdown("""
          <div class="fmt-row">
            <span class="fmt-badge">PNG</span><span class="fmt-badge">JPG</span>
            <span class="fmt-badge">WEBP</span><span class="fmt-badge">PDF</span>
          </div>
        </div></div>
        """, unsafe_allow_html=True)

        # Step 2
        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">2</span>
          <span class="sc-title">Create Your Secret Key</span>
        </div><div class="sc-body">
          <div class="ibox">Choose any passphrase. You will need the same key to verify this file later. Keep it safe.</div>
          <div class="flabel">Passphrase</div>
        """, unsafe_allow_html=True)

        secret = st.text_input("key", placeholder="e.g. my-company-2024",
                               key="sk", type="password", label_visibility="collapsed")
        st.markdown("""
          <div style="font-size:12px;color:var(--muted);margin-top:8px">
            Your key is never sent to any server. It stays on your device only.
          </div>
        </div></div>
        """, unsafe_allow_html=True)

        sign_btn = st.button("Sign File →", key="sb")

    with R:
        if sign_btn and uploaded and secret:
            is_pdf = uploaded.name.lower().endswith(".pdf")
            base   = uploaded.name.rsplit(".", 1)[0]

            if is_pdf:
                with st.spinner("Signing all pages…"):
                    spdf, sigs, np_ = sign_pdf(uploaded.getvalue(), secret, strength=0.03)

                st.markdown(f"""
                <div class="scard"><div class="scard-hd">Signed Document</div><div class="scard-bd">
                  <div class="res-ok">
                    <div class="res-icon">📑</div>
                    <div class="res-title" style="color:var(--ok)">{np_} Page{"s" if np_!=1 else ""} Signed</div>
                    <div class="res-sub">Invisible signature embedded</div>
                  </div>
                </div></div>""", unsafe_allow_html=True)

                from pdf2image import convert_from_bytes as _cfb
                pv = _cfb(spdf, dpi=72, first_page=1, last_page=min(2, np_))
                st.markdown('<div class="scard"><div class="scard-hd">Page Preview</div><div class="scard-bd">', unsafe_allow_html=True)
                pc = st.columns(len(pv))
                for i,(col,pg) in enumerate(zip(pc,pv)):
                    with col:
                        st.markdown(f'<div style="text-align:center;font-size:10px;color:var(--muted);margin-bottom:2px">Page {i+1}</div>', unsafe_allow_html=True)
                        st.image(pg, use_container_width=True)
                st.markdown('</div></div>', unsafe_allow_html=True)

                cn,_ = st.columns([3,1])
                with cn: fname = st.text_input("Name", value=f"wavesign_{base}", key="dn", label_visibility="visible")
                fname = (fname or f"wavesign_{base}").strip()
                zb = io.BytesIO()
                with zipfile.ZipFile(zb,"w",zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(f"{fname}.pdf",  spdf)
                    zf.writestr(f"{fname}.json", json.dumps(sigs, indent=2))
                zb.seek(0)
                st.download_button("⬇ Download Signed Package", zb.getvalue(),
                                   file_name=f"{fname}.zip", mime="application/zip", use_container_width=True)
                st.markdown(f'<div style="font-size:11px;color:var(--muted);margin-top:6px;text-align:center">Contains: <code>{fname}.pdf</code> + verification file</div>', unsafe_allow_html=True)

            else:
                with st.spinner("Signing your file…"):
                    img = Image.open(uploaded)
                    m   = detect_mode(img)
                    wm  = embed_watermark(img, secret, strength=0.015 if m=="color" else 0.03, mode=m)
                    sig = sign_image(wm, secret, mode=m)

                st.markdown('<div class="scard"><div class="scard-hd">Your Signed File</div><div class="scard-bd">', unsafe_allow_html=True)
                c1,c2 = st.columns(2)
                with c1:
                    st.markdown('<div style="text-align:center;font-size:10px;font-weight:600;text-transform:uppercase;color:var(--muted);margin-bottom:3px">Original</div>', unsafe_allow_html=True)
                    st.image(img, use_container_width=True)
                with c2:
                    st.markdown('<div style="text-align:center;font-size:10px;font-weight:600;text-transform:uppercase;color:var(--accent);margin-bottom:3px">Signed</div>', unsafe_allow_html=True)
                    st.image(wm, use_container_width=True)
                st.markdown(f'<div class="sighash">{sig["sig_hash"][:48]}…</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)

                cn,_ = st.columns([3,1])
                with cn: fname = st.text_input("Name", value=f"wavesign_{base}", key="dn", label_visibility="visible", placeholder="e.g. contract_signed")
                fname = (fname or f"wavesign_{base}").strip()
                zb = io.BytesIO()
                with zipfile.ZipFile(zb,"w",zipfile.ZIP_DEFLATED) as zf:
                    ib = io.BytesIO(); wm.save(ib, format="PNG")
                    zf.writestr(f"{fname}.png",  ib.getvalue())
                    zf.writestr(f"{fname}.json", json.dumps(sig, indent=2))
                zb.seek(0)
                st.download_button("⬇ Download Signed Package", zb.getvalue(),
                                   file_name=f"{fname}.zip", mime="application/zip", use_container_width=True)
                st.markdown(f'<div style="font-size:11px;color:var(--muted);margin-top:6px;text-align:center">Contains: <code>{fname}.png</code> + verification file</div>', unsafe_allow_html=True)

        elif sign_btn:
            st.warning("Please upload a file and enter a secret key.")
        else:
            st.markdown("""
            <div class="scard"><div class="scard-hd">Your Signed File</div><div class="scard-bd">
              <div class="ready"><div style="font-size:26px;color:var(--muted2)">✦</div>
              <div class="ready-lbl">Ready to sign</div></div>
            </div></div>

            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 2 — VERIFY
# ══════════════════════════════════════════════════════════════════════
with tab2:
    L, R = st.columns([1, 0.56], gap="large")

    with L:
        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">1</span>
          <span class="sc-title">Upload Signed File</span>
        </div><div class="sc-body">
          <div class="ibox">Upload the signed image or PDF from your WaveSign package — not the original.</div>
        """, unsafe_allow_html=True)
        vf = st.file_uploader("Signed file", type=["png","jpg","jpeg","webp","pdf"],
                              key="vu", label_visibility="collapsed")
        st.markdown('</div></div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">2</span>
          <span class="sc-title">Upload Verification File</span>
        </div><div class="sc-body">
          <div class="ibox">Upload the <strong>.json</strong> verification file from your WaveSign package. Keep it safe — it cannot be recovered if lost.</div>
        """, unsafe_allow_html=True)
        sf = st.file_uploader("Verification file", type=["json"],
                              key="sfu", label_visibility="collapsed")
        st.markdown('</div></div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">3</span>
          <span class="sc-title">Enter Your Secret Key</span>
        </div><div class="sc-body">
          <div class="flabel">Passphrase</div>
        """, unsafe_allow_html=True)
        vk = st.text_input("vkey", placeholder="the key used when signing…",
                           key="vk", type="password", label_visibility="collapsed")
        st.markdown('</div></div>', unsafe_allow_html=True)

        vbtn = st.button("Check Authenticity →", key="vb")

    with R:
        if vbtn and vf and sf and vk:
            try:
                sd       = json.loads(sf.getvalue().decode("utf-8"))
                is_pdf   = vf.name.lower().endswith(".pdf")
                is_pdf_s = isinstance(sd, list)

                if is_pdf and is_pdf_s:
                    with st.spinner("Checking all pages…"):
                        res = verify_pdf(vf.getvalue(), vk, sd)
                    ok   = all(r["is_valid"] for r in res)
                    tot  = len(res)
                    fail = [str(r["page_index"]+1) for r in res if not r["is_valid"]]

                    if ok:
                        st.markdown(f"""<div class="res-ok">
                          <div class="res-icon">✅</div>
                          <div class="res-title" style="color:var(--ok)">Document Authentic</div>
                          <div class="res-sub">All {tot} pages verified — no changes detected</div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div class="res-err">
                          <div class="res-icon">❌</div>
                          <div class="res-title" style="color:var(--err)">Document Modified</div>
                          <div class="res-sub">Page{"s" if len(fail)>1 else ""} {", ".join(fail)} failed</div>
                        </div>""", unsafe_allow_html=True)

                    if tot > 1:
                        st.markdown('<div class="scard"><div class="scard-hd">Page Results</div><div class="scard-bd">', unsafe_allow_html=True)
                        for r in res:
                            ic  = "✅" if r["is_valid"] else "❌"
                            cls = "mv-ok" if r["is_valid"] else "mv-err"
                            lbl = "Authentic" if r["is_valid"] else "Modified"
                            st.markdown(f'<div class="mrow"><span class="mlbl">Page {r["page_index"]+1}</span><span class="mval {cls}">{ic} {lbl}</span></div>', unsafe_allow_html=True)
                        st.markdown('</div></div>', unsafe_allow_html=True)

                elif not is_pdf and not is_pdf_s:
                    image = Image.open(vf)
                    with st.spinner("Checking your file…"):
                        r = verify_image(image, vk, sd)

                    if r["is_valid"]:
                        st.markdown("""<div class="res-ok">
                          <div class="res-icon">✅</div>
                          <div class="res-title" style="color:var(--ok)">File is Authentic</div>
                          <div class="res-sub">Signature verified — no changes detected</div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        reason = "File modified after signing" if not r.get("spatial_hash_match", True) else "Wrong key or different signing account"
                        st.markdown(f"""<div class="res-err">
                          <div class="res-icon">❌</div>
                          <div class="res-title" style="color:var(--err)">Verification Failed</div>
                          <div class="res-sub">{reason}</div>
                        </div>""", unsafe_allow_html=True)

                    st.image(image, use_container_width=True)
                else:
                    st.error("Verification file doesn't match the uploaded file type.")

            except Exception as e:
                st.error(f"Error: {e}")

        elif vbtn:
            st.warning("Please complete all three steps.")
        else:
            st.markdown("""
            <div class="scard"><div class="scard-hd">Verification Result</div><div class="scard-bd">
              <div class="ready">
                <div style="font-size:26px;color:var(--muted2)">🔍</div>
                <div class="ready-lbl">Awaiting verification</div>
              </div>
            </div></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 3 — HOW IT WORKS
# ══════════════════════════════════════════════════════════════════════
with tab3:
    C1, C2 = st.columns([3, 2], gap="large")

    with C1:
        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">✍</span>
          <span class="sc-title">Signing a File</span>
        </div><div class="sc-body">""", unsafe_allow_html=True)

        for n, t, d in [
            ("1", "Upload your file", "Choose any image or PDF to protect. Format is detected automatically."),
            ("2", "Set a secret key", "Your passphrase locks the signature. Only someone with the same key can verify it. It never leaves your device."),
            ("3", "Download your package", "A ZIP with two files: the signed file (visually identical to the original) and a small verification file. Keep both together."),
        ]:
            st.markdown(f'<div class="how-step"><div class="how-num">{n}</div><div><div class="how-title">{t}</div><div class="how-desc">{d}</div></div></div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="sc" style="margin-top:14px"><div class="sc-hd">
          <span class="sc-badge">🔍</span>
          <span class="sc-title">Verifying a File</span>
        </div><div class="sc-body">""", unsafe_allow_html=True)

        for n, t, d in [
            ("1", "Upload the signed file", "Use the signed copy from your package — not the original."),
            ("2", "Upload the verification file", "The small .json file from your package. Without it, verification isn't possible."),
            ("3", "Enter your key", "WaveSign instantly tells you whether the file is authentic or has been changed since signing."),
        ]:
            st.markdown(f'<div class="how-step"><div class="how-num">{n}</div><div><div class="how-title">{t}</div><div class="how-desc">{d}</div></div></div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    with C2:
        st.markdown('<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-bottom:10px">Use Cases</div>', unsafe_allow_html=True)
        for ico, t, d in [
            ("📄", "Contracts & Documents", "Share a signed PDF — any edit is instantly caught on verification"),
            ("🖼️", "Images & Photos", "Prove your image hasn't been cropped, filtered, or altered"),
            ("🎨", "Creative Work", "Sign before publishing — verify origin and integrity later"),
            ("🔐", "Sensitive Files", "Any modification after signing invalidates the signature"),
        ]:
            st.markdown(f'<div class="ucard"><div class="uicon">{ico}</div><div><div class="utitle">{t}</div><div class="udesc">{d}</div></div></div>', unsafe_allow_html=True)

        st.markdown('<div class="scard" style="margin-top:14px"><div class="scard-hd">Important to Know</div><div class="scard-bd">', unsafe_allow_html=True)
        for tip in [
            "Always share the <strong>signed file</strong>, not the original",
            "Keep your <strong>verification file</strong> — it cannot be recovered",
            "Use the <strong>same key</strong> to sign and verify",
            "Signed files look <strong>identical</strong> to the original",
        ]:
            st.markdown(f'<div style="display:flex;gap:8px;padding:7px 0;border-bottom:1px solid var(--border);font-size:13px;color:var(--ink2);align-items:flex-start"><span style="color:var(--accent);font-weight:700;flex-shrink:0">→</span><span>{tip}</span></div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 4 — API ACCESS
# ══════════════════════════════════════════════════════════════════════
with tab4:
    AC, BC = st.columns([3, 2], gap="large")

    with AC:
        # Hero intro card
        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">⚡</span>
          <span class="sc-title">REST API — Workflow Integration</span>
        </div><div class="sc-body">
          <div class="ibox">
            The WaveSign REST API lets you embed invisible file signing and verification
            directly into your pipelines, scripts, and applications — no browser required.
            Every request is authenticated with your personal <strong>API token</strong>.
            Files are processed by the same proprietary signing engine that powers this app.
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:4px">
            <div class="trust-pill">🔐 Token-authenticated</div>
            <div class="trust-pill">📂 multipart/form-data</div>
            <div class="trust-pill">⚡ JSON responses</div>
            <div class="trust-pill">🖼 Images &amp; PDFs</div>
          </div>
        </div></div>
        """, unsafe_allow_html=True)

        # POST /sign card
        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">1</span>
          <span class="sc-title">POST /sign</span>
        </div><div class="sc-body">
          <div class="flabel">Endpoint</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;margin-bottom:14px;word-break:break-all;">
            POST &nbsp;https://roseluo-wavesign-api.hf.space/sign
          </div>
          <div class="flabel">Request — multipart/form-data</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;margin-bottom:14px;line-height:1.9">
            <span style="color:var(--accent)">file</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;image/PDF to sign (PNG · JPG · WEBP · PDF)<br>
            <span style="color:var(--accent)">key</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;your secret passphrase<br>
            <span style="color:var(--accent)">Authorization</span> &nbsp;Bearer &lt;your-api-token&gt;
          </div>
          <div class="flabel">Response — application/zip</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;margin-bottom:14px;line-height:1.9">
            <span style="color:var(--ok)">signed_package.zip</span><br>
            &nbsp;&nbsp;<span style="color:var(--muted)">└──</span> <span style="color:var(--ok)">signed.png / signed.pdf</span> &nbsp;watermarked file<br>
            &nbsp;&nbsp;<span style="color:var(--muted)">└──</span> <span style="color:var(--ok)">sig.json</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;signature file for verification
          </div>
          <div class="flabel">curl example</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:11.5px;background:var(--ink);color:#e2eaff;border-radius:var(--rs);padding:14px 16px;line-height:1.85;white-space:pre;overflow-x:auto">curl -X POST https://roseluo-wavesign-api.hf.space/sign \\
  -H "Authorization: Bearer &lt;your-api-token&gt;" \\
  -F "file=@document.pdf" \\
  -F "key=my-secret-passphrase" \\
  --output signed_package.zip</div>
        </div></div>
        """, unsafe_allow_html=True)

        # POST /verify card
        st.markdown("""
        <div class="sc"><div class="sc-hd">
          <span class="sc-badge">2</span>
          <span class="sc-title">POST /verify</span>
        </div><div class="sc-body">
          <div class="flabel">Endpoint</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;margin-bottom:14px;word-break:break-all;">
            POST &nbsp;https://roseluo-wavesign-api.hf.space/verify
          </div>
          <div class="flabel">Request — multipart/form-data</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;margin-bottom:14px;line-height:1.9">
            <span style="color:var(--accent)">file</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;the signed image or PDF<br>
            <span style="color:var(--accent)">sig_file</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;the .json signature file from signing<br>
            <span style="color:var(--accent)">key</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;your secret passphrase<br>
            <span style="color:var(--accent)">Authorization</span> &nbsp;Bearer &lt;your-api-token&gt;
          </div>
          <div class="flabel">Response — application/json</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;margin-bottom:14px;line-height:1.9">
            <span style="color:var(--ok)">is_valid</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;true / false<br>
            <span style="color:var(--ok)">verdict</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"AUTHENTIC" or "TAMPERED or INVALID KEY"<br>
            <span style="color:var(--ok)">similarity_score</span> &nbsp;&nbsp;0.0 – 1.0 confidence<br>
            <span style="color:var(--ok)">mode</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detected image mode (RGB · L · …)
          </div>
          <div class="flabel">curl example</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:11.5px;background:var(--ink);color:#e2eaff;border-radius:var(--rs);padding:14px 16px;line-height:1.85;white-space:pre;overflow-x:auto">curl -X POST https://roseluo-wavesign-api.hf.space/verify \\
  -H "Authorization: Bearer &lt;your-api-token&gt;" \\
  -F "file=@document_signed.pdf" \\
  -F "sig_file=@document_signed.json" \\
  -F "key=my-secret-passphrase"</div>
        </div></div>
        """, unsafe_allow_html=True)

    with BC:
        # Python example card
        st.markdown("""
        <div class="scard"><div class="scard-hd">Python Example</div><div class="scard-bd">
          <div style="font-family:'JetBrains Mono',monospace;font-size:11px;background:var(--ink);color:#e2eaff;border-radius:var(--rs);padding:14px 16px;line-height:1.85;white-space:pre;overflow-x:auto">import requests, zipfile, io

API_TOKEN = "&lt;your-api-token&gt;"
BASE_URL  = "https://roseluo-wavesign-api.hf.space"
HEADERS   = {"Authorization": f"Bearer {API_TOKEN}"}

# ── sign ─────────────────────────────
with open("document.pdf", "rb") as f:
    r = requests.post(f"{BASE_URL}/sign",
                      headers=HEADERS,
                      files={"file": f},
                      data={"key": "my-secret"})

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    signed = z.read("signed.pdf")
    sig    = z.read("sig.json")

with open("document_signed.pdf", "wb") as f: f.write(signed)
with open("document_signed.json", "wb") as f: f.write(sig)

# ── verify ───────────────────────────
with (open("document_signed.pdf", "rb") as pf,
      open("document_signed.json", "rb") as sf):
    r = requests.post(f"{BASE_URL}/verify",
                      headers=HEADERS,
                      files={"file": pf, "sig_file": sf},
                      data={"key": "my-secret"})
print(r.json())
# {"is_valid": true, "verdict": "AUTHENTIC", "similarity_score": 0.97}</div>
        </div></div>
        """, unsafe_allow_html=True)

        # Request access card
        st.markdown("""
        <div class="scard" style="margin-top:14px"><div class="scard-hd">Request API Access</div><div class="scard-bd">
          <div style="font-size:13px;color:var(--ink2);line-height:1.65;margin-bottom:14px">
            The WaveSign API is currently available on request.
            Reach out with a brief description of your use case and we'll send you an
            <strong>authentication token</strong> along with full integration documentation.
          </div>
          <div class="flabel">Contact</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;background:var(--accent-lt);border:1px solid #b3caff;border-radius:var(--rs);padding:10px 14px;color:var(--accent);font-weight:600;word-break:break-all;">
            rose.huiluo@gmail.com
          </div>
          <div style="font-size:12px;color:var(--muted);margin-top:10px;line-height:1.5">
            Please include your intended request volume and a short description of your
            integration so we can set the right rate limits for your token.
          </div>
        </div></div>
        """, unsafe_allow_html=True)

        # Key facts card
        st.markdown('<div class="scard" style="margin-top:14px"><div class="scard-hd">Key Facts</div><div class="scard-bd">', unsafe_allow_html=True)
        for lbl, val, cls in [
            ("Auth method",   "Bearer token",       "mv-neu"),
            ("File transfer", "multipart/form-data", "mv-neu"),
            ("Sign response", "ZIP archive",         "mv-neu"),
            ("Verify response", "JSON",              "mv-neu"),
            ("Max file size", "20 MB",               "mv-neu"),
            ("Formats",       "PNG · JPG · PDF",     "mv-neu"),
            ("GET /",         "API directory",       "mv-neu"),
        ]:
            st.markdown(f'<div class="mrow"><span class="mlbl">{lbl}</span><span class="mval {cls}">{val}</span></div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)


# ── footer + close wrapper ────────────────────────────────────────────
st.markdown("""
<div class="ws-ftr">
  <div class="ftr-links">
    <a href="https://github.com/roseluo/WaveSign" target="_blank">GitHub</a>
  </div>
  <div>WaveSign · Invisible File Authentication · © 2026 roseluo</div>
</div>
</div>
""", unsafe_allow_html=True)
