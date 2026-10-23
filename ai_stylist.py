# ai_stylist.py
import requests
import pandas as pd

class GroqAIStylist:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else ""
        self.chat_url = "https://api.groq.com/openai/v1/chat/completions"
        self.models_url = "https://api.groq.com/openai/v1/models"

    def _get_active_model(self) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            res = requests.get(self.models_url, headers=headers, timeout=5)
            if res.status_code == 200:
                model_ids = [m["id"] for m in res.json().get("data", [])]
                for p in ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]:
                    if p in model_ids:
                        return p
                for m_id in model_ids:
                    if not any(skip in m_id.lower() for skip in ["whisper", "embed", "guard", "llama3-8b"]):
                        return m_id
        except Exception:
            pass
        return "llama-3.3-70b-versatile"

    def generate_styling_advice(self, weather: dict, gender: str, rec_df: pd.DataFrame) -> str:
        if not self.api_key:
            return "⚠️ Groq API 키가 설정되지 않았습니다."

        if rec_df is None or rec_df.empty:
            return "⚠️ 분석할 추천 의류 데이터가 없습니다."

        # 1. 추천 데이터 1순위 추출
        outer_row = rec_df[rec_df["category"] == "아우터"].head(1)
        top_row = rec_df[rec_df["category"] == "상의"].head(1)
        bottom_row = rec_df[rec_df["category"] == "하의"].head(1)

        outer = outer_row.iloc[0] if not outer_row.empty else None
        top = top_row.iloc[0] if not top_row.empty else None
        bottom = bottom_row.iloc[0] if not bottom_row.empty else None

        if not all([outer, top, bottom]):
            return "⚠️ 전체 셋업(아우터, 상의, 하의) 데이터가 부족합니다."

        # ==========================================================
        # 2. [핵심] 파이썬을 이용해 브랜드명과 상품명을 화면에 100% 강제 고정
        # ==========================================================
        setup_display = (
            f"🎯 **오늘의 [{gender}] 원픽 셋업**\n"
            f"- **아우터:** [{outer['brand']}] {outer['name']}\n"
            f"- **상의:** [{top['brand']}] {top['name']}\n"
            f"- **하의:** [{bottom['brand']}] {bottom['name']}\n\n"
            f"💡 **스타일링 팁**\n"
        )

        city = weather.get("city", "부산")
        temp = weather.get("temp", 15.0)
        temp_diff = weather.get("temp_diff", 5.0)
        is_wet = weather.get("is_raining_or_snowing", False)
        wet_text = "비/눈 소식 있음" if is_wet else "맑음"

        # 3. AI에게는 오직 '이 옷을 입어야 하는 날씨적 이유'와 '신발 매치'만 물어봄
        prompt = f"""당신은 무신사 패션 에디터입니다.
오늘 {city} 날씨(기온 {temp}℃, 일교차 {temp_diff}℃, {wet_text})에 맞춰 추천된 코디의 장점을 설명해주세요.

[선정된 아이템 소재]
- 아우터: {outer['material']}
- 상의: {top['material']}
- 하의: {bottom['material']}

[작성 규칙]
1. 상품명이나 브랜드명은 말하지 말고, "이 아우터는...", "이 셋업은..." 등으로 부르세요.
2. 현재 날씨({temp}℃, {wet_text})와 위 소재들의 조합이 왜 쾌적하고 실용적인지 2문장으로 설명하세요.
3. 이 셋업에 어울릴 만한 구체적인 신발(예: 화이트 스니커즈, 더비 슈즈 등)이나 가방 매치 팁을 1문장 추가하세요.
4. 불릿 포인트(-)로 딱 3줄만 간결하고 트렌디하게 작성하세요."""

        active_model = self._get_active_model()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": "당신은 한국어 패션 매거진 에디터입니다."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            res = requests.post(self.chat_url, headers=headers, json=payload, timeout=20)
            if res.status_code != 200:
                return f"❌ Groq 응답 오류: {res.text}"
            
            ai_advice = res.json()["choices"][0]["message"]["content"]
            
            # 파이썬으로 만든 확정 텍스트 아래에 AI의 브리핑을 합쳐서 반환
            return f"{setup_display}{ai_advice}"
            
        except Exception as e:
            return f"❌ 통신 실패: {e}"