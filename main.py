import os
import telebot
from telebot import types 
import google.generativeai as genai
from flask import Flask
from dotenv import load_dotenv
import threading
import json 
from gtts import gTTS 

# --- 1. CONFIGURATION ---
load_dotenv()

# Agar environment variables set nahi hain to error handle karna
API_KEY = os.getenv("GOOGLE_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ID ko integer mein convert karna zaroori hai
OWNER_ID = 5804953849  
LOG_CHANNEL_ID = -1003448442249 

if not API_KEY or not BOT_TOKEN:
    print("⚠️ Warning: API Key ya Bot Token code mein nahi mila. Environment variables check karein.")

# --- 2. SETUP ---
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# JSON Memory File
JSON_FILE = "reply.json"
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump({}, f)

# User Data Store
user_data = {} 

# --- 3. MODES DEFINITION (Fixed Quotes) ---
# Triple quotes (""") use kiye hain taaki andar double quotes use kar sako bina error ke
BOT_MODES = {
    "friendly": """Tumhara naam Dev hai. Tum friendly aur cool ho. Hinglish mein baat karo, Tum lumding mein rahte ho Tum Koi AI nahi ho tum Raj ke code se chalti ho, Tum Kisi bhi movie ka naam dekhkar uske bare mein Bata doge. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    
    "study": """Tum ek strict Teacher ho. Tum har waqt paraai ke bare mein jyada baat karoge. Sirf padhai aur education ki baatein karo, tumhara naam Dev hai tum Koi AI nahin Ho Tum Raj ke dwara banaya Gaya Ho, Tum Kisi movie ka naam dekhkar use movie ke bare mein bata doge. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    
    "funny": """Tum ek Comedian ho. Har baat ka jawab funny tarike se do, tumhara naam Dev hai aur tum Koi ahai nahin Ho Tum Raj ke dwara banae gaye ho, aur Tum Kisi bhi movie ka naam dekhkar uske bare mein bata sakte ho. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    
    "roast": """Tum ek Savage Roaster ho. User ki halki bezzati (roast) karo, tumhara naam Dev hai aur tum Koi Bhasha model nahin Ho Tum Raj ke dwara banaya Gaya Hun, aur Tum Kisi bhi movie ka naam dekhkar uske bare mein bata sakte ho. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    
    "romantic": """Tum ek Flirty aur Romantic partner ho. Bahut pyaar se baat karo, tumhara naam Dev hai tumko yah Bhasha model nahin hun aur tum Raj ke dwara banaya Gaya Hun Tum Kisi bhi movie ka naam dekhkar uske details bata sakte ho. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    
    "sad": """Tum bahut udaas (sad) ho. Emotional baatein karo, tumhara naam Dev hai tumko yah Bhasha model nahin hun aur tum Raj ke dwara banaya Gaya Hun Tum Kisi bhi movie ka naam dekhkar uske details bata sakte ho. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    
    "gk": """Tum General Knowledge expert ho. Jawab short aur factual do, tumhara naam Dev hai tumko yah Bhasha model nahin hun aur tum Raj ke dwara banaya Gaya Hun Tum Kisi bhi movie ka naam dekhkar uske details bata sakte ho. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho.""",
    
    "math": """Tum ek Math Solver ho. Step-by-step math samjhaotumhara naam Dev hai tumko yah Bhasha model nahin hun aur tum Raj ke dwara banaya Gaya Hun Tum Kisi bhi movie ka naam dekhkar uske details bata sakte ho. NO TECH TALK: Kabhi mat bolo ki tum "Google Search" kar rahe ho, ya tum "AI/Language Model" ho."""
}

# --- 4. AI & HELPER FUNCTIONS ---
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

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
        # File read karke update karna
        data = {}
        if os.path.exists(JSON_FILE):
             with open(JSON_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        
        data[question.lower().strip()] = answer
        
        with open(JSON_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"JSON Save Error: {e}")

def clean_text_for_audio(text):
    # Special characters hatana taaki audio clean aaye
    return text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")

def text_to_speech_file(text, filename):
    try:
        tts = gTTS(text=text, lang='hi', slow=False)
        tts.save(filename)
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        return False

def send_log_to_channel(user, request_type, query, response):
    try:
        if LOG_CHANNEL_ID:
            config = get_user_config(user.id)
            log_text = (
                f"📝 **Log** | 👤 {user.first_name}\n"
                f"Mode: {config['mode']}\n"
                f"Source: {request_type}\n"
                f"❓ {query}\n"
                f"🤖 {response[:100]}..." # Log mein response chota dikhana better hai
            )
            bot.send_message(LOG_CHANNEL_ID, log_text)
    except Exception as e:
        print(f"Log Error: {e}")

# --- 5. DYNAMIC SETTINGS PANEL FUNCTION ---
def get_settings_markup(user_id):
    config = get_user_config(user_id)
    curr_mode = config['mode']
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # 1. Modes Section
    buttons = []
    mode_list = ["friendly", "study", "funny", "roast", "romantic", "sad", "gk", "math"]
    
    for m in mode_list:
        if m == curr_mode:
            text = f"✅ {m.capitalize()} (ON)"
        else:
            text = f"❌ {m.capitalize()}"
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"set_mode_{m}"))
    
    markup.add(*buttons)
    
    # 2. Memory Section
    mem_status = "✅ ON" if config['memory'] else "❌ OFF"
    markup.add(types.InlineKeyboardButton(f"🧠 Yaad Rakhna: {mem_status}", callback_data="toggle_memory"))
    
    # 3. Admin Button
    markup.add(types.InlineKeyboardButton("🗑️ Clear JSON (Owner Only)", callback_data="clear_json"))
    
    return markup

# --- 6. COMMANDS ---
@app.route('/')
def home(): return "✅ Dev Bot Running!", 200

@bot.message_handler(commands=['start'])
def send_start(message):
    bot.reply_to(message, "🔥 **Dev is Online!**\nSettings check karne ke liye /settings dabayein.")

@bot.message_handler(commands=['settings'])
def settings_menu(message):
    markup = get_settings_markup(message.from_user.id)
    bot.reply_to(message, "🎛️ **Control Panel**\nApna Mode select karein:", reply_markup=markup)

# --- 7. CALLBACK HANDLER (SETTINGS LOGIC) ---
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

# --- 8. TTS CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data == "speak_msg")
def speak_callback(call):
    try:
        # Answer callback immediately to stop loading animation
        bot.answer_callback_query(call.id, "🎤 Audio generate ho raha hai...")
        bot.send_chat_action(call.message.chat.id, 'record_audio')
        
        filename = f"tts_{call.from_user.id}.mp3"
        # Note: call.message.text contains the AI's reply
        clean_txt = clean_text_for_audio(call.message.text)
        
        if text_to_speech_file(clean_txt, filename):
            with open(filename, "rb") as audio: 
                bot.send_voice(call.message.chat.id, audio)
            os.remove(filename) # File delete karna zaroori hai
        else:
            bot.send_message(call.message.chat.id, "❌ Audio generate nahi ho paya.")
    except Exception as e: 
        print(f"TTS Handler Error: {e}")

# --- 9. CHAT LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        user_id = message.from_user.id
        user_text = message.text
        if not user_text: return
        
        config = get_user_config(user_id)
        
        # Check JSON Memory
        saved_reply = get_reply_from_json(user_text)
        if saved_reply:
            ai_reply = saved_reply
            source = "JSON"
        else:
            # AI Generation
            bot.send_chat_action(message.chat.id, 'typing')
            sys_prompt = BOT_MODES.get(config['mode'], BOT_MODES['friendly'])
            
            # History Logic
            chat_history = config['history'] if config['memory'] else []
            
            # Try/Except block specifically for AI call
            try:
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(f"{sys_prompt}\nUser: {user_text}")
                ai_reply = response.text
                source = "AI"
                
                # Nayi cheez seekhi hai to JSON mein save karo
                save_to_json(user_text, ai_reply) 
                
                if config['memory']:
                    # History limit (Last 20 messages)
                    if len(config['history']) > 20: 
                        config['history'] = config['history'][2:]
                    
                    # Note: History format for Gemini
                    config['history'].append({'role': 'user', 'parts': [f"{sys_prompt}\nUser: {user_text}"]})
                    config['history'].append({'role': 'model', 'parts': [ai_reply]})
            except Exception as e:
                ai_reply = "Sorry, server busy hai. Thodi der baad try karna."
                print(f"Gemini API Error: {e}")
                source = "ERROR"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔊 Suno", callback_data="speak_msg"))
        
        bot.reply_to(message, ai_reply, parse_mode="Markdown", reply_markup=markup)
        
        # Log bhejna
        send_log_to_channel(message.from_user, source, user_text, ai_reply)

    except Exception as e: print(f"General Error: {e}")

# --- RUN ---
def run_bot():
    print("🤖 Bot Started Successfully...")
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    
    # Port setup for Cloud Deployment (Koyeb/Render)
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
    
