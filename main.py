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

# --- 1. CONFIGURATION (YAHA APNI KEYS DALEIN) ---
load_dotenv()

# Yahan apni 2 alag-alag API Keys dalein
API_KEYS = [
    "AIzaSyAtMlcnUKg97zE1OmwOegSWTTp440E_-KY",  # <-- Pehli Key yahan paste karein
    "AIzaSyAG0r5Rsauv9FW9giCcHCCehjjRtazbA0E"    # <-- Dusri Key yahan paste karein
]

# Agar environment variables use kar rahe ho to ye line uncomment karo:
# API_KEYS = [os.getenv("KEY1"), os.getenv("KEY2")]

TELEGRAM_BOT_TOKEN = "8546441412:AAHyXwxr6knaYbf2cqQqRT59H0PO5WwDQq8"  # <-- Bot Token yahan paste karein

# Agar .env use kar rahe ho:
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

OWNER_ID = 5804953849  
LOG_CHANNEL_ID = -1003448442249 

# --- 2. KEY ROTATION LOGIC ---
current_key_index = 0

def configure_genai():
    """Current index ke hisab se API Key set karta hai"""
    global current_key_index
    key = API_KEYS[current_key_index]
    genai.configure(api_key=key)
    print(f"🔑 Using API Key: {current_key_index + 1}")

def rotate_key():
    """Key fail hone par agli key par switch karta hai"""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    configure_genai()
    print(f"🔄 Switching to Key {current_key_index + 1}...")

# Pehli baar configure karein
configure_genai()

# --- 3. SETUP ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# Model Definition (Gemini 1.5 Flash - Faster & Stable)
model_name = 'gemini-1.5-flash' 
model = genai.GenerativeModel(model_name)

# JSON Memory File
JSON_FILE = "reply.json"
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)

user_data = {} 

# --- 4. MODES DEFINITION ---
BOT_MODES = {
    "friendly": "Tumhara naam Dev hai. Tum friendly aur cool ho. Hinglish mein baat karo. Tum Raj ke code se chalti ho.",
    "study": "Tum ek strict Teacher ho. Sirf padhai aur education ki baatein karo. Tumhara naam Dev hai.",
    "funny": "Tum ek Comedian ho. Har baat ka jawab funny tarike se do. Tumhara naam Dev hai.",
    "roast": "Tum ek Savage Roaster ho. User ki halki bezzati (roast) karo. Tumhara naam Dev hai.",
    "romantic": "Tum ek Flirty aur Romantic partner ho. Bahut pyaar se baat karo. Tumhara naam Dev hai.",
    "sad": "Tum bahut udaas (sad) ho. Emotional baatein karo. Tumhara naam Dev hai.",
    "gk": "Tum General Knowledge expert ho. Jawab short aur factual do. Tumhara naam Dev hai.",
    "math": "Tum ek Math Solver ho. Step-by-step math samjhaao. Tumhara naam Dev hai."
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
            bot.send_message(LOG_CHANNEL_ID, f"📝 **Log** | 👤 {user.first_name}\nMode: {config['mode']}\nKey Index: {current_key_index}\n❓ {query}\n🤖 {response}")
    except: pass

# --- 6. SETTINGS PANEL ---
def get_settings_markup(user_id):
    config = get_user_config(user_id)
    curr_mode = config['mode']
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = []
    mode_list = ["friendly", "study", "funny", "roast", "romantic", "sad", "gk", "math"]
    for m in mode_list:
        text = f"✅ {m.capitalize()}" if m == curr_mode else f"❌ {m.capitalize()}"
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"set_mode_{m}"))
    markup.add(*buttons)
    
    mem_status = "✅ ON" if config['memory'] else "❌ OFF"
    markup.add(types.InlineKeyboardButton(f"🧠 Memory: {mem_status}", callback_data="toggle_memory"))
    markup.add(types.InlineKeyboardButton("🗑️ Clear JSON (Owner Only)", callback_data="clear_json"))
    return markup

# --- 7. COMMANDS ---
@app.route('/')
def home(): return "✅ Dev Running!", 200

@bot.message_handler(commands=['start'])
def send_start(message):
    bot.reply_to(message, "🔥 **Dev is Online!**\nSettings check karne ke liye /settings dabayein.")

@bot.message_handler(commands=['settings'])
def settings_menu(message):
    markup = get_settings_markup(message.from_user.id)
    bot.reply_to(message, "🎛️ **Control Panel**\nApna Mode select karein:", reply_markup=markup)

# --- 8. CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("set_mode_") or call.data == "toggle_memory" or call.data == "clear_json")
def handle_settings_callbacks(call):
    user_id = call.from_user.id
    config = get_user_config(user_id)
    needs_refresh = False 

    if call.data.startswith("set_mode_"):
        new_mode = call.data.split("_")[2]
        if config['mode'] != new_mode:
            config['mode'] = new_mode
            config['history'] = [] 
            needs_refresh = True
            bot.answer_callback_query(call.id, f"Mode Updated: {new_mode.upper()}")
        else:
            bot.answer_callback_query(call.id, "Ye Mode pehle se ON hai!")

    elif call.data == "toggle_memory":
        config['memory'] = not config['memory']
        needs_refresh = True
        status = "ON" if config['memory'] else "OFF"
        bot.answer_callback_query(call.id, f"Memory: {status}")

    elif call.data == "clear_json":
        if user_id == OWNER_ID:
            with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
            bot.answer_callback_query(call.id, "Brain Washed! 🗑️")
        else:
            bot.answer_callback_query(call.id, "Sirf Owner ye kar sakta hai!")

    if needs_refresh:
        try:
            new_markup = get_settings_markup(user_id)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_markup)
        except: pass

@bot.callback_query_handler(func=lambda call: call.data == "speak_msg")
def speak_callback(call):
    try:
        bot.answer_callback_query(call.id, "🎤 Generating Audio...")
        bot.send_chat_action(call.message.chat.id, 'record_audio')
        filename = f"tts_{call.from_user.id}.mp3"
        clean_txt = clean_text_for_audio(call.message.text) if call.message.text else "Audio error"
        
        if text_to_speech_file(clean_txt, filename):
            with open(filename, "rb") as audio: 
                bot.send_voice(call.message.chat.id, audio)
            os.remove(filename)
        else:
            bot.send_message(call.message.chat.id, "❌ Audio Error")
    except Exception as e: print(f"TTS Error: {e}")

# --- 9. MAIN CHAT LOGIC (WITH RETRY & ROTATION) ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        user_id = message.from_user.id
        user_text = message.text
        if not user_text: return
        
        config = get_user_config(user_id)
        
        # 1. JSON Check
        saved_reply = get_reply_from_json(user_text)
        if saved_reply:
            ai_reply = saved_reply
            source = "JSON"
        else:
            # 2. AI Generation with Retry Logic
            bot.send_chat_action(message.chat.id, 'typing')
            sys_prompt = BOT_MODES.get(config['mode'], BOT_MODES['friendly'])
            chat_history = config['history'] if config['memory'] else []
            
            ai_reply = "Sorry, error aa raha hai."
            source = "ERROR"
            
            # Retry loop (Max 3 attempts - Key Rotation)
            for attempt in range(3):
                try:
                    chat = model.start_chat(history=chat_history)
                    response = chat.send_message(f"System: {sys_prompt}\nUser: {user_text}")
                    ai_reply = response.text
                    source = "AI"
                    
                    # Agar success ho gaya, to loop se bahar niklo
                    break 
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️ Error on Key {current_key_index + 1}: {error_msg}")
                    
                    # Agar 429 (Quota) error hai, to key change karo
                    if "429" in error_msg or "quota" in error_msg.lower():
                        print("🚫 I am busy! Rotating Key...")
                        rotate_key()
                        time.sleep(1) # Thoda ruko switch karne ke baad
                        continue # Dobara try karo new key ke sath
                    else:
                        # Agar koi aur error hai (internet etc), to loop tod do
                        ai_reply = "Google API connect nahi ho raha."
                        break

            # 3. History & JSON Save
            if source == "AI":
                if config['memory']:
                    if len(config['history']) > 20: config['history'] = config['history'][2:]
                    config['history'].append({'role': 'user', 'parts': [user_text]})
                    config['history'].append({'role': 'model', 'parts': [ai_reply]})
                save_to_json(user_text, ai_reply)

        # 4. Sending Reply
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔊 Suno", callback_data="speak_msg"))
        
        try:
            bot.reply_to(message, ai_reply, parse_mode="Markdown", reply_markup=markup)
        except:
            bot.reply_to(message, ai_reply, reply_markup=markup)
            
        send_log_to_channel(message.from_user, source, user_text, ai_reply)

    except Exception as e:
        print(f"❌ Critical Error: {e}")

# --- RUN ---
def run_bot():
    print("🤖 Dev Bot Started with Key Rotation...")
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
        
