import os
import telebot
from telebot import types 
import google.generativeai as genai
from flask import Flask
from dotenv import load_dotenv
import threading
import json 
from gtts import gTTS 
import time

# --- 1. CONFIGURATION ---
load_dotenv()

# 👇 APNI KEYS YAHAN DALEIN (Dhyan se paste karein)
API_KEYS = [
    "AIzaSyAG0r5Rsauv9FW9giCcHCCehjjRtazbA0E",  # Pehli Key
    "AIzaSyAtMlcnUKg97zE1OmwOegSWTTp440E_-KY"   # Dusri Key
]

# 👇 TELEGRAM TOKEN YAHAN DALEIN
TELEGRAM_BOT_TOKEN = "8546441412:AAGmnP2MAilRoDN4FUInDnH7QmJfc_X_wHk"

# (Agar environment variables use kar rahe hain to in lines ko uncomment karein)
# API_KEYS = [os.getenv("KEY1"), os.getenv("KEY2")]
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

OWNER_ID = 5804953849  
LOG_CHANNEL_ID = -1003448442249 

# --- 2. KEY ROTATION & SAFETY SETTINGS ---
current_key_index = 0

# 🔥 SAFETY SETTINGS: Filters ko OFF kar diya taaki bot khul ke bole
safe = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

def configure_genai():
    global current_key_index
    key = API_KEYS[current_key_index]
    if not key or "YOUR_" in key:
        print("❌ Error: API Key sahi se nahi dali hai!")
    else:
        genai.configure(api_key=key)
        print(f"🔑 Using API Key: {current_key_index + 1}")

def rotate_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    configure_genai()
    print(f"🔄 Switching to Key {current_key_index + 1}...")

configure_genai()

# --- 3. SETUP ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# Model Setup with Safety OFF
model_name = 'gemini-1.5-flash' 
model = genai.GenerativeModel(model_name, safety_settings=safe)

JSON_FILE = "reply.json"
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)

user_data = {} 

# --- 4. MODES DEFINITION ---
BOT_MODES = {
    "friendly": "Tumhara naam Dev hai. Tum friendly aur cool ho. Hinglish mein baat karo.",
    "study": "Tum ek strict Teacher ho. Sirf padhai ki baatein karo.",
    "funny": "Tum ek Comedian ho. Har baat ka jawab funny tarike se do.",
    "roast": "Tum ek Savage Roaster ho. User ki halki bezzati (roast) karo.",
    "romantic": "Tum ek Flirty partner ho. Pyaar se baat karo.",
    "sad": "Tum bahut udaas (sad) ho.",
    "gk": "Tum GK expert ho. Short answer do.",
    "math": "Tum Math solver ho. Step-by-step samjhaao."
}

# --- 5. HELPER FUNCTIONS ---
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
        with open(JSON_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        data[question.lower().strip()] = answer
        with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

def clean_text_for_audio(text):
    return text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")

def text_to_speech_file(text, filename):
    try:
        tts = gTTS(text=text, lang='hi', slow=False)
        tts.save(filename)
        return True
    except: return False

def send_log_to_channel(user, request_type, query, response):
    try:
        if LOG_CHANNEL_ID:
            config = get_user_config(user.id)
            bot.send_message(LOG_CHANNEL_ID, f"📝 **Log** | 👤 {user.first_name}\nMode: {config['mode']}\nKey: {current_key_index+1}\n❓ {query}\n🤖 {response}")
    except: pass

# --- 6. SETTINGS ---
def get_settings_markup(user_id):
    config = get_user_config(user_id)
    curr_mode = config['mode']
    markup = types.InlineKeyboardMarkup(row_width=2)
    mode_list = ["friendly", "study", "funny", "roast", "romantic", "sad", "gk", "math"]
    buttons = []
    for m in mode_list:
        text = f"✅ {m.capitalize()}" if m == curr_mode else f"❌ {m.capitalize()}"
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"set_mode_{m}"))
    markup.add(*buttons)
    mem_status = "✅ ON" if config['memory'] else "❌ OFF"
    markup.add(types.InlineKeyboardButton(f"🧠 Yaad Rakhna: {mem_status}", callback_data="toggle_memory"))
    markup.add(types.InlineKeyboardButton("🗑️ Clear JSON", callback_data="clear_json"))
    return markup

# --- 7. COMMANDS & CALLBACKS ---
@app.route('/')
def home(): return "✅ Bot Running", 200

@bot.message_handler(commands=['start'])
def send_start(message):
    bot.reply_to(message, "🔥 **Dev is Online!**\nSettings: /settings")

@bot.message_handler(commands=['settings'])
def settings_menu(message):
    bot.reply_to(message, "🎛️ **Settings**", reply_markup=get_settings_markup(message.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_mode_") or call.data in ["toggle_memory", "clear_json", "speak_msg"])
def handle_callbacks(call):
    user_id = call.from_user.id
    config = get_user_config(user_id)
    
    if call.data == "speak_msg":
        bot.answer_callback_query(call.id, "🎤 Audio...")
        filename = f"tts_{user_id}.mp3"
        clean = clean_text_for_audio(call.message.text) if call.message.text else "Error"
        if text_to_speech_file(clean, filename):
            with open(filename, "rb") as audio: bot.send_voice(call.message.chat.id, audio)
            os.remove(filename)
        return

    needs_refresh = False
    if call.data.startswith("set_mode_"):
        new_mode = call.data.split("_")[2]
        if config['mode'] != new_mode:
            config['mode'] = new_mode
            config['history'] = []
            needs_refresh = True
            bot.answer_callback_query(call.id, f"Mode: {new_mode}")
    elif call.data == "toggle_memory":
        config['memory'] = not config['memory']
        needs_refresh = True
        bot.answer_callback_query(call.id, f"Memory: {config['memory']}")
    elif call.data == "clear_json":
        if user_id == OWNER_ID:
            with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
            bot.answer_callback_query(call.id, "Deleted!")

    if needs_refresh:
        try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_settings_markup(user_id))
        except: pass

# --- 8. MAIN LOGIC (FIXED) ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        user_id = message.from_user.id
        user_text = message.text
        if not user_text: return
        config = get_user_config(user_id)
        
        # JSON CHECK
        saved = get_reply_from_json(user_text)
        if saved:
            ai_reply, source = saved, "JSON"
        else:
            # AI GENERATION
            bot.send_chat_action(message.chat.id, 'typing')
            sys_prompt = BOT_MODES.get(config['mode'], BOT_MODES['friendly'])
            chat_hist = config['history'] if config['memory'] else []
            
            ai_reply = "Error"
            source = "ERROR"
            
            for attempt in range(3): # Retry Loop
                try:
                    chat = model.start_chat(history=chat_hist)
                    resp = chat.send_message(f"System: {sys_prompt}\nUser: {user_text}")
                    ai_reply = resp.text
                    source = "AI"
                    break
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️ Key {current_key_index+1} Error: {error_msg}")
                    
                    if "429" in error_msg or "quota" in error_msg.lower():
                        rotate_key()
                        time.sleep(1)
                    else:
                        # Agar Safety ya koi aur error hai, to seedha error batao logs mein
                        ai_reply = f"Google Error: {error_msg}" 
                        break

            if source == "AI" and config['memory']:
                if len(config['history']) > 20: config['history'] = config['history'][2:]
                config['history'].append({'role': 'user', 'parts': [user_text]})
                config['history'].append({'role': 'model', 'parts': [ai_reply]})
                save_to_json(user_text, ai_reply)

        # REPLY
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔊 Suno", callback_data="speak_msg"))
        try: bot.reply_to(message, ai_reply, parse_mode="Markdown", reply_markup=markup)
        except: bot.reply_to(message, ai_reply, reply_markup=markup)
        
        send_log_to_channel(message.from_user, source, user_text, ai_reply)

    except Exception as e: print(f"CRITICAL: {e}")

if __name__ == "__main__":
    t = threading.Thread(target=bot.infinity_polling)
    t.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
        
