# ============================================================
# TNZ SHOPPING - PRODUCT INFORMATION
# ============================================================
#
# IMPORTANT:
# This file contains the product/business information.
#
# When you want to sell another product, normally you only need
# to change this file. The main.py sales/order logic can remain
# the same.
# ============================================================


PRODUCT_INFORMATION = {

    # --------------------------------------------------------
    # BASIC PRODUCT INFORMATION
    # --------------------------------------------------------

    "name": "M10 Power Earbuds",

    "short_description": (
        "M10 Power Earbuds are wireless earbuds designed for "
        "music, calls and everyday use."
    ),

    "description": """
M10 Power Earbuds are practical wireless earbuds for everyday use.
They are portable, convenient and designed for customers who want
wireless listening without cables.
""",

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    "features": [
        "Wireless Bluetooth connection",
        "Portable and easy to carry",
        "Modern design",
        "Suitable for music",
        "Suitable for calls",
        "Easy for everyday use"
    ],

    # --------------------------------------------------------
    # CUSTOMER BENEFITS
    # --------------------------------------------------------

    "benefits": [
        "Enjoy music without cables",
        "Easy to carry anywhere",
        "Convenient for daily use",
        "Useful for music and calls",
        "Simple and practical wireless listening"
    ],

    # --------------------------------------------------------
    # PRICE & OFFER
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # The sales agent MUST follow these rules exactly.
    #
    # 1 paid pair = 1 pair total
    #
    # 2 paid pairs = 3 pairs total
    #                (1 pair FREE)
    #
    # There is NO free pair when buying only 1 pair.
    # --------------------------------------------------------

    "offer": {

        "currency": "TZS",

        "price_per_paid_pair": 89000,

        "option_1": {
            "paid_quantity": 1,
            "free_quantity": 0,
            "total_quantity": 1,
            "price": 89000,
            "description": "Buy 1 pair for 89,000 TZS. You receive 1 pair."
        },

        "option_2": {
            "paid_quantity": 2,
            "free_quantity": 1,
            "total_quantity": 3,
            "price": 178000,
            "description": (
                "Buy 2 pairs for 178,000 TZS and receive "
                "1 additional pair FREE. You receive 3 pairs total."
            )
        }
    },

    # --------------------------------------------------------
    # DELIVERY
    # --------------------------------------------------------

    "delivery": {
        "price": 0,
        "description": "Free delivery throughout Tanzania."
    },

    # --------------------------------------------------------
    # TARGET CUSTOMER
    # --------------------------------------------------------

    "target_customer": (
        "Customers in Tanzania looking for practical wireless "
        "earbuds for music, calls and everyday use."
    ),

    # --------------------------------------------------------
    # SALES STYLE
    # --------------------------------------------------------

    "sales_style": """
Be friendly, professional and persuasive.

Focus on customer benefits rather than simply listing features.

When appropriate, explain why the product is useful for the
customer's everyday life.

Do not pressure the customer aggressively.

Answer objections naturally and try to move the conversation
toward a purchase.

Keep responses reasonably short and suitable for Facebook Messenger.
""",

    # --------------------------------------------------------
    # STRICT BUSINESS RULES
    # --------------------------------------------------------
    #
    # These rules are extremely important.
    # --------------------------------------------------------

    "strict_rules": """
NEVER invent product information.

NEVER invent prices.

NEVER invent discounts.

NEVER invent free products.

NEVER change the official offer.

The official offer is:

1 paid pair = 89,000 TZS = 1 pair received.

2 paid pairs = 178,000 TZS = 3 pairs received,
because 1 additional pair is FREE.

Buying 1 pair DOES NOT include a free pair.

Buying 2 pairs DOES include exactly 1 free pair.

Delivery is FREE throughout Tanzania.

If the customer asks about something that is not specified
in the product information, do not invent an answer.

If necessary, say that the available information does not
specify that detail.
""",

    # --------------------------------------------------------
    # COMMON OBJECTIONS
    # --------------------------------------------------------

    "objections": {

        "expensive": (
            "Emphasize the value and convenience of the earbuds, "
            "and mention the 2-pair offer when appropriate."
        ),

        "delivery": (
            "Delivery is free throughout Tanzania."
        ),

        "quality": (
            "Only mention the features and benefits provided in "
            "this product file. Do not invent technical specifications."
        ),

        "think_about_it": (
            "Be helpful and non-aggressive. Remind the customer "
            "of the current offer and ask if they would like "
            "help placing the order."
        )
    },

    # --------------------------------------------------------
    # ORDER INFORMATION
    # --------------------------------------------------------

    "order": {

        "required_fields": [
            "customer_name",
            "phone",
            "region",
            "quantity"
        ],

        "quantity_type": (
            "Quantity means the number of PAID pairs."
        ),

        "allowed_quantities": [1, 2],

        "phone_country": "Tanzania",

        "currency": "TZS"
    },

    # --------------------------------------------------------
    # LANGUAGE
    # --------------------------------------------------------

    "languages": {

        "supported": [
            "English",
            "Swahili"
        ],

        "rule": (
            "Detect the customer's language and reply in the "
            "same language. Do not randomly switch languages."
        )
    }
}