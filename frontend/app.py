import tempfile
import uuid
from pathlib import Path

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

PERSONALITY_OPTIONS = {
    "brutal": "💀 Brutal Mentor — zero patience, maximum truth",
    "hype": "🚀 Hype Engineer — everything is REVOLUTIONARY",
    "tired": "😮‍💨 Tired Veteran — seen it all, caffeinated on spite",
}

BONUS_STYLES = {
    "follow_up": {"emoji": "🤔", "label": "Follow-Up Question", "color": "#FFF3CD", "border": "#FFC107"},
    "hot_take": {"emoji": "🔥", "label": "Hot Take", "color": "#F8D7DA", "border": "#DC3545"},
    "related_fact": {"emoji": "💡", "label": "You Should Know", "color": "#D1ECF1", "border": "#0DCAF0"},
}


def init_session_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []


def api_post(endpoint: str, payload: dict) -> dict | None:
    try:
        response = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None


def api_get(endpoint: str) -> dict | list | None:
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None


def api_delete(endpoint: str) -> dict | None:
    try:
        response = requests.delete(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None


def render_bonus_box(bonus_type: str, bonus_content: str) -> None:
    style = BONUS_STYLES.get(bonus_type, BONUS_STYLES["related_fact"])
    st.markdown(
        f"""
        <div style="
            background-color: {style['color']};
            border-left: 4px solid {style['border']};
            padding: 12px 16px;
            border-radius: 6px;
            margin: 8px 0;
        ">
            <strong>{style['emoji']} {style['label']}</strong><br/>
            {bonus_content}
        </div>
        """,
        unsafe_allow_html=True,
    )


def ingest_content(content_type: str, content: str) -> None:
    result = api_post("/ingest", {"content_type": content_type, "content": content})
    if result:
        if result.get("success"):
            st.success(result.get("message", "Ingested successfully."))
        else:
            st.error(result.get("message", "Ingestion failed."))


def load_sources() -> list[dict]:
    data = api_get("/sources")
    return data if isinstance(data, list) else []


def main() -> None:
    st.set_page_config(page_title="BrainRot", page_icon="🧠", layout="wide")
    init_session_state()

    with st.sidebar:
        st.header("Settings")

        personality = st.radio(
            "Personality",
            options=list(PERSONALITY_OPTIONS.keys()),
            format_func=lambda key: PERSONALITY_OPTIONS[key],
            index=0,
        )

        st.divider()
        st.subheader("Feed the Brain")

        tab_url, tab_pdf, tab_text = st.tabs(["URL", "PDF", "Text"])

        with tab_url:
            url = st.text_input("URL", placeholder="https://example.com/article", key="url_input")
            if st.button("Ingest URL", key="ingest_url"):
                if url.strip():
                    ingest_content("url", url.strip())
                else:
                    st.warning("Enter a URL first.")

        with tab_pdf:
            uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_upload")
            if st.button("Ingest PDF", key="ingest_pdf"):
                if uploaded:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded.getvalue())
                        pdf_path = tmp.name
                    ingest_content("pdf_path", pdf_path)
                else:
                    st.warning("Upload a PDF first.")

        with tab_text:
            raw_text = st.text_area("Raw text", height=150, placeholder="Paste text here...", key="text_input")
            if st.button("Ingest Text", key="ingest_text"):
                if raw_text.strip():
                    ingest_content("text", raw_text.strip())
                else:
                    st.warning("Enter some text first.")

        st.divider()
        st.subheader("Ingested Sources")
        sources = load_sources()
        if sources:
            for src in sources:
                st.caption(f"**{src['source']}** — {src['chunk_count']} chunks ({src['ingested_at'][:19]})")
        else:
            st.caption("No sources ingested yet.")

        st.divider()
        if st.button("Reset Knowledge Base", type="secondary"):
            st.session_state.confirm_reset = True

        if st.session_state.get("confirm_reset"):
            st.warning("This will delete all ingested content. Are you sure?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, reset"):
                    result = api_delete("/reset")
                    if result:
                        st.success("Knowledge base cleared.")
                        st.session_state.confirm_reset = False
                        st.rerun()
            with col2:
                if st.button("Cancel"):
                    st.session_state.confirm_reset = False
                    st.rerun()

    st.title("🧠 BrainRot")
    st.caption("Feed it. Chat with it. Get roasted.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "bonus_type" in msg:
                render_bonus_box(msg["bonus_type"], msg["bonus_content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("Sources"):
                    for source in msg["sources"]:
                        st.text(source)

    if prompt := st.chat_input("Ask BrainRot something..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = api_post(
                    "/chat",
                    {
                        "question": prompt,
                        "personality": personality,
                        "session_id": st.session_state.session_id,
                    },
                )

            if result:
                st.markdown(result["answer"])
                render_bonus_box(result["bonus_type"], result["bonus_content"])
                if result.get("sources"):
                    with st.expander("Sources"):
                        for source in result["sources"]:
                            st.text(source)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "bonus_type": result["bonus_type"],
                        "bonus_content": result["bonus_content"],
                        "sources": result.get("sources", []),
                    }
                )


if __name__ == "__main__":
    main()
