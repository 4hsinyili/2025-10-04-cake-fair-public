
import streamlit as st

from app.page.util import generate_chat


def main():
    st.write("嗨，這裡可以以對話方式設定你今天想要的飲料情境")
    try:
        generate_chat("drink_preference_chat")
    except Exception as e:
        st.error(f"發生錯誤: {e}")


if __name__ == "__main__":
    main()