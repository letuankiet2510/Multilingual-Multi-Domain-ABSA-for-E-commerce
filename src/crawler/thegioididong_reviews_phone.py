import time
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/json, text/plain, */*",
}

INPUT_PRODUCTS = "data/raw/thegioididong_products_phone.csv"
OUTPUT_REVIEWS = "data/raw/thegioididong_reviews_phone.csv"

TARGET_REVIEWS = 1000


def clean_text(text):
    if not isinstance(text, str):
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def crawl_reviews_by_product(product, max_pages=10):

    reviews = []

    product_id = product["product_id"]
    product_name = product["product_name"]
    product_url = product["product_url"]

    for page in range(1, max_pages + 1):

        url = "https://www.thegioididong.com/aj/Comment/LoadComment"

        params = {
            "objectid": int(product_id),
            "objecttype": 2,
            "pageindex": page
        }

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                print(f"Status error {response.status_code} product={product_id}")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            items = soup.select("li, .comment__item, .cmt_item, .par")

            if not items:
                break

            for item in items:
                text = clean_text(item.get_text(" ", strip=True))

                if len(text) < 15:
                    continue

                if "đã mua tại" not in text.lower() and "hài lòng" not in text.lower():
                    continue

                reviews.append({
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": "phone",
                    "platform": "thegioididong",
                    "rating": None,
                    "comment": text,
                    "created_at": None,
                    "product_url": product_url
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"Error product={product_id}, page={page}: {e}")
            break

    return reviews


if __name__ == "__main__":

    products_df = pd.read_csv(INPUT_PRODUCTS)

    products_df = products_df.dropna(subset=["product_id"])
    products_df["product_id"] = products_df["product_id"].astype(int)

    all_reviews = []

    for _, product in tqdm(
        products_df.iterrows(),
        total=len(products_df),
        desc="Crawling TGDD reviews"
    ):

        if len(all_reviews) >= TARGET_REVIEWS:
            break

        print(f"\nCrawling: {product['product_name']}")

        reviews = crawl_reviews_by_product(
            product=product,
            max_pages=10
        )

        all_reviews.extend(reviews)

        print(f"Collected {len(reviews)} reviews")
        print(f"Total collected: {len(all_reviews)}")

        time.sleep(0.7)

    reviews_df = pd.DataFrame(all_reviews)

    if len(reviews_df) == 0:
        print("Không crawl được review nào.")
    else:
        reviews_df.drop_duplicates(
            subset=["comment"],
            inplace=True
        )

        reviews_df = reviews_df.head(TARGET_REVIEWS)
        reviews_df.reset_index(drop=True, inplace=True)

        reviews_df.to_csv(
            OUTPUT_REVIEWS,
            index=False,
            encoding="utf-8-sig"
        )

        print("\nDONE!")
        print("Total reviews:", len(reviews_df))
        print(reviews_df.head(20))