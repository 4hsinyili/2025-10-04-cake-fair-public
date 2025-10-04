import logging

import httpx
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from app.resource.httpx import get_cached_httpx_client


class ApiClient:
    def __init__(
        self,
        httpx_client: httpx.Client,
        end_point: str = None,
        logger: logging.Logger = None,
        *args,
        **kwargs,
    ):
        self.httpx_client: httpx.Client = httpx_client
        self.end_point = end_point
        self.logger = logger

    def set_request_kwargs(
        self,
        method: str,
        path: str,
        params: dict = None,
        json: dict = None,
        headers: dict = None,
        **kwargs,
    ):
        st_context = get_script_run_ctx()
        session_id = st_context.session_id
        user_email = st_context.user_info.get("email", "Unknown")
        request_kwargs = {
            "method": method,
            "url": f"{self.end_point}{path}",
            "headers": {
                "x-client-session-id": session_id,
                "x-client-user-email": user_email,
            },
        }
        if params:
            request_kwargs["params"] = params
        if json:
            request_kwargs["json"] = json
        if headers:
            request_kwargs["headers"].update(headers)
        request_kwargs.update(kwargs)
        self.logger.info(
            f"Calling {self.end_point}{path} with kwargs: {request_kwargs}"
        )
        return request_kwargs

    def call(
        self,
        method: str,
        path: str,
        params: dict = None,
        json: dict = None,
        headers: dict = None,
        **kwargs,
    ):
        request_kwargs = self.set_request_kwargs(
            method, path, params=params, json=json, headers=headers, **kwargs
        )

        resp = self.httpx_client.request(**request_kwargs)
        self.logger.info(f"Got response: {resp.status_code} in {resp.elapsed}")
        return resp

    def stream(
        self,
        method: str,
        path: str,
        params: dict = None,
        json: dict = None,
        headers: dict = None,
        **kwargs,
    ):
        return self.httpx_client.stream(
            method,
            f"{self.end_point}{path}",
            headers=headers,
            params=params,
            json=json,
            **kwargs,
        )

    def get(self, path: str, params: dict = None, json: dict = None, stream: bool = False, **kwargs):
        if stream:
            return self.stream("GET", path, params=params, json=json, **kwargs)
        return self.call("GET", path, params=params, json=json, **kwargs)

    def post(self, path: str, params: dict = None, json: dict = None, stream: bool = False, **kwargs):
        if stream:
            return self.stream("POST", path, params=params, json=json, **kwargs)
        return self.call("POST", path, params=params, json=json, **kwargs)

    def put(self, path: str, params: dict = None, json: dict = None, stream: bool = False, **kwargs):
        if stream:
            return self.stream("PUT", path, params=params, json=json, **kwargs)
        return self.call("PUT", path, params=params, json=json, **kwargs)

    def delete(self, path: str, params: dict = None, json: dict = None, stream: bool = False, **kwargs):
        if stream:
            return self.stream("DELETE", path, params=params, json=json, **kwargs)
        return self.call("DELETE", path, params=params, json=json, **kwargs)


@st.cache_resource
def get_cached_api_client(end_point: str = None) -> ApiClient:
    """
    Get the API client.
    """
    httpx_client = get_cached_httpx_client()
    logger = logging.getLogger("api_client")
    api_client = ApiClient(
        httpx_client=httpx_client, end_point=end_point, logger=logger
    )
    return api_client
