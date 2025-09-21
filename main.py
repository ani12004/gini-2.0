# Save as main.py
from dotenv import load_dotenv

load_dotenv()

import os
import re
import json
import time
import telebot
import google.generativeai as genai
from telebot.types import Message
from datetime import datetime
import requests
from PIL import Image
import io

# ================= CONFIG =================
CONFIDENCE_THRESHOLD_FAKE = 65
CONFIDENCE_THRESHOLD_REAL = 60
MIN_MESSAGE_LENGTH = 10
CHAT_HISTORY_LIMIT = 6
LOG_FILE = "bot_logs.txt"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    print("❌ TELEGRAM_TOKEN or GEMINI_API_KEY not set in .env file!")
    exit(1)


# ================= LOGGING =================
def log_event(user, action: str, details: str = ""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = getattr(user, "id", "SYSTEM")
        username = getattr(user, "username", "SYSTEM")
        f.write(f"[{timestamp}] User:{user_id} ({username}) | {action} | {details}\n")


# ================= STORAGE =================
def load_user_data():
    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_user_data(data):
    with open("user_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


bot_user_data = load_user_data()

# ================= TELEGRAM & GEMINI INIT =================
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# ================= PROMPTS =================
# MODIFIED: A new universal prompt for structured analysis of text and/or images.
UNIVERSAL_ANALYSIS_PROMPT = """You are an AI misinformation and scam detector for text and images, focused on India.
Analyze the user's content, which may include text and/or an image.
Look for indicators of scams, fake news, or manipulation.
Decide if the content is REAL, FAKE, or UNSURE.
Respond ONLY in valid JSON:
{{
  "result": "FAKE" | "REAL" | "UNSURE",
  "confidence": 0-100,
  "reason": "Short technical reason for your conclusion based on the content provided.",
  "why_card_en": "1-2 simple bullet point explanation in English.",
  "why_card_hi": "1-2 simple bullet point explanation in Hindi.",
  "red_flags": ["list of risk indicators like 'Suspicious QR Code', 'Urgent Action Required', etc."]
}}
User's query text: "{query}"
"""

IMAGE_DESCRIPTION_PROMPT = """You are an AI image analyst. Your task is to analyze the provided image and its caption.
1.  **Describe the image:** Briefly describe the key elements in the image.
2.  **Check for Manipulation:** Assess if the image shows signs of being digitally altered, photoshopped, or AI-generated.
3.  **Contextual Analysis:** Based on the image and caption, provide a brief conclusion about its likely authenticity or purpose.
Respond in clear, concise Markdown.
"""


# ================= GEMINI CALLS =================
# MODIFIED: This is now the primary function for all structured analysis.
def call_gemini_for_structured_analysis(query: str, img: Image = None) -> dict:
    """Calls Gemini for structured analysis on text and/or an image, returning JSON."""
    if not query and not img:
        return {"result": "UNSURE", "confidence": 0, "reason": "No content provided.",
                "why_card_en": "No content to analyze.", "why_card_hi": "विश्लेषण के लिए कोई सामग्री नहीं।",
                "red_flags": []}

    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt_parts = [UNIVERSAL_ANALYSIS_PROMPT.format(query=query)]
    if img:
        prompt_parts.append(img)

    try:
        resp = model.generate_content(
            prompt_parts,
            generation_config={"response_mime_type": "application/json"}
        )
        if not resp.parts: raise ValueError("Blocked by AI safety filter.")
        text = resp.text.strip()
        log_event("SYSTEM", "RAW_GEMINI_ANALYSIS_RESPONSE", text[:1000])
        return json.loads(text)
    except Exception as e:
        log_event("SYSTEM", "ERROR", f"Structured analysis failed: {repr(e)}")
        return {"result": "UNSURE", "confidence": 40, "reason": "AI error occurred.",
                "why_card_en": "Could not analyze due to an AI error.",
                "why_card_hi": "एआई त्रुटि के कारण विश्लेषण विफल हुआ।", "red_flags": []}


def call_gemini_for_image_description(img: Image, caption: str) -> str:
    """Calls Gemini for a descriptive analysis of an image."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        prompt_parts = [IMAGE_DESCRIPTION_PROMPT, f"**User's Caption:** _{caption}_\n\n---", img]
        resp = model.generate_content(prompt_parts)
        if not resp.parts: raise ValueError("Blocked by AI safety filter.")
        return resp.text
    except Exception as e:
        log_event("SYSTEM", "ERROR", f"Image description failed: {repr(e)}")
        return "⚠️ An error occurred while describing the image."


def call_gemini_for_chat(query: str, history: list) -> str:
    # This function remains unchanged
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        chat = model.start_chat(history=history[-CHAT_HISTORY_LIMIT:])
        resp = chat.send_message(query)
        return resp.text
    except Exception as e:
        log_event("SYSTEM", "ERROR", f"Chat error: {repr(e)}")
        return "⚠️ The AI is currently unavailable."


# ================= HELPERS & FORMATTING =================
def get_result_color(j: dict) -> str:
    res, conf = j.get("result", "UNSURE"), float(j.get("confidence", 0))
    if res == "FAKE" and conf >= CONFIDENCE_THRESHOLD_FAKE: return "RED"
    if res == "REAL" and conf >= CONFIDENCE_THRESHOLD_REAL: return "GREEN"
    return "YELLOW"


def format_analysis_reply(j: dict) -> str:
    color = get_result_color(j)
    result = j.get("result", "UNSURE").title()
    confidence = int(j.get("confidence", 0))
    if color == "RED":
        title = f"🚨 *Result: {result}* (Red Flag)"
    elif color == "GREEN":
        title = f"✅ *Result: {result}* (Green Flag)"
    else:
        title = f"⚠️ *Result: {result}* (Yellow Flag)"
    filled = round(confidence / 10)
    bar = '🟩' * filled + '⬜' * (10 - filled)
    reply = f"{title}\n\n*Confidence:* {bar} ({confidence}%)\n*Reason:* {j.get('reason', 'N/A')}\n\n"
    reply += f"🇬🇧 *Summary:*\n> {j.get('why_card_en', 'N/A')}\n\n🇮🇳 *सारांश:*\n> {j.get('why_card_hi', 'N/A')}\n"
    if j.get("red_flags"):
        reply += "\n*🔎 Textual Red Flags:*\n" + "\n".join(f"• _{flag}_" for flag in j["red_flags"])
    return reply


def send_safe_reply(message, text, **kwargs):
    try:
        bot.reply_to(message, text, **kwargs)
    except Exception as e:
        log_event(message.from_user, "SEND_FAIL", f"Failed to send: {e}")


# ================= CORE BOT LOGIC =================
# MODIFIED: A universal analysis runner for both text and images.
def run_analysis(message: Message, content: str, img: Image = None):
    user_id_str = str(message.from_user.id)
    thinking_msg = bot.reply_to(message, "🔎 Analyzing content...")
    try:
        analysis_json = call_gemini_for_structured_analysis(content, img)
        reply_text = format_analysis_reply(analysis_json)
        if get_result_color(analysis_json) == "RED":
            complaint_text = f"Content: {content}\n\nAI Analysis: {analysis_json.get('reason')}"
            bot_user_data.setdefault(user_id_str, {})["last_complaint"] = complaint_text
            save_user_data(bot_user_data)
            reply_text += "\n\n*Action:* Use `/complaint` for report text."
        bot.edit_message_text(reply_text, thinking_msg.chat.id, thinking_msg.message_id, parse_mode="Markdown")
        log_event(message.from_user, "ANALYSIS_SUCCESS", f"Result={analysis_json.get('result')}")
    except Exception as e:
        log_event(message.from_user, "ERROR", f"Analysis loop crash: {repr(e)}")
        bot.edit_message_text("❌ Error during analysis.", thinking_msg.chat.id, thinking_msg.message_id)


# ================= COMMAND HANDLERS =================
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    welcome_text = (
        "👋 Hello! I'm your AI analyzer.\n\n"
        "**How to use me:**\n"
        "1.  💬 **Chat:** Talk to me normally.\n"
        "2.  🔎 **Structured Analysis:** Use `/search <text>` OR send a photo with `/search` in the caption.\n"
        "3.  🖼️ **Descriptive Analysis:** Send a photo *without* a command to get a description.\n"
        "4.  📝 **Report:** Use `/complaint` after a 'Red Flag' result."
    )
    send_safe_reply(message, welcome_text, parse_mode="Markdown")
    log_event(message.from_user, "COMMAND_START")


@bot.message_handler(commands=["search"])
def search_command(message: Message):
    """Handles the /search command for text messages."""
    try:
        content_to_analyze = message.text.split(' ', 1)[1]
        run_analysis(message, content_to_analyze, img=None)
    except IndexError:
        run_analysis(message, content="", img=None)  # Handle /search with no text


@bot.message_handler(commands=["complaint"])
def complaint_cmd(message: Message):
    # This function remains unchanged
    user_id_str = str(message.from_user.id)
    complaint = bot_user_data.get(user_id_str, {}).get("last_complaint")
    if complaint:
        text = f"📝 **Complaint Text:**\n\n`{complaint}`\n\n_Copy this to report._"
        send_safe_reply(message, text, parse_mode="Markdown")
    else:
        send_safe_reply(message, "No 'Red Flag' text found. Run `/search` first.")
    log_event(message.from_user, "COMMAND_COMPLAINT")


# ================= PHOTO & CHAT HANDLERS =================
# MODIFIED: This handler now routes photos based on the caption.
@bot.message_handler(content_types=['photo'])
def handle_photo(message: Message):
    caption = message.caption or ""

    # Route to structured analysis if caption is /search
    if caption.strip().lower().startswith('/search'):
        try:
            # Extract text after /search command
            content_to_analyze = caption.split(' ', 1)[1] if ' ' in caption else ""

            # Download image
            photo_id = message.photo[-1].file_id
            file_info = bot.get_file(photo_id)
            download_url = f'https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}'
            image_response = requests.get(download_url)
            image_response.raise_for_status()
            img = Image.open(io.BytesIO(image_response.content))

            # Run the universal analysis
            run_analysis(message, content_to_analyze, img=img)
        except Exception as e:
            log_event(message.from_user, "ERROR", f"Photo search failed: {repr(e)}")
            send_safe_reply(message, "❌ Error processing your image search request.")
        return

    # Otherwise, perform the descriptive analysis
    thinking_msg = bot.reply_to(message, "🖼️ Analyzing image for a description...")
    try:
        photo_id = message.photo[-1].file_id
        file_info = bot.get_file(photo_id)
        download_url = f'https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}'
        image_response = requests.get(download_url)
        image_response.raise_for_status()
        img = Image.open(io.BytesIO(image_response.content))
        analysis_result = call_gemini_for_image_description(img, caption)
        bot.edit_message_text(analysis_result, thinking_msg.chat.id, thinking_msg.message_id, parse_mode="Markdown")
        log_event(message.from_user, "IMAGE_DESCRIPTION_SUCCESS")
    except Exception as e:
        log_event(message.from_user, "ERROR", f"Photo description failed: {repr(e)}")
        bot.edit_message_text("❌ Error describing the image.", thinking_msg.chat.id, thinking_msg.message_id)


@bot.message_handler(func=lambda m: True)
def handle_chat(message: Message):
    # This function remains unchanged
    user_id_str = str(message.from_user.id)
    if user_id_str not in bot_user_data:
        bot_user_data[user_id_str] = {"history": []}
    history = bot_user_data[user_id_str].get("history", [])
    response = call_gemini_for_chat(message.text, history)
    send_safe_reply(message, response)
    if "⚠️" not in response:
        history.extend(
            [{'role': 'user', 'parts': [message.text]},
             {'role': 'model', 'parts': [response]}]
        )
        bot_user_data[user_id_str]["history"] = history[-CHAT_HISTORY_LIMIT:]
        save_user_data(bot_user_data)
    log_event(message.from_user, "CHAT_MESSAGE")


# ================= START BOT =================
if __name__ == "__main__":
    print("🤖 Techgini Bot (Universal Search) is running...")
    log_event("SYSTEM", "BOT_START")
    bot.infinity_polling()