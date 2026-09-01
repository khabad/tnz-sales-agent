import os
import requests

from dotenv import load_dotenv
from flask import Flask, request
from google import genai

from product_info import PRODUCT_INFORMATION


# ========================================
# Load environment variables
# ========================================

load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not VERIFY_TOKEN:
    raise ValueError("VERIFY_TOKEN was not found")

if not PAGE_ACCESS_TOKEN:
    raise ValueError("PAGE_ACCESS_TOKEN was not found")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY was not found")


# ========================================
# Connect to Gemini
# ========================================

client = genai.Client(api_key=GEMINI_API_KEY)


# ========================================
# Flask
# ========================================

app = Flask(__name__)


# ========================================
# Store Gemini chats for each customer
# ========================================

customer_chats = {}


# ========================================
# AI Sales Agent Instructions
# ========================================

SYSTEM_PROMPT = f"""
You are a professional AI sales agent for an online store.

Your job is to answer customers, explain products,
and help interested customers make a purchase.

LANGUAGE RULES:

- Detect the language used by the customer.
- If the customer speaks English, respond in English.
- If the customer speaks Swahili, respond in Swahili.
- Continue using the customer's language.
- Do not randomly switch languages.

CONVERSATION RULES:

- Remember everything said earlier in the conversation.
- Do not ask again for information the customer already provided.
- Be friendly, natural and helpful.
- Keep answers reasonably short.
- Do not be overly pushy.
- Never invent product information.
- Never invent prices.

PRODUCT INFORMATION:

{PRODUCT_INFORMATION}
"""


# ========================================
# Get or create chat for customer
# ========================================

def get_customer_chat(sender_id):

    if sender_id not in customer_chats:

        print("Creating new Gemini chat for:", sender_id)

        customer_chats[sender_id] = client.chats.create(
            model="gemini-3.6-flash",
            config={
                "system_instruction": SYSTEM_PROMPT
            }
        )

    return customer_chats[sender_id]


# ========================================
# Meta Webhook Verification
# ========================================

@app.route("/webhook", methods=["GET"])
def verify_webhook():

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:

        print("Webhook verified successfully!")

        return challenge, 200

    return "Verification failed", 403


# ========================================
# Receive Messenger Messages
# ========================================

@app.route("/webhook", methods=["POST"])
def receive_webhook():

    data = request.get_json()

    print("\n========== NEW EVENT ==========")
    print(data)

    if data.get("object") == "page":

        for entry in data.get("entry", []):

            for event in entry.get("messaging", []):

                sender_id = event.get("sender", {}).get("id")

                message = event.get("message", {})
                text = message.get("text")

                if sender_id and text:

                    print("Customer:", text)
                    print("Sender ID:", sender_id)

                    try:

                        # Get this customer's personal Gemini chat
                        chat = get_customer_chat(sender_id)

                        # Send customer message to Gemini
                        response = chat.send_message(text)

                        ai_reply = response.text

                        print("AI:", ai_reply)

                        # Send Gemini response back to Messenger
                        send_message(
                            sender_id,
                            ai_reply
                        )

                    except Exception as e:

                        print("AI ERROR:", e)

                        send_message(
                            sender_id,
                            "Sorry, I'm having a little technical problem. Please try again."
                        )

    return "EVENT_RECEIVED", 200


# ========================================
# Send Message to Messenger
# ========================================

def send_message(recipient_id, message_text):

    url = "https://graph.facebook.com/v23.0/me/messages"

    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    }

    response = requests.post(
        url,
        params=params,
        json=payload
    )

    print("Facebook response:")
    print(response.status_code)
    print(response.text)


# ========================================
# Start Server
# ========================================

if __name__ == "__main__":

    print("Starting Messenger webhook...")
    print("Page Access Token loaded:", bool(PAGE_ACCESS_TOKEN))
    print("Gemini API loaded:", bool(GEMINI_API_KEY))

    app.run(port=5000)