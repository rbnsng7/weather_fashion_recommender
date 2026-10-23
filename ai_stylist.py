# ai_stylist.py
import requests
import pandas as pd

class GroqAIStylist:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else ""
        self.chat_url = "https://api.groq.com/openai/v1/chat/completions"
        self.models_url = "https://api.groq.com/openai/v1/models"

    def _get_available_model(self) -> str:
        """현재 계정에서 사용 가능한 텍스트 모델을 동적으로 탐색"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            res = requests.get(self.models_url, headers=headers, timeout=5)
            if res.status_code == 200:
                models = [m["id"] for m in res.json().get("data", [])]
                # 선호 모델 우선순위
                for pref in ["llama-3.1-8b-instant", "llama3-8b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"]:
                    if pref in models:
                        return pref
                # 없으면 whisper 등 음성 모델을 제외한 첫 번째 모델 선택
                for m_id in models:
                    if "whisper" not in m_id.lower():
                        return m_id
        except Exception:
            pass
        return "llama-3.1-8b-instant"

    def generate_styling_advice(self, weather: dict, gender: str, rec_df: pd.DataFrame) -> str:
        if not self.api_key:
            return "⚠️ Groq API 키가 비어있습니다. Secrets 설정을 확인해 주세요."

        # 추천 데이터 추출
        outer_row = rec_df[rec_df["category"] == "아우터"].head(1)
        top_row = rec_df[rec_df["category"] == "상의"].head(1)
        bottom_row = rec_df[rec_df["category"] == "하의"].head(1)

        outer_item = outer_row.iloc[0] if not outer_row.empty else None
        top_item = top_row.iloc[0] if not top_row.empty else None
        bottom_item = bottom_row.iloc[0] if not bottom_row.empty else None

        if outer_item is None or top_item is None or bottom_item is None:
            return "추천할 의류 데이터가 부족합니다."

        fixed_outer = f"[{outer_item['brand']}] {outer_item['name']} ({outer_item['material']})"
        fixed_top = f"[{top_item['brand']}] {top_item['name']} ({top_item['material']})"
        fixed_bottom = f"[{bottom_item['brand']}] {bottom_item['name']} ({bottom_item['material']})"

        city = weather.get("city", "부산")
        temp = weather.get("temp", 0)
        temp_diff = weather.get("temp_diff", 0)

        prompt = f"""
당신은 날씨 패션 에디터입니다.
실제 기상({city}, 현재 {temp}℃, 일교차 {temp_diff}℃)에 맞춰 아래 셋업을 추천하는 이유를 간결하게 3줄로 작성하세요.

- 아우터: {fixed_outer}
- 상의: {fixed_top}
- 하의: {fixed_bottom}
"""

        chosen_model = self._get_available_model()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": chosen_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 400
        }

        try:
            res = requests.post(self.chat_url, headers=headers, json=payload, timeout=15)
            
            # 200 성공이 아닌 경우 서버 응답 내용을 직접 출력
            if res.status_code != 200:
                return f"❌ [Groq 응답 코드 {res.status_code}] 사용모델: `{chosen_model}`\n\n서버 응답: `{res.text}`"

            return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"❌ 통신 예외 발생: {e}"