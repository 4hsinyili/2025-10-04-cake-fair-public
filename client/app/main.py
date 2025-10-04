import pathlib
import sys

import streamlit as st


def set_path(file_path):
    sys.path.append(str(pathlib.Path(file_path).parent.parent))

def main():
    set_path(__file__)

    pages = [
        st.Page("page/recommened.py", title="飲料推薦", url_path="recommened"),
        # st.Page("page/drink_preference.py", title="用聊天的方式找想喝的飲料", url_path="drink_preference"),
        st.Page("page/response_preference.py", title="回應情境設定", url_path="response_preference"),

    ]

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
