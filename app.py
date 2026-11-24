
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

