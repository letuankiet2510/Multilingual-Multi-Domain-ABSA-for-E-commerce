%%writefile app.py

import streamlit as st
import torch
import torch.nn as nn
import joblib
import requests
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
from transformers import AutoTokenizer, AutoModel

MODEL_DIR = "/content/saved_models"

# =========================
# MODEL
# =========================

class MultiTaskABSA(nn.Module):
    def __init__(self, model_name="xlm-roberta-base"):
        super().__init__()

        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size

        self.aspect_classifier = nn.Linear(hidden_size, 12)
        self.sentiment_classifier = nn.Linear(hidden_size, 3)
        self.domain_classifier = nn.Linear(hidden_size, 3)
        self.language_classifier = nn.Linear(hidden_size, 2)

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        pooled_output = outputs.last_hidden_state[:, 0, :]

        return {
            "aspect": self.aspect_classifier(pooled_output),
            "sentiment": self.sentiment_classifier(pooled_output),
            "domain": self.domain_classifier(pooled_output),
            "language": self.language_classifier(pooled_output)
        }


@st.cache_resource
def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(f"{MODEL_DIR}/tokenizer")
    encoders = joblib.load(f"{MODEL_DIR}/encoders.pkl")

    model = MultiTaskABSA()

    model.load_state_dict(
        torch.load(
            f"{MODEL_DIR}/multitask_model.pt",
            map_location=device
        )
    )

    model.to(device)
    model.eval()

    return model, tokenizer, encoders, device


# =========================
# PREDICT
# =========================

def predict_batch(reviews_data, batch_size=16):
    model, tokenizer, encoders, device = load_model()

    key_map = {
        "aspect": "mt_aspect_encoder",
        "sentiment": "mt_sentiment_encoder",
        "domain": "mt_domain_encoder",
        "language": "mt_language_encoder"
    }

    results = []
    texts = [item["review"] for item in reviews_data]

    for start in range(0, len(texts), batch_size):
        batch_texts = texts[start:start + batch_size]
        batch_items = reviews_data[start:start + batch_size]

        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"]
            )

        for i in range(len(batch_texts)):
            item_result = {}

            for task, encoder_key in key_map.items():
                probs = torch.softmax(outputs[task], dim=1)[i]
                pred_id = torch.argmax(probs).cpu().item()
                confidence = probs[pred_id].cpu().item()
                label = encoders[encoder_key].inverse_transform([pred_id])[0]

                item_result[task] = label
                item_result[f"{task}_confidence"] = round(confidence, 4)

            item_result["review"] = batch_items[i]["review"]
            item_result["rating"] = batch_items[i]["rating"]
            item_result["source"] = "Tiki"

            results.append(item_result)

    return results


# =========================
# TIKI CRAWLER
# =========================

def get_tiki_product_id(url):
    match = re.search(r"-p(\d+)\.html", url)

    if match:
        return match.group(1)

    return None


def crawl_tiki_reviews(url, limit_pages=3):
    product_id = get_tiki_product_id(url)

    if product_id is None:
        return []

    reviews = []

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    for page in range(1, limit_pages + 1):
        api_url = "https://tiki.vn/api/v2/reviews"

        params = {
            "product_id": product_id,
            "page": page,
            "limit": 20,
            "include": "comments,contribute_info,attribute_vote_summary"
        }

        try:
            response = requests.get(
                api_url,
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                break

            data = response.json()
            items = data.get("data", [])

            if len(items) == 0:
                break

            for item in items:
                content = item.get("content", "")
                rating = item.get("rating", None)

                if content and content.strip() != "":
                    reviews.append({
                        "review": content.strip(),
                        "rating": rating
                    })

        except Exception as e:
            print("Tiki Error:", e)
            break

    return reviews


# =========================
# PURCHASE DECISION
# =========================

def build_purchase_decision(total_reviews, positive_count, negative_count, neutral_count):
    positive_rate = positive_count / total_reviews * 100 if total_reviews > 0 else 0
    negative_rate = negative_count / total_reviews * 100 if total_reviews > 0 else 0
    neutral_rate = neutral_count / total_reviews * 100 if total_reviews > 0 else 0

    recommend_score = (
        positive_rate * 1.0
        + neutral_rate * 0.3
        - negative_rate * 0.7
    )

    recommend_score = max(0, min(100, recommend_score))

    if positive_rate >= 70 and negative_rate <= 15:
        decision = "NÊN MUA"
        decision_icon = "✅"
        decision_color = "#22C55E"
        decision_reason = "Sản phẩm có tỷ lệ đánh giá tích cực rất cao và số lượng phản hồi tiêu cực thấp."

    elif positive_rate >= 50 and negative_rate <= 30:
        decision = "CÂN NHẮC"
        decision_icon = "⚠️"
        decision_color = "#F59E0B"
        decision_reason = "Sản phẩm có nhiều đánh giá tích cực nhưng vẫn tồn tại một số phản hồi tiêu cực cần xem xét."

    else:
        decision = "KHÔNG NÊN MUA"
        decision_icon = "❌"
        decision_color = "#EF4444"
        decision_reason = "Tỷ lệ đánh giá tiêu cực khá cao hoặc mức độ hài lòng của khách hàng chưa ổn định."

    return {
        "positive_rate": positive_rate,
        "negative_rate": negative_rate,
        "neutral_rate": neutral_rate,
        "recommend_score": recommend_score,
        "decision": decision,
        "decision_icon": decision_icon,
        "decision_color": decision_color,
        "decision_reason": decision_reason
    }


# =========================
# SUMMARY INSIGHT
# =========================

def build_auto_summary(df_result, decision_info):
    sentiment_series = df_result["sentiment"].astype(str).str.lower()

    positive_df = df_result[sentiment_series == "positive"]
    negative_df = df_result[sentiment_series == "negative"]

    strengths = []
    weaknesses = []

    if len(positive_df) > 0:
        top_positive_aspects = positive_df["aspect"].value_counts().head(3).index.tolist()

        for asp in top_positive_aspects:
            strengths.append(f"Nhiều khách hàng đánh giá tích cực về khía cạnh **{asp}**.")

    if len(negative_df) > 0:
        top_negative_aspects = negative_df["aspect"].value_counts().head(3).index.tolist()

        for asp in top_negative_aspects:
            weaknesses.append(f"Một số khách hàng phản hồi chưa tốt về khía cạnh **{asp}**.")

    if len(strengths) == 0:
        strengths.append("Chưa có đủ review tích cực rõ ràng để xác định điểm mạnh nổi bật.")

    if len(weaknesses) == 0:
        weaknesses.append("Chưa ghi nhận vấn đề tiêu cực nổi bật từ nhóm review đã phân tích.")

    conclusion = (
        f"Hệ thống đưa ra khuyến nghị **{decision_info['decision']}** "
        f"với điểm khuyến nghị **{decision_info['recommend_score']:.1f}/100**."
    )

    return strengths, weaknesses, conclusion


# =========================
# UI
# =========================

st.set_page_config(
    page_title="Tiki Purchase Decision System",
    page_icon="🛒",
    layout="wide"
)

# =========================
# SESSION STATE
# =========================

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "df_result" not in st.session_state:
    st.session_state.df_result = None

if "decision_info" not in st.session_state:
    st.session_state.decision_info = None

if "total_reviews" not in st.session_state:
    st.session_state.total_reviews = 0

if "positive_count" not in st.session_state:
    st.session_state.positive_count = 0

if "negative_count" not in st.session_state:
    st.session_state.negative_count = 0

if "neutral_count" not in st.session_state:
    st.session_state.neutral_count = 0


st.markdown(
    """
    <style>
    .hero-box {
        padding: 34px;
        border-radius: 26px;
        background: linear-gradient(135deg, #0F172A 0%, #111827 45%, #1D4ED8 100%);
        border: 1px solid #334155;
        margin-bottom: 24px;
        box-shadow: 0 18px 40px rgba(0,0,0,0.35);
    }
    .hero-title {
        font-size: 44px;
        font-weight: 900;
        color: white;
        margin-bottom: 10px;
    }
    .hero-sub {
        font-size: 18px;
        color: #CBD5E1;
    }
    .metric-card {
        padding: 24px;
        border-radius: 22px;
        background: #111827;
        border: 1px solid #334155;
        text-align: center;
        box-shadow: 0 8px 22px rgba(0,0,0,0.22);
    }
    .metric-number {
        font-size: 38px;
        font-weight: 900;
        color: #60A5FA;
    }
    .metric-label {
        color: #D1D5DB;
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hero-box">
        <div class="hero-title">🛒 Tiki ABSA Purchase Decision System</div>
        <div class="hero-sub">
            Hệ thống phân tích review Tiki theo cảm xúc, khía cạnh và hỗ trợ quyết định mua hàng.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

with st.container(border=True):
    url = st.text_input(
        "🔗 Nhập link sản phẩm Tiki:",
        placeholder="Ví dụ: https://tiki.vn/...-p123456.html"
    )

    limit_pages = st.slider(
        "📄 Số trang review muốn lấy:",
        min_value=1,
        max_value=15,
        value=3
    )

    col_run, col_clear = st.columns([3, 1])

    with col_run:
        run_button = st.button(
            "🚀 Lấy review và phân tích",
            use_container_width=True
        )

    with col_clear:
        clear_button = st.button(
            "🧹 Xóa kết quả",
            use_container_width=True
        )

if clear_button:
    st.session_state.analysis_done = False
    st.session_state.df_result = None
    st.session_state.decision_info = None
    st.session_state.total_reviews = 0
    st.session_state.positive_count = 0
    st.session_state.negative_count = 0
    st.session_state.neutral_count = 0
    st.rerun()


# =========================
# RUN ANALYSIS
# =========================

if run_button:

    if url.strip() == "":
        st.warning("Vui lòng nhập link sản phẩm Tiki.")

    else:
        with st.spinner("Đang lấy review từ Tiki..."):
            reviews_data = crawl_tiki_reviews(
                url,
                limit_pages=limit_pages
            )

        if len(reviews_data) == 0:
            st.error("Không lấy được review từ Tiki.")

        else:
            st.success(f"Lấy được {len(reviews_data)} review.")

            with st.spinner("Đang phân tích bằng model..."):
                results = predict_batch(
                    reviews_data,
                    batch_size=16
                )

            df_result = pd.DataFrame(results)

            cols = [
                "source",
                "review",
                "rating",
                "aspect",
                "sentiment",
                "domain",
                "language",
                "aspect_confidence",
                "sentiment_confidence",
                "domain_confidence",
                "language_confidence"
            ]

            df_result = df_result[cols]

            total_reviews = len(df_result)
            sentiment_series = df_result["sentiment"].astype(str).str.lower()

            positive_count = (sentiment_series == "positive").sum()
            negative_count = (sentiment_series == "negative").sum()
            neutral_count = (sentiment_series == "neutral").sum()

            decision_info = build_purchase_decision(
                total_reviews,
                positive_count,
                negative_count,
                neutral_count
            )

            st.session_state.df_result = df_result
            st.session_state.decision_info = decision_info
            st.session_state.total_reviews = total_reviews
            st.session_state.positive_count = positive_count
            st.session_state.negative_count = negative_count
            st.session_state.neutral_count = neutral_count
            st.session_state.analysis_done = True


# =========================
# DISPLAY RESULTS
# =========================

if st.session_state.analysis_done:

    df_result = st.session_state.df_result
    decision_info = st.session_state.decision_info
    total_reviews = st.session_state.total_reviews
    positive_count = st.session_state.positive_count
    negative_count = st.session_state.negative_count
    neutral_count = st.session_state.neutral_count

    # =========================
    # DECISION BOX
    # =========================

    with st.container(border=True):
        st.markdown(
            f"<h1 style='color:{decision_info['decision_color']}; font-size:46px;'>{decision_info['decision_icon']} Kết luận: {decision_info['decision']}</h1>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"### Điểm khuyến nghị: **{decision_info['recommend_score']:.1f}/100**"
        )

        st.write(decision_info["decision_reason"])

        st.markdown(
            f"""
            **Positive:** {decision_info["positive_rate"]:.1f}% |
            **Negative:** {decision_info["negative_rate"]:.1f}% |
            **Neutral:** {decision_info["neutral_rate"]:.1f}%
            """
        )

    # =========================
    # METRICS
    # =========================

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        ("Tổng review", total_reviews),
        ("Positive", positive_count),
        ("Negative", negative_count),
        ("Neutral", neutral_count)
    ]

    for col, metric in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-number">{metric[1]}</div>
                    <div class="metric-label">{metric[0]}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    # =========================
    # CHARTS
    # =========================

    st.subheader("📊 Dashboard phân tích cảm xúc")

    chart_col1, chart_col2 = st.columns(2)

    sentiment_counts = (
        df_result["sentiment"]
        .astype(str)
        .str.lower()
        .value_counts()
        .reset_index()
    )

    sentiment_counts.columns = ["sentiment", "count"]

    with chart_col1:
        fig_pie = px.pie(
            sentiment_counts,
            names="sentiment",
            values="count",
            hole=0.45,
            title="Tỷ lệ Positive / Negative / Neutral"
        )

        fig_pie.update_traces(
            textposition="inside",
            textinfo="percent+label"
        )

        st.plotly_chart(
            fig_pie,
            use_container_width=True
        )

    with chart_col2:
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=decision_info["recommend_score"],
                title={"text": "Purchase Recommendation Score"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": decision_info["decision_color"]},
                    "steps": [
                        {"range": [0, 35], "color": "#7F1D1D"},
                        {"range": [35, 60], "color": "#78350F"},
                        {"range": [60, 100], "color": "#14532D"},
                    ],
                }
            )
        )

        fig_gauge.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=60, b=20)
        )

        st.plotly_chart(
            fig_gauge,
            use_container_width=True
        )

    # =========================
    # TOP NEGATIVE ISSUES
    # =========================

    st.subheader("🚨 Top vấn đề khách hàng phàn nàn")

    negative_df = df_result[
        df_result["sentiment"]
        .astype(str)
        .str.lower() == "negative"
    ]

    if len(negative_df) > 0:
        negative_issue_counts = (
            negative_df["aspect"]
            .value_counts()
            .reset_index()
        )

        negative_issue_counts.columns = ["aspect", "negative_count"]

        fig_negative = px.bar(
            negative_issue_counts.head(10),
            x="aspect",
            y="negative_count",
            title="Các khía cạnh bị đánh giá tiêu cực nhiều nhất",
            text="negative_count"
        )

        st.plotly_chart(
            fig_negative,
            use_container_width=True
        )
    else:
        st.info("Không phát hiện vấn đề tiêu cực nổi bật.")

    # =========================
    # ASPECT & DOMAIN
    # =========================

    col5, col6 = st.columns(2)

    with col5:
        st.subheader("📌 Phân bố Aspect")
        st.bar_chart(df_result["aspect"].value_counts())

    with col6:
        st.subheader("🌐 Phân bố Domain")
        st.bar_chart(df_result["domain"].value_counts())

    # =========================
    # AUTO SUMMARY
    # =========================

    strengths, weaknesses, conclusion = build_auto_summary(
        df_result,
        decision_info
    )

    with st.container(border=True):
        st.subheader("📝 Tóm tắt tự động sản phẩm")

        col_strength, col_weakness = st.columns(2)

        with col_strength:
            st.markdown("### ✅ Điểm mạnh")
            for item in strengths:
                st.markdown(f"- {item}")

        with col_weakness:
            st.markdown("### ⚠️ Điểm cần cân nhắc")
            for item in weaknesses:
                st.markdown(f"- {item}")

        st.markdown("### 🎯 Kết luận hệ thống")
        st.markdown(conclusion)

    # =========================
    # FILTER TABLE
    # =========================

    st.subheader("🔎 Bộ lọc kết quả phân tích")

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        sentiment_options = ["Tất cả"] + sorted(df_result["sentiment"].astype(str).unique().tolist())
        selected_sentiment = st.selectbox("Lọc theo sentiment", sentiment_options)

    with filter_col2:
        aspect_options = ["Tất cả"] + sorted(df_result["aspect"].astype(str).unique().tolist())
        selected_aspect = st.selectbox("Lọc theo aspect", aspect_options)

    with filter_col3:
        rating_options = ["Tất cả"] + sorted(df_result["rating"].dropna().astype(str).unique().tolist())
        selected_rating = st.selectbox("Lọc theo rating", rating_options)

    filtered_df = df_result.copy()

    if selected_sentiment != "Tất cả":
        filtered_df = filtered_df[
            filtered_df["sentiment"].astype(str) == selected_sentiment
        ]

    if selected_aspect != "Tất cả":
        filtered_df = filtered_df[
            filtered_df["aspect"].astype(str) == selected_aspect
        ]

    if selected_rating != "Tất cả":
        filtered_df = filtered_df[
            filtered_df["rating"].astype(str) == selected_rating
        ]

    st.subheader("📋 Kết quả phân tích chi tiết")

    st.dataframe(
        filtered_df,
        use_container_width=True
    )

    # =========================
    # NEGATIVE REVIEW DETAIL
    # =========================

    st.subheader("⚠️ Review tiêu cực chi tiết")

    if len(negative_df) == 0:
        st.info("Không có review negative.")
    else:
        st.dataframe(
            negative_df,
            use_container_width=True
        )

    csv = df_result.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "⬇️ Tải toàn bộ kết quả CSV",
        data=csv,
        file_name="tiki_purchase_decision.csv",
        mime="text/csv",
        use_container_width=True
    )
