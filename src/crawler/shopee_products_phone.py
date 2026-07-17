# pyright: reportArgumentType=false

import time
import requests
import pandas as pd
from tqdm import tqdm


HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://shopee.vn/",
}

OUTPUT_PRODUCTS = "data/raw/shopee_products_phone.csv"


def crawl_phone_products(max_pages=10):

    products = []

    for page in tqdm(
        range(max_pages),
        desc="Crawling Shopee phones"
    ):

        url = "https://shopee.vn/api/v4/search/search_items"

        params = {
            "by": "pop",
            "limit": 60,
            "match_id": 11036031,
            "newest": page * 60,
            "order": "desc",
            "page_type": "search",
            "scenario": "PAGE_CATEGORY",
            "version": 2,
        }

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=15
            )

            print("STATUS:", response.status_code)

            if response.status_code != 200:
                print(response.text[:300])
                continue

            data = response.json()
            items = data.get("items", [])

            if not items:
                print("Hết sản phẩm")
                break

            print(f"Page {page}: {len(items)} products")

            for row in items:

                item = row.get("item_basic", row)

                itemid = item.get("itemid")
                shopid = item.get("shopid")
                name = item.get("name")

                if not itemid or not shopid or not name:
                    continue

                price = item.get("price")

                if price:
                    price = price / 100000

                products.append({
                    "product_id": itemid,
                    "shop_id": shopid,
                    "product_name": name,
                    "category": "phone",
                    "platform": "shopee",
                    "price": price,
                    "rating_avg": (
                        item.get("item_rating", {})
                        .get("rating_star")
                    ),
                    "total_reviews": item.get("cmt_count"),
                    "product_url": (
                        f"https://shopee.vn/product/"
                        f"{shopid}/{itemid}"
                    )
                })

            time.sleep(1)

        except Exception as e:
            print("Error:", e)

    return products


if __name__ == "__main__":

    products = crawl_phone_products(max_pages=10)

    df = pd.DataFrame(products)

    if len(df) == 0:
        print("Không crawl được sản phẩm nào.")

    else:
        df = df.drop_duplicates(subset=["product_id"])
        df = df.reset_index(drop=True)

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
        print("Total Shopee phone products:", len(df))
        print(df.head(20))