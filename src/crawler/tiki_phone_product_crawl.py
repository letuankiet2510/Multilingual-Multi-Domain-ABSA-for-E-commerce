import time
import requests
import pandas as pd
from tqdm import tqdm


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
}

OUTPUT_PRODUCTS = "data/raw/tiki_products_phone.csv"


def is_valid_phone_product(product_name):
    if not isinstance(product_name, str):
        return False

    name = product_name.lower()

    exclude_keywords = [
        "ốp", "ốp lưng", "bao da", "bao điện thoại",
        "túi", "túi chống nước",
        "cáp", "dây sạc", "củ sạc", "sạc",
        "tai nghe", "loa bluetooth",
        "kính cường lực", "miếng dán", "dán màn hình",
        "giá đỡ", "holder",
        "phụ kiện", "linh kiện",
        "sim", "thẻ nhớ",
        "pin dự phòng",
        "case", "adapter", "dock",
        "bút", "stylus",
        "tablet", "ipad", "máy tính bảng",
        "đồng hồ", "watch",
        "máy ảnh"
    ]

    include_keywords = [
        "điện thoại",
        "iphone",
        "samsung galaxy",
        "samsung",
        "xiaomi",
        "redmi",
        "oppo",
        "vivo",
        "realme",
        "nokia",
        "tecno",
        "itel",
        "infinix",
        "galaxy"
    ]

    if any(word in name for word in exclude_keywords):
        return False

    if any(word in name for word in include_keywords):
        return True

    return False


def crawl_products_by_keyword(keyword, max_pages=100):
    products = []

    for page in tqdm(range(1, max_pages + 1), desc=f"Crawling {keyword}"):

        url = "https://tiki.vn/api/v2/products"

        params = {
            "limit": 40,
            "page": page,
            "q": keyword
        }

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                print(f"Status error {response.status_code} at {keyword} page {page}")
                continue

            data = response.json()
            items = data.get("data", [])

            if not items:
                break

            for item in items:
                product_name = item.get("name", "")

                if not is_valid_phone_product(product_name):
                    continue

                products.append({
                    "product_id": item.get("id"),
                    "product_name": product_name,
                    "category": "phone",
                    "platform": "tiki",
                    "price": item.get("price"),
                    "rating_avg": item.get("rating_average"),
                    "total_reviews": item.get("review_count"),
                    "product_url": "https://tiki.vn/" + item.get("url_path", "")
                })

            time.sleep(0.7)

        except Exception as e:
            print(f"Error keyword={keyword}, page={page}: {e}")
            continue

    return products


if __name__ == "__main__":
    keywords = [
        

        "điện thoại chính hãng",
        "điện thoại smartphone"
    ]

    all_products = []

    for keyword in keywords:
        products = crawl_products_by_keyword(
            keyword=keyword,
            max_pages=100
        )
        all_products.extend(products)

    df = pd.DataFrame(all_products)

    if len(df) == 0:
        print("Không crawl được sản phẩm nào.")
    else:
        df = df.drop_duplicates(subset=["product_id"])
        df = df.reset_index(drop=True)

        df["total_reviews"] = df["total_reviews"].fillna(0).astype(int)

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
        print("Total phone products:", len(df))
        print(df.head(30))