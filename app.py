import streamlit as st
import requests
import re
from fpdf import FPDF
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Meeting Intelligence",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e8f0; }
.hero-title {
    font-size: 3rem; font-weight: 700;
    background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 0.25rem; line-height: 1.1;
}
.hero-sub { color: #6b7280; font-size: 1.05rem; margin-bottom: 2.5rem; }
.card { background: #13131f; border: 1px solid #1f1f35; border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem; }
.card-header { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #6b7280; margin-bottom: 0.75rem; font-family: 'JetBrains Mono', monospace; }
.tag-purple { color: #a78bfa; } .tag-blue { color: #60a5fa; } .tag-green { color: #34d399; } .tag-red { color: #f87171; } .tag-yellow { color: #fbbf24; }
.bullet-item { display: flex; align-items: flex-start; gap: 0.6rem; padding: 0.5rem 0; border-bottom: 1px solid #1a1a2e; font-size: 0.92rem; color: #c4c4d4; line-height: 1.5; }
.bullet-item:last-child { border-bottom: none; }
.dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 0.45rem; flex-shrink: 0; }
.dot-purple { background: #a78bfa; } .dot-blue { background: #60a5fa; } .dot-green { background: #34d399; } .dot-red { background: #f87171; }
.action-card { background: #0f0f1e; border: 1px solid #1f1f35; border-radius: 12px; padding: 0.9rem 1.1rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.75rem; }
.assignee-badge { background: #1e1340; color: #a78bfa; border-radius: 6px; padding: 0.2rem 0.6rem; font-size: 0.78rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
.deadline-badge { background: #0f2318; color: #34d399; border-radius: 6px; padding: 0.2rem 0.6rem; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
.status-pill { display: inline-flex; align-items: center; gap: 0.35rem; background: #0d1f14; color: #34d399; border: 1px solid #1a3d28; border-radius: 999px; padding: 0.3rem 0.9rem; font-size: 0.8rem; font-weight: 500; }
.detected-pill { display: inline-flex; align-items: center; gap: 0.35rem; background: #1e1340; color: #a78bfa; border: 1px solid #3b1d8a; border-radius: 999px; padding: 0.25rem 0.8rem; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; margin: 0.2rem; }
.speaker-box { background: #13131f; border: 1px solid #2a2a45; border-radius: 12px; padding: 1.2rem; margin-bottom: 0.75rem; }
.section-divider { border: none; border-top: 1px solid #1a1a2e; margin: 2rem 0; }
.transcript-box { background: #0a0a12; border: 1px solid #1f1f35; border-radius: 12px; padding: 1.2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #8888aa; max-height: 200px; overflow-y: auto; line-height: 1.6; }
.stButton > button { background: linear-gradient(135deg, #7c3aed, #4f46e5); color: white; border: none; border-radius: 10px; padding: 0.6rem 1.5rem; font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 0.9rem; cursor: pointer; width: 100%; transition: opacity 0.2s; }
.stButton > button:hover { opacity: 0.85; }
.stTextInput > div > div > input { background: #13131f; border: 1px solid #2a2a45; color: #e8e8f0; border-radius: 10px; font-family: 'Space Grotesk', sans-serif; }
.stDownloadButton > button { background: #13131f; color: #a78bfa; border: 1px solid #2a2a45; border-radius: 10px; font-family: 'Space Grotesk', sans-serif; font-weight: 500; }
div[data-testid="stFileUploader"] { background: #0d0d1a; border: 2px dashed #2a2a45; border-radius: 16px; padding: 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def sanitize(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    for k, v in {"\u2013":"-","\u2014":"-","\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',"\u2022":"-","\u2026":"...","\u2192":"->","\u2713":"v","\u26a0":"!"}.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def get_speaker_letters_from_transcript(transcript: str) -> list:
    letters = sorted(set(re.findall(r'\[Speaker ([A-Z])\]', transcript)))
    return letters if letters else ["A", "B"]


def generate_txt(data: dict, transcript: str) -> bytes:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["="*60, "  MEETING INTELLIGENCE REPORT", f"  Generated: {now}", "="*60, "", "SUMMARY", "-"*40]
    for s in data.get("summary", []): lines.append(f"  * {s}")
    lines += ["", "ACTION ITEMS", "-"*40]
    for a in data.get("action_items", []):
        dl = f" [{a.get('deadline','-')}]" if a.get("deadline") else ""
        lines.append(f"  -> {a.get('assignee','?')} : {a.get('task','')}{dl}")
    lines += ["", "DECISIONS", "-"*40]
    for d in data.get("decisions", []): lines.append(f"  v {d}")
    lines += ["", "RISKS & BLOCKERS", "-"*40]
    for r in data.get("risks", []): lines.append(f"  ! {r}")
    lines += ["", "", "FULL TRANSCRIPT", "-"*40, transcript, ""]
    return "\n".join(lines).encode("utf-8")


def generate_pdf(data: dict, transcript: str) -> bytes:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(100, 80, 200)
    pdf.multi_cell(page_w, 12, sanitize("Meeting Intelligence Report"), align="L")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 140)
    pdf.multi_cell(page_w, 6, sanitize(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), align="L")
    pdf.ln(4)

    def section(title, color, items, mode="bullet"):
        pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(*color)
        pdf.multi_cell(page_w, 8, sanitize(title), align="L")
        pdf.set_draw_color(*color)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(3); pdf.set_font("Helvetica", "", 9); pdf.set_text_color(50, 50, 70)
        for item in items:
            if mode == "bullet": pdf.multi_cell(page_w, 6, sanitize(f"  - {item}"), align="L")
            elif mode == "action":
                dl = f"  [{item.get('deadline','-')}]" if item.get("deadline") else ""
                pdf.multi_cell(page_w, 6, sanitize(f"  -> {item.get('assignee','?')} : {item.get('task','')}{dl}"), align="L")
            pdf.ln(1)
        pdf.ln(4)

    section("SUMMARY", (120,80,220), data.get("summary",[]))
    section("ACTION ITEMS", (60,120,200), data.get("action_items",[]), mode="action")
    section("DECISIONS", (40,160,120), data.get("decisions",[]))
    section("RISKS & BLOCKERS", (200,80,80), data.get("risks",[]))
    pdf.set_font("Helvetica","B",10); pdf.set_text_color(80,80,120)
    pdf.multi_cell(page_w, 8, "FULL TRANSCRIPT", align="L")
    pdf.set_draw_color(80,80,120)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w-pdf.r_margin, pdf.get_y())
    pdf.ln(3); pdf.set_font("Helvetica","",8); pdf.set_text_color(80,80,100)
    pdf.multi_cell(page_w, 5, sanitize(transcript[:5000]+("..." if len(transcript)>5000 else "")), align="L")
    return bytes(pdf.output())


def render_results(data: dict):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="card"><div class="card-header tag-purple">📋 Summary</div>', unsafe_allow_html=True)
        for s in data.get("summary",[]): st.markdown(f'<div class="bullet-item"><div class="dot dot-purple"></div><span>{s}</span></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-header tag-blue">✅ Decisions</div>', unsafe_allow_html=True)
        for d in data.get("decisions",[]): st.markdown(f'<div class="bullet-item"><div class="dot dot-blue"></div><span>{d}</span></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><div class="card-header tag-green">⚡ Action Items</div>', unsafe_allow_html=True)
        for a in data.get("action_items",[]):
            dl_html = f'<span class="deadline-badge">📅 {a.get("deadline","—")}</span>' if a.get("deadline") else ""
            st.markdown(f'<div class="action-card"><span class="assignee-badge">{a.get("assignee","?")}</span><span style="flex:1;font-size:0.88rem;color:#c4c4d4">{a.get("task","")}</span>{dl_html}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-header tag-red">⚠️ Risks & Blockers</div>', unsafe_allow_html=True)
        for r in data.get("risks",[]): st.markdown(f'<div class="bullet-item"><div class="dot dot-red"></div><span>{r}</span></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
defaults = {"transcript":"","results":None,"uploaded":False,"speaker_map":{},"speaker_step":"idle","num_speakers":2}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🎙️ Meeting Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Upload your Teams recording · Get instant summaries, action items & decisions</div>', unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown("### Upload Meeting")

# Number of speakers slider
num_speakers = st.slider(
    "Expected number of speakers in the video",
    min_value=1, max_value=6, value=st.session_state.num_speakers,
    help="Set this correctly to improve speaker detection accuracy"
)
st.session_state.num_speakers = num_speakers

uploaded_file = st.file_uploader(
    "Drop your Teams recording or transcript",
    type=["mp4","mkv","mov","avi","webm","txt","pdf","docx"],
    help="Video files will be transcribed automatically using AssemblyAI"
)

if uploaded_file and not st.session_state.uploaded:
    with st.spinner(f"⏳ Processing file with {num_speakers} speaker(s)..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        try:
            res = requests.post(
                f"{API_URL}/upload",
                files=files,
                params={"num_speakers": num_speakers},
                timeout=3600
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.uploaded = True
                st.session_state.speaker_step = "detecting"
                speakers_found = data.get("speakers_found", ["A","B"])
                st.markdown(f'<div class="status-pill">✅ {data["filename"]} processed · {data["transcript_length"]:,} chars · {len(speakers_found)} speaker(s) found</div>', unsafe_allow_html=True)
                tr = requests.get(f"{API_URL}/transcript").json()
                st.session_state.transcript = tr.get("transcript","")
            else:
                st.error(f"Upload failed: {res.json().get('detail','Unknown error')}")
        except Exception as e:
            st.error(f"Connection error: {e}")

if st.session_state.transcript:
    with st.expander("📄 View Transcript Preview"):
        st.markdown(f'<div class="transcript-box">{st.session_state.transcript[:1000]}{"..." if len(st.session_state.transcript)>1000 else ""}</div>', unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── Speaker Detection ─────────────────────────────────────────────────────────
if st.session_state.uploaded:
    st.markdown("### 👥 Speaker Names")

    if st.session_state.speaker_step == "detecting":
        with st.spinner("🔍 Auto detecting speaker names from transcript..."):
            try:
                res = requests.post(f"{API_URL}/detect-speakers", timeout=30)
                if res.status_code == 200:
                    speaker_map = res.json().get("speaker_map", {})
                    detected = {k: v for k, v in speaker_map.items() if v}
                    st.session_state.speaker_map = speaker_map
                    st.session_state.speaker_step = "detected" if detected else "manual"
                else:
                    st.session_state.speaker_step = "manual"
            except Exception:
                st.session_state.speaker_step = "manual"
        st.rerun()

    elif st.session_state.speaker_step == "detected":
        speaker_map = st.session_state.speaker_map
        detected = {k: v for k, v in speaker_map.items() if v}
        not_detected = {k: v for k, v in speaker_map.items() if not v}

        st.markdown('<div class="speaker-box">', unsafe_allow_html=True)
        st.markdown('<div class="card-header tag-green">✅ Auto Detected Names</div>', unsafe_allow_html=True)
        pills = "".join([f'<span class="detected-pill">Speaker {k} → {v}</span>' for k, v in detected.items()])
        st.markdown(pills, unsafe_allow_html=True)
        if not_detected:
            st.markdown(f'<div style="color:#6b7280;font-size:0.85rem;margin-top:0.5rem">⚠️ Could not detect: Speaker {", ".join(not_detected.keys())}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✅ Use These Names", use_container_width=True):
                try:
                    requests.post(f"{API_URL}/map-speakers", json={"speaker_map": detected}, timeout=30)
                    tr = requests.get(f"{API_URL}/transcript").json()
                    st.session_state.transcript = tr.get("transcript","")
                    st.session_state.speaker_step = "done"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with c2:
            if st.button("✏️ Edit Names", use_container_width=True):
                st.session_state.speaker_step = "manual"
                st.rerun()
        with c3:
            if st.button("⏭️ Skip", use_container_width=True):
                st.session_state.speaker_step = "done"
                st.rerun()

    elif st.session_state.speaker_step == "manual":
        # Auto detect speaker letters from transcript
        letters = get_speaker_letters_from_transcript(st.session_state.transcript)
        speaker_map = st.session_state.speaker_map or {l: None for l in letters}

        st.markdown('<div class="speaker-box">', unsafe_allow_html=True)
        st.markdown('<div class="card-header tag-yellow">⚠️ Enter Speaker Names Manually</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#6b7280;font-size:0.85rem;margin-bottom:1rem">Leave blank to keep as Speaker A, Speaker B etc.</div>', unsafe_allow_html=True)

        # Dynamically create input for each speaker found
        cols = st.columns(min(len(letters), 3))
        manual_map = {}
        for i, letter in enumerate(letters):
            with cols[i % 3]:
                existing = speaker_map.get(letter) or ""
                name = st.text_input(
                    f"Speaker {letter}",
                    value=existing,
                    placeholder=f"e.g. John",
                    key=f"speaker_input_{letter}"
                )
                if name.strip():
                    manual_map[letter] = name.strip()

        st.markdown("</div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Apply Names", use_container_width=True):
                if manual_map:
                    try:
                        requests.post(f"{API_URL}/map-speakers", json={"speaker_map": manual_map}, timeout=30)
                        tr = requests.get(f"{API_URL}/transcript").json()
                        st.session_state.transcript = tr.get("transcript","")
                        st.session_state.speaker_map = manual_map
                    except Exception as e:
                        st.error(f"Error: {e}")
                st.session_state.speaker_step = "done"
                st.rerun()
        with c2:
            if st.button("⏭️ Skip", use_container_width=True):
                st.session_state.speaker_step = "done"
                st.rerun()

    elif st.session_state.speaker_step == "done":
        applied = {k: v for k, v in st.session_state.speaker_map.items() if v}
        if applied:
            pills = "".join([f'<span class="detected-pill">Speaker {k} → {v}</span>' for k, v in applied.items()])
            st.markdown(f'<div style="margin-bottom:0.5rem">{pills}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── Analyse ───────────────────────────────────────────────────────────────────
if st.session_state.uploaded and st.session_state.speaker_step in ["done", "idle"]:
    if st.button("🚀 Analyse Meeting", use_container_width=True):
        with st.spinner("🤖 Extracting insights with Groq LLaMA3..."):
            try:
                res = requests.post(f"{API_URL}/extract", timeout=60)
                if res.status_code == 200:
                    st.session_state.results = res.json()["data"]
                else:
                    st.error(f"Extraction failed: {res.json().get('detail')}")
            except Exception as e:
                st.error(f"Error: {e}")

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.results:
    st.markdown("### Meeting Insights")
    render_results(st.session_state.results)
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    st.markdown("### Export Report")
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.download_button(
            label="📄 Download as TXT",
            data=generate_txt(st.session_state.results, st.session_state.transcript),
            file_name=f"meeting_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain", use_container_width=True
        )
    with dcol2:
        st.download_button(
            label="📑 Download as PDF",
            data=generate_pdf(st.session_state.results, st.session_state.transcript),
            file_name=f"meeting_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf", use_container_width=True
        )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    st.markdown("### 💬 Ask About the Meeting")
    question = st.text_input("", placeholder="e.g. What did Priyanka say about the project?")
    if st.button("Ask", use_container_width=False) and question:
        with st.spinner("Thinking..."):
            try:
                res = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=30)
                if res.status_code == 200:
                    st.markdown(f'<div class="card"><div class="card-header tag-blue">Answer</div><div style="color:#c4c4d4;font-size:0.95rem;line-height:1.6">{res.json()["answer"]}</div></div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")

# ── Reset ─────────────────────────────────────────────────────────────────────
if st.session_state.uploaded:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Reset — Upload New Meeting", use_container_width=True):
        st.session_state.transcript = ""
        st.session_state.results = None
        st.session_state.uploaded = False
        st.session_state.speaker_map = {}
        st.session_state.speaker_step = "idle"
        st.session_state.num_speakers = 2
        st.rerun()
