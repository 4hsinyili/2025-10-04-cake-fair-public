import json
import random
import time

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from app.resource.api import get_cached_api_client


def response_simulator():
    response = random.choice(
        [
            "Hello there! How can I assist you today?",
            "Hi, human! Is there anything I can help you with?",
            "Do you need help?",
        ]
    )
    for word in response.split():
        yield word + " "
        time.sleep(0.05)


def response_streamer(chat_type, message):
    session_id = get_script_run_ctx().session_id
    payload = {"session_id": session_id, "message": message, "chat_type": chat_type, "user_id": session_id, "app_name": chat_type}
    api_client = get_cached_api_client("http://localhost:3001")
    response = api_client.post(f"/agent/chat/{chat_type}", json=payload, stream=True)
    with response as response:
        for line in response.iter_lines():
            if line:
                record = json.loads(line)
                yield record[0]["content"]["parts"][0]["text"]


def generate_chat(key):
    if key not in st.session_state or st.session_state.get("use_demo", False):
        st.session_state["use_demo"] = False
        st.session_state[key] = []
        st.session_state[f"{key}_chat"] = []

    # Display chat messages from history on app rerun
    for message in st.session_state[key]:
        role = message["role"]
        avatar = "👤" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("今天想要設定的情境是什麼呢？"):
        # Display user message in chat message container
        st.chat_message("user", avatar="👤").markdown(prompt)
        # Add user message to chat history
        st.session_state[key].append({"role": "user", "content": prompt})
        # Display assistant response in chat message container
        with st.chat_message("assistant", avatar="🤖"):
            try:
                with st.spinner("AI 助手思考中..."):
                    stream = response_streamer(key, {"role": "user", "content": prompt})
                    # stream = response_simulator()
                    response = st.write_stream(stream)
            except Exception:
                response = "抱歉，提示詞系統發生錯誤，可能是因為 LLM 服務呼叫太過頻繁，請稍後再試。如果持續發生，請聯絡開發者"
        # Add assistant response to chat history
        st.session_state[key].append({"role": "assistant", "content": response})
    col_l, col_r = st.columns([1, 3])
    if len(st.session_state[key]) > 0:
        clear_btn = col_l.button(":red[清除對話紀錄]", type="secondary", width="stretch")
        if clear_btn:
            st.session_state[key] = []
            st.session_state[f"{key}_chat"] = []
            st.success("已清除對話紀錄")
            st.rerun()
    return_btn = col_r.button("回到推薦頁面", type="primary", width="stretch")
    if return_btn:
        st.switch_page("page/recommened.py")
