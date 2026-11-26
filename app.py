import streamlit as st
import os
import re
import requests
import serpapi
from urllib.parse import urlparse, unquote, parse_qs, urlencode, urlunparse, quote_plus
from datetime import datetime
from dotenv import load_dotenv

# =====================================================
# BHARAT PRICE COMPARE - Google Shopping + Croma Direct API
# =====================================================
st.set_page_config(page_title="Bharat Price Compare", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")
load_dotenv()

# API configuration: Streamlit Secrets first, then .env/environment.
def secret_or_env(name, default=""):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value or os.getenv(name, default) or "").strip()

SERPAPI_API_KEY = secret_or_env("SERPAPI_API_KEY")
AMAZON_ASSOCIATE_TAG = secret_or_env("AMAZON_ASSOCIATE_TAG")
APISH_KEY = secret_or_env("APISH_KEY")
CROMA_API_URL = "https://api.api.sh/croma/v1/search"

# =====================================================
# CUSTOM CSS
# =====================================================
st.markdown("""\
<style>
.stApp { background: #080F1C; color: white; }
[data-testid="stSidebar"] { background: #101B2D; border-right: 1px solid #24334B; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1450px; }
h1, h2, h3 { color: white !important; }
p, label { color: #B9C5D8; }
.hero { background: linear-gradient(120deg,#142B45,#102039,#123B45); padding: 35px; border-radius: 20px; border: 1px solid #25445A; margin-bottom: 25px; }
.hero-tag { color: #38D6BD; font-size: 13px; font-weight: 800; letter-spacing: 3px; }
.hero-title { font-size: 40px; font-weight: 850; margin-top: 12px; line-height: 1.2; color: white; }
.highlight { color: #39D9C0; }
.feature-card { background: #111E30; border: 1px solid #243650; border-radius: 15px; padding: 20px; min-height: 140px; margin-bottom: 12px; }
.feature-title { color: white; font-size: 17px; font-weight: 750; margin-top: 10px; }
.feature-description { color: #A9B7C9; font-size: 13px; margin-top: 7px; line-height: 1.5; }
.platform-card { background: #111E30; border: 1px solid #263A55; padding: 15px 10px; border-radius: 12px; text-align: center; color: white; font-weight: 700; margin-bottom: 10px; }
.platform-status { font-size: 11px; color: #39D9C0; margin-top: 5px; }
div.stButton > button { background: linear-gradient(90deg,#12BFA8,#23D6BB); color: #07131F; border: none; border-radius: 10px; font-weight: 800; min-height: 42px; }
div.stButton > button:hover { background: #36E2CA; color: #07131F; }
div[data-testid="stTextInput"] input { background: #142239; color: white; border: 1px solid #31445F; border-radius: 10px; }
.deal-card { background: #111E30; border: 1px solid #263A55; padding: 15px; border-radius: 14px; margin-bottom: 10px; }
.footer { border-top: 1px solid #243650; padding-top: 20px; margin-top: 50px; text-align: center; color: #8798AF; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================
for key, initial in {
    "product_url": "", "search_history": [], "live_results": [], "last_query": "",
    "custom_affiliate_url": "", "croma_results": [], "croma_error": "", "croma_query": "",
    "url_comparison_results": [], "url_comparison_query": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = initial

# =====================================================
# SUPPORTED PLATFORMS / URL ANALYZER
# =====================================================
PLATFORMS = {
    "flipkart.com": "Flipkart", "amazon.in": "Amazon India", "croma.com": "Croma",
    "reliancedigital.in": "Reliance Digital", "vijaysales.com": "Vijay Sales", "tatacliq.com": "Tata CLiQ"
}

def analyze_product_url(url):
    url = (url or "").strip()
    if not url:
        return None, "Please enter a product URL."
    if not url.startswith(("https://", "http://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = (parsed.hostname or "").lower().removeprefix("www.")
        platform = next((name for website, name in PLATFORMS.items() if domain == website or domain.endswith("." + website)), None)
        if not platform:
            return None, "This shopping platform is not supported yet."
        return {"url": url, "platform": platform, "domain": domain}, None
    except Exception:
        return None, "Invalid product URL."


def extract_product_details_from_url(url):
    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower().removeprefix("www.")
    path = unquote(parsed.path)
    asin = ""
    title = ""
    if "amazon.in" in domain:
        match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", path, re.I)
        if match:
            asin = match.group(1).upper()
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
    title = re.sub(r"\s+", " ", title).strip()[:180]
    return {"title": title, "asin": asin, "domain": domain}


def product_query_from_url(url):
    return extract_product_details_from_url(url).get("title", "")


_STOPWORDS = {"for","with","and","the","of","in","on","by","from","to","new","best","buy","online","india","amazon","flipkart","product","men","women","unisex","pack","pcs","piece","pieces"}

def _title_tokens(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {word for word in words if len(word) > 1 and word not in _STOPWORDS}

def product_title_match_score(anchor_title, candidate_title):
    a, b = _title_tokens(anchor_title), _title_tokens(candidate_title)
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    recall, precision = overlap / len(a), overlap / len(b)
    score = 0.72 * recall + 0.28 * precision
    if a.issubset(b):
        score = max(score, 0.82)
    return min(score, 1.0)

def filter_comparison_matches(anchor_title, results, minimum_score=0.48):
    kept = []
    for product in results or []:
        product["match_score"] = product_title_match_score(anchor_title, product.get("title", ""))
        if product["match_score"] >= minimum_score:
            kept.append(product)
    return kept

# =====================================================
# PRICE HELPERS + AFFILIATE LINKS
# =====================================================
def parse_price(price_text):
    if price_text is None:
        return None
    if isinstance(price_text, (int, float)):
        return float(price_text)
    text = str(price_text).replace(",", "")
    text = re.sub(r"[^\d.]", "", text)
    try:
        return float(text)
    except (ValueError, TypeError):
        return None

def convert_to_affiliate_link(original_url):
    if not original_url:
        return original_url, False, "No URL"
    if not AMAZON_ASSOCIATE_TAG:
        return original_url, False, "Affiliate tag not configured"
    try:
        parsed = urlparse(original_url)
        domain = (parsed.hostname or "").lower().removeprefix("www.")
        if not (domain == "amazon.in" or domain.endswith(".amazon.in")):
            return original_url, False, "Standard Link"
        params = parse_qs(parsed.query, keep_blank_values=True)
        params["tag"] = [AMAZON_ASSOCIATE_TAG]
        return urlunparse(parsed._replace(query=urlencode(params, doseq=True))), True, "Amazon Affiliate"
    except Exception:
        return original_url, False, "Standard Link"

# =====================================================
# GOOGLE SHOPPING SEARCH
# =====================================================
def search_live_products(query):
    if not SERPAPI_API_KEY:
        return None, "SerpApi API key is missing. Add it in Streamlit Secrets or .env."
    try:
        client = serpapi.Client(api_key=SERPAPI_API_KEY, timeout=25)
        response = client.search(engine="google_shopping", q=query, gl="in", hl="en", location="India")
        if response.get("error"):
            return None, response.get("error")
        products = []
        for item in response.get("shopping_results", []):
            price_text = item.get("price", "")
            price_value = item.get("extracted_price")
            if price_value is None:
                price_value = parse_price(price_text)
            original_link = item.get("link", "")
            affiliate_link, is_affiliate, affiliate_type = convert_to_affiliate_link(original_link)
            products.append({
                "title": item.get("title", "Product"), "price_text": price_text, "price": price_value,
                "source": item.get("source", "Unknown Seller"), "link": original_link,
                "affiliate_link": affiliate_link, "is_affiliate": is_affiliate, "affiliate_type": affiliate_type,
                "thumbnail": item.get("thumbnail", ""), "rating": item.get("rating"),
                "reviews": item.get("reviews"), "delivery": item.get("delivery", ""), "brand": "", "mrp": None,
                "discount": "", "product_id": "", "highlights": []
            })
        products.sort(key=lambda p: p["price"] if p["price"] is not None else float("inf"))
        return products, None
    except Exception as exc:
        return None, str(exc)

# =====================================================
# CROMA DIRECT SEARCH - flexible response parsing
# =====================================================
def _first_value(item, keys, default=None):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return default

def _croma_product_list(payload):
    """Extract product records from common API response wrappers."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("products", "items", "results", "data", "productList", "product_list"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _croma_product_list(value)
            if nested:
                return nested
    return []

def _normalize_croma_product(item):
    if not isinstance(item, dict):
        return None
    price = parse_price(_first_value(item, ["price", "sellingPrice", "selling_price", "finalPrice", "salePrice", "offerPrice"]))
    mrp = parse_price(_first_value(item, ["mrp", " MRP", "originalPrice", "original_price", "listPrice", "maximumRetailPrice"]))
    image = _first_value(item, ["image", "imageUrl", "image_url", "thumbnail", "thumb", "productImage", "product_image"], "")
    if isinstance(image, dict):
        image = _first_value(image, ["url", "src", "link"], "")
    link = _first_value(item, ["url", "link", "productUrl", "product_url", "pdpUrl", "pdp_url"], "")
    title = _first_value(item, ["name", "title", "productName", "product_name", "displayName"], "Croma Product")
    brand = _first_value(item, ["brand", "brandName", "brand_name"], "")
    discount = _first_value(item, ["discount", "discountText", "discount_text", "discountPercentage", "discount_percentage"], "")
    if isinstance(discount, (int, float)):
        discount = f"{discount:g}%"
    if not discount and price is not None and mrp and mrp > price:
        discount = f"{round((mrp - price) / mrp * 100)}% off"
    product_id = _first_value(item, ["code", "productId", "product_id", "sku", "id"], "")
    rating = _first_value(item, ["rating", "averageRating", "average_rating"], None)
    reviews = _first_value(item, ["reviews", "reviewCount", "review_count"], None)
    highlights = _first_value(item, ["highlights", "features", "keyFeatures"], [])
    return {
        "title": str(title), "brand": brand, "price": price,
        "price_text": f"₹{price:,.0f}" if price is not None else "", "mrp": mrp,
        "discount": discount, "source": "Croma", "link": link,
        "affiliate_link": link, "is_affiliate": False, "affiliate_type": "Standard Link",
        "thumbnail": image, "rating": rating, "reviews": reviews, "delivery": "",
        "product_id": product_id, "highlights": highlights, "match_score": 1.0
    }

def search_croma_products(query):
    if not APISH_KEY:
        return [], "APISH_KEY is missing. Add it to Streamlit Secrets or .env."
    try:
        response = requests.get(CROMA_API_URL, params={"q": query}, headers={"x-api-key": APISH_KEY}, timeout=25)
        response.raise_for_status()
        payload = response.json()
        raw_products = _croma_product_list(payload)
        normalized = [_normalize_croma_product(item) for item in raw_products]
        products = [p for p in normalized if p]
        products.sort(key=lambda p: p["price"] if p["price"] is not None else float("inf"))
        return products, None
    except requests.exceptions.Timeout:
        return [], "Croma API request timed out."
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        return [], f"Croma API returned HTTP {status}. Check API key/endpoint/usage limits."
    except requests.exceptions.RequestException as exc:
        return [], f"Croma API connection error: {exc}"
    except (ValueError, TypeError, AttributeError) as exc:
        return [], f"Croma response parsing error: {exc}"

# =====================================================
# RESULT CARD DISPLAY
# =====================================================
def show_live_results(products, query):
    st.markdown("---")
    st.subheader("🛍️ Google Shopping Live Results")
    st.caption(f"Search results for: {query}")
    if not products:
        st.warning("No shopping results found for this search.")
        return
    priced = [p for p in products if p.get("price") is not None]
    if priced:
        lowest, highest = priced[0], priced[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("🏆 Lowest Found Price", f"₹{lowest['price']:,.0f}", lowest.get("source", ""))
        col2.metric("Highest Found Price", f"₹{highest['price']:,.0f}")
        col3.metric("Potential Difference", f"₹{(highest['price']-lowest['price']):,.0f}" if len(priced)>1 else "₹0")
        st.success(f"Lowest listed price: ₹{lowest['price']:,.0f} at {lowest.get('source','Unknown seller')}")
    st.markdown("### 📊 Price Comparison")
    for product in products:
        is_lowest = bool(priced and product.get("price") is not None and product["price"] == priced[0]["price"])
        with st.container(border=True):
            col_img, col_info = st.columns([1, 3])
            with col_img:
                if product.get("thumbnail"):
                    st.image(product["thumbnail"], use_container_width=True)
                else:
                    st.write("🛍️")
            with col_info:
                if is_lowest:
                    st.markdown("### 🏆 BEST PRICE FOUND")
                st.markdown(f"**{product.get('title','Product')}**")
                st.write(f"**Seller:** {product.get('source','Unknown Seller')}")
                if product.get("price") is not None:
                    st.markdown(f"## ₹{product['price']:,.0f}")
                elif product.get("price_text"):
                    st.write(f"**Price:** {product['price_text']}")
                else:
                    st.warning("Price not available")
                if product.get("rating"):
                    st.write(f"⭐ Rating: {product['rating']}")
                if product.get("reviews"):
                    st.write(f"📝 Reviews: {product['reviews']}")
                if product.get("delivery"):
                    st.caption(product["delivery"])
                result_url = product.get("link") or product.get("product_link") or product.get("product_url") or ""
                buy_url = product.get("affiliate_link") or result_url
                if buy_url.startswith(("https://", "http://")):
                    st.link_button("🛒 BUY NOW", buy_url, use_container_width=True)
                    st.caption("Affiliate link • Commission may be earned" if product.get("is_affiliate") else "Retailer product link")
                view_url = result_url or ("https://www.google.com/search?tbm=shop&q=" + quote_plus(product.get("title", query)))
                if view_url.startswith(("https://", "http://")):
                    st.link_button("🔎 VIEW DEALS", view_url, use_container_width=True)

def show_croma_results(products, query):
    st.markdown("---")
    st.subheader("🛍️ Croma Direct API Results")
    st.caption(f"Croma search: {query}")
    if not products:
        st.info("No Croma products returned for this search.")
        return
    priced = [p for p in products if p.get("price") is not None]
    if priced:
        lowest = min(priced, key=lambda p: p["price"])
        st.success(f"Lowest Croma price found: ₹{lowest['price']:,.0f}")
    for product in products:
        with st.container(border=True):
            col_img, col_info = st.columns([1, 3])
            with col_img:
                image_url = product.get("thumbnail") or ""
                if isinstance(image_url, str) and image_url.startswith(("https://", "http://")):
                    st.image(image_url, use_container_width=True)
                else:
                    st.write("🛍️")
            with col_info:
                st.markdown(f"**{product.get('title','Croma Product')}**")
                if product.get("brand"):
                    st.write(f"Brand: {product['brand']}")
                if product.get("price") is not None:
                    st.markdown(f"## ₹{product['price']:,.0f}")
                if product.get("mrp") is not None:
                    st.write(f"MRP: ₹{product['mrp']:,.0f}")
                if product.get("discount"):
                    st.success(f"Discount: {product['discount']}")
                if product.get("rating"):
                    st.write(f"⭐ Rating: {product['rating']}")
                if product.get("reviews"):
                    st.write(f"📝 Reviews: {product['reviews']}")
                if product.get("product_id"):
                    st.caption(f"Product ID: {product['product_id']}")
                link = product.get("link", "")
                if isinstance(link, str) and link.startswith(("https://", "http://")):
                    st.link_button("🛒 BUY NOW — CROMA", link, use_container_width=True)
                highlights = product.get("highlights", [])
                if highlights:
                    with st.expander("Product Highlights"):
                        if isinstance(highlights, list):
                            for item in highlights:
                                st.write("•", item)
                        else:
                            st.write(highlights)

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.markdown("## 🛒 BharatCompare")
    st.caption("INDIA'S PRODUCT PRICE INTELLIGENCE")
    st.divider()
    menu = st.radio("MAIN MENU", ["🏠 Home", "🔍 Compare Products", "🔥 Best Deals", "📊 Price History", "❤️ Wishlist", "ℹ️ About"])
    st.divider()
    st.markdown("### 🌐 Supported Platforms")
    for platform_name in PLATFORMS.values():
        st.write("🟢", platform_name)
    st.divider()
    st.caption("Version 1.3.0 | Croma API Integration")

# =====================================================
# HOME PAGE
# =====================================================
if menu == "🏠 Home":
    st.markdown("""\
    <div class="hero">
      <div class="hero-tag">SMART SHOPPING FOR EVERY INDIAN</div>
      <div class="hero-title">Don't Pay More.<br><span class="highlight">Find The Best Deal.</span></div>
      <p>Compare products, prices and shopping offers. Make smarter shopping decisions.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("## 🔍 Compare Any Product")
    with st.form("home_search_form"):
        home_query = st.text_input("Product Name", placeholder="Example: Samsung Galaxy S25 256GB")
        home_search = st.form_submit_button("🔎 SEARCH LIVE PRICES", use_container_width=True)
    if home_search:
        st.session_state.custom_affiliate_url = ""
        st.session_state.live_results = []
        st.session_state.croma_results = []
        st.session_state.croma_error = ""
        if not home_query.strip():
            st.warning("Please enter a product name.")
        else:
            with st.spinner("Searching Google Shopping and Croma..."):
                google_results, google_error = search_live_products(home_query)
                croma_results, croma_error = search_croma_products(home_query)
            if google_error:
                st.error("Google Shopping search failed.")
                st.caption(google_error)
            else:
                st.session_state.live_results = google_results or []
                st.session_state.last_query = home_query
            st.session_state.croma_results = croma_results or []
            st.session_state.croma_error = croma_error or ""
            st.session_state.croma_query = home_query
            st.session_state.search_history.append({"query": home_query, "time": datetime.now().strftime("%d-%m-%Y %H:%M")})
    if st.session_state.live_results:
        show_live_results(st.session_state.live_results, st.session_state.last_query)
    if st.session_state.croma_results:
        show_croma_results(st.session_state.croma_results, st.session_state.croma_query)
    elif st.session_state.croma_error:
        st.warning("Croma search is currently unavailable.")
        st.caption(st.session_state.croma_error)
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
            st.markdown(f"<div class='feature-card'><div>{feature[0]}</div><div class='feature-title'>{feature[1]}</div><div class='feature-description'>{feature[2]}</div></div>", unsafe_allow_html=True)
    st.markdown("## 🛍️ Shopping Platforms")
    platform_cols = st.columns(3)
    for index, platform_name in enumerate(PLATFORMS.values()):
        with platform_cols[index % 3]:
            st.markdown(f"<div class='platform-card'>🛒 {platform_name}<div class='platform-status'>Search availability depends on live results</div></div>", unsafe_allow_html=True)

# =====================================================
# COMPARE PRODUCTS PAGE
# =====================================================
elif menu == "🔍 Compare Products":
    st.title("🔍 Compare Products")
    st.write("Search a product name or analyze a supported shopping URL.")
    search_type = st.radio("Choose Search Method", ["Product Name", "Shopping URL"], horizontal=True)
    if search_type == "Product Name":
        st.markdown("### 🔎 Search Product")
        with st.form("live_product_search"):
            product_name = st.text_input("Product Name", placeholder="Example: iPhone 16 128GB")
            search_button = st.form_submit_button("🔍 SEARCH LIVE PRODUCTS", use_container_width=True)
        if search_button:
            st.session_state.custom_affiliate_url = ""
            st.session_state.live_results = []
            st.session_state.croma_results = []
            st.session_state.croma_error = ""
            if not product_name.strip():
                st.warning("Please enter a product name.")
            else:
                with st.spinner("Searching Google Shopping and Croma..."):
                    google_results, google_error = search_live_products(product_name)
                    croma_results, croma_error = search_croma_products(product_name)
                if google_error:
                    st.error("Google Shopping search failed.")
                    st.caption(google_error)
                else:
                    st.session_state.live_results = google_results or []
                    st.session_state.last_query = product_name
                    st.success(f"{len(google_results or [])} Google Shopping results found!")
                st.session_state.croma_results = croma_results or []
                st.session_state.croma_error = croma_error or ""
                st.session_state.croma_query = product_name
                if croma_results:
                    st.success(f"{len(croma_results)} Croma products found!")
                st.session_state.search_history.append({"query": product_name, "time": datetime.now().strftime("%d-%m-%Y %H:%M")})
        if st.session_state.live_results:
            show_live_results(st.session_state.live_results, st.session_state.last_query)
        if st.session_state.croma_results:
            show_croma_results(st.session_state.croma_results, st.session_state.croma_query)
        elif st.session_state.croma_error:
            st.warning("Croma search failed.")
            st.caption(st.session_state.croma_error)
    else:
        st.markdown("### 🔗 Analyze Shopping URL")
        compare_url = st.text_input("Enter Product URL", value=st.session_state.product_url, placeholder="https://www.amazon.in/...")
        if st.button("ANALYZE PRODUCT URL", use_container_width=True):
            st.session_state.live_results = []
            st.session_state.croma_results = []
            st.session_state.croma_error = ""
            st.session_state.url_comparison_results = []
            product, error = analyze_product_url(compare_url)
            if error:
                st.error(error)
            else:
                st.session_state.product_url = product["url"]
                st.session_state.custom_affiliate_url = product["url"]
                st.success(f"Valid {product['platform']} product URL.")
                st.markdown("### 🔗 Your Submitted Product")
                st.caption("This button opens the exact product URL you entered.")
                if product["url"].startswith(("https://", "http://")):
                    st.link_button("🛒 BUY NOW — SUBMITTED LINK", product["url"], use_container_width=True)
                details = extract_product_details_from_url(product["url"])
                extracted_query = details["title"] or product_query_from_url(product["url"])
                asin = details.get("asin", "")
                st.markdown("### Identified Product (URL-based)")
                st.write(extracted_query or "Product title could not be extracted from this URL.")
                if asin:
                    st.caption(f"Amazon product ID (ASIN): {asin}")
                st.markdown("### 🧾 Original Product from Your Link")
                st.caption("This is the exact URL you submitted. Search results below are candidate matches, not guaranteed identical products.")
                original_buy_url, original_is_affiliate, _ = convert_to_affiliate_link(product["url"])
                st.link_button("🛒 BUY NOW — ORIGINAL PRODUCT", original_buy_url or product["url"], use_container_width=True)
                if original_is_affiliate:
                    st.caption("Amazon affiliate tracking tag attached (if configured in app secrets).")
                queries = []
                if asin:
                    queries.append(asin)
                if extracted_query and extracted_query.lower() not in [q.lower() for q in queries]:
                    queries.append(extracted_query)
                google_candidates, croma_candidates = [], []
                google_search_error, croma_search_error = "", ""
                with st.spinner("Searching Google Shopping and Croma for matching listings..."):
                    for candidate_query in queries[:2]:
                        g_results, g_error = search_live_products(candidate_query)
                        if g_error:
                            google_search_error = g_error
                        else:
                            google_candidates.extend(g_results or [])
                        c_results, c_error = search_croma_products(candidate_query)
                        if c_error:
                            croma_search_error = c_error
                        else:
                            croma_candidates.extend(c_results or [])
                # Deduplicate combined candidates by title/source/link.
                all_candidates = google_candidates + croma_candidates
                unique_candidates, seen_keys = [], set()
                for candidate in all_candidates:
                    key = (candidate.get("title", "").strip().lower(), candidate.get("source", "").strip().lower(), candidate.get("link", "").strip())
                    if key not in seen_keys:
                        seen_keys.add(key)
                        unique_candidates.append(candidate)
                matches = filter_comparison_matches(extracted_query, unique_candidates, minimum_score=0.48) if extracted_query else []
                submitted_lower = product["url"].lower().rstrip("/")
                matches = [m for m in matches if (m.get("link", "").lower().rstrip("/") != submitted_lower)]
                matches.sort(key=lambda p: (p.get("match_score", 0), p.get("price") is not None), reverse=True)
                st.markdown("### 🌐 Cross-Store Comparison")
                st.caption("Listings are filtered by title similarity. Verify model, specifications and seller before buying.")
                if matches:
                    google_matches = [p for p in matches if p.get("source") != "Croma"]
                    croma_matches = [p for p in matches if p.get("source") == "Croma"]
                    if google_matches:
                        show_live_results(google_matches, extracted_query)
                    if croma_matches:
                        show_croma_results(croma_matches, extracted_query)
                else:
                    st.warning("No sufficiently similar listings found. Unrelated products are hidden to avoid misleading comparisons.")
                    if unique_candidates:
                        with st.expander("See unfiltered candidate titles"):
                            for candidate in unique_candidates[:8]:
                                st.write(candidate.get("title", "Product"), "—", candidate.get("source", ""), candidate.get("price_text", ""))
                if google_search_error:
                    st.caption("Google Shopping note: " + google_search_error)
                if croma_search_error:
                    st.caption("Croma note: " + croma_search_error)
                st.code(product["url"])

# =====================================================
# BEST DEALS
# =====================================================
elif menu == "🔥 Best Deals":
    st.title("🔥 Best Deals")
    all_deals = list(st.session_state.live_results or []) + list(st.session_state.croma_results or [])
    if all_deals:
        st.write("Deals from your most recent search:")
        priced = [p for p in all_deals if p.get("price") is not None]
        priced.sort(key=lambda p: p["price"])
        if priced:
            for p in priced[:10]:
                st.markdown(f"**{p.get('title','Product')}**  \nSeller: {p.get('source','')}  \nPrice: ₹{p['price']:,.0f}")
                deal_url = p.get("affiliate_link") or p.get("link") or ""
                if deal_url.startswith(("https://", "http://")):
                    st.link_button("🛒 BUY NOW" if p.get("is_affiliate") else "VIEW DEAL", deal_url)
                    if p.get("is_affiliate"):
                        st.caption("Affiliate link")
                st.divider()
        else:
            st.info("No priced products available yet.")
    else:
        st.info("Search a product first to see deals here.")

# =====================================================
# PLACEHOLDER PAGES
# =====================================================
elif menu == "📊 Price History":
    st.title("📊 Price History")
    st.info("Historical prices will be available after a price database and scheduled price tracking are implemented.")
elif menu == "❤️ Wishlist":
    st.title("❤️ My Wishlist")
    st.info("Wishlist database and user accounts are planned for a future update.")
elif menu == "ℹ️ About":
    st.title("ℹ️ About Bharat Price Compare")
    st.markdown("""\
    ### Smart Shopping. Better Savings.
    Bharat Price Compare helps users search shopping listings and compare prices from available online merchants.
    **Our goals:** Find products online, compare listed prices, discover sellers, find lower-priced options, and make smarter shopping decisions.
    **Our Mission:** Help every Indian customer shop smarter.
    """)

# =====================================================
# SEARCH HISTORY + FOOTER
# =====================================================
if st.session_state.search_history:
    with st.expander("🕘 Recent Searches"):
        for item in reversed(st.session_state.search_history[-10:]):
            st.write(item)

st.markdown("""\
<div class="footer"><b>Bharat Price Compare</b><br>Smart Shopping. Better Savings.<br><br>Made for India 🇮🇳<br><br>© 2026 Bharat Price Compare. All Rights Reserved.</div>
""", unsafe_allow_html=True)
st.markdown("---")
st.markdown("<h3 style='text-align:center;'>Affiliate Disclosure</h3>", unsafe_allow_html=True)
st.caption("Some shopping links may be affiliate links. Bharat Price Compare may earn commission from qualifying purchases. Prices and availability can change; verify details on the retailer page.")
st.markdown("---")
