# weather_api.py
from datetime import datetime
import requests

class WeatherClient:
    def __init__(self, api_key: str = "YOUR_OPENWEATHER_API_KEY"):
        self.api_key = api_key
        # 1. 현재 날씨 엔드포인트 (현재 기온, 강수, 날씨 상태용)
        self.current_url = "https://api.openweathermap.org/data/2.5/weather"
        # 2. 5일/3시간 예보 엔드포인트 (오늘의 실제 최고/최저 기온 계산용)
        self.forecast_url = "https://api.openweathermap.org/data/2.5/forecast"

    def get_weather_by_city(self, city: str = "Busan") -> dict:
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "lang": "kr"
        }

        try:
            # [Step 1] 현재 날씨 호출
            curr_res = requests.get(self.current_url, params=params, timeout=5)
            curr_res.raise_for_status()
            curr_data = curr_res.json()

            temp_current = round(curr_data["main"]["temp"], 1)
            weather_main = curr_data["weather"][0]["main"]
            description = curr_data["weather"][0]["description"]
            humidity = curr_data["main"]["humidity"]

            rain_1h = curr_data.get("rain", {}).get("1h", 0.0)
            snow_1h = curr_data.get("snow", {}).get("1h", 0.0)
            precipitation = rain_1h + snow_1h
            is_wet = weather_main in ["Rain", "Snow", "Drizzle", "Thunderstorm"] or precipitation > 0

            # [Step 2] 3시간 예보 호출하여 오늘의 실제 최저/최고 기온 추출
            fore_res = requests.get(self.forecast_url, params=params, timeout=5)
            fore_res.raise_for_status()
            fore_data = fore_res.json()

            # 오늘 날짜(YYYY-MM-DD) 기준
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_temps = []

            for item in fore_data.get("list", []):
                # 예보 시각 문자열 (예: "2026-10-17 12:00:00")
                dt_txt = item.get("dt_txt", "")
                if dt_txt.startswith(today_str):
                    today_temps.append(item["main"]["temp"])

            # 만약 밤늦게 호출해서 오늘 남은 예보가 1개 이하일 경우 다음 24시간(8개 슬롯) 데이터 사용
            if len(today_temps) < 2:
                today_temps = [item["main"]["temp"] for item in fore_data.get("list", [])[:8]]

            if today_temps:
                real_temp_min = round(min(today_temps), 1)
                real_temp_max = round(max(today_temps), 1)
            else:
                real_temp_min = temp_current - 3.0
                real_temp_max = temp_current + 3.0

            # 현재 기온이 예보 최저보다 낮거나 최고보다 높을 수 있으므로 보정
            real_temp_min = min(real_temp_min, temp_current)
            real_temp_max = max(real_temp_max, temp_current)
            temp_diff = round(real_temp_max - real_temp_min, 1)

            return {
                "city": city,
                "temp": temp_current,
                "temp_min": real_temp_min,
                "temp_max": real_temp_max,
                "temp_diff": temp_diff,
                "humidity": humidity,
                "weather_main": weather_main,
                "description": description,
                "precipitation": precipitation,
                "is_raining_or_snowing": is_wet
            }

        except Exception as e:
            # API 키 오류나 네트워크 제한 시 기본 테스트값 반환
            return {
                "city": city,
                "temp": 15.0,
                "temp_min": 8.5,
                "temp_max": 20.0,
                "temp_diff": 11.5,
                "humidity": 65,
                "weather_main": "Clear",
                "description": "맑고 쾌청함",
                "precipitation": 0.0,
                "is_raining_or_snowing": False
            }