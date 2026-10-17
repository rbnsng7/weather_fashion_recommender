# app.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st

from weather_api import WeatherClient
from recommender import GenderRankingWeatherRecommender

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="무신사 실시간 랭킹 × 날씨 맞춤 코디 추천",
    page_icon="🧥",
    layout="wide"
)

DB_PATH = "data/clothes_db.csv"
FEEDBACK_PATH = "data/feedback_log.csv"

# 피드백 저장 함수
def log_feedback(user_id: str, item_id: int, gender: str, temp: float, weather_main: str, rating: int):
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    new_row = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "gender_filter": gender,
        "item_id": item_id,
        "temp": temp,
        "weather_main": weather_main,
        "rating": rating
    }])
    if os.path.exists(FEEDBACK_PATH):
        new_row.to_csv(FEEDBACK_PATH, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        new_row.to_csv(FEEDBACK_PATH, mode="w", header=True, index=False, encoding="utf-8-sig")


# --- 2. 사이드바 설정 (시뮬레이션 제거) ---
st.sidebar.header("👤 맞춤 설정")
user_id = st.sidebar.text_input("사용자 ID", value="user_01")

selected_gender = st.sidebar.radio(
    "성별 선택",
    options=["남성", "여성"],
    index=0,
    horizontal=True,
    help="선택한 성별의 실시간 랭킹 100위 대조 및 500개 풀 기반으로 추천합니다."
)

st.sidebar.divider()
st.sidebar.header("🌤️ 지역 선택")
city = st.sidebar.selectbox("지역 선택", ["Busan", "Seoul", "Incheon", "Daegu", "Jeju"])

# app.py 3번 영역: 실시간 날씨 API 연동 부분 교체
# ----------------------------------------------------
if "OPENWEATHER_API_KEY" not in st.secrets:
    st.error("🔑 Streamlit Secrets에 `OPENWEATHER_API_KEY`가 설정되어 있지 않습니다.")
    st.info("로컬 환경: `.streamlit/secrets.toml` 파일에 키를 추가해 주세요.\n\n클라우드 배포 환경: App Settings -> Secrets에 키를 입력해 주세요.")
    st.stop()

API_KEY = st.secrets["OPENWEATHER_API_KEY"]
client = WeatherClient(api_key=API_KEY)
weather = client.get_weather_by_city(city)
# ----------------------------------------------------


# --- 4. 메인 날씨 요약 배너 ---
weather_icons = {"Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️", "Snow": "❄️", "Thunderstorm": "⛈️"}
icon = weather_icons.get(weather["weather_main"], "🌤️")
bracket = GenderRankingWeatherRecommender.get_current_temp_bracket(weather["temp"])

st.title(f"{icon} {weather['city']} 실시간 기상 × 무신사 [{selected_gender}] 코디 추천")
st.markdown(
    f"**현재 날씨:** {weather['description']} (기온별 **{bracket}단계** 구간) · "
    f"**적용 필터:** 무신사 **{selected_gender}** 랭킹(100위) 대조 및 500개 풀 기반"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("현재 기온", f"{weather['temp']} ℃", f"최고 {weather['temp_max']}℃ / 최저 {weather['temp_min']}℃")
col2.metric("일교차", f"{weather['temp_diff']} ℃", "레이어드 필수!" if weather["temp_diff"] >= 10 else "일교차 보통")
col3.metric("습도", f"{weather['humidity']} %")
col4.metric("강수 상태", "강수 감지됨 ☔" if weather["is_raining_or_snowing"] else "강수 없음", f"{weather['precipitation']} mm")

if weather["temp_diff"] >= 10 and weather["is_raining_or_snowing"]:
    st.warning(f"💡 **오늘의 {selected_gender} 스타일 팁:** 일교차가 10℃ 이상 벌어지고 비/눈 소식이 있습니다. 가벼운 아우터 레이어드와 방수 의류를 추천합니다!")
elif weather["temp_diff"] >= 10:
    st.info(f"💡 **오늘의 {selected_gender} 스타일 팁:** 낮과 밤의 기온 차가 10℃ 이상 벌어집니다. 입고 벗기 편한 가디건이나 자켓을 꼭 챙기세요.")
elif weather["is_raining_or_snowing"]:
    st.warning("💡 **오늘의 스타일 팁:** 강수가 감지되었습니다. 방수/발수 소재 의류가 최우선 추천됩니다.")

st.divider()


# --- 5. 카테고리별 맞춤 의류 추천 카드 (아우터, 상의, 하의) ---
if not os.path.exists(DB_PATH):
    st.error("의류 데이터베이스(`data/clothes_db.csv`)가 없습니다. 터미널에서 `python bulk_crawler.py`를 먼저 실행해 주세요.")
    st.stop()

recommender = GenderRankingWeatherRecommender(DB_PATH, FEEDBACK_PATH)
rec_df = recommender.recommend(weather, target_gender=selected_gender, user_id=user_id)

categories = ["아우터", "상의", "하의"]
st.subheader(f"👕 [{selected_gender}] 카테고리별 추천 TOP 3")

cols = st.columns(3)
for idx, cat in enumerate(categories):
    with cols[idx]:
        st.markdown(f"### 📌 {cat}")
        cat_items = rec_df[rec_df["category"] == cat].head(3)

        if cat_items.empty:
            st.caption(f"현재 기온에 알맞은 {cat} 상품이 없습니다.")
        for _, item in cat_items.iterrows():
            with st.container(border=True):
                if item["is_ranking_item"]:
                    st.markdown(f"🔥 **{selected_gender} 실시간 랭킹 {int(item['rank'])}위** | `{item['brand']}`")
                else:
                    st.markdown(f"✨ **{selected_gender} 인기 #{int(item['order_rank'])}** | `{item['brand']}`")

                st.image(item["image_url"], use_container_width=True)
                st.markdown(f"**{item['name']}**")
                st.caption(f"소재: {item['material']} | 추천점수: **{item['score']}점**")
                st.markdown(f"🏷️ `{item['reason']}`")
                st.link_button("🔗 무신사 상품 확인하기", item["product_url"], use_container_width=True)

                btn1, btn2 = st.columns(2)
                if btn1.button("👍 좋아요", key=f"like_{item['item_id']}"):
                    log_feedback(user_id, item["item_id"], selected_gender, weather["temp"], weather["weather_main"], 1)
                    st.toast(f"'{item['name']}' 선호 취향이 저장되었습니다!")
                    st.rerun()
                if btn2.button("👎 싫어요", key=f"dislike_{item['item_id']}"):
                    log_feedback(user_id, item["item_id"], selected_gender, weather["temp"], weather["weather_main"], -1)
                    st.toast(f"'{item['name']}' 비선호 피드백이 반영되었습니다.")
                    st.rerun()