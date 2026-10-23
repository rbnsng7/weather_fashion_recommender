# ai_stylist.py
import requests
import pandas as pd

class GroqAIStylist:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else ""
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"

    def generate_styling_advice(self, weather: dict, gender: str, rec_df: pd.DataFrame) -> str:
        if not self.api_key or not self.api_key.startswith("gsk_"):
            return "⚠️ 올바른 Groq API 키가 설정되지 않았습니다."

        # 추천 엔진이 최고 점수로 선정한 1순위 실제 상품 데이터 추출
        outer_row = rec_df[rec_df["category"] == "아우터"].head(1)
        top_row = rec_df[rec_df["category"] == "상의"].head(1)
        bottom_row = rec_df[rec_df["category"] == "하의"].head(1)

        outer_item = outer_row.iloc[0] if not outer_row.empty else None
        top_item = top_row.iloc[0] if not top_row.empty else None
        bottom_item = bottom_row.iloc[0] if not bottom_row.empty else None

        if outer_item is None or top_item is None or bottom_item is None:
            return "추천할 의류 데이터 풀이 부족하여 브리핑을 생성할 수 없습니다."

        # 실제 확정된 아이템 정보 (CSV 기반 실제 데이터)
        fixed_outer = f"[{outer_item['brand']}] {outer_item['name']} (소재: {outer_item['material']})"
        fixed_top = f"[{top_item['brand']}] {top_item['name']} (소재: {top_item['material']})"
        fixed_bottom = f"[{bottom_item['brand']}] {bottom_item['name']} (소재: {bottom_item['material']})"

        # 실제 OpenWeather 수치
        city = weather.get("city", "")
        temp = weather.get("temp", 0)
        temp_min = weather.get("temp_min", 0)
        temp_max = weather.get("temp_max", 0)
        temp_diff = weather.get("temp_diff", 0)
        desc = weather.get("description", "")
        precip = weather.get("precipitation", 0.0)
        is_wet = weather.get("is_raining_or_snowing", False)

        prompt = f"""
당신은 날씨 기반 패션 에디터입니다.
아래에 제공된 [실제 기상 측정 데이터]와 알고리즘이 선정한 [확정 추천 의류]만 바탕으로 코디 분석 브리핑을 작성하세요.

[실제 기상 측정 데이터 (OpenWeather API)]
- 지역: {city}
- 현재 기온: {temp}℃ (최저 {temp_min}℃ / 최고 {temp_max}℃)
- 당일 일교차: {temp_diff}℃
- 날씨 상태: {desc}
- 강수량: {precip}mm (비/눈 여부: {'있음' if is_wet else '없음'})

[확정 추천 의류 셋업 (무신사 실제 데이터)]
- 아우터: {fixed_outer}
- 상의: {fixed_top}
- 하의: {fixed_bottom}

[엄격한 작성 규칙]
1. 위 [확정 추천 의류 셋업]에 명시된 아우터, 상의, 하의의 브랜드와 상품명만을 그대로 언급할 것. 새로운 제품이나 없는 브랜드를 지어내지 말 것.
2. 현재 기온({temp}℃)과 일교차({temp_diff}℃), 강수 정보만을 인용하여 왜 이 3가지 옷의 소재와 구성이 오늘 날씨에 최적인지 논리적으로 설명할 것.
3. 텍스트는 4줄 내외의 깔끔한 불릿 포인트 형식으로 작성할 것.
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 사실만을 바탕으로 패션 코디를 설명하는 AI 어시스턴트입니다. 제공된 데이터 외의 정보나 임의의 상품을 날조(지어내기)하지 마십시오."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,  # 사실성 유지를 위해 0.2로 낮춰 무작위성을 차단
            "max_tokens": 400
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"❌ 코디 브리핑 생성 실패: {e}"