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
        # 구형 Llama3 단종에 대비해 가장 안정적인 Mixtral을 최후의 보루로 설정
        fallback_model = "mixtral-8x7b-32768"
        
        try:
            res = requests.get(self.models_url, headers=headers, timeout=5)
            if res.status_code == 200:
                model_ids = [m["id"] for m in res.json().get("data", [])]
                
                # 현재 Groq에서 100% 공식 지원하는 최신/안정화 텍스트 모델 목록
                preferred_models = [
                    "llama-3.3-70b-versatile",
                    "gemma2-9b-it",
                    "mixtral-8x7b-32768"
                ]
                for p in preferred_models:
                    if p in model_ids:
                        return p
        except Exception:
            pass
        return fallback_model

    def generate_styling_advice(self, weather: dict, gender: str, rec_df: pd.DataFrame) -> str:
        if not self.api_key:
            return "⚠️ Groq API 키가 설정되지 않았습니다."

        if rec_df is None or rec_df.empty:
            return "⚠️ 분석할 추천 의류 데이터가 없습니다."

        outer_row = rec_df[rec_df["category"] == "아우터"].head(1)
        top_row = rec_df[rec_df["category"] == "상의"].head(1)
        bottom_row = rec_df[rec_df["category"] == "하의"].head(1)

        outer = outer_row.iloc[0] if not outer_row.empty else None
        top = top_row.iloc[0] if not top_row.empty else None
        bottom = bottom_row.iloc[0] if not bottom_row.empty else None

        if outer is None or top is None or bottom is None:
            return "⚠️ 전체 셋업(아우터, 상의, 하의) 데이터가 부족합니다."

        def format_item(item):
            name = str(item['name'])
            if "상품 상세로 이동" in name or len(name) < 2:
                name = f"추천 {item['category']} 확인하기"
            return f"[{item['brand']}] **[{name}]({item['product_url']})**"

        setup_display = (
            f"🎯 **오늘의 [{gender}] 원픽 셋업**\n"
            f"- **아우터:** {format_item(outer)}\n"
            f"- **상의:** {format_item(top)}\n"
            f"- **하의:** {format_item(bottom)}\n\n"
            f"💡 **스타일링 팁**\n\n"
        )

        city = weather.get("city", "부산")
        temp = weather.get("temp", 15.0)
        temp_diff = weather.get("temp_diff", 5.0)
        is_wet = weather.get("is_raining_or_snowing", False)
        wet_text = "비/눈 소식 있음" if is_wet else "강수 없음"

        prompt = f"""당신은 무신사 패션 에디터입니다.
오늘 {city} 날씨(기온 {temp}℃, 일교차 {temp_diff}℃, {wet_text})에 맞춰 아래 소재 조합의 장점을 설명해주세요.

[선정된 아이템 소재]
- 아우터: {outer['material']}
- 상의: {top['material']}
- 하의: {bottom['material']}

[작성 규칙]
1. 인사말이나 다른 말 없이 바로 본론만 출력하세요.
2. 현재 기온({temp}℃)에 위 소재 조합이 왜 쾌적하고 실용적인지 2문장으로 설명하세요.
3. 이 셋업에 어울릴 만한 구체적인 신발(예: 스니커즈, 더비 슈즈 등)이나 가방 매치 팁을 1문장 추가하세요.
4. 반드시 불릿 포인트(-)로 시작하는 3줄로만 간결하게 작성하세요."""

        active_model = self._get_active_model()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": "당신은 답변을 시작할 때 반드시 '-' 기호로 시작해야 합니다. 빈 텍스트를 반환하지 마십시오."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4,
            "max_tokens": 500
        }

        try:
            res = requests.post(self.chat_url, headers=headers, json=payload, timeout=20)
            if res.status_code != 200:
                return f"{setup_display}\n❌ (Groq API 오류: {res.text})"
            
            ai_advice = res.json()["choices"][0]["message"]["content"].strip()
            
            if not ai_advice:
                ai_advice = (
                    f"- 현재 기온({temp}℃)에 부합하는 밸런스 좋은 조합입니다.\n"
                    f"- 일교차({temp_diff}℃)에 대비해 입고 벗기 편하게 구성되었습니다.\n"
                    f"- 미니멀한 스니커즈를 매치하면 더욱 세련된 룩이 완성됩니다."
                )
                
            return f"{setup_display}{ai_advice}"
            
        except Exception as e:
            return f"{setup_display}\n❌ 통신 실패: {e}"