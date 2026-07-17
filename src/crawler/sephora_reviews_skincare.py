import time
import requests
import pandas as pd
from tqdm import tqdm


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
}

INPUT_PRODUCTS = "data/raw/sephora_products_skincare.csv"
OUTPUT_REVIEWS = "data/raw/sephora_reviews_skincare.csv"

API_URL = "https://api.bazaarvoice.com/data/reviews.json"

PASS_KEY = "calXm2DyQVjcCy9agq85vmTJv5ELuuBCF2sdg4BnJzJus"

MAX_REVIEWS_PER_PRODUCT = 5000
LIMIT = 100


def crawl_reviews_by_product(product_id, product_name, max_reviews=5000):

    reviews = []
    offset = 0

    while len(reviews) < max_reviews:

        params = {
            "Filter": [
                "contentlocale:en*",
                f"ProductId:{product_id}"
            ],
            "Sort": "SubmissionTime:desc",
            "Limit": LIMIT,
            "Offset": offset,
            "Include": "Products,Comments",
            "Stats": "Reviews",
            "passkey": PASS_KEY,
            "apiversion": "5.4",
            "Locale": "en_US"
        }

        try:
            response = requests.get(
                API_URL,
                headers=HEADERS,
                params=params,
                timeout=20
            )

            if response.status_code != 200:
                print(f"Status error {response.status_code} product={product_id}")
                break

            data = response.json()

            items = data.get("Results", [])

            if not items:
                break

            for item in items:

                content = item.get("ReviewText")

                if content and str(content).strip() != "":

                    reviews.append({
                        "product_id": product_id,
                        "product_name": product_name,
                        "category": "skincare",
                        "platform": "sephora",
                        "rating": item.get("Rating"),
                        "comment": content,
                        "created_at": item.get("SubmissionTime")
                    })

                    if len(reviews) >= max_reviews:
                        break

            print(f"Product {product_id}: {len(reviews)} reviews")

            offset += LIMIT

            time.sleep(0.5)

        except Exception as e:
            print(f"Error product={product_id}, offset={offset}: {e}")
            break

    return reviews


if __name__ == "__main__":

    products_df = pd.read_csv(INPUT_PRODUCTS)

    products_df["total_reviews"] = (
        products_df["total_reviews"]
        .fillna(0)
        .astype(int)
    )

    products_df = products_df.sort_values(
        by="total_reviews",
        ascending=False
    )

    all_reviews = []

    for _, row in tqdm(
        products_df.iterrows(),
        total=len(products_df),
        desc="Crawling Sephora skincare reviews"
    ):

        product_id = row["product_id"]
        product_name = row["product_name"]

        reviews = crawl_reviews_by_product(
            product_id=product_id,
            product_name=product_name,
            max_reviews=MAX_REVIEWS_PER_PRODUCT
        )

        all_reviews.extend(reviews)

        print(f"Current total reviews: {len(all_reviews)}")

        time.sleep(1)

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
        print("Total Sephora skincare reviews:", len(reviews_df))

        print("\nReviews per product:")
        print(reviews_df["product_id"].value_counts())

        print(reviews_df.head(20))