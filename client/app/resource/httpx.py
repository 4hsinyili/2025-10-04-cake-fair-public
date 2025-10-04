import logging

import httpx
import streamlit as st


@st.cache_resource
def get_cached_httpx_client():
    httpx_client = httpx.Client(
        timeout=httpx.Timeout(120.0, read=300.0),
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return httpx_client
