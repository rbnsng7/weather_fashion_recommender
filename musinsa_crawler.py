import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# musinsa_crawler.py 내부 함수 교체
def auto_label_from_title(title: str, main_category: str) -> dict:
    title_lower = title.lower()

    # 하의 카테고리일 때 전용 라벨링 (하의 누락 방지 핵심)
    if main_category == "하의":
        # 1. 겨울/기모 하의 (1~2단계)
        if any(w in title_lower for w in ["기모", "융기모", "웜", "플리스팬츠", "패딩팬츠"]):
            return {"sub_type": "기모팬츠", "temp_bracket": 1, "is_layered": False, "is_waterproof": False, "material": "기모 코튼"}
        
        # 2. 여름/반바지/린넨 (7~8단계)
        if any(w in title_lower for w in ["반바지", "쇼츠", "숏팬츠", "버뮤다", "린넨팬츠", "리넨", "쿨링", "나일론쇼츠"]):
            is_wp = any(w in title_lower for w in ["나일론", "발수", "방수"])
            return {"sub_type": "반바지/쇼츠", "temp_bracket": 7, "is_layered": False, "is_waterproof": is_wp, "material": "나일론/면"}
        
        # 3. 여성 스커트류
        if any(w in title_lower for w in ["스커트", "치마", "플리츠", "미니스커트", "롱스커트"]):
            return {"sub_type": "스커트", "temp_bracket": 5, "is_layered": False, "is_waterproof": False, "material": "폴리/코튼"}

        # 4. 일반 사계절 바지 (슬랙스, 청바지, 카고, 조거, 스웨트팬츠, 일반 팬츠)
        # 대부분의 바지는 3~6단계(10℃~22℃) 전반에서 착용 가능하므로 대표 5단계로 설정하되
        # recommender에서 사계절 하의로 폭넓게 인정하도록 설정
        sub = "팬츠"
        if any(w in title_lower for w in ["데님", "청바지", "진", "jean"]):
            sub = "청바지"
        elif any(w in title_lower for w in ["슬랙스", "트라우저"]):
            sub = "슬랙스"
        elif any(w in title_lower for w in ["조거", "스웨트", "트레이닝", "츄리닝"]):
            sub = "스웨트팬츠"
        elif any(w in title_lower for w in ["카고", "파라슈트", "워크"]):
            sub = "카고팬츠"

        return {"sub_type": sub, "temp_bracket": 5, "is_layered": False, "is_waterproof": False, "material": "코튼/데님"}

    # 아우터 및 상의 라벨링 (기존 로직)
    keyword_rules = [
        (["패딩", "푸퍼", "다운", "무스탕", "헤비"], ("패딩", 1, False, True, "다운/나일론")),
        (["기모", "융기모"], ("기모상의", 1, False, False, "기모 코튼")),
        (["울코트", "발마칸", "더플", "캐시미어 코트"], ("울코트", 2, False, False, "울 혼방")),
        (["가죽", "레더", "무톤", "라이더"], ("가죽자켓", 2, True, False, "레더")),
        (["플리스", "후리스", "뽀글이"], ("플리스", 2, True, False, "플리스")),
        (["트렌치", "맥코트"], ("트렌치코트", 3, True, False, "코튼/개버딘")),
        (["야상", "점퍼", "블루종", "바시티", "ma-1"], ("점퍼", 3, True, False, "나일론/폴리")),
        (["바람막이", "윈드브레이커", "아노락", "고어텍스"], ("바람막이", 4, True, True, "나일론(방수/발수)")),
        (["가디건", "볼레로"], ("가디건", 4, True, False, "니트/울")),
        (["자켓", "재킷", "블레이저", "트러커"], ("자켓", 4, True, False, "폴리/데님")),
        (["후드 집업", "후드집업"], ("후드집업", 4, True, False, "면/폴리")),
        (["니트", "스웨터", "풀오버", "터틀넥"], ("니트", 3, False, False, "울/아크릴")),
        (["맨투맨", "스웨트셔츠", "스웻셔츠"], ("맨투맨", 4, False, False, "면 100%")),
        (["후드"], ("후드티", 5, False, False, "면/폴리")),
        (["블라우스"], ("블라우스", 5, True, False, "폴리/실크")),
        (["셔츠", "남방", "옥스포드"], ("셔츠", 6, True, False, "코튼")),
        (["긴팔", "롱슬리브"], ("긴팔티", 6, False, False, "면")),
        (["크롭", "반팔", "티셔츠", "피케", "폴로"], ("반팔티", 7, False, False, "면/쿨링원단")),
        (["민소매", "슬리브리스", "나시"], ("민소매", 8, False, False, "면/린넨")),
        (["린넨", "리넨"], ("린넨의류", 8, True, False, "린넨")),
        (["원피스"], ("원피스", 6, False, False, "폴리/코튼"))
    ]

    for keywords, (sub_type, temp_bracket, is_layered, is_waterproof, material) in keyword_rules:
        if any(kw in title_lower for kw in keywords):
            if any(w in title_lower for w in ["방수", "발수", "워터프루프", "고어텍스", "나일론"]):
                is_waterproof = True
            return {
                "sub_type": sub_type, "temp_bracket": temp_bracket,
                "is_layered": is_layered, "is_waterproof": is_waterproof, "material": material
            }

    default_bracket = 4 if main_category == "아우터" else 5
    return {"sub_type": main_category, "temp_bracket": default_bracket, "is_layered": False, "is_waterproof": False, "material": "혼방"}

class MusinsaRankingCrawler:
    def __init__(self):
        self.gender_codes = {"전체": "A", "남성": "M", "여성": "F"}
        self.category_codes = {"아우터": "002000", "상의": "001000", "하의": "003000"}

    def _build_url(self, gender_label: str, category_label: str) -> str:
        gf = self.gender_codes.get(gender_label, "A")
        cat_code = self.category_codes.get(category_label, "001000")
        return f"https://www.musinsa.com/main/musinsa/ranking?gf={gf}&sectionId=200&categoryCode={cat_code}"

    def _init_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def crawl_rankings(self, target_genders: list = None, items_per_cat: int = 6, save_path: str = "data/clothes_db.csv") -> pd.DataFrame:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        if target_genders is None:
            target_genders = ["전체", "남성", "여성"]
        all_items = []
        item_id_counter = 1

        try:
            driver = self._init_driver()
            for gender in target_genders:
                for category_name in self.category_codes.keys():
                    url = self._build_url(gender, category_name)
                    driver.get(url)
                    time.sleep(1.5)
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    product_links = soup.select("a[href*='/products/']")
                    seen_urls, rank = set(), 1

                    for link in product_links:
                        if rank > items_per_cat: break
                        href = link.get("href", "")
                        if not href or href in seen_urls: continue
                        card = link.find_parent("div")
                        if not card: continue
                        img_tag = card.find("img")
                        title_text = link.get("aria-label") or link.get_text(strip=True)
                        if not title_text and img_tag: title_text = img_tag.get("alt", "")
                        if not title_text or len(title_text) < 3: continue

                        seen_urls.add(href)
                        img_url = (img_tag.get("src") or img_tag.get("data-original")) if img_tag else ""
                        if img_url and img_url.startswith("//"): img_url = "https:" + img_url

                        labels = auto_label_from_title(title_text, category_name)
                        all_items.append({
                            "item_id": item_id_counter, "gender": gender, "rank": rank, "brand": "무신사 랭킹",
                            "name": title_text, "category": category_name, "sub_type": labels["sub_type"],
                            "material": labels["material"], "is_layered": labels["is_layered"],
                            "is_waterproof": labels["is_waterproof"], "temp_bracket": labels["temp_bracket"],
                            "image_url": img_url if img_url else f"https://placehold.co/300x360?text={gender}+Rank+{rank}",
                            "product_url": href if href.startswith("http") else f"https://www.musinsa.com{href}"
                        })
                        item_id_counter += 1
                        rank += 1
            driver.quit()
        except Exception:
            pass

        if len(all_items) == 0:
            all_items = [
                {"item_id": 1, "gender": "전체", "rank": 1, "brand": "무신사", "name": "나일론 방수 바람막이", "category": "아우터", "sub_type": "바람막이", "material": "나일론", "is_layered": True, "is_waterproof": True, "temp_bracket": 4, "image_url": "https://placehold.co/300x360/2b5876/ffffff?text=Windbreaker", "product_url": "https://www.musinsa.com"},
                {"item_id": 2, "gender": "전체", "rank": 1, "brand": "무신사", "name": "오버핏 스웨트셔츠 맨투맨", "category": "상의", "sub_type": "맨투맨", "material": "면", "is_layered": False, "is_waterproof": False, "temp_bracket": 4, "image_url": "https://placehold.co/300x360/556270/ffffff?text=Sweatshirt", "product_url": "https://www.musinsa.com"},
                {"item_id": 3, "gender": "전체", "rank": 1, "brand": "무신사", "name": "와이드 히든 밴딩 슬랙스", "category": "하의", "sub_type": "슬랙스", "material": "폴리", "is_layered": False, "is_waterproof": False, "temp_bracket": 5, "image_url": "https://placehold.co/300x360/2c3e50/ffffff?text=Slacks", "product_url": "https://www.musinsa.com"},
                {"item_id": 4, "gender": "전체", "rank": 1, "brand": "헌터", "name": "오리지널 플레이 숏 레인부츠", "category": "악세서리", "sub_type": "레인부츠", "material": "고무", "is_layered": False, "is_waterproof": True, "temp_bracket": 0, "image_url": "https://placehold.co/300x360/27ae60/ffffff?text=RainBoots", "product_url": "https://www.musinsa.com"}
            ]

        df = pd.DataFrame(all_items)
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        return df