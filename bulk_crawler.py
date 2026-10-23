# bulk_crawler.py
import os
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from musinsa_crawler import auto_label_from_title

# 성별 코드 (전체 제외: 남성=M, 여성=F)
GENDERS = {
    "남성": "M",
    "여성": "F"
}

# 카테고리 코드 (001: 상의, 002: 아우터, 003: 하의/바지)
CATEGORY_CODES = {
    "상의": "001",
    "아우터": "002",
    "하의": "003"
}

CATEGORY_RANK_CODES = {
    "상의": "001000",
    "아우터": "002000",
    "하의": "003000"
}

def determine_season(bracket: int) -> str:
    if bracket in [1, 2]: return "겨울"
    elif bracket in [3, 4, 5, 6]: return "봄/가을"
    elif bracket in [7, 8]: return "여름"
    return "사계절"

def extract_goods_no(href: str) -> int:
    match = re.search(r"/products/(\d+)", href)
    return int(match.group(1)) if match else 0

class GenderSplitCrossReferenceCrawler:
    def __init__(self, save_path: str = "data/clothes_db.csv"):
        self.save_path = save_path
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

    def _init_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def fetch_ranking_map(self, driver, target_rank_count: int = 200) -> dict:
        """[1단계] 남성/여성별 각 카테고리 랭킹 상위권 매핑 (key: (성별, goods_no))"""
        print(f"🔍 [1/2] 성별(남성/여성) 실시간 랭킹 상위 {target_rank_count}개 수집 시작...")
        ranking_map = {}

        for gender_name, gf_code in GENDERS.items():
            for cat_name, rank_code in CATEGORY_RANK_CODES.items():
                rank_url = f"https://www.musinsa.com/main/musinsa/ranking?gf={gf_code}&sectionId=200&categoryCode={rank_code}"
                print(f"  - [{gender_name} - {cat_name}] 랭킹 접속 중: {rank_url}")
                driver.get(rank_url)
                time.sleep(3.0)

                cat_rank_count = 0
                seen_ids = set()
                no_new_attempts = 0

                while cat_rank_count < target_rank_count:
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    product_links = soup.select("a[href*='/products/']")
                    new_in_step = 0

                    for link in product_links:
                        if cat_rank_count >= target_rank_count:
                            break
                        goods_no = extract_goods_no(link.get("href", ""))
                        if goods_no == 0 or goods_no in seen_ids:
                            continue

                        seen_ids.add(goods_no)
                        cat_rank_count += 1
                        new_in_step += 1
                        # 성별과 상품번호를 튜플 키로 매핑
                        ranking_map[(gender_name, goods_no)] = cat_rank_count

                    if new_in_step > 0:
                        no_new_attempts = 0
                    else:
                        no_new_attempts += 1

                    driver.execute_script("window.scrollBy(0, 900);")
                    time.sleep(1.2)

                    if no_new_attempts >= 8:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2.0)
                        if no_new_attempts >= 15:
                            break

                print(f"    └─ [{gender_name} - {cat_name}] 랭킹 {cat_rank_count}개 수집 완료")

        print(f"✅ 총 {len(ranking_map)}개의 성별 실시간 랭킹 기준 확보 완료!\n")
        return ranking_map

    def fetch_category_items(self, driver, ranking_map: dict, target_per_category: int = 1000) -> list:
        """[2단계] 남성/여성 각 3개 카테고리에서 일반 상품 수집 및 랭킹 대조"""
        print(f"📦 [2/2] 성별 카테고리별 {target_per_category}개 수집 및 랭킹 대조 시작...")
        all_collected = []

        for gender_name, gf_code in GENDERS.items():
            for cat_name, cat_code in CATEGORY_CODES.items():
                cat_url = f"https://www.musinsa.com/category/{cat_code}/goods?gf={gf_code}"
                print(f"\n📂 [{gender_name} - {cat_name}] 상품 링크 접속 중: {cat_url}")
                driver.get(cat_url)
                time.sleep(3.5)

                cat_items = []
                seen_ids = set()
                no_new_attempts = 0

                while len(cat_items) < target_per_category:
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    product_links = soup.select("a[href*='/products/']")
                    new_in_step = 0

                    for link in product_links:
                        if len(cat_items) >= target_per_category:
                            break

                        href = link.get("href", "")
                        goods_no = extract_goods_no(href)
                        if goods_no == 0 or goods_no in seen_ids:
                            continue

                        card = link.find_parent("div")
                        if not card:
                            continue

                        img_tag = card.find("img")
                        
                        # 1. 무신사 title 속성 최우선 확인 및 시각장애인용 태그 필터링
                        title_text = link.get("title") or link.get("aria-label") or link.get_text(strip=True)
                        title_text = title_text.replace("상품 상세로 이동", "").strip()
                        
                        if not title_text and img_tag:
                            title_text = img_tag.get("alt", "").replace("상품 상세로 이동", "").strip()

                        if not title_text or len(title_text) < 2:
                            continue

                        brand_tag = card.select_one(".brand, .item_title, a[href*='/brand/']")
                        brand_name = brand_tag.get_text(strip=True) if brand_tag else "무신사"

                        img_url = (img_tag.get("src") or img_tag.get("data-original")) if img_tag else ""
                        if img_url and img_url.startswith("//"):
                            img_url = "https:" + img_url

                        # 기온별 8단계 자동 라벨링
                        labels = auto_label_from_title(title_text, cat_name)
                        season = determine_season(labels["temp_bracket"])

                        # 성별 랭킹 대조
                        is_in_ranking = (gender_name, goods_no) in ranking_map
                        realtime_rank = ranking_map[(gender_name, goods_no)] if is_in_ranking else 9999

                        seen_ids.add(goods_no)
                        new_in_step += 1

                        cat_items.append({
                            "item_id": goods_no,
                            "gender": gender_name,                  # '남성' 또는 '여성'
                            "is_ranking_item": is_in_ranking,
                            "rank": realtime_rank,
                            "order_rank": len(cat_items) + 1,
                            "brand": brand_name,
                            "name": title_text,
                            "category": cat_name,
                            "sub_type": labels["sub_type"],
                            "season": season,
                            "material": labels["material"],
                            "is_layered": labels["is_layered"],
                            "is_waterproof": labels["is_waterproof"],
                            "temp_bracket": labels["temp_bracket"],
                            "image_url": img_url,
                            "product_url": href if href.startswith("http") else f"https://www.musinsa.com{href}"
                        })

                    if new_in_step > 0:
                        no_new_attempts = 0
                        if len(cat_items) % 50 == 0 or len(cat_items) >= target_per_category:
                            matched = sum(1 for x in cat_items if x["is_ranking_item"])
                            print(f"  - [{gender_name} - {cat_name}] {len(cat_items)} / {target_per_category}개 수집 중 (랭킹 일치: {matched}개)")
                    else:
                        no_new_attempts += 1

                    driver.execute_script("window.scrollBy(0, 900);")
                    time.sleep(1.3)

                    if no_new_attempts >= 10:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2.0)
                        if no_new_attempts >= 20:
                            print(f"  - [{gender_name} - {cat_name}] 페이지 끝에 도달하여 수집을 마칩니다.")
                            break

                print(f"✅ [{gender_name} - {cat_name}] 수집 완료 (총 {len(cat_items)}개 중 랭킹 일치: {sum(1 for x in cat_items if x['is_ranking_item'])}개)")
                all_collected.extend(cat_items)

        return all_collected

    def run(self, ranking_target: int = 200, category_target: int = 1000) -> pd.DataFrame:
        driver = self._init_driver()
        try:
            ranking_map = self.fetch_ranking_map(driver, target_rank_count=ranking_target)
            data = self.fetch_category_items(driver, ranking_map, target_per_category=category_target)
        finally:
            driver.quit()

        df = pd.DataFrame(data)
        df.to_csv(self.save_path, index=False, encoding="utf-8-sig")
        print(f"\n🎉 총 {len(df):,}개 (남성/여성 전용) 상품 수집 및 랭킹 대조 완료! -> '{self.save_path}'")
        return df

if __name__ == "__main__":
    crawler = GenderSplitCrossReferenceCrawler(save_path="data/clothes_db.csv")
    # ranking_target=100 (남/여 랭킹 100개씩)
    # category_target=500 (남/여 일반 500개씩: 상의 500, 아우터 500, 하의 500)
    crawler.run(ranking_target=100, category_target=500)