
import streamlit as st
import os
import serpapi

from urllib.parse import urlparse, quote_plus
from datetime import datetime
from dotenv import load_dotenv

# =====================================================
# BHARAT PRICE COMPARE
# MAIN APPLICATION
# =====================================================

st.set_page_config(
    page_title="Bharat Price Compare",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)
# =====================================================
# SERPAPI CONFIGURATION
# =====================================================

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>

.stApp {
    background: #080F1C;
    color: #FFFFFF;
}

[data-testid="stHeader"] {
    background: transparent;
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
    color: #FFFFFF !important;
}

p, label {
    color: #B9C5D8;
}

.hero {
    background: linear-gradient(120deg, #142B45, #102039, #123B45);
    padding: 42px 35px;
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
    font-size: 43px;
    font-weight: 850;
    margin-top: 12px;
    line-height: 1.2;
    color: white;
}

.hero-description {
    color: #B8C9DC;
    font-size: 16px;
    margin-top: 12px;
    line-height: 1.7;
}

.highlight {
    color: #39D9C0;
}

.feature-card {
    background: #111E30;
    border: 1px solid #243650;
    border-radius: 15px;
    padding: 22px;
    min-height: 145px;
    margin-bottom: 12px;
}

.feature-icon {
    font-size: 27px;
}

.feature-title {
    color: #FFFFFF;
    font-size: 17px;
    font-weight: 750;
    margin-top: 12px;
}

.feature-description {
    color: #A9B7C9;
    font-size: 13px;
    margin-top: 7px;
    line-height: 1.5;
}

.section-heading {
    font-size: 24px;
    font-weight: 800;
    color: white;
    margin-top: 25px;
    margin-bottom: 15px;
}

.platform-card {
    background: #111E30;
    border: 1px solid #263A55;
    padding: 16px 10px;
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
    min-height: 45px;
    width: 100%;
}

div.stButton > button:hover {
    background: #36E2CA;
    color: #07131F;
    border: none;
}

div[data-testid="stTextInput"] input {
    background: #142239;
    color: white;
    border: 1px solid #31445F;
    border-radius: 10px;
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


# =====================================================
# SUPPORTED SHOPPING DOMAINS
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
# SHOPPING PLATFORM SEARCH LINKS
# =====================================================

def platform_search_url(platform, product_name):

    query = quote_plus(product_name)

    search_urls = {

        "Amazon India":
            f"https://www.amazon.in/s?k={query}",

        "Flipkart":
            f"https://www.flipkart.com/search?q={query}",

        "Croma":
            f"https://www.croma.com/search/?text={query}",

        "Reliance Digital":
            f"https://www.reliancedigital.in/search?q={query}",

        "Vijay Sales":
            f"https://www.vijaysales.com/search?query={query}",

        "Tata CLiQ":
            f"https://www.tatacliq.com/search/?searchCategory=all&text={query}",
    }

    return search_urls.get(platform, "")

# =====================================================
# DEMO PRODUCT DATABASE
# ALL PRICES ARE SAMPLE DATA, NOT LIVE PRICES
# =====================================================

DEMO_PRODUCTS = [
    {
        "name": "iPhone 16 128GB",
        "category": "Smartphone",
        "prices": {
            "Amazon India": 69999,
            "Flipkart": 67999,
            "Croma": 70499,
            "Reliance Digital": 69990,
            "Vijay Sales": 69500,
            "Tata CLiQ": 70999
        },
        "affiliate_links": {
            "Amazon India": "https://www.amazon.in/Boldfit-Corrector-Adjustable-Breathable-Straightener/dp/B0GHX848PP?aref=ZMc1TMLYti&content-id=amzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1%3Aamzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1&crid=2U1NOCLR3G3Z5&cv_ct_cx=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&keywords=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&pd_rd_i=B0GHX848PP&pd_rd_r=3a9cee39-ccbb-4851-b7ae-9ede563a00d1&pd_rd_w=OhF5q&pd_rd_wg=OAuyt&pf_rd_p=7b6188a8-103f-4f88-b43a-19aba06e30c1&pf_rd_r=933ZT0S3X42A18JZM2DQ&qid=1795525524&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sprefix=back%2Bbody%2Bpos%2Caps%2C747&sr=1-1-941ebe59-d25b-49d0-b214-12cc5b66c90f&th=1&linkCode=ll2&tag=bharatcompare-21&linkId=46af7374e35c2d4b7f93ec475558ce71&ref_=as_li_ss_tl",
            "Flipkart": "",
            "Croma": "",
            "Reliance Digital": "",
            "Vijay Sales": "",
            "Tata CLiQ": ""
        }
    },
    {
        "name": "Samsung Galaxy S25 256GB",
        "category": "Smartphone",
        "prices": {
            "Amazon India": 74999,
            "Flipkart": 72999,
            "Croma": 75999,
            "Reliance Digital": 74990,
            "Vijay Sales": 73999,
            "Tata CLiQ": 76999
        },
        "affiliate_links": {
            "Amazon India": "https://www.amazon.in/Boldfit-Corrector-Adjustable-Breathable-Straightener/dp/B0GHX848PP?aref=ZMc1TMLYti&content-id=amzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1%3Aamzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1&crid=2U1NOCLR3G3Z5&cv_ct_cx=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&keywords=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&pd_rd_i=B0GHX848PP&pd_rd_r=3a9cee39-ccbb-4851-b7ae-9ede563a00d1&pd_rd_w=OhF5q&pd_rd_wg=OAuyt&pf_rd_p=7b6188a8-103f-4f88-b43a-19aba06e30c1&pf_rd_r=933ZT0S3X42A18JZM2DQ&qid=1795525524&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sprefix=back%2Bbody%2Bpos%2Caps%2C747&sr=1-1-941ebe59-d25b-49d0-b214-12cc5b66c90f&th=1&linkCode=ll2&tag=bharatcompare-21&linkId=46af7374e35c2d4b7f93ec475558ce71&ref_=as_li_ss_tl",
            "Flipkart": "",
            "Croma": "",
            "Reliance Digital": "",
            "Vijay Sales": "",
            "Tata CLiQ": ""
        }
    },
    {
        "name": "Redmi Note 14 5G",
        "category": "Smartphone",
        "prices": {
            "Amazon India": 17999,
            "Flipkart": 17499,
            "Croma": 18299,
            "Reliance Digital": 18499,
            "Vijay Sales": 17990,
            "Tata CLiQ": 18999
        },
        "affiliate_links": {
            "Amazon India": "https://www.amazon.in/Boldfit-Corrector-Adjustable-Breathable-Straightener/dp/B0GHX848PP?aref=ZMc1TMLYti&content-id=amzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1%3Aamzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1&crid=2U1NOCLR3G3Z5&cv_ct_cx=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&keywords=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&pd_rd_i=B0GHX848PP&pd_rd_r=3a9cee39-ccbb-4851-b7ae-9ede563a00d1&pd_rd_w=OhF5q&pd_rd_wg=OAuyt&pf_rd_p=7b6188a8-103f-4f88-b43a-19aba06e30c1&pf_rd_r=933ZT0S3X42A18JZM2DQ&qid=1795525524&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sprefix=back%2Bbody%2Bpos%2Caps%2C747&sr=1-1-941ebe59-d25b-49d0-b214-12cc5b66c90f&th=1&linkCode=ll2&tag=bharatcompare-21&linkId=46af7374e35c2d4b7f93ec475558ce71&ref_=as_li_ss_tl",
            "Flipkart": "",
            "Croma": "",
            "Reliance Digital": "",
            "Vijay Sales": "",
            "Tata CLiQ": ""
        }
    },
    {
        "name": "HP 15s Laptop",
        "category": "Laptop",
        "prices": {
            "Amazon India": 42999,
            "Flipkart": 41999,
            "Croma": 43999,
            "Reliance Digital": 43499,
            "Vijay Sales": 42500,
            "Tata CLiQ": 44999
        },
        "affiliate_links": {
            "Amazon India": "https://www.amazon.in/Boldfit-Corrector-Adjustable-Breathable-Straightener/dp/B0GHX848PP?aref=ZMc1TMLYti&content-id=amzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1%3Aamzn1.sym.7b6188a8-103f-4f88-b43a-19aba06e30c1&crid=2U1NOCLR3G3Z5&cv_ct_cx=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&keywords=body%2Bback%2Bposture%2Bcorrecting%2Bbelt&pd_rd_i=B0GHX848PP&pd_rd_r=3a9cee39-ccbb-4851-b7ae-9ede563a00d1&pd_rd_w=OhF5q&pd_rd_wg=OAuyt&pf_rd_p=7b6188a8-103f-4f88-b43a-19aba06e30c1&pf_rd_r=933ZT0S3X42A18JZM2DQ&qid=1795525524&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sprefix=back%2Bbody%2Bpos%2Caps%2C747&sr=1-1-941ebe59-d25b-49d0-b214-12cc5b66c90f&th=1&linkCode=ll2&tag=bharatcompare-21&linkId=46af7374e35c2d4b7f93ec475558ce71&ref_=as_li_ss_tl",
            "Flipkart": "",
            "Croma": "",
            "Reliance Digital": "",
            "Vijay Sales": "",
            "Tata CLiQ": ""
        }
    }
]

# =====================================================
# DEMO PRODUCT SEARCH FUNCTION
# =====================================================

def search_demo_products(query):

    query = query.strip().lower()

    if not query:
        return []

    results = []

    for product in DEMO_PRODUCTS:

        product_name = product["name"].lower()
        category = product["category"].lower()

        if query in product_name or query in category:
            results.append(product)

    return results


# =====================================================
# DEMO PRICE COMPARISON FUNCTION
# =====================================================

def show_demo_comparison(product):

    st.markdown("---")

    st.subheader("📦 " + product["name"])

    st.caption("Category: " + product["category"])

    st.warning(
        "⚠️ DEMO DATA — NOT LIVE PRICE. "
        "These sample prices are only for testing the application."
    )

    prices = product["prices"]

    lowest_platform = min(prices, key=prices.get)
    highest_platform = max(prices, key=prices.get)

    lowest_price = prices[lowest_platform]
    highest_price = prices[highest_platform]

    savings = highest_price - lowest_price

    # PRICE SUMMARY

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🏆 Lowest Demo Price",
            f"₹{lowest_price:,}",
            lowest_platform
        )

    with col2:
        st.metric(
            "Highest Demo Price",
            f"₹{highest_price:,}",
            highest_platform
        )

    with col3:
        st.metric(
            "Potential Demo Savings",
            f"₹{savings:,}"
        )

    st.markdown("### 🛒 Compare Shopping Platforms")

    sorted_prices = sorted(
        prices.items(),
        key=lambda item: item[1]
    )

    for platform, price in sorted_prices:

        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.write("**" + platform + "**")

        with col2:
            st.write(f"₹{price:,}")

        with col3:
            affiliate_link = product.get("affiliate_links", {}).get(platform, "")

            if affiliate_link:
                st.link_button(
                    "🛒 BUY NOW",
                    affiliate_link,
                    use_container_width=True
                )

            elif platform == lowest_platform:
                st.success("🏆 Lowest Demo Price")

            else:
                st.info("Demo Price")

    st.caption(
        "Sample prices are illustrative only. "
        "No retailer API or live price has been connected."
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

    st.caption("Version 1.0.0 | Development Build")


# =====================================================
# HOME PAGE
# =====================================================

if menu == "🏠 Home":

    st.markdown("""
<div class="hero">
<div class="hero-tag">
SMART SHOPPING FOR EVERY INDIAN
</div>

<div class="hero-title">
Don't Pay More.<br>
<span class="highlight">Find The Best Deal.</span>
</div>

<div class="hero-description">
Compare product prices, discounts and offers
from multiple Indian shopping platforms.
Make smarter shopping decisions.
</div>
</div>
""", unsafe_allow_html=True)
    # PRODUCT SEARCH

    st.markdown(
        '<div class="section-heading">🔍 Compare Any Product</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Paste your Amazon, Flipkart or other supported product link below."
    )

    with st.form("product_search_form"):

        product_url = st.text_input(
            "Product URL",
            placeholder="https://www.flipkart.com/product-link",
            label_visibility="collapsed"
        )

        submit = st.form_submit_button(
            "🔎 ANALYZE PRODUCT LINK",
            use_container_width=True
        )

    if submit:

        product, error = analyze_product_url(product_url)

        if error:

            st.error(error)

        else:

            st.session_state.product_url = product["url"]

            st.session_state.search_history.append({
                "platform": product["platform"],
                "url": product["url"],
                "time": datetime.now().strftime("%d-%m-%Y %H:%M")
            })

            st.success(
                f"Product link recognized! Platform: {product['platform']}"
            )

            st.info(
                "URL analysis is working. Live product extraction and "
                "retailer price integrations are the next development steps. "
                "No live price has been fetched yet."
            )

            st.code(product["url"])

    st.markdown("---")

    # FEATURES

    st.markdown(
        '<div class="section-heading">⚡ Powerful Features</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💰</div>
            <div class="feature-title">Price Comparison</div>
            <div class="feature-description">
                Compare product prices across different
                shopping platforms.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎟️</div>
            <div class="feature-title">Offers & Coupons</div>
            <div class="feature-description">
                Discover available discounts, bank offers,
                coupons and cashback.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:

        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">AI Product Matching</div>
            <div class="feature-description">
                Find exact products and similar alternatives
                using intelligent matching.
            </div>
        </div>
        """, unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)

    with col4:

        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📉</div>
            <div class="feature-title">Price History</div>
            <div class="feature-description">
                Track product prices and understand
                historical price movements.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col5:

        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎁</div>
            <div class="feature-title">Combo Offers</div>
            <div class="feature-description">
                Find product combinations and
                additional promotional benefits.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col6:

        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔔</div>
            <div class="feature-title">Price Alerts</div>
            <div class="feature-description">
                Get notified when your favourite
                product reaches your target price.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # SHOPPING PLATFORMS

    st.markdown(
        '<div class="section-heading">🛍️ Shopping Platforms</div>',
        unsafe_allow_html=True
    )

    platform_cols = st.columns(3)

    for index, name in enumerate(PLATFORMS.values()):

        with platform_cols[index % 3]:

            st.markdown(f"""
            <div class="platform-card">
                🛒 {name}
                <div class="platform-status">
                    Connector planned
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.info(
        "Note: Platform names shown here represent planned integrations. "
        "Live retailer data will appear only after the respective "
        "connectors are implemented and tested."
    )



# =====================================================
# COMPARE PRODUCTS PAGE
# =====================================================

elif menu == "🔍 Compare Products":

    st.title("🔍 Compare Products")

    st.write(
        "Search a product by name or analyze a shopping URL."
    )

    search_type = st.radio(
        "Choose Search Method",
        ["Product Name", "Shopping URL"],
        horizontal=True
    )

    # PRODUCT NAME SEARCH

    if search_type == "Product Name":

        st.markdown("### 🔎 Search Your Product")

        with st.form("demo_product_search"):

            product_name = st.text_input(
                "Product Name",
                placeholder="Example: iPhone 16 128GB"
            )

            search_button = st.form_submit_button(
                "🔍 SEARCH PRODUCT",
                use_container_width=True
            )

        if search_button:

            if not product_name.strip():

                st.warning("Please enter a product name.")

            else:

                results = search_demo_products(product_name)

                if results:

                    st.success(
                        f"{len(results)} demo product(s) found."
                    )

                    for product in results:

                        show_demo_comparison(product)

                else:

                    st.error(
                        "No matching demo product found."
                    )

                    st.info(
                        "Try: iPhone 16, Samsung Galaxy S25, "
                        "Redmi Note 14 or HP 15s."
                    )

    # SHOPPING URL SEARCH

    else:

        st.markdown("### 🔗 Analyze Shopping URL")

        compare_url = st.text_input(
            "Enter Product URL",
            value=st.session_state.product_url,
            placeholder="https://www.amazon.in/..."
        )

        if st.button("ANALYZE PRODUCT URL"):

            product, error = analyze_product_url(compare_url)

            if error:

                st.error(error)

            else:

                st.session_state.product_url = product["url"]

                st.success(
                    f"Valid {product['platform']} product URL."
                )

                st.info(
                    "Platform recognized successfully. "
                    "Actual product details and price extraction "
                    "will be added in a future development step."
                )

                st.code(product["url"])


# =====================================================
# BEST DEALS PAGE
# =====================================================

elif menu == "🔥 Best Deals":

    st.title("🔥 Best Deals")

    st.info(
        "Best deal discovery will become available after "
        "retailer integrations are connected."
    )


# =====================================================
# PRICE HISTORY PAGE
# =====================================================

elif menu == "📊 Price History":

    st.title("📊 Price History")

    st.info(
        "Price history charts will appear after product prices "
        "start being collected and stored."
    )


# =====================================================
# WISHLIST PAGE
# =====================================================

elif menu == "❤️ Wishlist":

    st.title("❤️ My Wishlist")

    st.info(
        "User accounts and wishlist database functionality "
        "will be implemented in a later phase."
    )


# =====================================================
# ABOUT PAGE
# =====================================================

elif menu == "ℹ️ About":

    st.title("ℹ️ About Bharat Price Compare")

    st.markdown("""
    ### Smart Shopping. Better Savings.

    Bharat Price Compare is an Indian-focused product
    price intelligence platform.

    Our goal is to help customers:

    - Compare product prices.
    - Discover discounts and offers.
    - Find exact products and alternatives.
    - Track historical prices.
    - Make better shopping decisions.

    **Our Mission:** Help every Indian customer
    shop smarter.
    """)


# =====================================================
# FOOTER
# =====================================================

st.markdown("""
<div class="footer">
<b>Bharat Price Compare</b><br>
Smart Shopping. Better Savings.<br><br>
Made for India 🇮🇳
<br><br>
© 2026 Bharat Price Compare. All Rights Reserved.
</div>
""", unsafe_allow_html=True)


# ==========================================
# AFFILIATE DISCLOSURE
# ==========================================

st.markdown("---")

st.markdown(
    "<h2 style='text-align:center;'>Affiliate Disclosure</h2>",
    unsafe_allow_html=True
)

st.info(
    "As an Amazon Associate I earn from qualifying purchases."
)

st.caption(
    "Some links on Bharat Price Compare are affiliate links. "
    "We may earn a commission when you make a qualifying purchase. "
    "This comes at no additional cost to you."
)

st.markdown("---")

