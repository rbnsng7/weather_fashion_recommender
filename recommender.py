# recommender.py
import os
import pandas as pd

class GenderRankingWeatherRecommender:
    def __init__(self, db_path: str = "data/clothes_db.csv", feedback_path: str = "data/feedback_log.csv"):
        self.db_path = db_path
        self.feedback_path = feedback_path
        self.df = pd.read_csv(db_path)

    @staticmethod
    def get_current_temp_bracket(temp: float) -> int:
        if temp <= 4: return 1
        elif temp <= 8: return 2
        elif temp <= 11: return 3
        elif temp <= 16: return 4
        elif temp <= 19: return 5
        elif temp <= 22: return 6
        elif temp <= 27: return 7
        else: return 8

    def _get_feedback_bonus(self, user_id: str = "default_user") -> dict:
        if not os.path.exists(self.feedback_path): return {}
        fb_df = pd.read_csv(self.feedback_path)
        user_fb = fb_df[fb_df["user_id"] == user_id]
        if user_fb.empty: return {}
        scores = user_fb.groupby("item_id")["rating"].sum().to_dict()
        return {k: v * 15 if v > 0 else v * 20 for k, v in scores.items()}

    def recommend(self, weather: dict, target_gender: str = "남성", user_id: str = "default_user") -> pd.DataFrame:
        """
        선택한 성별(남성 또는 여성)의 데이터만 정확히 필터링한 후
        오늘 날씨(기온/일교차/강수) + 실시간 랭킹 대조 점수를 합산해 추천합니다.
        """
        target_bracket = self.get_current_temp_bracket(weather["temp"])
        is_high_diff = weather["temp_diff"] >= 10.0
        is_wet = weather["is_raining_or_snowing"]
        feedback_bonus = self._get_feedback_bonus(user_id)

        # 1. 성별 정확 일치 데이터만 추출 ('전체' 제외)
        filtered_df = self.df[self.df["gender"] == target_gender].copy()

        scores = []
        reasons = []

        for _, row in filtered_df.iterrows():
            score = 0
            reason_tags = []
            item_bracket = int(row["temp_bracket"])
            is_ranking = bool(row.get("is_ranking_item", False))
            realtime_rank = int(row.get("rank", 9999))
            order_rank = int(row.get("order_rank", 100))

            # 2. 기온 매칭 기본 점수
            if item_bracket == target_bracket:
                score += 50
                reason_tags.append("현재 기온 최적")
            elif abs(item_bracket - target_bracket) == 1:
                score += 30
                reason_tags.append("기온 호환")
            else:
                score -= 40

            # 3. ★ 실시간 랭킹(200위) 대조 가산점 ★
            if is_ranking and realtime_rank <= 200:
                # 랭킹 1위 +35점 ~ 200위 +15점
                rank_bonus = max(15, 35 - int(realtime_rank * 0.1))
                score += rank_bonus
                reason_tags.append(f"실시간 랭킹 {realtime_rank}위🔥")
            else:
                # 일반 1,000개 상품은 기본 노출 순서에 따라 소폭 가산 (+1 ~ +10점)
                base_bonus = max(1, 10 - int(order_rank * 0.01))
                score += base_bonus
                reason_tags.append(f"인기순 #{order_rank}")

            # 4. 일교차 10℃ 이상 시 레이어드 가중치
            if is_high_diff and row["is_layered"]:
                score += 25
                reason_tags.append("일교차 레이어드")

            # 5. 비/눈 올 때 방수/발수 가중치
            if is_wet and row["is_waterproof"]:
                score += 45
                reason_tags.append("우천 방수 특화☔")

            # 6. 사용자 좋아요/싫어요 반영
            fb_score = feedback_bonus.get(row["item_id"], 0)
            if fb_score != 0:
                score += fb_score
                reason_tags.append("취향 반영" if fb_score > 0 else "비선호 감점")

            scores.append(score)
            reasons.append(" · ".join(reason_tags))

        filtered_df["score"] = scores
        filtered_df["reason"] = reasons

        # 기온에 맞는 의류 중 점수 높은 순 정렬
        return filtered_df[filtered_df["score"] > 20].sort_values(
            by=["score", "rank", "order_rank"],
            ascending=[False, True, True]
        )