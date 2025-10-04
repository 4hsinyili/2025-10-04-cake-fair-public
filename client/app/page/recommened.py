import random
import time

import pandas as pd
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit_geolocation import streamlit_geolocation

from app.resource.api import get_cached_api_client
from app.resource.prompt.response_preference import PROMPTS

# ============================
# API 相關函式
# ============================

@st.cache_data(ttl=600)
def fetch_api_data(endpoint: str) -> list[dict]:
    """統一的 API 資料擷取函式"""
    api_client = get_cached_api_client("http://localhost:3001")
    response = api_client.get(endpoint)
    return response.json().get("data", [])


@st.cache_data(ttl=600)
def load_companies() -> list[dict]:
    """載入公司資料"""
    return fetch_api_data("/mongo/list/company")


@st.cache_data(ttl=600)  
def load_drink_tag_options() -> list[str]:
    """載入飲料標籤選項"""
    data = fetch_api_data("/mongo/list/drink_tag")
    return [d["name"] for d in data]


@st.cache_data(ttl=600)
def load_brand_options() -> list[str]:
    """載入品牌選項"""
    data = fetch_api_data("/mongo/list/brand")
    return [d["name"] for d in data]


# ============================
# 位置相關函式
# ============================

def reset_user_location():
    """重設使用者位置"""
    if st.session_state.get("user_location", None) == (None, None):
        st.session_state["select_user_location"] = "世貿一館 / 110台北市信義區信義路五段5號"

@st.dialog("取得所在位置", on_dismiss=lambda: reset_user_location())
def set_user_location():
    """設定使用者位置"""
    col_l, col_r = st.columns([4, 1], gap="large")
    col_l.write("請點選右方座標圖示後，依照瀏覽器提示操作")
    with col_r:
        raw_location = streamlit_geolocation()
    container = st.container()
    st.image("app/resource/img/computer.png", caption="電腦版")
    img_col_l, img_col_r = st.columns(2)
    img_col_l.image("app/resource/img/mobile_l.png", caption="手機版（App）")
    img_col_r.image("app/resource/img/mobile_r.png", caption="手機版（網頁）")
    if raw_location:
        lat, lon = raw_location["latitude"], raw_location["longitude"]
        st.session_state["user_location"] = (lon, lat)
    if st.session_state.get("user_location", (None, None)) == (None, None):
        container.info("請參考下方圖示允許取得您的位置以進行搜尋")
    else:
        container.success("已成功取得您的位置: " + str(st.session_state.get("user_location")) + "此視窗即將自動關閉")
        time.sleep(1)
        st.rerun()


def get_location() -> tuple[float, float]:
    """取得使用者選擇的位置"""
    companies = load_companies()
    addresses = [f"{c['name']} / {c['address']}" for c in companies]
    
    # 預設選項
    default_options = ["世貿一館 / 110台北市信義區信義路五段5號", "使用所在位置"]
    
    location = st.selectbox(
        "選擇您的位置",
        key="select_user_location",
        options=default_options + addresses,
    )
    
    # 處理不同的位置選擇
    if location == "使用所在位置":
        current_user_location = st.session_state.get("user_location", None)
        if not current_user_location or all(v is None for v in current_user_location):
            set_user_location()
        st.session_state["selected_location"] = current_user_location
    elif location == "世貿一館 / 110台北市信義區信義路五段5號":
        st.session_state["selected_location"] = (121.56222, 25.03389)
    else:
        address_index = addresses.index(location)
        st.session_state["selected_location"] = companies[address_index]["location"]["coordinates"]

    return st.session_state["selected_location"]


# ============================  
# UI 元件函式
# ============================

def get_drink_tags() -> list[str]:
    """取得飲料標籤"""
    return st.multiselect(
        "選擇飲料（可自行輸入）", 
        options=load_drink_tag_options(), 
        accept_new_options=True
    )


def get_brands() -> list[str]:
    """取得品牌"""
    return st.multiselect("選擇品牌", options=load_brand_options())


def get_delivery_platform() -> str:
    """取得外送平台"""
    return st.selectbox("選擇外送平台", options=["UberEats", "Foodpanda"])


# ============================
# 對話框相關函式  
# ============================

def _get_preference_config(key: str) -> dict:
    """取得偏好設定的配置資訊"""
    configs = {
        "drink_preference": {"name": "飲料偏好", "page": "drink_preference"},
        "response_preference": {"name": "回應偏好", "page": "response_preference"}
    }
    return configs.get(key, {"name": "偏好", "page": key})


def _display_chat_messages(messages: list[dict]):
    """顯示聊天訊息"""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


@st.dialog("載入聊天紀錄", on_dismiss="rerun", width="large")
def load_chat_history(key: str):
    """載入聊天紀錄對話框"""
    chat_history_key = f"{key}_chat"
    current_loaded = st.session_state.get(key, [])
    
    # 選擇載入方式
    col_l, col_r = st.columns([3, 1])
    with col_l:
        selected = st.selectbox(
            "載入方式",
            options=["載入最後一則", "載入所有"],
            index=1 if len(current_loaded) <= 1 else 0,
            key=f"select_load_{key}_chat_history",
            label_visibility="collapsed",
        )
    
    # 確認載入按鈕
    with col_r:
        confirm_load = st.button(
            "確認載入", 
            key=f"confirm_load_{key}_chat_history", 
            width="stretch",
        )
    
    # 取得要顯示的聊天紀錄
    all_history = st.session_state.get(chat_history_key, [])
    if selected == "載入最後一則":
        chat_history = all_history[-1:]
    else:
        st.warning("載入所有聊天紀錄可能會導致回傳速度緩慢")
        chat_history = all_history
    
    # 顯示聊天紀錄
    _display_chat_messages(chat_history)
    
    # 處理確認載入
    if confirm_load:
        st.session_state[key] = chat_history
        st.success("已載入聊天紀錄")
        st.rerun()

def get_user_preference(key: str) -> list[dict]:
    """取得使用者偏好設定"""
    config = _get_preference_config(key)
    pref_name = config["name"]
    chat_history_key = f"{key}_chat"
    
    # 初始化偏好設定
    if not st.session_state.get(key, []):
        st.session_state[key] = st.session_state.get(chat_history_key, [])[-1:]
    
    # 顯示目前狀態
    chat_length = len(st.session_state.get(chat_history_key, []))
    loaded_length = len(st.session_state.get(key, []))
    
    st.text(
        f"{pref_name}（已經載入 {loaded_length}/{chat_length} 則對話）",
        help=f"可以選擇「使用 Demo 提示詞」隨機載入預建立的提示詞，或點擊下方按鈕建立新的{pref_name}"
    )
    
    # 根據是否有偏好設定顯示不同按鈕
    if not st.session_state.get(key):
        col_demo, col_create = st.columns(2)
        if col_demo.button(":blue[使用 Demo 提示詞]", key=f"default_{key}_chat", width="stretch", type="secondary"):
            prompt = random.choice(PROMPTS)
            st.session_state[key] = [{"role": "assistant", "content": prompt}]
            st.session_state[chat_history_key] = st.session_state[key]
            st.session_state["use_demo"] = True
            st.rerun()
        if col_create.button(f"建立{pref_name}", key=f"load_{key}_chat_history", 
                    width="stretch", type="secondary"):
            st.switch_page(f"page/{config['page']}.py")
    else:
        btn_label = "載入所有" if loaded_length == 1 else "載入最後一則"
        col_l, col_m_l, col_m_r, col_r = st.columns(4)
        
        load_btn = col_l.button(
            f":orange[改為{btn_label}]", 
            key=f"reload_{key}_chat_history", 
            width="stretch", 
            type="secondary"
        )
        
        visit_btn = col_m_l.button(
            "繼續對話", 
            key=f"visit_{key}_chat", 
            width="stretch", 
            type="secondary"
        )
        
        regen_demo_btn = col_m_r.button(
            ":blue[重骰 Demo 提示詞]",
            key=f"regen_demo_{key}_chat",
            width="stretch",
            type="secondary"
        )

        clear_btn = col_r.button(
            ":red[清除對話]",
            key=f"clear_{key}_chat",
            width="stretch",
            type="secondary"
        )

        if visit_btn:
            st.session_state["use_demo"] = False
            st.session_state[key] = []
            st.session_state[f"{key}_chat"] = []
            st.switch_page(f"page/{config['page']}.py")
        if load_btn:
            load_chat_history(key)
        if regen_demo_btn:
            prompt = random.choice(PROMPTS)
            st.session_state[key] = [{"role": "assistant", "content": prompt}]
            st.session_state[chat_history_key] = st.session_state[key]
            st.session_state["use_demo"] = True
            st.rerun()
        if clear_btn:
            st.session_state[key] = []
            st.session_state[chat_history_key] = []
            st.session_state["use_demo"] = False
            st.rerun()
    
    return st.session_state.get(key, [])


# ============================
# 搜尋相關函式
# ============================

@st.dialog(title="搜尋飲料", on_dismiss="rerun", width="large")
def show_drink_table(message: str, drinks: list[dict]):
    """顯示飲料搜尋結果表格"""
    st.info(f"找到 {len(drinks)} 筆符合條件的飲料")
    st.markdown(message)
    df = pd.DataFrame(drinks)
    st.dataframe(
        df,
        column_config={
            "name": st.column_config.TextColumn("飲料名稱", width="small"),
            "store_name": st.column_config.TextColumn("店家名稱", width="small"),
            "brand_name": st.column_config.TextColumn("品牌", width="small"),
            "price": st.column_config.NumberColumn("價格", format="$%.2f"),
            "description": st.column_config.TextColumn("描述"),
            "store_url": st.column_config.LinkColumn(
                "店家連結", 
                display_text="前往訂購", 
                validate=True
            ),
        },
        column_order=[
            "name", "price", "store_name", "store_url", "brand_name", "description"
        ],
        hide_index=True,
        width="stretch",
        row_height=45,
        height=600
    )


def _create_recommendation_payload(
    location: tuple[float, float],
    drink_tags: list[str], 
    brands: list[str],
    drink_preference: list[dict],
    response_preference: list[dict]
) -> dict:
    """建立搜尋請求的 payload"""
    return {
        "location": location,
        "drink_tags": drink_tags,
        "brands": brands,
        "drink_preference": drink_preference,
        "response_preference": response_preference,
    }


def invoke_recommender(
    location: tuple[float, float],
    drink_tags: list[str],
    brands: list[str], 
    drink_preference: list[dict] = [],
    response_preference: list[dict] = []
):
    """執行飲料搜尋"""
    api_client = get_cached_api_client("http://localhost:3001")
    payload = _create_recommendation_payload(
        location, drink_tags, brands, drink_preference, response_preference
    )
    
    # 根據是否有偏好設定選擇不同的 API 端點
    if drink_preference or response_preference:
        # 使用 AI 搜尋
        session_id = get_script_run_ctx().session_id
        payload.update({
            "user_id": session_id,
            "session_id": session_id,
            # "drink_preference_chats": drink_preference,
            "response_preference_chats": response_preference,
        })
        response = api_client.post("/agent/recommend", json=payload)
        st.info("正在根據您的偏好搜尋飲料，請稍候...")
        response_json: dict = response.json()
        message = response_json.get("message", "以下是根據您的偏好搜尋的飲料：")
        drinks = response_json.get("drinks", [])
        if drinks:
            show_drink_table(message=message, drinks=drinks)
        else:
            st.warning("找不到符合條件的飲料，請調整搜尋條件")
    else:
        # 使用一般搜尋
        response = api_client.post("/mongo/list/drink", json=payload)
        data = response.json().get("data", [])
        message = "以下是根據您的條件搜尋的飲料："
        if data:
            show_drink_table(message=message, drinks=data)
        else:
            st.warning("找不到符合條件的飲料，請調整搜尋條件")


# ============================
# 主要業務邏輯
# ============================

def _render_filter_inputs() -> tuple[list[str], list[str]]:
    """渲染篩選輸入區域"""
    drink_col, brand_col = st.columns([3, 2])
    
    with drink_col:
        drink_tags = get_drink_tags()
    with brand_col:
        brands = get_brands()
    
    return drink_tags, brands


def _render_preference_inputs() -> tuple[list[dict], list[dict]]:
    """渲染偏好設定區域"""
    drink_pref_col, response_pref_col = st.columns(2, border=True)
    
    with drink_pref_col:
        drink_preference = get_user_preference("drink_preference")
    with response_pref_col:
        response_preference = get_user_preference("response_preference")
    
    return drink_preference, response_preference

def _render_preference_input() -> list[dict]:
    """渲染單一偏好設定區域"""
    response_preference = get_user_preference("response_preference")
    return response_preference

def _page_help():
    help_text = """
    此系統可協助您搜尋 UberEats 上的飲料選項。請依照以下步驟操作：
    1. 選擇位置：從下拉選單中選擇您的位置。
        - 若選擇「使用所在位置」，請允許瀏覽器取得您的地理位置。
    2. 篩選條件：可選擇飲料名稱或種類、品牌等篩選條件以縮小搜尋範圍。
    3. 偏好設定：可選擇設定「回應偏好」以影響搜尋結果的風格與語氣。
    4. 搜尋飲品：點擊「搜尋飲品」按鈕開始搜尋。系統將根據您的條件與偏好提供推薦結果。
    5. 查看結果：搜尋完成後，系統會顯示符合條件的飲料清單。
    """
    return help_text

def _page_footer():
    """頁面頁尾"""
    st.divider()
    with st.expander("Readme", expanded=False):
        st.markdown(
            """
            ### App 
            - 前端：使用 Streamlit 建立互動式網頁介面
            - 後端：使用 FastAPI 提供 API 服務，並串接 MongoDB 與 LLM
            - LLM：使用 Google ADK 配合 OpenRouter 串接多種大型語言模型

            ### Infra
            - 服務架構：使用單一 Google Cloud Run 服務部署多個 Sidecar Container
            - 資料庫：使用 MongoDB Atlas 儲存飲料與店家資料
            - 自動化部署：使用 Cloud Build 持續部署

            ### Repository
            https://github.com/4hsinyili/2025-10-04-cake-fair-public
            
            ### Usage
            請點選頁面標題旁的「?」圖示以查看使用說明

            ### About Me
            Hsin Yi Li&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;李心毅&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;4hsinyili@gmail.com\n
            Data Engineer\n
            [GitHub Profile](https://github.com/4hsinyili)&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;[Cake Profile](https://www.cake.me/me/4hsinyili)&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;[LinkedInProfile](https://www.linkedin.com/in/4hsinyili/)
            """
        )

def main():
    """主要函式"""
    st.set_page_config(
        initial_sidebar_state="collapsed",
        page_icon="🥤",
        page_title="外送飲料搜尋系統",
    )
    st.title("Ubereats 外送飲料搜尋系統", help=_page_help(), anchor=False)
    # 位置選擇
    get_location()
    
    # 篩選條件輸入
    drink_tags, brands = _render_filter_inputs()
    
    # 偏好設定
    # drink_preference, response_preference = _render_preference_inputs()
    response_preference = _render_preference_input()
    
    # 搜尋按鈕
    if st.button("搜尋飲品", width="stretch", type="primary"):
        location = st.session_state.get("selected_location")
        if not location:
            st.error("請先選擇您的位置")
            return
            
        with st.spinner("正在根據您的條件搜尋飲料，請稍候..."):
            invoke_recommender(
                location=location,
                drink_tags=drink_tags,
                brands=brands,
                # drink_preference=drink_preference,
                response_preference=response_preference,
            )
    _page_footer()

if __name__ == "__main__":
    main()
