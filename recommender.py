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
        target_bracket = self.get_current_temp_bracket(weather["temp"])
        is_high_diff = weather["temp_diff"] >= 10.0
        is_wet = weather["is_raining_or_snowing"]
        feedback_bonus = self._get_feedback_bonus(user_id)

        # 선택한 성별 데이터만 필터링
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

            diff = abs(item_bracket - target_bracket)

            # [수정된 기온 매칭 로직: 하의 사계절 특성 반영]
            if row["category"] == "하의":
                if row.get("sub_type") == "반바지/쇼츠" and target_bracket <= 2:
                    score -= 40
                elif row.get("sub_type") == "기모팬츠" and target_bracket >= 6:
                    score -= 40
                else:
                    if diff <= 1:
                        score += 50
                        reason_tags.append("현재 기온 최적")
                    elif diff <= 3:
                        score += 35
                        reason_tags.append("사계절 데일리 팬츠")
                    else:
                        score += 20
                        reason_tags.append("기본 매칭")
            else:
                if diff == 0:
                    score += 50
                    reason_tags.append("현재 기온 최적")
                elif diff == 1:
                    score += 40
                    reason_tags.append("체감 기온 호환(±1)")
                elif diff == 2:
                    score += 15
                    reason_tags.append("체감 기온 허용(±2)")
                else:
                    score -= 30

            # 2. 실시간 랭킹 대조 가산점
            if is_ranking and realtime_rank <= 100:
                rank_bonus = max(15, 35 - int(realtime_rank * 0.2))
                score += rank_bonus
                reason_tags.append(f"실시간 랭킹 {realtime_rank}위🔥")
            else:
                base_bonus = max(1, 10 - int(order_rank * 0.02))
                score += base_bonus
                reason_tags.append(f"인기순 #{order_rank}")

            # 3. 일교차 10℃ 이상 레이어드 가중치
            if is_high_diff and row["is_layered"]:
                score += 25
                reason_tags.append("일교차 레이어드")

            # 4. 강수(비/눈) 방수/발수 가중치
            if is_wet and row["is_waterproof"]:
                score += 45
                reason_tags.append("우천 방수 특화☔")

            # 5. 사용자 피드백 반영
            fb_score = feedback_bonus.get(row["item_id"], 0)
            if fb_score != 0:
                score += fb_score
                reason_tags.append("취향 반영" if fb_score > 0 else "비선호 감점")

            scores.append(score)
            reasons.append(" · ".join(reason_tags))

        filtered_df["score"] = scores
        filtered_df["reason"] = reasons

        return filtered_df[filtered_df["score"] > 10].sort_values(
            by=["score", "rank", "order_rank"],
            ascending=[False, True, True]
        )