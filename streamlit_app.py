"""
Streamlit frontend for NexAI.
Run: streamlit run streamlit_app.py
"""
import streamlit as st
import requests

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NexAI | AI Workspace",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }
body { background: radial-gradient(circle at 20% 0%, rgba(99,102,241,.16), transparent 34%), #0b1020; }
.block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #eaf0f8 !important; border-right: 1px solid #cbd5e1; }
[data-testid="stSidebar"] > div:first-child { background: #eaf0f8 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stMetricLabel"], [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #172033 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #172033; }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] [data-testid="stNumberInput"] div[data-baseweb="input"] { background: #fff !important; border-color: #94a3b8 !important; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #3730a3 !important; }
[data-testid="stSidebar"] [data-testid="stProgress"] > div { background: #cbd5e1; }
[data-testid="stSidebar"] hr { border-color: #cbd5e1; }
.hero-card { padding: 2rem; border: 1px solid rgba(148,163,184,.2); border-radius: 24px; background: linear-gradient(135deg, rgba(99,102,241,.18), rgba(15,23,42,.82)); box-shadow: 0 24px 70px rgba(0,0,0,.22); margin-bottom: 1.25rem; }
.hero-kicker { color: #a5b4fc; font-size: .78rem; text-transform: uppercase; letter-spacing: .15em; font-weight: 700; }
.hero-title { font-size: 2.1rem; line-height: 1.15; font-weight: 700; color: #f8fafc; margin: .45rem 0; }
.hero-subtitle { color: #cbd5e1; margin: 0; }
.auth-card { max-width: 680px; margin: 5vh auto 0; }
.auth-layout { max-width: 1080px; margin: 5vh auto 0; align-items: center; }
.auth-brand { padding: 2.5rem 1.5rem 2.5rem .25rem; }
.brand-mark { width: 54px; height: 54px; display:flex; align-items:center; justify-content:center; border-radius: 17px; background: linear-gradient(135deg,#818cf8,#6d28d9); color:white; font-size:1.7rem; box-shadow:0 10px 30px rgba(99,102,241,.35); }
.brand-name { display:block; color:#a78bfa !important; -webkit-text-fill-color:#a78bfa; font-size:3rem; line-height:1.15; font-weight:800; letter-spacing:-.045em; margin:1.3rem 0 .65rem; text-shadow:0 2px 18px rgba(139,92,246,.3); }
.brand-copy { color:#aebbd0; font-size:1.02rem; line-height:1.65; max-width:450px; }
.brand-feature { color:#dbe4f2; font-size:.9rem; padding:.8rem 0; border-bottom:1px solid rgba(148,163,184,.16); }
.brand-feature span { color:#a5b4fc; margin-right:.5rem; }
.st-key-nexai_auth_panel { padding:1.5rem 1.6rem; border:1px solid #dbe3ef; border-radius:22px; background:#f8fafc; color:#172033; box-shadow:0 26px 75px rgba(0,0,0,.24); }
.st-key-nexai_auth_panel [data-testid="stMarkdownContainer"],
.st-key-nexai_auth_panel [data-testid="stCaptionContainer"],
.st-key-nexai_auth_panel label,
.st-key-nexai_auth_panel p { color:#172033 !important; }
.auth-panel-title { font-size:1.5rem; font-weight:700; color:#111827; margin:.2rem 0; }
.auth-panel-subtitle { color:#475569; margin-bottom:1.25rem; font-size:.9rem; }
.st-key-nexai_auth_panel [data-testid="stTabs"] button { color:#334155 !important; }
.st-key-nexai_auth_panel [data-testid="stTabs"] button[aria-selected="true"] { color:#4338ca !important; }
.st-key-nexai_auth_panel [data-baseweb="input"] > div { background:#fff !important; border-color:#94a3b8 !important; }
.st-key-nexai_auth_panel input { color:#111827 !important; caret-color:#4f46e5; }
.st-key-nexai_auth_panel input::placeholder { color:#64748b !important; opacity:1; }
.st-key-nexai_auth_panel [data-testid="stForm"] { border:0; padding:0; }
.st-key-nexai_auth_panel [data-testid="stFormSubmitButton"] button { min-height:2.9rem; border-radius:10px; font-weight:650; background:#4f46e5; color:#fff; border:0; }
.st-key-nexai_auth_panel [data-testid="stFormSubmitButton"] button:hover { background:#4338ca; color:#fff; }
.st-key-nexai_auth_panel [data-testid="stAlert"] { color:#172033; }
.auth-footnote { color:#475569; font-size:.75rem; margin-top:.75rem; text-align:center; }
.section-heading { color: #e2e8f0; font-weight: 650; letter-spacing: -.02em; }

/* Dark glassmorphism cards */
.metric-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    backdrop-filter: blur(12px);
    margin-bottom: 0.75rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(99,102,241,0.2);
}
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #6366f1, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.metric-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
}
.metric-card[title] { cursor: help; }
.metric-description { color: #94a3b8; font-size: .78rem; margin-top: .35rem; }
.badge-ollama {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white; border-radius: 20px;
    padding: 2px 10px; font-size: 0.75rem; font-weight: 600;
}
.badge-groq {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    color: white; border-radius: 20px;
    padding: 2px 10px; font-size: 0.75rem; font-weight: 600;
}
.chat-msg-user {
    background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15));
    border-left: 3px solid #6366f1;
    border-radius: 0 12px 12px 0;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
}
.chat-msg-assistant {
    background: rgba(255,255,255,0.04);
    border-left: 3px solid #10b981;
    border-radius: 0 12px 12px 0;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
}
.perf-pill {
    display: inline-block;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.75rem;
    color: #a78bfa;
    margin: 2px;
}
.quota-bar-label {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8000"


def show_api_error(response: requests.Response, fallback: str) -> None:
    """Render the shared API error envelope, including Pydantic field details."""
    try:
        body = response.json()
    except ValueError:
        st.error(fallback)
        return

    error = body.get("error", fallback)
    if isinstance(error, dict):
        details = error.get("message", fallback)
        st.error(f"{error.get('code', 'request_error').replace('_', ' ').title()} (HTTP {response.status_code})")
        st.caption(str(details))
        return
    details = body.get("detail")
    st.error(f"{error.replace('_', ' ').title()} (HTTP {response.status_code})")
    if isinstance(details, list):
        for item in details:
            if isinstance(item, dict):
                st.caption(f"{item.get('field', 'request')}: {item.get('message', 'Invalid value')}")
            else:
                st.caption(str(item))
    elif details:
        st.caption(str(details))

# ── Session State ─────────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None


def auth_header() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api_post(path: str, payload: dict, auth: bool = True) -> requests.Response:
    headers = auth_header() if auth else {}
    return requests.post(f"{API_BASE}{path}", json=payload, headers=headers, timeout=120)


def api_get(path: str) -> requests.Response:
    return requests.get(f"{API_BASE}{path}", headers=auth_header(), timeout=30)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

def show_auth():
    st.markdown('<div class="hero-kicker" style="text-align:center; margin-bottom:1rem">AI WORKSPACE · PRIVATE BY DESIGN</div>', unsafe_allow_html=True)
    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown(
            '<div class="auth-brand">'
            '<div class="brand-mark">✦</div>'
            '<div class="brand-name">NexAI</div>'
            '<p class="brand-copy">A clear workspace for AI chat, model performance, and resume screening.</p>'
            '<div class="brand-feature"><span>✧</span> Work with local Ollama or Groq models</div>'
            '<div class="brand-feature"><span>✧</span> Track tokens and response performance</div>'
            '<div class="brand-feature"><span>✧</span> Screen resumes with explainable matching</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with right:
        with st.container(border=True, key="nexai_auth_panel"):
            st.markdown('<div class="auth-panel-title">Welcome back</div><div class="auth-panel-subtitle">Sign in to continue to your workspace.</div>', unsafe_allow_html=True)
            tab_login, tab_register = st.tabs(["Sign in", "Create account"])

            with tab_login:
                with st.form("login_form"):
                    username = st.text_input("Username", placeholder="your_username")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    submitted = st.form_submit_button("Sign in to NexAI", use_container_width=True, type="primary")

                if submitted:
                    try:
                        resp = requests.post(
                            f"{API_BASE}/v1/auth/token",
                            json={"username": username, "password": password},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.username = username
                            st.success("Signed in successfully.")
                            st.rerun()
                        else:
                            show_api_error(resp, "Sign in failed")
                    except requests.RequestException as e:
                        st.error(f"Could not connect to the API: {e}")

            with tab_register:
                with st.form("register_form"):
                    new_user = st.text_input("Username", placeholder="choose_username", key="reg_user")
                    new_pass = st.text_input("Password", type="password", placeholder="At least 8 characters", key="reg_pass")
                    submitted = st.form_submit_button("Create NexAI account", use_container_width=True, type="primary")

                if submitted:
                    try:
                        resp = requests.post(
                            f"{API_BASE}/v1/auth/register",
                            json={"username": new_user, "password": new_pass},
                            timeout=10,
                        )
                        if resp.status_code == 201:
                            st.success("Account created. Sign in to continue.")
                        else:
                            show_api_error(resp, "Account creation failed")
                    except requests.RequestException as e:
                        st.error(f"Could not connect to the API: {e}")
            st.markdown('<div class="auth-footnote">Your workspace is protected with token-based authentication.</div>', unsafe_allow_html=True)


def show_resume_screener(provider: str, model: str, temperature: float) -> None:
    """Render resume upload and ranked API results without importing backend code."""
    st.markdown(
        '<div class="hero-card"><div class="hero-kicker">Private candidate review</div>'
        '<div class="hero-title">📄 Screen Resumes</div>'
        '<p class="hero-subtitle">Compare resume evidence with job requirements. Ollama keeps processing local.</p></div>',
        unsafe_allow_html=True,
    )
    job_description = st.text_area("Job description", height=180, key="screen_job_description")
    skill_text = st.text_input("Required skills (optional, comma separated)", placeholder="Python, FastAPI, Docker")
    uploads = st.file_uploader("PDF resumes (up to 10 files, 5 MB each)", type=["pdf"], accept_multiple_files=True)
    if st.button("Screen", type="primary", use_container_width=True, key="screen_resumes_button"):
        if len(job_description.strip()) < 50:
            st.error("Job description must contain at least 50 characters.")
            return
        if not uploads:
            st.error("Upload at least one PDF resume.")
            return
        skills = [value.strip() for value in skill_text.split(",") if value.strip()]
        request_preview = {
            "job_description": job_description,
            "required_skills": skills or None,
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "files": [{"filename": item.name} for item in uploads],
        }
        files = [("files", (item.name, item.getvalue(), "application/pdf")) for item in uploads]
        with st.spinner("Screening resumes…"):
            try:
                form_data = [
                    ("job_description", job_description),
                    ("provider", provider),
                    ("temperature", str(temperature)),
                ]
                if model:
                    form_data.append(("model", model))
                form_data.extend(("required_skills", skill) for skill in skills)
                response = requests.post(
                    f"{API_BASE}/v1/screen/upload", headers=auth_header(),
                    data=form_data,
                    files=files, timeout=300,
                )
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {"error": {"code": "invalid_response", "message": response.text[:500]}}
                st.session_state.screen_result = {
                    "status": response.status_code,
                    "request": request_preview,
                    "response": response_data,
                }
            except requests.RequestException as exc:
                st.error(f"Could not reach the screening API: {exc}")
                return

    state = st.session_state.get("screen_result")
    if not state:
        return
    with st.expander("View raw JSON"):
        st.json({"request": state["request"], "response": state["response"]})
    response_data = state["response"]
    if state["status"] != 200:
        error = response_data.get("error", {})
        message = error.get("message", "Screening failed") if isinstance(error, dict) else str(error)
        st.error(f"{message} (HTTP {state['status']})")
        return
    ranked = response_data.get("ranked", [])
    if ranked:
        st.subheader("Ranked candidates")
        st.dataframe([
            {"Rank": row["rank"], "Name": row["result"]["candidate_name"],
             "Score": row["result"]["match_score"],
             "Recommendation": ({"shortlist": "🟢", "maybe": "🟡", "reject": "🔴"}.get(row["result"]["recommendation"], "⚪") + " " + row["result"]["recommendation"]),
             "File": row["filename"]}
            for row in ranked
        ], use_container_width=True, hide_index=True)
        for row in ranked:
            result = row["result"]
            icon = {"shortlist": "🟢", "maybe": "🟡", "reject": "🔴"}.get(result["recommendation"], "⚪")
            with st.expander(f"{row['rank']}. {result['candidate_name']} — {result['match_score']}/100 {icon} {result['recommendation'].title()}"):
                st.write("**Matched skills:** " + (", ".join(result["matched_skills"]) or "None"))
                st.write("**Missing skills:** " + (", ".join(result["missing_skills"]) or "None"))
                st.write(result["summary"])
                metrics = row["metrics"]
                cost_label = f"${metrics['cost_usd']:.4f}" if metrics["cost_usd"] is not None else "not estimated"
                st.caption(
                    f"Tokens: {metrics['input_tokens']} in / {metrics['output_tokens']} out · "
                    f"TTFT: {metrics['ttft_ms'] if metrics['ttft_ms'] is not None else 'N/A'} ms · "
                    f"Speed: {metrics['tokens_per_sec'] if metrics['tokens_per_sec'] is not None else 'N/A'} tok/s · "
                    f"Cost: {cost_label}"
                )
                if row["provider"] == "ollama":
                    st.caption("Processed locally: $0.00")
    for item in response_data.get("failed", []):
        st.warning(f"{item['filename']}: {item['error']}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

def show_app():
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### 👋 {st.session_state.username}")
        st.divider()
        page = st.radio("Workspace", ["Chat", "Screen Resumes"], horizontal=True)

        # Settings
        st.markdown("#### ⚙️ Settings")
        backend = st.selectbox("Backend", ["ollama", "groq"], index=0)

        # Load models
        try:
            models_resp = api_get("/v1/models")
            if models_resp.status_code == 200:
                available = models_resp.json()
                model_list = available.get(backend, [])
            else:
                model_list = []
        except Exception:
            model_list = []

        if model_list:
            model = st.selectbox("Model", model_list, key=f"model_{backend}")
        else:
            default = "llama3.2" if backend == "ollama" else "openai/gpt-oss-20b"
            model = st.text_input("Model name", value=default)

        temperature = st.slider(
            "Temperature", 0.0, 2.0, 0.7, 0.05,
            help="Controls how varied the AI's answers are. Lower values are more consistent; higher values are more creative and less predictable.",
        )
        max_tokens = st.number_input(
            "Max Tokens", 64, 8192, 512, 64,
            help="The maximum length of the AI's reply. A token is a small piece of text, often part of a word.",
        )
        st.divider()

        # Usage stats
        st.markdown("#### 📊 Token Usage")
        try:
            usage_resp = api_get("/v1/usage")
            if usage_resp.status_code == 200:
                usage = usage_resp.json()
                today_used = usage["today"]["total_tokens"]
                quota = usage["daily_quota"]
                pct = min(today_used / max(quota, 1), 1.0)

                st.markdown(f'<div class="quota-bar-label" title="Tokens are small pieces of text processed or generated by the AI. This bar shows how much of your daily allowance you have used.">Daily: {today_used:,} / {quota:,} tokens</div>', unsafe_allow_html=True)
                st.progress(pct)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Today", f"{today_used:,}", help="Total tokens processed by your requests today. This includes both your messages and the AI's replies.")
                with col2:
                    st.metric("Month", f"{usage['this_month']['total_tokens']:,}", help="Total tokens processed by your requests this month, including your messages and the AI's replies.")
                st.caption(f"Resets: {usage['quota_reset_at'][:10]}")
        except Exception:
            st.warning("Could not load usage stats.")

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.username = None
            st.session_state.messages = []
            st.session_state.last_metrics = None
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    if page == "Screen Resumes":
        show_resume_screener(backend, model, temperature)
        return

    # ── Main Content ──────────────────────────────────────────────────────────
    col_main, col_metrics = st.columns([2, 1])

    with col_main:
        st.markdown('<div class="hero-card"><div class="hero-kicker">NexAI workspace</div><div class="hero-title">💬 Chat workspace</div><p class="hero-subtitle">Choose a model, ask a question, and review its performance.</p></div>', unsafe_allow_html=True)

        # Display chat history
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-msg-user">👤 <strong>You</strong><br/>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                content_html = msg["content"].replace("\n", "<br/>")
                st.markdown(
                    f'<div class="chat-msg-assistant">🤖 <strong>Assistant</strong><br/>{content_html}</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("metrics"):
                    m = msg["metrics"]
                    pills = []
                    if m.get("ttft_ms") is not None:
                        pills.append(f"⚡ TTFT: {m['ttft_ms']:.0f}ms")
                    pills.append(f"⏱ Latency: {m['total_latency_ms']:.0f}ms")
                    if m.get("tokens_per_second"):
                        pills.append(f"🚀 {m['tokens_per_second']:.1f} tok/s")
                    pills.append(f"📥 {m['input_tokens']} in / 📤 {m['output_tokens']} out")
                    pill_help = {
                        "ttft": "Time to first token: how long it took for the first piece of the AI's reply to arrive.",
                        "latency": "Total time from sending your request until the full reply was ready.",
                        "speed": "How many pieces of text (tokens) the AI generated per second. Higher is faster.",
                        "usage": "Input tokens are from your prompt; output tokens are from the AI's reply. A token is a small piece of text.",
                    }
                    pill_html = " ".join(
                        f'<span class="perf-pill" title="{description}">{label}</span>'
                        for label, description in zip(pills, [
                            *([pill_help["ttft"]] if m.get("ttft_ms") is not None else []),
                            pill_help["latency"],
                            *([pill_help["speed"]] if m.get("tokens_per_second") else []),
                            pill_help["usage"],
                        ])
                    )
                    st.markdown(pill_html, unsafe_allow_html=True)

        # Input
        st.markdown("---")
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Message",
                placeholder="Ask anything...",
                height=80,
                label_visibility="collapsed",
            )
            col_send, col_clear = st.columns([4, 1])
            with col_send:
                send = st.form_submit_button("Send ↩", use_container_width=True, type="primary")
            with col_clear:
                clear = st.form_submit_button("🗑 Clear", use_container_width=True)

        if clear:
            st.session_state.messages = []
            st.rerun()

        if send and user_input.strip():
            st.session_state.messages.append({"role": "user", "content": user_input.strip()})

            payload = {
                "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                "backend": backend,
                "model": model,
                "temperature": temperature,
                "max_tokens": int(max_tokens),
                "stream": False,
            }

            with st.spinner("🤔 Thinking..."):
                try:
                    resp = api_post("/v1/chat/completions", payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": data["content"],
                            "metrics": data.get("metrics"),
                        })
                        st.session_state.last_metrics = data.get("metrics")
                        st.rerun()
                    elif resp.status_code == 429:
                        show_api_error(resp, "Daily token quota exceeded.")
                    else:
                        show_api_error(resp, f"Request failed (HTTP {resp.status_code})")
                except Exception as e:
                    st.error(f"Request failed: {e}")

    # ── Metrics Panel ─────────────────────────────────────────────────────────
    with col_metrics:
        st.markdown("## 📈 Metrics")

        # Last request metrics
        if st.session_state.last_metrics:
            m = st.session_state.last_metrics
            st.markdown("**Last Request**")
            badge = f'<span class="badge-{m["backend"]}">{m["backend"].upper()}</span>'
            st.markdown(badge, unsafe_allow_html=True)
            st.caption(f"Model: `{m['model']}`")

            st.markdown(f"""
<div class="metric-card" title="Time to first token: how long the AI took to begin responding. Lower is quicker.">
  <div class="metric-value">{f"{m['ttft_ms']:.0f}" if m.get('ttft_ms') else "N/A"}</div>
  <div class="metric-label">TTFT (ms)</div>
</div>
<div class="metric-card" title="Total time from sending your request until the full reply was ready. Lower is quicker.">
  <div class="metric-value">{m['total_latency_ms']:.0f}</div>
  <div class="metric-label">Total Latency (ms)</div>
</div>
<div class="metric-card" title="How many pieces of text (tokens) the AI generated per second. Higher means faster generation.">
  <div class="metric-value">{f"{m['tokens_per_second']:.1f}" if m.get('tokens_per_second') else "N/A"}</div>
  <div class="metric-label">Tokens / Second</div>
</div>
<div class="metric-card" title="The combined text processed from your prompt (input) and generated in the reply (output). A token is a small piece of text.">
  <div class="metric-value">{m['input_tokens'] + m['output_tokens']}</div>
  <div class="metric-label">Total Tokens (in+out)</div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        # Global metrics
        st.markdown("**Global Metrics**")
        st.caption("Service-wide performance across requests from all users.")
        if st.button("🔄 Refresh", key="refresh_metrics"):
            st.rerun()
        try:
            gm_resp = api_get("/metrics")
            if gm_resp.status_code == 200:
                gm = gm_resp.json()
                st.markdown(f"""
<div class="metric-card" title="The total number of chat requests handled by this service.">
  <div class="metric-value">{gm['total_requests']}</div>
  <div class="metric-label">Total Requests</div><div class="metric-description">Chat requests handled by the service.</div>
</div>
<div class="metric-card" title="Average time before the first piece of an AI reply arrives, across requests that report this measurement. Lower is quicker.">
  <div class="metric-value">{f"{gm['avg_ttft_ms']:.0f}" if gm.get('avg_ttft_ms') else "N/A"}</div>
  <div class="metric-label">Avg TTFT (ms)</div><div class="metric-description">Average wait for the first part of a reply.</div>
</div>
<div class="metric-card" title="Average number of pieces of text generated per second across requests. Higher means faster generation.">
  <div class="metric-value">{f"{gm['avg_tokens_per_second']:.1f}" if gm.get('avg_tokens_per_second') else "N/A"}</div>
  <div class="metric-label">Avg Tokens/sec</div><div class="metric-description">Average reply generation speed.</div>
</div>
""", unsafe_allow_html=True)

                if gm.get("avg_latency_ms") is not None:
                    st.metric(
                        "Avg Total Latency (ms)", f"{gm['avg_latency_ms']:.0f}",
                        help="Average time from sending a request until the complete reply was ready.",
                    )

                if gm["by_backend"]:
                    st.markdown("**By Backend**")
                    st.caption("Request count and average response time for each AI provider. Each provider is a service that runs the model.")
                    for b, stats in gm["by_backend"].items():
                        badge_cls = "badge-ollama" if b == "ollama" else "badge-groq"
                        st.markdown(
                            f'<span class="{badge_cls}">{b}</span> — '
                            f'{stats["requests"]} reqs, {stats["avg_latency_ms"]:.0f}ms avg',
                            unsafe_allow_html=True,
                        )
                if gm.get("by_model"):
                    st.markdown("**By Model**")
                    st.caption("Request count and average response time grouped by the selected AI model.")
                    for model_name, stats in gm["by_model"].items():
                        st.caption(
                            f"{model_name} — {stats['requests']} requests, "
                            f"{stats['avg_latency_ms']:.0f} ms average response time"
                        )
        except Exception as e:
            st.warning(f"Metrics unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.token is None:
    show_auth()
else:
    show_app()
