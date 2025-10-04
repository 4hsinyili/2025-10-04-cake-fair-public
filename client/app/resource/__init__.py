
import streamlit as st
from openai import OpenAI
from streamlit_cookies_controller import CookieController

from app.setting import setting


def get_cookie_controller():
    controller = CookieController()
    return controller


@st.cache_resource
def get_openai_client():
    client = OpenAI(
        api_key=setting.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1"
    )
    return client
