# ai_stylist.py
import requests
import pandas as pd

class GroqAIStylist:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else ""
        self.chat_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"

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

        # 비상 대체 텍스트 구성
        fixed_outer = f"[{outer_item['brand']}] {outer_item['name']} ({outer_item['material']})" if outer_item is not None else "기본 아우터"
        fixed_top = f"[{top_item['brand']}] {top_item['name']} ({top_item['material']})" if top_item is not None else "기본 상의"
        fixed_bottom = f"[{bottom_item['brand']}] {bottom_item['name']} ({bottom_item['material']})" if bottom_item is not None else "기본 하의"

        city = weather.get("city", "부산")
        temp = weather.get("temp", 15)
        temp_diff = weather.get("temp_diff", 5)

        prompt = f"""당신은 트렌디한 2030 무신사 패션 스타일리스트입니다.
오늘의 실제 기상({city}, 현재 {temp}℃, 일교차 {temp_diff}℃)과 추천 1위 아이템들을 바탕으로 코디 브리핑을 작성하세요.

[선정된 원픽 셋업]
- 아우터: {fixed_outer}
- 상의: {fixed_top}
- 하의: {fixed_bottom}

[작성 요구사항]
1. 위 셋업의 실제 브랜드명과 상품명을 정확히 언급하며 베스트 코디 조합을 제안하세요.
2. 현재 기온({temp}℃)에 이 옷의 소재와 구성이 왜 어울리는지 2문장으로 설명하세요.
3. 어울리는 신발이나 이너 매치 팁을 1문장 추가하세요.
4. 불릿 포인트(-) 형식으로 깔끔하게 4줄 내외로 작성하세요."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "당신은 무신사 실시간 랭킹 의류를 매칭해 주는 패션 에디터입니다."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4,
            "max_tokens": 500
        }

        try:
            res = requests.post(self.chat_url, headers=headers, json=payload, timeout=15)
            if res.status_code != 200:
                return f"❌ Groq 응답 오류 ({res.status_code}): {res.text}"
            
            result_json = res.json()
            return result_json["choices"][0]["message"]["content"]
        except Exception as e:
            return f"❌ AI 통신 실패: {e}"