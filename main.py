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

# 👇 Apni dono API Keys yahan dalein
API_KEYS = [
    "AIzaSyAtMlcnUKg97zE1OmwOegSWTTp440E_-KY", 
    "AIzaSyAG0r5Rsauv9FW9giCcHCCehjjRtazbA0E"
]

# 👇 Apna Telegram Token yahan dalein
TELEGRAM_BOT_TOKEN = "8546441412:AAGmnP2MAilRoDN4FUInDnH7QmJfc_X_wHk"

OWNER_ID = 5804953849  
LOG_CHANNEL_ID = -1003448442249 

# --- 2. AUTO MODEL SELECTOR (JUGAAD) ---
# Ye list mein se jo model chalega, bot usse connect kar lega
ALL_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
    "gemini-pro", 
    "gemini-1.0-pro"
]

current_key_index = 0
active_model_name = None # Ye automatic set hoga

# Safety Filters OFF
safe = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

def configure_genai():
    global current_key_index
    try:
        key = API_KEYS[current_key_index]
        if "YOUR_" in key:
            print("❌ ERROR: API Key code mein paste nahi ki gayi hai!")
        else:
            genai.configure(api_key=key)
            print(f"🔑 Using API Key Index: {current_key_index + 1}")
    except Exception as e: print(e)

def get_working_model():
    """Ye function check karega ki kaunsa model zinda hai"""
    global active_model_name
    print("🔄 Checking working model...")
    
    for model_name in ALL_MODELS:
        try:
            # Test connection
            test_model = genai.GenerativeModel(model_name, safety_settings=safe)
            test_model.generate_content("Hi") # Dummy request
            print(f"✅ Success! Connected to: {model_name}")
            active_model_name = model_name
            return test_model
        except Exception as e:
            print(f"❌ {model_name} failed. Trying next...")
            continue
            
    print("🚫 All models failed! Google API down or Keys quota over.")
    return None

def rotate_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    configure_genai()
    print(f"🔄 Rotating Key... Now using Key {current_key_index + 1}")

# Initialize
configure_genai()
model = get_working_model()

# Agar pehli key se model nahi mila, to key change karke try karo
if not model:
    rotate_key()
    model = get_working_model()

# --- 3. FLASK & TELEBOT SETUP ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)
JSON_FILE = "reply.json"
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
user_data = {} 

# --- 4. MODES & HELPERS ---
BOT_MODES = {
    "friendly": "Tumhara naam Dev hai. Tum friendly aur cool ho. Hinglish mein baat karo.",
    "study": "Tum ek strict Teacher ho. Sirf padhai ki baatein karo.",
    "funny": "Tum ek Comedian ho. Funny jawab do.",
    "roast": "Tum ek Savage Roaster ho. User ki bezzati karo.",
    "romantic": "Tum ek Flirty partner ho. Pyaar se baat karo.",
    "sad": "Tum bahut udaas (sad) ho.",
    "gk": "Tum GK expert ho. Short answer do.",
    "math": "Tum Math solver ho. Step-by-step samjhaao."
}

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

def clean_text_for_audio(text): return text.replace("*", "").replace("_", "").replace("`", "")

def text_to_speech_file(text, filename):
    try:
        tts = gTTS(text=text, lang='hi', slow=False)
        tts.save(filename)
        return True
    except: return False

def send_log_to_channel(user, source, query, response):
    try:
        if LOG_CHANNEL_ID:
            config = get_user_config(user.id)
            bot.send_message(LOG_CHANNEL_ID, f"📝 **Log** | 👤 {user.first_name}\nMode: {config['mode']}\nModel: {active_model_name}\n❓ {query}\n🤖 {response}")
    except: pass

# --- 5. ROUTES & COMMANDS ---
@app.route('/')
def home(): return f"✅ Bot Running on {active_model_name}", 200

@bot.message_handler(commands=['start'])
def send_start(message):
    bot.reply_to(message, "🔥 **Dev is Online!**\n/settings dabayein.")

@bot.message_handler(commands=['settings'])
def settings_menu(message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    mode_list = ["friendly", "study", "funny", "roast", "romantic", "sad", "gk", "math"]
    btns = []
    for m in mode_list:
        txt = f"✅ {m.capitalize()}" if m == config['mode'] else f"❌ {m.capitalize()}"
        btns.append(types.InlineKeyboardButton(txt, callback_data=f"set_mode_{m}"))
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton(f"🧠 Memory: {'ON' if config['memory'] else 'OFF'}", callback_data="toggle_memory"))
    markup.add(types.InlineKeyboardButton("🗑️ Clear JSON", callback_data="clear_json"))
    bot.reply_to(message, "🎛️ **Settings**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    config = get_user_config(user_id)
    
    if call.data == "speak_msg":
        bot.answer_callback_query(call.id, "🎤 Audio...")
        fn = f"tts_{user_id}.mp3"
        txt = clean_text_for_audio(call.message.text) if call.message.text else "Err"
        if text_to_speech_file(txt, fn):
            with open(fn, "rb") as a: bot.send_voice(call.message.chat.id, a)
            os.remove(fn)
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
        try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=settings_menu(call.message)) # logic shortcut
        except: pass

# --- 6. MAIN CHAT LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        user_id = message.from_user.id
        user_text = message.text
        if not user_text: return
        config = get_user_config(user_id)
        
        saved = get_reply_from_json(user_text)
        if saved:
            ai_reply, source = saved, "JSON"
        else:
            bot.send_chat_action(message.chat.id, 'typing')
            sys_prompt = BOT_MODES.get(config['mode'], BOT_MODES['friendly'])
            chat_hist = config['history'] if config['memory'] else []
            ai_reply = "Server Error"
            source = "ERROR"
            
            # Retry Loop with Model
            for attempt in range(3):
                try:
                    if not model: raise Exception("No Working Model Found")
                    chat = model.start_chat(history=chat_hist)
                    resp = chat.send_message(f"System: {sys_prompt}\nUser: {user_text}")
                    ai_reply = resp.text
                    source = "AI"
                    break
                except Exception as e:
                    err = str(e)
                    print(f"⚠️ Error: {err}")
                    if "429" in err or "quota" in err.lower():
                        rotate_key()
                        time.sleep(1)
                    else:
                        ai_reply = "Google se connect nahi ho raha."
                        break
            
            if source == "AI" and config['memory']:
                if len(config['history']) > 20: config['history'] = config['history'][2:]
                config['history'].append({'role': 'user', 'parts': [user_text]})
                config['history'].append({'role': 'model', 'parts': [ai_reply]})
                save_to_json(user_text, ai_reply)

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔊 Suno", callback_data="speak_msg"))
        try: bot.reply_to(message, ai_reply, parse_mode="Markdown", reply_markup=markup)
        except: bot.reply_to(message, ai_reply, reply_markup=markup)
        
        send_log_to_channel(message.from_user, source, user_text, ai_reply)

    except Exception as e: print(e)

if __name__ == "__main__":
    t = threading.Thread(target=bot.infinity_polling)
    t.start()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
    
