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
당신은 트렌디한 2030 무신사 패션 에디터입니다.
오늘의 실제 기상({city}, 현재 {temp}℃, 일교차 {temp_diff}℃)과 추천 1위 아이템들을 분석하여 실전 코디 브리핑을 작성하세요.

[선정된 원픽 셋업]
- 아우터: {fixed_outer}
- 상의: {fixed_top}
- 하의: {fixed_bottom}

[작성 가이드라인]
1. 위 셋업의 실제 [브랜드명]과 [상품명]을 정확히 언급하며 베스트 코디 조합을 제안하세요.
2. 현재 기온({temp}℃)과 날씨 조건에서 이 조합이 왜 최적인지 소재와 실루엣 관점에서 2문장으로 설명하세요.
3. 여기에 어울릴 만한 신발(스니커즈, 로퍼 등)이나 이너/가방 연출 팁을 1문장 추가하세요.
4. 불릿 포인트(-) 형식으로 읽기 편하게 4줄 내외로 작성하세요.
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