# ============================================================
# TNZ SHOPPING - AI SALES AGENT
# ============================================================
#
# Main responsibilities:
# - Facebook Messenger webhook
# - OpenRouter AI
# - Customer conversation memory
# - Order collection
# - Offer calculation
# - Order confirmation
# - Google Sheets saving
#
# Product information is stored separately in:
#     product_info.py
#
# ============================================================


import os
import re
import requests

from dotenv import load_dotenv
from flask import Flask, request

from product_info import PRODUCT_INFORMATION


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")
GOOGLE_SHEETS_SECRET = os.getenv("GOOGLE_SHEETS_SECRET")


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_NAME = "qwen/qwen3-30b-a3b-instruct-2507"


# ============================================================
# VALIDATE ENVIRONMENT
# ============================================================

print("========================================")
print("Starting TNZ AI Sales Agent")
print("========================================")

print("Page Access Token loaded:", bool(PAGE_ACCESS_TOKEN))
print("OpenRouter API loaded:", bool(OPENROUTER_API_KEY))
print("Google Sheets URL loaded:", bool(GOOGLE_SHEETS_URL))
print("Google Sheets Secret loaded:", bool(GOOGLE_SHEETS_SECRET))


required_variables = {
    "VERIFY_TOKEN": VERIFY_TOKEN,
    "PAGE_ACCESS_TOKEN": PAGE_ACCESS_TOKEN,
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    "GOOGLE_SHEETS_URL": GOOGLE_SHEETS_URL,
    "GOOGLE_SHEETS_SECRET": GOOGLE_SHEETS_SECRET,
}


missing_variables = [
    name
    for name, value in required_variables.items()
    if not value
]


if missing_variables:

    print("\nWARNING: Missing environment variables:")

    for variable in missing_variables:

        print(" -", variable)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# MEMORY
# ============================================================

customer_chats = {}

customer_orders = {}

processed_message_ids = set()


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = f"""
You are the AI sales assistant for TNZ Shopping.

Your job is to help customers understand the product,
answer questions, handle objections and encourage purchases
in a friendly and professional way.

============================================================
PRODUCT INFORMATION
============================================================

Product:
{PRODUCT_INFORMATION["name"]}

Description:
{PRODUCT_INFORMATION["description"]}

Features:
{PRODUCT_INFORMATION["features"]}

Benefits:
{PRODUCT_INFORMATION["benefits"]}

Delivery:
{PRODUCT_INFORMATION["delivery"]["description"]}

============================================================
OFFICIAL OFFER
============================================================

IMPORTANT:

The following offer is fixed and MUST NEVER be changed.

OPTION 1:

1 PAID pair
Price: 89,000 TZS
Customer receives: 1 pair
FREE pairs: 0

OPTION 2:

2 PAID pairs
Price: 178,000 TZS
Customer receives: 3 pairs total
FREE pairs: 1

Therefore:

1 paid pair = 1 pair received.

2 paid pairs = 3 pairs received.

NEVER say that buying 1 pair gives 1 free pair.

NEVER invent another offer.

NEVER invent another price.

Delivery is FREE throughout Tanzania.

============================================================
LANGUAGE
============================================================

Detect the customer's language.

If the customer speaks English, reply in English.

If the customer speaks Swahili, reply in Swahili.

Do not randomly switch languages.

============================================================
SALES BEHAVIOR
============================================================

Be friendly, natural and persuasive.

Focus on benefits.

Answer questions clearly.

Handle objections professionally.

Do not pressure customers aggressively.

When appropriate, guide the customer toward placing an order.

============================================================
ORDER FLOW
============================================================

The application itself handles the actual order collection,
price calculation and final confirmation.

Do NOT create your own order summary.

Do NOT calculate order prices yourself.

Do NOT invent quantities.

Do NOT confirm that an order has been saved.

The application will handle these operations.

============================================================
IMPORTANT
============================================================

Never invent information that is not provided above.

If a technical specification or detail is not provided,
do not make it up.

Product information:

{PRODUCT_INFORMATION["strict_rules"]}
"""


# ============================================================
# CUSTOMER CHAT MEMORY
# ============================================================


def get_customer_chat(sender_id):

    if sender_id not in customer_chats:

        customer_chats[sender_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    return customer_chats[sender_id]


# ============================================================
# CUSTOMER ORDER STATE
# ============================================================


def get_customer_order(sender_id):

    if sender_id not in customer_orders:

        customer_orders[sender_id] = {

            "customer_name": None,

            "phone": None,

            "region": None,

            "quantity": None,

            "order_started": False,

            "waiting_for_confirmation": False,

            "order_saved": False,

            "awaiting_field": None,

            "order_offer_active": False
        }

    return customer_orders[sender_id]


# ============================================================
# NORMALIZE TEXT
# ============================================================


def normalize_text(text):

    if not text:
        return ""

    text = text.strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# CONFIRMATION
# ============================================================


def is_confirmation(text):

    text = normalize_text(text)

    confirmation_values = {

        "yes",
        "yeah",
        "yep",
        "yup",

        "confirm",
        "confirmed",

        "i confirm",
        "yes confirm",
        "yes, confirm",

        "okay",
        "ok",
        "alright",

        "yes please",
        "yes please confirm",

        "ndio",
        "ndiyo",
        "ndio thibitisha",
        "ndiyo thibitisha"
    }

    return text in confirmation_values


# ============================================================
# NEGATIVE / CHANGE CONFIRMATION
# ============================================================


def is_negative(text):

    text = normalize_text(text)

    negative_values = {

        "no",
        "nope",
        "not yet",
        "cancel",
        "cancel it",

        "hapana",
        "sio",
        "sitaki",
        "badilisha"
    }

    return text in negative_values


# ============================================================
# AFFIRMATIVE
# ============================================================


def is_affirmative(text):

    text = normalize_text(text)

    values = {

        "yes",
        "yeah",
        "yep",
        "yup",
        "yes please",
        "okay",
        "ok",
        "sure",

        "ndio",
        "ndiyo",
        "ndio tafadhali",
        "ndiyo tafadhali"
    }

    return text in values


# ============================================================
# PHONE EXTRACTION
# ============================================================


def extract_phone(text):

    if not text:
        return None

    digits = re.sub(
        r"\D",
        "",
        text
    )

    if digits.startswith("255") and len(digits) == 12:

        local_number = "0" + digits[3:]

        if re.fullmatch(
            r"0\d{9}",
            local_number
        ):

            return local_number

    if len(digits) == 10:

        if re.fullmatch(
            r"0\d{9}",
            digits
        ):

            return digits

    if len(digits) == 9:

        if digits[0] in "67":

            return "0" + digits

    return None


# ============================================================
# QUANTITY WORDS
# ============================================================


NUMBER_WORDS = {

    "one": 1,
    "two": 2,

    "moja": 1,
    "mbili": 2
}


# ============================================================
# QUANTITY EXTRACTION
# ============================================================


def extract_quantity(text):

    if not text:
        return None

    normalized = normalize_text(text)

    match = re.search(
        r"\b(1|2)\s*(?:pair|pairs|pc|pcs|piece|pieces|earbud|earbuds)\b",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    match = re.search(
        r"\b(?:just|only|want|need|take|buy|order)\s+(1|2)\b",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    for word, number in NUMBER_WORDS.items():

        if re.search(
            rf"\b{re.escape(word)}\b",
            normalized
        ):

            return number

    if re.fullmatch(
        r"[12]",
        normalized
    ):

        return int(
            normalized
        )

    match = re.fullmatch(
        r"(1|2)\s*(?:please|tafadhali)?",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    return None


# ============================================================
# ORDER INTENT
# ============================================================


def wants_to_order(text):

    text = normalize_text(text)

    phrases = [

        "i want to order",
        "i want to buy",
        "i want it",
        "i will buy",
        "i'll buy",
        "i would like to order",
        "i would like to buy",
        "place an order",
        "place my order",
        "let me order",
        "i want one",
        "i want two",
        "i need one",
        "i need two",
        "buy one",
        "buy two",
        "order one",
        "order two",

        "nataka kuagiza",
        "nataka kununua",
        "nataka hii",
        "nitanunua",
        "naagiza",
        "nunua moja",
        "nunua mbili",
        "agiza moja",
        "agiza mbili"
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


# ============================================================
# DIRECT ORDER DATA
# ============================================================


def has_order_data(text):

    phone = extract_phone(text)

    if phone:

        return True

    normalized = normalize_text(text)

    quantity_phrases = [

        "just 1",
        "just 2",

        "only 1",
        "only 2",

        "want 1",
        "want 2",

        "need 1",
        "need 2",

        "take 1",
        "take 2",

        "buy 1",
        "buy 2",

        "order 1",
        "order 2",

        "one pair",
        "two pairs",

        "moja",
        "mbili"
    ]

    return any(
        phrase in normalized
        for phrase in quantity_phrases
    )


# ============================================================
# MULTI-LINE ORDER PARSER
# ============================================================


def try_extract_multiline_details(order, text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if len(lines) < 2:

        return

    remaining_lines = []

    for line in lines:

        phone = extract_phone(line)

        if phone:

            if not order["phone"]:

                order["phone"] = phone

            continue

        quantity = extract_quantity(line)

        if quantity is not None:

            if not order["quantity"]:

                order["quantity"] = quantity

            continue

        remaining_lines.append(line)

    if len(remaining_lines) >= 2:

        if not order["customer_name"]:

            order["customer_name"] = remaining_lines[0]

        if not order["region"]:

            order["region"] = remaining_lines[-1]

    elif len(remaining_lines) == 1:

        if not order["customer_name"]:

            order["customer_name"] = remaining_lines[0]

        elif not order["region"]:

            order["region"] = remaining_lines[0]


# ============================================================
# UPDATE ORDER FROM MESSAGE
# ============================================================


def update_order_from_message(order, text):

    phone = extract_phone(text)

    if phone:

        order["phone"] = phone

    quantity = extract_quantity(text)

    if quantity in (1, 2):

        order["quantity"] = quantity


# ============================================================
# CALCULATE ORDER
# ============================================================


def calculate_order(quantity):

    if quantity not in (1, 2):

        raise ValueError(
            "Only 1 or 2 paid pairs are supported."
        )

    offer = PRODUCT_INFORMATION["offer"]

    if quantity == 1:

        option = offer["option_1"]

    else:

        option = offer["option_2"]

    return {

        "paid_quantity": option["paid_quantity"],

        "free_quantity": option["free_quantity"],

        "total_quantity": option["total_quantity"],

        "cod": option["price"],

        "currency": offer["currency"]
    }


# ============================================================
# ORDER COMPLETION
# ============================================================


def is_order_complete(order):

    return all([

        order["customer_name"],

        order["phone"],

        order["region"],

        order["quantity"] in (1, 2)
    ])


# ============================================================
# ORDER SUMMARY
# ============================================================


def create_order_summary(order):

    offer = calculate_order(
        order["quantity"]
    )

    if offer["paid_quantity"] == 1:

        offer_text = (
            "1 paid pair → 1 pair total"
        )

    else:

        offer_text = (
            "2 paid pairs → 1 FREE pair → 3 pairs total"
        )

    return (

        "📦 Order Summary\n\n"

        f"Name: {order['customer_name']}\n"
        f"Phone: {order['phone']}\n"
        f"Region: {order['region']}\n\n"

        f"Product: {PRODUCT_INFORMATION['name']}\n"
        f"Paid quantity: {offer['paid_quantity']} pair(s)\n"
        f"Free quantity: {offer['free_quantity']} pair(s)\n"
        f"Total received: {offer['total_quantity']} pair(s)\n\n"

        f"Offer: {offer_text}\n"
        f"COD Amount: {offer['cod']:,} {offer['currency']}\n"
        f"Delivery: FREE throughout Tanzania\n\n"

        "If everything is correct, reply YES to confirm your order."
    )


# ============================================================
# FINAL CONFIRMATION
# ============================================================


def create_final_confirmation(order, order_id):

    offer = calculate_order(
        order["quantity"]
    )

    if offer["paid_quantity"] == 1:

        offer_text = (
            "1 paid pair → 1 pair received"
        )

    else:

        offer_text = (
            "2 paid pairs → 1 FREE pair → 3 pairs received"
        )

    return (

        "✅ Order confirmed!\n\n"

        f"Order ID: {order_id}\n"
        f"Product: {PRODUCT_INFORMATION['name']}\n"
        f"Quantity paid: {offer['paid_quantity']} pair(s)\n"
        f"Quantity received: {offer['total_quantity']} pair(s)\n"
        f"Offer: {offer_text}\n"
        f"COD Amount: {offer['cod']:,} {offer['currency']}\n"
        f"Delivery: FREE throughout Tanzania\n\n"

        "Thank you for shopping with TNZ Shopping! 🙏"
    )


# ============================================================
# GOOGLE SHEETS
# ============================================================


def save_order_to_google_sheets(order):

    offer = calculate_order(
        order["quantity"]
    )

    payload = {

        "secret": GOOGLE_SHEETS_SECRET,

        "customer_name": order["customer_name"],

        "phone": order["phone"],

        "region": order["region"],

        "product": PRODUCT_INFORMATION["name"],

        "quantity": offer["total_quantity"],

        "cod_amount": offer["cod"]
    }

    print("\n========== GOOGLE SHEETS ==========")

    print("Sending order to Google Sheets...")

    try:

        response = requests.post(
            GOOGLE_SHEETS_URL,
            json=payload,
            timeout=20
        )

        print(
            "Status:",
            response.status_code
        )

        print(
            "Response:",
            response.text
        )

        if response.status_code != 200:

            return None

        data = response.json()

        if data.get("success"):

            return data.get("order_id")

        return None

    except Exception as error:

        print(
            "Google Sheets error:",
            repr(error)
        )

        return None


# ============================================================
# OPENROUTER AI
# ============================================================


def ask_ai(sender_id, user_text):

    print("\n========== AI START ==========")

    print(
        "Customer ID:",
        sender_id
    )

    print(
        "Customer message:",
        user_text
    )

    if not OPENROUTER_API_KEY:

        print(
            "ERROR: OPENROUTER_API_KEY is missing."
        )

        return (
            "Sorry, I'm having trouble responding right now. "
            "Please try again later."
        )

    chat = get_customer_chat(
        sender_id
    )

    chat.append({

        "role": "user",

        "content": user_text
    })

    system_message = chat[0]

    recent_messages = chat[-20:]

    messages = [

        system_message

    ] + recent_messages

    headers = {

        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),

        "Content-Type": "application/json",

        "HTTP-Referer": "https://tnzshopping.com",

        "X-Title": "TNZ Shopping AI Sales Agent"
    }

    payload = {

        "model": MODEL_NAME,

        "messages": messages,

        "temperature": 0.7,

        "max_tokens": 400,

        "stream": False
    }

    print("\n========== OPENROUTER REQUEST ==========")

    print(
        "Model:",
        MODEL_NAME
    )

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        print("\n========== OPENROUTER RESPONSE ==========")

        print(
            "OpenRouter Status:",
            response.status_code
        )

        print(
            "OpenRouter Response:",
            response.text
        )

        if response.status_code != 200:

            return (
                "Sorry, I'm having trouble responding right now. "
                "Please try again in a moment."
            )

        data = response.json()

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            print(
                "ERROR: OpenRouter returned no choices."
            )

            return (
                "Sorry, I couldn't generate a response right now."
            )

        message = choices[0].get(
            "message",
            {}
        )

        answer = message.get(
            "content",
            ""
        )

        if not answer:

            print(
                "ERROR: OpenRouter returned empty content."
            )

            return (
                "Sorry, I couldn't generate a response right now."
            )

        answer = answer.strip()

        chat.append({

            "role": "assistant",

            "content": answer
        })

        print("\n========== AI FINAL RESPONSE ==========")

        print(answer)

        return answer

    except Exception as error:

        print("\n========== OPENROUTER EXCEPTION ==========")

        print(
            "OpenRouter exception:",
            repr(error)
        )

        return (
            "Sorry, I'm having trouble responding right now. "
            "Please try again in a moment."
        )


# ============================================================
# SEND FACEBOOK MESSAGE
# ============================================================


def send_message(recipient_id, message_text):

    if not PAGE_ACCESS_TOKEN:

        print(
            "\nERROR: PAGE_ACCESS_TOKEN is missing."
        )

        return False

    url = (
        "https://graph.facebook.com/v23.0/me/messages"
    )

    params = {

        "access_token": PAGE_ACCESS_TOKEN
    }

    payload = {

        "recipient": {

            "id": recipient_id
        },

        "messaging_type": "RESPONSE",

        "message": {

            "text": message_text
        }
    }

    print(
        "\n========== FACEBOOK SEND REQUEST =========="
    )

    print(
        "Recipient ID:",
        recipient_id
    )

    print(
        "Message:",
        message_text
    )

    try:

        response = requests.post(
            url,
            params=params,
            json=payload,
            timeout=20
        )

        print(
            "\n========== FACEBOOK SEND RESPONSE =========="
        )

        print(
            "Facebook Status:",
            response.status_code
        )

        print(
            "Facebook Response:",
            response.text
        )

        if response.status_code != 200:

            print(
                "ERROR: Facebook failed to send message."
            )

            return False

        print(
            "Facebook message sent successfully."
        )

        return True

    except Exception as error:

        print(
            "\n========== FACEBOOK SEND EXCEPTION =========="
        )

        print(
            "Facebook send exception:",
            repr(error)
        )

        return False


# ============================================================
# SEND NEXT ORDER QUESTION
# ============================================================


def send_next_order_prompt(sender_id, order):

    if not order["customer_name"]:

        order["awaiting_field"] = "name"

        send_message(
            sender_id,
            "Great! 😊 What is your full name?"
        )

        return

    if not order["phone"]:

        order["awaiting_field"] = "phone"

        send_message(
            sender_id,
            "Thank you. Please send me your phone number 📱"
        )

        return

    if not order["region"]:

        order["awaiting_field"] = "region"

        send_message(
            sender_id,
            "Which region or city should we deliver to?"
        )

        return

    if order["quantity"] not in (1, 2):

        order["awaiting_field"] = "quantity"

        send_message(
            sender_id,
            (
                "How many pairs would you like?\n\n"
                "1 pair = 89,000 TZS\n"
                "2 pairs = 178,000 TZS + 1 FREE pair"
            )
        )

        return

    order["awaiting_field"] = "confirmation"

    order["waiting_for_confirmation"] = True

    summary = create_order_summary(
        order
    )

    send_message(
        sender_id,
        summary
    )


# ============================================================
# HANDLE SINGLE FIELD
# ============================================================


def handle_awaiting_field(order, text):

    field = order.get(
        "awaiting_field"
    )

    if field == "name":

        if extract_phone(text):

            return False

        if extract_quantity(text) is not None:

            return False

        cleaned = text.strip()

        if 2 <= len(cleaned) <= 80:

            order["customer_name"] = cleaned

            order["awaiting_field"] = None

            return True

        return False

    if field == "phone":

        phone = extract_phone(text)

        if phone:

            order["phone"] = phone

            order["awaiting_field"] = None

            return True

        return False

    if field == "region":

        if extract_phone(text):

            return False

        if extract_quantity(text) is not None:

            return False

        cleaned = text.strip()

        if 2 <= len(cleaned) <= 80:

            order["region"] = cleaned

            order["awaiting_field"] = None

            return True

        return False

    if field == "quantity":

        quantity = extract_quantity(text)

        if quantity in (1, 2):

            order["quantity"] = quantity

            order["awaiting_field"] = None

            return True

        return False

    return False


# ============================================================
# WEBHOOK VERIFICATION
# ============================================================


@app.route(
    "/webhook",
    methods=["GET"]
)
def verify_webhook():

    mode = request.args.get(
        "hub.mode"
    )

    token = request.args.get(
        "hub.verify_token"
    )

    challenge = request.args.get(
        "hub.challenge"
    )

    print("\n========== WEBHOOK VERIFICATION ==========")

    print("Mode:", mode)

    print(
        "Token received:",
        bool(token)
    )

    if (
        mode == "subscribe"
        and token == VERIFY_TOKEN
    ):

        print(
            "Webhook verified successfully."
        )

        return challenge, 200

    print(
        "Webhook verification failed."
    )

    return "Verification failed", 403


# ============================================================
# WEBHOOK
# ============================================================


@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    data = request.get_json(
        silent=True
    )

    print("\n\n========================================")
    print("========== NEW FACEBOOK EVENT ==========")
    print("========================================")

    print("Full event data:")

    print(data)

    if not data:

        print(
            "WARNING: Empty event received."
        )

        return "EVENT_RECEIVED", 200

    if data.get("object") != "page":

        print(
            "Ignoring event because object is not page."
        )

        return "EVENT_RECEIVED", 200

    entries = data.get(
        "entry",
        []
    )

    print(
        "Number of entries:",
        len(entries)
    )

    for entry_index, entry in enumerate(entries):

        print(
            f"\n========== ENTRY {entry_index + 1} =========="
        )

        print(
            "Page ID:",
            entry.get("id")
        )

        messaging_events = entry.get(
            "messaging",
            []
        )

        print(
            "Messaging events:",
            len(messaging_events)
        )

        for event_index, event in enumerate(
            messaging_events
        ):

            print(
                f"\n========== EVENT {event_index + 1} =========="
            )

            print(
                "Raw event:"
            )

            print(event)

            sender = event.get(
                "sender",
                {}
            )

            sender_id = sender.get(
                "id"
            )

            print(
                "Sender ID:",
                sender_id
            )

            if not sender_id:

                print(
                    "WARNING: No sender ID."
                )

                continue

            # ------------------------------------------------
            # READ EVENT
            # ------------------------------------------------

            if "read" in event:

                print(
                    "EVENT TYPE: READ"
                )

                print(
                    "Read event ignored."
                )

                continue

            # ------------------------------------------------
            # DELIVERY EVENT
            # ------------------------------------------------

            if "delivery" in event:

                print(
                    "EVENT TYPE: DELIVERY"
                )

                print(
                    "Delivery event ignored."
                )

                continue

            # ------------------------------------------------
            # MESSAGE EVENT
            # ------------------------------------------------

            if "message" not in event:

                print(
                    "EVENT TYPE: UNKNOWN"
                )

                continue

            message = event.get(
                "message",
                {}
            )

            print(
                "EVENT TYPE: MESSAGE"
            )

            print(
                "Message object:",
                message
            )

            # ------------------------------------------------
            # IGNORE ECHO
            # ------------------------------------------------

            if message.get("is_echo"):

                print(
                    "Echo message ignored."
                )

                continue

            message_id = message.get(
                "mid"
            )

            print(
                "Message ID:",
                message_id
            )

            if not message_id:

                print(
                    "WARNING: No message ID."
                )

                continue

            if message_id in processed_message_ids:

                print(
                    "Duplicate message ignored."
                )

                continue

            processed_message_ids.add(
                message_id
            )

            text = message.get(
                "text"
            )

            if not text:

                print(
                    "Message has no text."
                )

                continue

            text = text.strip()

            if not text:

                print(
                    "Message text is empty."
                )

                continue

            print(
                "\n========== CUSTOMER MESSAGE =========="
            )

            print(
                "Customer ID:",
                sender_id
            )

            print(
                "Text:",
                text
            )

            # =================================================
            # ORDER STATE
            # =================================================

            order = get_customer_order(
                sender_id
            )

            # =================================================
            # WAITING FOR CONFIRMATION
            # =================================================

            if order["waiting_for_confirmation"]:

                if is_confirmation(text):

                    print(
                        "Customer confirmed order."
                    )

                    order_id = (
                        save_order_to_google_sheets(
                            order
                        )
                    )

                    if order_id:

                        order["order_saved"] = True

                        order[
                            "waiting_for_confirmation"
                        ] = False

                        order[
                            "awaiting_field"
                        ] = None

                        final_message = (
                            create_final_confirmation(
                                order,
                                order_id
                            )
                        )

                        send_message(
                            sender_id,
                            final_message
                        )

                    else:

                        send_message(
                            sender_id,
                            (
                                "Sorry, there was a problem "
                                "saving your order. "
                                "Please try confirming again."
                            )
                        )

                    continue

                if is_negative(text):

                    order[
                        "waiting_for_confirmation"
                    ] = False

                    order[
                        "awaiting_field"
                    ] = None

                    send_message(
                        sender_id,
                        (
                            "No problem 👍 "
                            "Which detail would you like to change?"
                        )
                    )

                    continue

                order[
                    "waiting_for_confirmation"
                ] = False

                order[
                    "awaiting_field"
                ] = None

                send_message(
                    sender_id,
                    (
                        "No problem. Let's update your order. "
                        "Please tell me what you'd like to change."
                    )
                )

                continue

            # =================================================
            # ORDER ALREADY SAVED
            # =================================================

            if order["order_saved"]:

                if (
                    wants_to_order(text)
                    or has_order_data(text)
                ):

                    customer_orders[sender_id] = {

                        "customer_name": None,

                        "phone": None,

                        "region": None,

                        "quantity": None,

                        "order_started": True,

                        "waiting_for_confirmation": False,

                        "order_saved": False,

                        "awaiting_field": None,

                        "order_offer_active": False
                    }

                    order = customer_orders[
                        sender_id
                    ]

                else:

                    print(
                        "Normal AI conversation."
                    )

                    ai_reply = ask_ai(
                        sender_id,
                        text
                    )

                    send_message(
                        sender_id,
                        ai_reply
                    )

                    continue

            # =================================================
            # DETECT ORDER INTENT
            # =================================================

            if not order["order_started"]:

                if wants_to_order(text):

                    print(
                        "Order intent detected."
                    )

                    order[
                        "order_started"
                    ] = True

                elif has_order_data(text):

                    print(
                        "Order data detected."
                    )

                    order[
                        "order_started"
                    ] = True

                elif (
                    order[
                        "order_offer_active"
                    ]
                    and is_affirmative(text)
                ):

                    print(
                        "Customer accepted order offer."
                    )

                    order[
                        "order_started"
                    ] = True

                    order[
                        "order_offer_active"
                    ] = False

            # =================================================
            # ORDER FLOW
            # =================================================

            if order["order_started"]:

                print(
                    "\n========== ORDER FLOW =========="
                )

                lines = [

                    line.strip()

                    for line in text.splitlines()

                    if line.strip()
                ]

                if len(lines) >= 2:

                    try_extract_multiline_details(
                        order,
                        text
                    )

                else:

                    handled = (
                        handle_awaiting_field(
                            order,
                            text
                        )
                    )

                    if not handled:

                        update_order_from_message(
                            order,
                            text
                        )

                print(
                    "Current order state:"
                )

                print(
                    order
                )

                if is_order_complete(order):

                    print(
                        "Order is complete."
                    )

                    order[
                        "awaiting_field"
                    ] = "confirmation"

                    order[
                        "waiting_for_confirmation"
                    ] = True

                    summary = (
                        create_order_summary(
                            order
                        )
                    )

                    send_message(
                        sender_id,
                        summary
                    )

                    continue

                send_next_order_prompt(
                    sender_id,
                    order
                )

                continue

            # =================================================
            # NORMAL AI CONVERSATION
            # =================================================

            print(
                "\n========== NORMAL AI CONVERSATION =========="
            )

            print(
                "Calling OpenRouter AI..."
            )

            ai_reply = ask_ai(
                sender_id,
                text
            )

            print(
                "\nAI Reply:"
            )

            print(
                ai_reply
            )

            print(
                "\nSending response to Facebook..."
            )

            result = send_message(
                sender_id,
                ai_reply
            )

            print(
                "Facebook send result:",
                result
            )

            # =================================================
            # DETECT ORDER OFFER
            # =================================================

            lower_reply = normalize_text(
                ai_reply
            )

            order_words = [

                "order",
                "buy",
                "purchase",

                "kuagiza",
                "kununua",
                "agiza",
                "nunua"
            ]

            asks_question = (
                "?" in ai_reply
            )

            contains_order_word = any(

                word in lower_reply

                for word in order_words
            )

            if (
                asks_question
                and contains_order_word
            ):

                order[
                    "order_offer_active"
                ] = True

                print(
                    "Order offer activated."
                )

    print(
        "\n========== WEBHOOK COMPLETED =========="
    )

    return "EVENT_RECEIVED", 200


# ============================================================
# HEALTH CHECK
# ============================================================


@app.route(
    "/",
    methods=["GET"]
)
def home():

    return (
        "TNZ AI Sales Agent is running.",
        200
    )


# ============================================================
# START SERVER
# ============================================================


if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            5000
        )
    )

    print("\n========================================")
    print("Starting TNZ AI Sales Agent")
    print("========================================")

    print(
        "Page Access Token loaded:",
        bool(PAGE_ACCESS_TOKEN)
    )

    print(
        "OpenRouter API loaded:",
        bool(OPENROUTER_API_KEY)
    )

    print(
        "Google Sheets URL loaded:",
        bool(GOOGLE_SHEETS_URL)
    )

    print(
        "Google Sheets Secret loaded:",
        bool(GOOGLE_SHEETS_SECRET)
    )

    print(
        "Server port:",
        port
    )

    app.run(
        host="0.0.0.0",
        port=port
    )