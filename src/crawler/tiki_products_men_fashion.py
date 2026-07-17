import time
import requests
import pandas as pd
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
}

OUTPUT_PRODUCTS = "data/raw/tiki_products_men_fashion.csv"


def crawl_men_fashion_products(max_pages=100):

    products = []

    for page in tqdm(range(1, max_pages + 1), desc="Crawling men fashion"):

        url = "https://tiki.vn/api/personalish/v1/blocks/listings"

        params = {
            "limit": 40,
            "page": page,

            # category thời trang nam
            "category": 915
        }

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                print(f"Status error {response.status_code}")
                continue

            data = response.json()

            items = data.get("data", [])

            if not items:
                print("Hết dữ liệu")
                break

            print(f"Page {page}: {len(items)} products")

            for item in items:

                products.append({
                    "product_id": item.get("id"),
                    "product_name": item.get("name"),
                    "category": "men_fashion",
                    "platform": "tiki",
                    "price": item.get("price"),
                    "rating_avg": item.get("rating_average"),
                    "total_reviews": item.get("review_count"),
                    "product_url": "https://tiki.vn/" + item.get("url_path", "")
                })

            time.sleep(0.7)

        except Exception as e:
            print("Error:", e)

    return products


if __name__ == "__main__":

    products = crawl_men_fashion_products(max_pages=100)

    df = pd.DataFrame(products)

    if len(df) == 0:
        print("Không crawl được sản phẩm nào.")
    else:

        df = df.drop_duplicates(subset=["product_id"])

        df["total_reviews"] = (
            df["total_reviews"]
            .fillna(0)
            .astype(int)
        )

        df = df.sort_values(
            by="total_reviews",
            ascending=False
        )

        df.to_csv(
            OUTPUT_PRODUCTS,
            index=False,
            encoding="utf-8-sig"
        )

        print("\nDONE!")
        print("Total men fashion products:", len(df))
        print(df.head(20))