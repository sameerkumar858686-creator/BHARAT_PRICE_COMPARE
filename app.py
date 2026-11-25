
import streamlit as st
import os
import re
import serpapi

from urllib.parse import urlparse, unquote
from datetime import datetime
from dotenv import load_dotenv

# =====================================================
# BHARAT PRICE COMPARE
# LIVE PRODUCT SEARCH - SERPAPI GOOGLE SHOPPING
# =====================================================

st.set_page_config(
    page_title="Bharat Price Compare",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# =====================================================
# API CONFIGURATION
# =====================================================

try:
    SERPAPI_API_KEY = st.secrets.get("SERPAPI_API_KEY", "")
except Exception:
    SERPAPI_API_KEY = ""

SERPAPI_API_KEY = (
    SERPAPI_API_KEY or os.getenv("SERPAPI_API_KEY", "")
).strip()

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
.stApp {
    background: #080F1C;
    color: white;
}
[data-testid="stSidebar"] {
    background: #101B2D;
    border-right: 1px solid #24334B;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}
h1, h2, h3 {
    color: white !important;
}
p, label {
    color: #B9C5D8;
}
.hero {
    background: linear-gradient(120deg, #142B45, #102039, #123B45);
    padding: 35px;
    border-radius: 20px;
    border: 1px solid #25445A;
    margin-bottom: 25px;
}
.hero-tag {
    color: #38D6BD;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 3px;
}
.hero-title {
    font-size: 40px;
    font-weight: 850;
    margin-top: 12px;
    line-height: 1.2;
    color: white;
}
.highlight {
    color: #39D9C0;
}
.feature-card {
    background: #111E30;
    border: 1px solid #243650;
    border-radius: 15px;
    padding: 20px;
    min-height: 140px;
    margin-bottom: 12px;
}
.feature-title {
    color: white;
    font-size: 17px;
    font-weight: 750;
    margin-top: 10px;
}
.feature-description {
    color: #A9B7C9;
    font-size: 13px;
    margin-top: 7px;
    line-height: 1.5;
}
.platform-card {
    background: #111E30;
    border: 1px solid #263A55;
    padding: 15px 10px;
    border-radius: 12px;
    text-align: center;
    color: white;
    font-weight: 700;
    margin-bottom: 10px;
}
.platform-status {
    font-size: 11px;
    color: #39D9C0;
    margin-top: 5px;
}
div.stButton > button {
    background: linear-gradient(90deg, #12BFA8, #23D6BB);
    color: #07131F;
    border: none;
    border-radius: 10px;
    font-weight: 800;
    min-height: 42px;
}
div.stButton > button:hover {
    background: #36E2CA;
    color: #07131F;
}
div[data-testid="stTextInput"] input {
    background: #142239;
    color: white;
    border: 1px solid #31445F;
    border-radius: 10px;
}
.deal-card {
    background: #111E30;
    border: 1px solid #263A55;
    padding: 15px;
    border-radius: 14px;
    margin-bottom: 10px;
}
.footer {
    border-top: 1px solid #243650;
    padding-top: 20px;
    margin-top: 50px;
    text-align: center;
    color: #8798AF;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================

if "product_url" not in st.session_state:
    st.session_state.product_url = ""

if "search_history" not in st.session_state:
    st.session_state.search_history = []

if "live_results" not in st.session_state:
    st.session_state.live_results = []

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# =====================================================
# SUPPORTED PLATFORMS
# =====================================================

PLATFORMS = {
    "flipkart.com": "Flipkart",
    "amazon.in": "Amazon India",
    "croma.com": "Croma",
    "reliancedigital.in": "Reliance Digital",
    "vijaysales.com": "Vijay Sales",
    "tatacliq.com": "Tata CLiQ"
}

# =====================================================
# URL ANALYZER
# =====================================================

def analyze_product_url(url):
    url = url.strip()

    if not url:
        return None, "Please enter a product URL."

    if not url.startswith(("https://", "http://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        domain = (parsed.hostname or "").lower()

        if domain.startswith("www."):
            domain = domain[4:]

        platform = None

        for website, name in PLATFORMS.items():
            if domain == website or domain.endswith("." + website):
                platform = name
                break

        if not platform:
            return None, "This shopping platform is not supported yet."

        return {
            "url": url,
            "platform": platform,
            "domain": domain
        }, None

    except Exception:
        return None, "Invalid product URL."

# =====================================================
# EXTRACT SEARCH QUERY FROM PRODUCT URL
# =====================================================

def product_query_from_url(url):
    parsed = urlparse(url)
    path = unquote(parsed.path)

    # Amazon product links often contain /product-name/dp/ASIN
    if "/dp/" in path:
        path = path.split("/dp/")[0]

    # Remove common shopping URL noise
    path = path.replace("-", " ").replace("_", " ").replace("/", " ")
    path = re.sub(r"\s+", " ", path)
    path = re.sub(r"\b(dp|gp|product|products|item)\b", " ", path)
    path = re.sub(r"\s+", " ", path).strip()

    return path[:150]

# =====================================================
# PRICE PARSER
# =====================================================

def parse_price(price_text):
    if price_text is None:
        return None

    if isinstance(price_text, (int, float)):
        return float(price_text)

    text = str(price_text)
    text = text.replace(",", "")
    text = re.sub(r"[^\d.]", "", text)

    try:
        return float(text)
    except (ValueError, TypeError):
        return None

# =====================================================
# LIVE SERPAPI GOOGLE SHOPPING SEARCH
# =====================================================

def search_live_products(query):
    if not SERPAPI_API_KEY:
        return None, "SerpApi API key is missing. Add it in Streamlit Secrets."

    try:
        client = serpapi.Client(
            api_key=SERPAPI_API_KEY,
            timeout=25
        )

        response = client.search(
            engine="google_shopping",
            q=query,
            gl="in",
            hl="en",
            location="India"
        )

        if response.get("error"):
            return None, response.get("error")

        raw_results = response.get("shopping_results", [])
        products = []

        for item in raw_results:
            price_text = item.get("price", "")
            price_value = item.get("extracted_price")

            if price_value is None:
                price_value = parse_price(price_text)

            products.append({
                "title": item.get("title", "Product"),
                "price_text": price_text,
                "price": price_value,
                "source": item.get("source", "Unknown Seller"),
                "link": item.get("link", ""),
                "thumbnail": item.get("thumbnail", ""),
                "rating": item.get("rating"),
                "reviews": item.get("reviews"),
                "delivery": item.get("delivery", "")
            })

        products.sort(
            key=lambda x: x["price"] if x["price"] is not None else float("inf")
        )

        return products, None

    except Exception as e:
        return None, str(e)

# =====================================================
# DISPLAY LIVE PRODUCT RESULTS
# =====================================================

def show_live_results(products, query):
    st.markdown("---")
    st.subheader("🛍️ Live Shopping Results")
    st.caption(f"Search results for: {query}")

    priced_products = [
        p for p in products
        if p["price"] is not None
    ]

    if not products:
        st.warning("No shopping results found for this search.")
        return

    if priced_products:
        lowest = priced_products[0]
        highest = priced_products[-1]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "🏆 Lowest Found Price",
            f"₹{lowest['price']:,.0f}",
            lowest["source"]
        )

        col2.metric(
            "Highest Found Price",
            f"₹{highest['price']:,.0f}"
        )

        if len(priced_products) > 1:
            savings = highest["price"] - lowest["price"]
        else:
            savings = 0

        col3.metric(
            "Potential Difference",
            f"₹{savings:,.0f}"
        )

        st.success(
            f"🏆 Lowest listed price: ₹{lowest['price']:,.0f} "
            f"at {lowest['source']}"
        )

    st.markdown("### 📊 Price Comparison")

    for index, product in enumerate(products):
        is_lowest = (
            priced_products
            and product["price"] is not None
            and product["price"] == priced_products[0]["price"]
        )

        with st.container(border=True):
            col_img, col_info = st.columns([1, 3])

            with col_img:
                if product["thumbnail"]:
                    st.image(product["thumbnail"], use_container_width=True)
                else:
                    st.write("🛍️")

            with col_info:
                if is_lowest:
                    st.markdown("### 🏆 BEST PRICE FOUND")

                st.markdown(f"**{product['title']}**")
                st.write(f"**Seller:** {product['source']}")

                if product["price"] is not None:
                    st.markdown(
                        f"## ₹{product['price']:,.0f}"
                    )
                elif product["price_text"]:
                    st.markdown(f"**Price:** {product['price_text']}")
                else:
                    st.warning("Price not available")

                if product["rating"]:
                    st.write(f"⭐ Rating: {product['rating']}")

                if product["reviews"]:
                    st.write(f"📝 Reviews: {product['reviews']}")

                if product["delivery"]:
                    st.caption(product["delivery"])

                if product["link"]:
                    st.link_button(
                        "🛒 VIEW DEAL",
                        product["link"],
                        use_container_width=True
                    )

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.markdown("## 🛒 BharatCompare")
    st.caption("INDIA'S PRODUCT PRICE INTELLIGENCE")
    st.divider()

    menu = st.radio(
        "MAIN MENU",
        [
            "🏠 Home",
            "🔍 Compare Products",
            "🔥 Best Deals",
            "📊 Price History",
            "❤️ Wishlist",
            "ℹ️ About"
        ]
    )

    st.divider()
    st.markdown("### 🌐 Supported Platforms")

    for name in PLATFORMS.values():
        st.write("🟢", name)

    st.divider()
    st.caption("Version 1.1.0 | Live Search Build")

# =====================================================
# HOME PAGE
# =====================================================

if menu == "🏠 Home":

    st.markdown("""
    <div class="hero">
        <div class="hero-tag">SMART SHOPPING FOR EVERY INDIAN</div>
        <div class="hero-title">
            Don't Pay More.<br>
            <span class="highlight">Find The Best Deal.</span>
        </div>
        <p>
            Compare products, prices and shopping offers.
            Make smarter shopping decisions.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🔍 Compare Any Product")

    with st.form("home_search_form"):
        home_query = st.text_input(
            "Product Name",
            placeholder="Example: Samsung Galaxy S25 256GB"
        )

        home_search = st.form_submit_button(
            "🔎 SEARCH LIVE PRICES",
            use_container_width=True
        )

    if home_search:
        if not home_query.strip():
            st.warning("Please enter a product name.")
        else:
            with st.spinner("Searching live shopping results..."):
                results, error = search_live_products(home_query)

            if error:
                st.error("Search failed.")
                st.caption(error)
            else:
                st.session_state.live_results = results
                st.session_state.last_query = home_query

                st.session_state.search_history.append({
                    "query": home_query,
                    "time": datetime.now().strftime("%d-%m-%Y %H:%M")
                })

    if st.session_state.live_results:
        show_live_results(
            st.session_state.live_results,
            st.session_state.last_query
        )

    st.markdown("---")
    st.markdown("## ⚡ Powerful Features")

    feature_data = [
        ("💰", "Price Comparison", "Compare live shopping listings and prices."),
        ("🎟️", "Offers & Coupons", "Discover deals when available in search results."),
        ("🤖", "Product Matching", "Find products using shopping search results."),
        ("📉", "Price History", "Historical tracking will be added in a future update."),
        ("🎁", "Combo Offers", "Explore promotions when available."),
        ("🔔", "Price Alerts", "Price alert system is planned for a future update.")
    ]

    cols = st.columns(3)

    for i, feature in enumerate(feature_data):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="feature-card">
                <div>{feature[0]}</div>
                <div class="feature-title">{feature[1]}</div>
                <div class="feature-description">{feature[2]}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("## 🛍️ Shopping Platforms")

    platform_cols = st.columns(3)

    for index, name in enumerate(PLATFORMS.values()):
        with platform_cols[index % 3]:
            st.markdown(f"""
            <div class="platform-card">
                🛒 {name}
                <div class="platform-status">
                    Search availability depends on live results
                </div>
            </div>
            """, unsafe_allow_html=True)

# =====================================================
# COMPARE PRODUCTS PAGE
# =====================================================

elif menu == "🔍 Compare Products":

    st.title("🔍 Compare Products")
    st.write("Search a product name or analyze a supported shopping URL.")

    search_type = st.radio(
        "Choose Search Method",
        ["Product Name", "Shopping URL"],
        horizontal=True
    )

    if search_type == "Product Name":
        st.markdown("### 🔎 Search Product")

        with st.form("live_product_search"):
            product_name = st.text_input(
                "Product Name",
                placeholder="Example: iPhone 16 128GB"
            )

            search_button = st.form_submit_button(
                "🔍 SEARCH LIVE PRODUCTS",
                use_container_width=True
            )

        if search_button:
            if not product_name.strip():
                st.warning("Please enter a product name.")
            else:
                with st.spinner("Searching Google Shopping..."):
                    results, error = search_live_products(product_name)

                if error:
                    st.error("Live search could not be completed.")
                    st.caption(error)
                else:
                    st.session_state.live_results = results
                    st.session_state.last_query = product_name

                    st.session_state.search_history.append({
                        "query": product_name,
                        "time": datetime.now().strftime("%d-%m-%Y %H:%M")
                    })

                    if results:
                        st.success(f"{len(results)} shopping results found!")
                    else:
                        st.warning("No products found.")

        if st.session_state.live_results:
            show_live_results(
                st.session_state.live_results,
                st.session_state.last_query
            )

    else:
        st.markdown("### 🔗 Analyze Shopping URL")

        compare_url = st.text_input(
            "Enter Product URL",
            value=st.session_state.product_url,
            placeholder="https://www.amazon.in/..."
        )

        if st.button("ANALYZE PRODUCT URL", use_container_width=True):
            product, error = analyze_product_url(compare_url)

            if error:
                st.error(error)
            else:
                st.session_state.product_url = product["url"]

                st.success(f"Valid {product['platform']} product URL.")

                extracted_query = product_query_from_url(product["url"])

                st.write("### Extracted Product Search")
                st.write(extracted_query)

                if extracted_query:
                    with st.spinner("Searching for this product..."):
                        results, search_error = search_live_products(extracted_query)

                    if search_error:
                        st.error("Could not fetch shopping results.")
                        st.caption(search_error)
                    else:
                        st.session_state.live_results = results
                        st.session_state.last_query = extracted_query

                        if results:
                            show_live_results(results, extracted_query)
                        else:
                            st.warning("No matching shopping results found.")

                st.code(product["url"])

# =====================================================
# BEST DEALS
# =====================================================

elif menu == "🔥 Best Deals":

    st.title("🔥 Best Deals")

    if st.session_state.live_results:
        st.write("Deals from your most recent search:")

        priced = [
            p for p in st.session_state.live_results
            if p["price"] is not None
        ]

        priced.sort(key=lambda p: p["price"])

        if priced:
            for p in priced[:10]:
                st.markdown(f"""
                **{p['title']}**  
                Seller: {p['source']}  
                Price: ₹{p['price']:,.0f}
                """)
                if p["link"]:
                    st.link_button("VIEW DEAL", p["link"])
                st.divider()
        else:
            st.info("No priced products available yet.")
    else:
        st.info("Search a product first to see deals here.")

# =====================================================
# PRICE HISTORY
# =====================================================

elif menu == "📊 Price History":

    st.title("📊 Price History")
    st.info(
        "Historical prices will be available after a price database "
        "and scheduled price tracking are implemented."
    )

# =====================================================
# WISHLIST
# =====================================================

elif menu == "❤️ Wishlist":

    st.title("❤️ My Wishlist")
    st.info("Wishlist database and user accounts are planned for a future update.")

# =====================================================
# ABOUT
# =====================================================

elif menu == "ℹ️ About":

    st.title("ℹ️ About Bharat Price Compare")

    st.markdown("""
    ### Smart Shopping. Better Savings.

    Bharat Price Compare helps users search shopping listings
    and compare prices from available online merchants.

    Our goals:

    - Find products online.
    - Compare listed prices.
    - Discover sellers.
    - Find lower-priced options.
    - Make smarter shopping decisions.

    **Our Mission:** Help every Indian customer shop smarter.
    """)

# =====================================================
# SEARCH HISTORY
# =====================================================

if st.session_state.search_history:
    with st.expander("🕘 Recent Searches"):
        for item in reversed(st.session_state.search_history[-10:]):
            st.write(item)

# =====================================================
# FOOTER
# =====================================================

st.markdown("""
<div class="footer">
<b>Bharat Price Compare</b><br>
Smart Shopping. Better Savings.<br><br>
Made for India 🇮🇳<br><br>
© 2026 Bharat Price Compare. All Rights Reserved.
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    "<h3 style='text-align:center;'>Affiliate Disclosure</h3>",
    unsafe_allow_html=True
)
st.caption(
    "Shopping links may lead to retailer websites. "
    "Price and availability can change; verify details on the retailer page."
)
st.markdown("---")
