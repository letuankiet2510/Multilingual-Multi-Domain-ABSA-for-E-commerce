import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/predict"

st.set_page_config(
    page_title="ABSA Ecommerce Demo",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Multi-domain Multi-language ABSA")
st.caption("Phân tích cảm xúc theo khía cạnh cho review thương mại điện tử")

review = st.text_area(
    "Nhập review sản phẩm:",
    value="Áo đẹp nhưng hơi chật",
    height=120
)

if st.button("Phân tích"):
    if not review.strip():
        st.warning("Vui lòng nhập review.")
    else:
        with st.spinner("Đang phân tích..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"text": review},
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()

                    st.success("Phân tích thành công!")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Domain", result.get("domain"))

                    with col2:
                        st.metric("Language", result.get("language"))

                    with col3:
                        st.metric("Sentiment", result.get("sentiment"))

                    st.subheader("Kết quả chi tiết")
                    st.json(result)

                else:
                    st.error(f"Lỗi API: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error("Không gọi được FastAPI. Kiểm tra server đã chạy chưa.")
                st.exception(e)