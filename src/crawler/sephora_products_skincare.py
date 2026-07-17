import pandas as pd

OUTPUT_PRODUCTS = "data/raw/sephora_products_skincare.csv"


def crawl_skincare_products():

    products = [
        {
            "product_id": "P511921",
            "product_name": "EADEM Le Chouchou Exfoliating Softening Peptide Lip Balm",
            "category": "skincare",
            "platform": "sephora",
            "price": None,
            "rating_avg": None,
            "total_reviews": 5000,
            "product_url": "https://www.sephora.com/product/eadem-le-chouchou-exfoliating-softening-peptide-lip-balm-P511921?skuId=2960730&icid2=products%20grid:p511921:product"
        },
        {
            "product_id": "P517552",
            "product_name": "Peptide Lip Tint",
            "category": "skincare",
            "platform": "sephora",
            "price": None,
            "rating_avg": None,
            "total_reviews": 5000,
            "product_url": "https://www.sephora.com/product/peptide-lip-tint-P517552?skuId=2895993&icid2=products%20grid:p517552:product"
        },
        {
            "product_id": "P507659",
            "product_name": "The Acne Set",
            "category": "skincare",
            "platform": "sephora",
            "price": None,
            "rating_avg": None,
            "total_reviews": 5000,
            "product_url": "https://www.sephora.com/product/the-acne-set-P507659?skuId=2698355&icid2=products%20grid:p507659:product"
        },
        {
            "product_id": "P515952",
            "product_name": "Bio-Collagen Real Deep Mask For Pore Minimizing Firming Care",
            "category": "skincare",
            "platform": "sephora",
            "price": None,
            "rating_avg": None,
            "total_reviews": 5000,
            "product_url": "https://www.sephora.com/product/bio-collagen-real-deep-mask-for-pore-minimizing-firming-care-P515952?skuId=2865186&icid2=products%20grid:p515952:product"
        },
        {
            "product_id": "P519160",
            "product_name": "Glazing Milk",
            "category": "skincare",
            "platform": "sephora",
            "price": None,
            "rating_avg": None,
            "total_reviews": 5000,
            "product_url": "https://www.sephora.com/product/glazing-milk-P519160?skuId=2898419&icid2=products%20grid:p519160:product"
        },
        {
            "product_id": "P518624",
            "product_name": "PHA 5 Exfoliating Lip Serum",
            "category": "skincare",
            "platform": "sephora",
            "price": None,
            "rating_avg": None,
            "total_reviews": 5000,
            "product_url": "https://www.sephora.com/product/pha-5-exfoliating-lip-serum-P518624?skuId=2913911&icid2=products%20grid:p518624:product"
        },
        {
            "product_id": "P517678",
            "product_name": "Day Dew Sunscreen SPF",
            "category": "skincare",
            "platform": "sephora",
            "price": None,
            "rating_avg": None,
            "total_reviews": 5000,
            "product_url": "https://www.sephora.com/product/day-dew-sunscreen-exclusive-50ml-P517678?skuId=2893485&icid2=products%20grid:p517678:product"
        }
    ]

    return products


if __name__ == "__main__":

    products = crawl_skincare_products()

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
        print("Total skincare products:", len(df))
        print(df.head(20))