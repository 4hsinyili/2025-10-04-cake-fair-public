
import streamlit as st

from app.page.util import generate_chat


def main():
    st.write("嗨，這裡可以以對話方式設定你今天想要的回應情境")
    generate_chat("response_preference_chat")


if __name__ == "__main__":
    main()