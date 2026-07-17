import time
import requests
import pandas as pd
from tqdm import tqdm


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
}

INPUT_PRODUCTS = "data/raw/tiki_products_phone1.csv"
OUTPUT_REVIEWS = "data/raw/tiki_raw_reviews_phone1.csv"

TARGET_REVIEWS = 1000


def crawl_reviews(product, limit_pages=10):
    reviews_data = []

    for page in range(1, limit_pages + 1):
        url = "https://tiki.vn/api/v2/reviews"

        params = {
            "product_id": int(product["product_id"]),
            "limit": 20,
            "page": page,
            "include": "comments"
        }

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=5
            )

            if response.status_code != 200:
                print(f"Status {response.status_code} - skip product {product['product_id']}")
                break

            try:
                data = response.json()
            except Exception:
                print(f"Not JSON - skip product {product['product_id']}")
                break

            reviews = data.get("data", [])

            if not reviews:
                break

            for review in reviews:
                content = review.get("content", "")

                if not content:
                    continue

                if len(content.strip()) < 5:
                    continue

                reviews_data.append({
                    "review_id": review.get("id"),
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "category": product["category"],
                    "platform": product["platform"],
                    "rating": review.get("rating"),
                    "review_text": content,
                    "review_date": review.get("created_at")
                })

            time.sleep(0.3)

        except Exception as e:
            print(f"Error product {product['product_id']}: {e}")
            break

    return reviews_data


if __name__ == "__main__":
    products_df = pd.read_csv(INPUT_PRODUCTS)

    print("Total products:", len(products_df))

    products_df = products_df.reset_index(drop=True)

    all_reviews = []

    for _, product in tqdm(
        products_df.iterrows(),
        total=len(products_df),
        desc="Crawling reviews"
    ):
        if len(all_reviews) >= TARGET_REVIEWS:
            break

        print(f"\nCrawling: {product['product_name']}")

        try:
            reviews = crawl_reviews(
                product,
                limit_pages=10
            )

            all_reviews.extend(reviews)

            print(f"Collected {len(reviews)} reviews")
            print(f"Total collected: {len(all_reviews)}")

        except Exception as e:
            print(f"Skip because {e}")
            continue

    df_reviews = pd.DataFrame(all_reviews)

    if len(df_reviews) > 0:
        df_reviews = df_reviews.drop_duplicates(
            subset=["review_text"]
        )

        df_reviews = df_reviews.head(TARGET_REVIEWS)
        df_reviews = df_reviews.reset_index(drop=True)

    df_reviews.to_csv(
        OUTPUT_REVIEWS,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nDONE!")
    print("Total reviews:", len(df_reviews))
    print(df_reviews.head())