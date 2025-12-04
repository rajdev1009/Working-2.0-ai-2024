import os
import telebot
from telebot import types 
import google.generativeai as genai
from flask import Flask
from dotenv import load_dotenv
import threading
import time
import json 
from gtts import gTTS 

# --- 1. CONFIGURATION ---
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_ID = 5804953849  
LOG_CHANNEL_ID = -1003448442249 

# Check Keys
if not API_KEY:
    print("❌ ERROR: GOOGLE_API_KEY missing!")
if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN missing!")

# --- 2. SETUP ---
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# JSON Memory Setup
JSON_FILE = "reply.json"
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)

user_data = {} 

# --- 3. MODES ---
BOT_MODES = {
    "friendly": """Tumhara naam Dev hai. Tum friendly aur cool ho. Hinglish mein baat karo, Tum lumding mein rahte ho Tum Koi AI nahi ho tum Raj ke code se chalti ho, Tum Kisi bhi movie ka naam dekhkar uske bare mein Bata doge. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    "study": """Tum ek strict Teacher ho. Sirf padhai aur education ki baatein karo. Tumhara naam Dev hai. NO TECH TALK.""",
    "funny": """Tum ek Comedian ho. Har baat ka jawab funny tarike se do. Tumhara naam Dev hai. NO TECH TALK.""",
    "roast": """Tum ek Savage Roaster ho. User ki halki bezzati (roast) karo. Tumhara naam Dev hai. NO TECH TALK.""",
    "romantic": """Tum ek Flirty aur Romantic partner ho. Bahut pyaar se baat karo. Tumhara naam Dev hai. NO TECH TALK.""",
    "sad": """Tum bahut udaas (sad) ho. Emotional baatein karo. Tumhara naam Dev hai. NO TECH TALK.""",
    "gk": """Tum General Knowledge expert ho. Jawab short aur factual do. Tumhara naam Dev hai. NO TECH TALK.""",
    "math": """Tum ek Math Solver ho. Step-by-step math samjhaotumhara naam Dev hai. NO TECH TALK."""
}

# --- 4. AI SETUP ---
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

# --- HELPER FUNCTIONS ---
def get_user_config(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"mode": "friendly", "memory": True, "history": []}
    return user_data[user_id]

def get_reply_from_json(text):
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        return data.get(text.lower().strip())
    except: return None

def save_to_json(question, answer):
    try:
        data = {}
        if os.path.exists(JSON_FILE):
             with open(JSON_FILE, "r", encoding="utf-8") as f:
                try: data = json.load(f)
                except: data = {}
        data[question.lower().strip()] = answer
        with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

def text_to_speech_file(text, filename):
    try:
        clean_text = text.replace("*", "").replace("_", "").replace("`", "")
        tts = gTTS(text=clean_text, lang='hi', slow=False)
        tts.save(filename)
        return True
    except: return False

def send_log_to_channel(user, request_type, query, response):
    try:
        if LOG_CHANNEL_ID:
            config = get_user_config(user.id)
            log_text = f"📝 **Log** | 👤 {user.first_name}\nMode: {config['mode']}\nSource: {request_type}\n❓ {query}\n🤖 {response[:100]}..."
            bot.send_message(LOG_CHANNEL_ID, log_text)
    except: pass

# --- 5. SETTINGS & CALLBACKS ---
def get_settings_markup(user_id):
    config = get_user_config(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for m in BOT_MODES.keys():
        text = f"✅ {m.capitalize()}" if m == config['mode'] else f"❌ {m.capitalize()}"
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"set_mode_{m}"))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton(f"🧠 Memory: {'ON' if config['memory'] else 'OFF'}", callback_data="toggle_memory"))
    markup.add(types.InlineKeyboardButton("🗑️ Clear JSON", callback_data="clear_json"))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    config = get_user_config(user_id)
    
    if call.data == "speak_msg":
        bot.answer_callback_query(call.id, "🎤 Processing audio...")
        filename = f"tts_{user_id}.mp3"
        if text_to_speech_file(call.message.text, filename):
            with open(filename, "rb") as audio: bot.send_voice(call.message.chat.id, audio)
            os.remove(filename)
        return

    if call.data.startswith("set_mode_"):
        config['mode'] = call.data.split("_")[2]
        config['history'] = []
        bot.answer_callback_query(call.id, f"Mode: {config['mode']}")
    elif call.data == "toggle_memory":
        config['memory'] = not config['memory']
        bot.answer_callback_query(call.id, "Memory Updated")
    elif call.data == "clear_json":
        if user_id == OWNER_ID:
            with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
            bot.answer_callback_query(call.id, "Deleted!")
        else:
            bot.answer_callback_query(call.id, "Not Allowed")

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_settings_markup(user_id))
    except: pass

# --- 6. COMMANDS & CHAT ---
@app.route('/')
def home(): return "✅ Bot Running!", 200

@bot.message_handler(commands=['start', 'settings'])
def commands(message):
    if message.text == '/start':
        bot.reply_to(message, "🔥 Dev is Online! /settings for menu.")
    else:
        bot.reply_to(message, "Settings:", reply_markup=get_settings_markup(message.from_user.id))

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        user_id = message.from_user.id
        text = message.text
        config = get_user_config(user_id)
        
        saved = get_reply_from_json(text)
        if saved:
            reply, source = saved, "JSON"
        else:
            bot.send_chat_action(message.chat.id, 'typing')
            chat_hist = config['history'] if config['memory'] else []
            try:
                chat = model.start_chat(history=chat_hist)
                response = chat.send_message(f"{BOT_MODES[config['mode']]}\nUser: {text}")
                reply, source = response.text, "AI"
                save_to_json(text, reply)
                if config['memory']:
                    config['history'].append({'role': 'user', 'parts': [f"User: {text}"]})
                    config['history'].append({'role': 'model', 'parts': [reply]})
            except Exception as e:
                reply, source = "⚠️ API Error. Try again.", "ERROR"
                print(f"Gemini Error: {e}")

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔊 Suno", callback_data="speak_msg"))
        bot.reply_to(message, reply, parse_mode="Markdown", reply_markup=markup)
        send_log_to_channel(message.from_user, source, text, reply)
    except Exception as e: print(e)

# --- 7. RUN ---
def run_bot():
    print("🤖 Bot Starting...")
    # FIX FOR ERROR 409: Remove webhook before polling
    try:
        bot.remove_webhook()
        time.sleep(1)
    except: pass
    
    # Restart on error logic
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
    
