
import streamlit as st
import os
import re
import serpapi

from urllib.parse import (
    urlparse,
    unquote,
    parse_qs,
    urlencode,
    urlunparse
)
from datetime import datetime
from dotenv import load_dotenv

# =====================================================
# BHARAT PRICE COMPARE
# LIVE PRODUCT SEARCH - SERPAPI GOOGLE SHOPPING
# AFFILIATE LINK SUPPORT
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
# AFFILIATE CONFIGURATION
# =====================================================

try:
    AMAZON_ASSOCIATE_TAG = st.secrets.get(
        "AMAZON_ASSOCIATE_TAG", ""
    )
except Exception:
    AMAZON_ASSOCIATE_TAG = ""

AMAZON_ASSOCIATE_TAG = (
    AMAZON_ASSOCIATE_TAG
    or os.getenv("AMAZON_ASSOCIATE_TAG", "")
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

if "custom_affiliate_url" not in st.session_state:
    st.session_state.custom_affiliate_url = ""

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
    details = extract_product_details_from_url(url)
    return details.get("title", "")[:150]

# =====================================================
# PRODUCT URL DETAILS + TITLE MATCHING
# =====================================================

def extract_product_details_from_url(url):
    """Extract a search title and product identifier from supported product URLs.
    This does not scrape the retailer page; URL slug/IDs are the available signals.
    """
    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower().removeprefix("www.")
    path = unquote(parsed.path)
    asin = ""
    title = ""

    if "amazon.in" in domain:
        m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", path, re.I)
        if m:
            asin = m.group(1).upper()
        # Amazon product title is generally in the path before /dp/.
        if "/dp/" in path:
            title_path = path.split("/dp/")[0]
        elif "/gp/product/" in path:
            title_path = path.split("/gp/product/")[0]
        else:
            title_path = path
        title = re.sub(r"^/", "", title_path)
    else:
        title = path

    title = re.sub(r"[-_/]+", " ", title)
    title = re.sub(r"\b(?:dp|gp|product|products|item|ref|tag)\b", " ", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip()
    # Strip common URL tracking/query fragments from extracted text.
    title = title[:180]
    return {"title": title, "asin": asin, "domain": domain}



_STOPWORDS = {
    "for", "with", "and", "the", "of", "in", "on", "by", "from", "to",
    "new", "best", "buy", "online", "india", "amazon", "flipkart", "product",
    "men", "women", "unisex", "pack", "pcs", "piece", "pieces"
}

def _title_tokens(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 1 and w not in _STOPWORDS}


def product_title_match_score(anchor_title, candidate_title):
    """Token overlap score with containment bonus; used as a conservative filter."""
    a = _title_tokens(anchor_title)
    b = _title_tokens(candidate_title)
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    # Recall of the URL-derived anchor title is more important than candidate verbosity.
    recall = overlap / len(a)
    precision = overlap / len(b)
    score = 0.72 * recall + 0.28 * precision
    if a.issubset(b):
        score = max(score, 0.82)
    return min(score, 1.0)


def filter_comparison_matches(anchor_title, results, minimum_score=0.48):
    """Keep only plausibly matching product titles; never claim certainty."""
    kept = []
    for product in results or []:
        score = product_title_match_score(anchor_title, product.get("title", ""))
        product["match_score"] = score
        if score >= minimum_score:
            kept.append(product)
    return kept



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
# AUTOMATIC AFFILIATE LINK CONVERSION
# =====================================================

def convert_to_affiliate_link(original_url):
    """
    Converts direct Amazon India product URLs to affiliate links
    using the configured Amazon Associate Tag.

    Other platforms remain normal links until their official
    affiliate link method is configured.
    """

    if not original_url:
        return original_url, False, "No URL"

    if not AMAZON_ASSOCIATE_TAG:
        return original_url, False, "Affiliate tag not configured"

    try:
        parsed = urlparse(original_url)
        domain = (parsed.hostname or "").lower()

        if domain.startswith("www."):
            domain = domain[4:]

        # Only convert direct Amazon India links
        is_amazon = (
            domain == "amazon.in"
            or domain.endswith(".amazon.in")
        )

        if not is_amazon:
            return original_url, False, "Standard Link"

        query_params = parse_qs(
            parsed.query,
            keep_blank_values=True
        )

        # Add or replace Amazon Associate tracking tag
        query_params["tag"] = [AMAZON_ASSOCIATE_TAG]

        new_query = urlencode(
            query_params,
            doseq=True
        )

        affiliate_url = urlunparse(
            parsed._replace(query=new_query)
        )

        return affiliate_url, True, "Amazon Affiliate"

    except Exception:
        return original_url, False, "Standard Link"

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

            original_link = item.get("link", "")

            # Affiliate conversion
            affiliate_link, is_affiliate, affiliate_type = (
                convert_to_affiliate_link(original_link)
            )

            products.append({
                "title": item.get("title", "Product"),
                "price_text": price_text,
                "price": price_value,
                "source": item.get("source", "Unknown Seller"),
                "link": original_link,
                "affiliate_link": affiliate_link,
                "is_affiliate": is_affiliate,
                "affiliate_type": affiliate_type,
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

            # PRODUCT ACTION BUTTONS
                normal_url = (
                    product.get("link")
                    or product.get("product_link")
                    or product.get("product_url")
                    or ""
                )
                # Each search-result card must use its OWN product URL.
                # Never attach the user's separately submitted URL to result index 0.
                result_url = normal_url
                affiliate_url = product.get("affiliate_link") or ""

                # Buy Now: affiliate URL for this result, otherwise its normal URL.
                buy_url = affiliate_url or result_url
                if buy_url and buy_url.startswith(("https://", "http://")):
                    st.link_button("🛒 BUY NOW", buy_url, use_container_width=True)
                    if product.get("is_affiliate"):
                        st.caption("Affiliate link • Commission may be earned")
                    else:
                        st.caption("Retailer product link")

                # View Deals uses the listing's own link, or Google Shopping search fallback.
                view_url = result_url
                if not view_url:
                    from urllib.parse import quote_plus
                    view_url = "https://www.google.com/search?tbm=shop&q=" + quote_plus(product.get("title", query))

                if view_url and view_url.startswith(("https://", "http://")):
                    st.link_button("🔎 VIEW DEALS", view_url, use_container_width=True)

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
    st.caption("Version 1.2.0 | Affiliate Build")

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
        st.session_state.custom_affiliate_url = ""
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
            st.session_state.custom_affiliate_url = ""
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
            st.session_state.live_results = []
            st.session_state.last_query = ""
            product, error = analyze_product_url(compare_url)

            if error:
                st.error(error)
            else:
                st.session_state.product_url = product["url"]
                st.session_state.custom_affiliate_url = product["url"]

                st.success(f"Valid {product['platform']} product URL.")

                # Dedicated card for the exact URL the user submitted.
                # It is kept separate from Google Shopping search results so
                # it cannot accidentally open an unrelated result.
                st.markdown("### 🔗 Your Submitted Product")
                st.caption("This button opens the exact product URL you entered.")
                submitted_url = st.session_state.custom_affiliate_url
                if submitted_url and submitted_url.startswith(("https://", "http://")):
                    st.link_button("🛒 BUY NOW — SUBMITTED LINK", submitted_url, use_container_width=True)

                details = extract_product_details_from_url(product["url"])
                extracted_query = details["title"] or product_query_from_url(product["url"])
                asin = details.get("asin", "")

                st.write("### Identified Product (URL-based)")
                st.write(extracted_query or "Product title could not be extracted from this URL.")
                if asin:
                    st.caption(f"Amazon product ID (ASIN): {asin}")

                # Keep the customer's original URL as the exact anchor product.
                st.markdown("### 🧾 Original Product from Your Link")
                st.caption("This is the exact URL you submitted. Search results below are candidate matches, not guaranteed identical products.")
                original_buy_url, original_is_affiliate, _ = convert_to_affiliate_link(product["url"])
                st.link_button("🛒 BUY NOW — ORIGINAL PRODUCT", original_buy_url or product["url"], use_container_width=True)
                if original_is_affiliate:
                    st.caption("Amazon affiliate tracking tag is attached (if configured in app secrets).")

                # Search using extracted title, plus ASIN for Amazon URLs.
                all_candidates = []
                search_error = None
                search_queries = []
                if asin:
                    search_queries.append(asin)
                if extracted_query and extracted_query.lower() not in [q.lower() for q in search_queries]:
                    search_queries.append(extracted_query)

                with st.spinner("Searching for the same product across shopping listings..."):
                    for candidate_query in search_queries[:2]:
                        candidate_results, candidate_error = search_live_products(candidate_query)
                        if candidate_error:
                            search_error = candidate_error
                            continue
                        all_candidates.extend(candidate_results or [])

                # Deduplicate by title + source + URL before scoring.
                seen_candidate_keys = set()
                unique_candidates = []
                for candidate in all_candidates:
                    key = (candidate.get("title", "").strip().lower(),
                           candidate.get("source", "").strip().lower(),
                           candidate.get("link", "").strip())
                    if key not in seen_candidate_keys:
                        seen_candidate_keys.add(key)
                        unique_candidates.append(candidate)

                matches = filter_comparison_matches(extracted_query, unique_candidates, minimum_score=0.48)
                # Avoid listing the exact submitted retailer URL as a duplicate comparison card.
                submitted_lower = product["url"].lower()
                matches = [m for m in matches if (m.get("link", "").lower() != submitted_lower)]
                matches.sort(key=lambda p: (p.get("match_score", 0), p.get("price") is not None), reverse=True)

                st.markdown("### 🌐 Cross-Store Comparison")
                st.caption("Candidate listings are filtered by product-title similarity. Verify model/specifications before purchase.")
                if search_error and not unique_candidates:
                    st.error("Could not fetch shopping results.")
                    st.caption(search_error)
                elif matches:
                    st.session_state.live_results = matches
                    st.session_state.last_query = extracted_query
                    show_live_results(matches, extracted_query)
                else:
                    st.session_state.live_results = []
                    st.session_state.last_query = extracted_query
                    st.warning("No sufficiently similar listings were found. We are hiding unrelated products rather than showing a misleading comparison.")
                    if unique_candidates:
                        with st.expander("See unfiltered search candidates (not comparison matches)"):
                            for candidate in unique_candidates[:6]:
                                st.write(candidate.get("title", "Product"), "—", candidate.get("source", ""), candidate.get("price_text", ""))

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

                deal_url = p.get("affiliate_link") or p.get("link")

                if deal_url:
                    if p.get("is_affiliate"):
                        st.link_button("🛒 BUY NOW", deal_url)
                        st.caption("Affiliate link")
                    else:
                        st.link_button("VIEW DEAL", deal_url)

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
    "Some shopping links may be affiliate links. "
    "Bharat Price Compare may earn commission from qualifying purchases. "
    "Prices and availability can change; verify details on the retailer page."
)
st.markdown("---")
