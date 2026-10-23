# ai_stylist.py
import requests
import pandas as pd

class GroqAIStylist:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else ""
        self.chat_url = "https://api.groq.com/openai/v1/chat/completions"
        self.models_url = "https://api.groq.com/openai/v1/models"

    def _get_active_model(self) -> str:
        """한국어를 잘 구사하는 고성능 모델만 엄선하여 동적 선택"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            res = requests.get(self.models_url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                model_ids = [m["id"] for m in data]

                # 한국어를 매끄럽게 처리하는 검증된 모델 우선순위 (외계어 뿜는 8B는 배제)
                korean_supported_models = [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-70b-versatile",
                    "mixtral-8x7b-32768",
                    "gemma2-9b-it"
                ]
                for model_candidate in korean_supported_models:
                    if model_candidate in model_ids:
                        return model_candidate

                # 혹시 위 목록이 없으면 음성/임베딩/구형8B 제외한 첫 모델 선택
                for m_id in model_ids:
                    skip_keywords = ["whisper", "embed", "guard", "llama3-8b"]
                    if not any(skip in m_id.lower() for skip in skip_keywords):
                        return m_id
        except Exception:
            pass
        return "llama-3.3-70b-versatile"

    def generate_styling_advice(self, weather: dict, gender: str, rec_df: pd.DataFrame) -> str:
        if not self.api_key:
            return "⚠️ Groq API 키가 설정되지 않았습니다. Secrets를 확인해 주세요."

        if rec_df is None or rec_df.empty:
            return "⚠️ 분석할 추천 의류 데이터가 없습니다."

        # 추천 데이터 1순위 추출
        outer_row = rec_df[rec_df["category"] == "아우터"].head(1)
        top_row = rec_df[rec_df["category"] == "상의"].head(1)
        bottom_row = rec_df[rec_df["category"] == "하의"].head(1)

        outer_item = outer_row.iloc[0] if not outer_row.empty else None
        top_item = top_row.iloc[0] if not top_row.empty else None
        bottom_item = bottom_row.iloc[0] if not bottom_row.empty else None

        fixed_outer = f"[{outer_item['brand']}] {outer_item['name']} ({outer_item['material']})" if outer_item is not None else "기본 아우터"
        fixed_top = f"[{top_item['brand']}] {top_item['name']} ({top_item['material']})" if top_item is not None else "기본 상의"
        fixed_bottom = f"[{bottom_item['brand']}] {bottom_item['name']} ({bottom_item['material']})" if bottom_item is not None else "기본 하의"

        city = weather.get("city", "부산")
        temp = weather.get("temp", 15)
        temp_diff = weather.get("temp_diff", 5)

        prompt = f"""당신은 무신사 공식 패션 에디터입니다.
오늘 {city} 날씨(현재 기온 {temp}℃, 일교차 {temp_diff}℃)에 맞춰 선별된 아래 3개 아이템의 스타일링 가이드를 작성해 주세요.

[확정된 코디 아이템]
1. 아우터: {fixed_outer}
2. 상의: {fixed_top}
3. 하의: {fixed_bottom}

[작성 규칙]
- 위 3개 아이템의 실제 브랜드명과 상품명을 있는 그대로 인용하세요.
- 현재 날씨와 기온({temp}℃)에 이 옷들의 소재와 조합이 왜 적절한지 설명하세요.
- 어울리는 신발이나 레이어드 팁을 한 줄 덧붙이세요.
- 한국어로 자연스럽고 깔끔하게 3~4개의 불릿 포인트(-)로 정리하세요."""

        active_model = self._get_active_model()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": "당신은 한국어 패션 매거진 에디터입니다. 반드시 자연스러운 한국어로만 답변하십시오."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 800
        }

        try:
            res = requests.post(self.chat_url, headers=headers, json=payload, timeout=20)
            if res.status_code != 200:
                return f"❌ Groq 응답 오류 ({res.status_code}) [선택모델: {active_model}]: {res.text}"

            result_json = res.json()
            return result_json["choices"][0]["message"]["content"]
        except Exception as e:
            return f"❌ AI 통신 실패: {e}"