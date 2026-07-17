import time
import requests
import pandas as pd
from tqdm import tqdm


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
}

INPUT_PRODUCTS = "data/raw/tiki_products_skincare11.csv"
OUTPUT_REVIEWS = "data/raw/tiki_reviews_skincare11.csv"


def crawl_reviews_by_product(product_id, product_name, max_pages=100):

    reviews = []

    for page in range(1, max_pages + 1):

        url = "https://tiki.vn/api/v2/reviews"

        params = {
            "limit": 20,
            "page": page,
            "product_id": product_id,
            "sort": "score|desc"
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
                break

            data = response.json()

            items = data.get("data", [])

            if not items:
                break

            for item in items:

                content = item.get("content")

                if content and str(content).strip() != "":

                    reviews.append({
                        "product_id": product_id,
                        "product_name": product_name,
                        "category": "skincare",
                        "platform": "tiki",
                        "rating": item.get("rating"),
                        "comment": content,
                        "created_at": item.get("created_at")
                    })

            time.sleep(0.5)

        except Exception as e:
            print(f"Error product={product_id}, page={page}: {e}")
            break

    return reviews


if __name__ == "__main__":

    products_df = pd.read_csv(INPUT_PRODUCTS)

    # ưu tiên sản phẩm nhiều review
    products_df["total_reviews"] = (
        products_df["total_reviews"]
        .fillna(0)
        .astype(int)
    )

    products_df = products_df.sort_values(
        by="total_reviews",
        ascending=False
    )

    # lấy top sản phẩm nhiều review nhất
    products_df = products_df.head(100)

    all_reviews = []

    for _, row in tqdm(
        products_df.iterrows(),
        total=len(products_df),
        desc="Crawling skincare reviews"
    ):

        product_id = row["product_id"]
        product_name = row["product_name"]

        reviews = crawl_reviews_by_product(
            product_id=product_id,
            product_name=product_name,
            max_pages=100
        )

        all_reviews.extend(reviews)

        print(f"Current reviews: {len(all_reviews)}")

        time.sleep(0.7)

    reviews_df = pd.DataFrame(all_reviews)

    if len(reviews_df) == 0:
        print("Không crawl được review nào.")

    else:

        reviews_df.drop_duplicates(
            subset=["product_id", "comment"],
            inplace=True
        )

        reviews_df.reset_index(drop=True, inplace=True)

        reviews_df.to_csv(
            OUTPUT_REVIEWS,
            index=False,
            encoding="utf-8-sig"
        )

        print("\nDONE!")
        print("Total skincare reviews:", len(reviews_df))
        print(reviews_df.head(20))