# =================================================================
#               BOT TELEGRAM MODERATOR & ASISTEN AI
#             Versi Final v8.1 (Manual Topic Redirect)
# =================================================================
# Fitur:
# 1. Verifikasi Human (Captcha Tombol Emoji) saat join
# 2. Sistem Mute-on-Join dengan Unlock via Pilihan Airdrop
# 3. Sistem Verifikasi Partisipasi di dalam setiap Topik Airdrop
# 4. Perintah /getid untuk debugging
# 5. Filter Kata Kasar & Quick Replies
# 6. Penyimpanan data verifikasi di memori (reset saat restart)
# =================================================================

import os
import random
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from telegram import Update, Bot, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# Muat variabel dari file .env
load_dotenv()

# Ambil token dan key dari environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Konfigurasi Awal ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Konfigurasi API Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- DAFTAR KONFIGURASI BOT ---
KATA_FILTER = ["anjing", "babi", "bangsat", "kontol", "memek", "goblok", "tolol"]
TRIGGER_WORDS = ["bot,", "ai,", "#tanya", "#apakabar"]
QUICK_REPLY_GREETING = ['halo','hallo','hello']
QUICK_REPLY_REACTION = ['done', 'sudah']
REACTION_STICKER_ID = 'CAACAgEAAxkBAAE2GUVoRoU7LlAnvxHpl7b8it0V-ta8GwACywQAAvwrMEYAAZUQtKibugI2BA' 

# --- KONFIGURASI GRUP & VERIFIKASI (PENTING!) ---
GROUP_USERNAME_FOR_GETID = "username_grup_public" # Hanya untuk helper /getid

# LINK PENDAFTARAN AIRDROP (LINK KELUAR)
AIRDROP_REGISTRATION_LINKS = {
    'cryptox': "https://gleam.io/example-cryptox",
    'blockseed': "https://forms.gle/example-blockseed",
    'defichain': "https://discord.gg/example-defichain"
}

# MAP ID TOPIK KE NAMA AIRDROP (DAPATKAN DARI /getid)
TOPIC_ID_TO_NAME_MAP = {
    2: "cryptox", 
    3: "blockseed", 
    4: "defichain"
}

# LINK REDIRECT KE TOPIK (WAJIB DIISI MANUAL DARI HASIL /getid)
TOPIC_REDIRECT_LINKS = {
    'cryptox': "https://t.me/c/12345/2",    # GANTI DENGAN LINK LENGKAP KE TOPIK CRYPTOX
    'blockseed': "https://t.me/c/12345/3",  # GANTI DENGAN LINK LENGKAP KE TOPIK BLOCKSEED
    'defichain': "https://t.me/c/12345/4"   # GANTI DENGAN LINK LENGKAP KE TOPIK DEFICHAIN
}


# --- PENYIMPANAN DATA VERIFIKASI (IN-MEMORY) ---
VERIFIED_USERS = defaultdict(set)

# --- FUNGSI-FUNGSI UTAMA BOT ---
def get_time_based_greeting() -> str:
    tz = ZoneInfo("Asia/Makassar")
    now = datetime.now(tz)
    hour = now.hour
    if 4 <= hour < 11: return "Selamat Pagi"
    elif 11 <= hour < 15: return "Selamat Siang"
    elif 15 <= hour < 19: return "Selamat Sore"
    else: return "Selamat Malam"

async def get_gemini_response(user_prompt: str) -> str:
    if not GEMINI_API_KEY: return "Maaf, API Key Gemini belum diatur."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = await model.generate_content_async(user_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error saat menghubungi API Gemini: {e}")
        return "Maaf, terjadi kesalahan saat menghubungi AI Gemini."

# --- HANDLER PERINTAH ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Halo {user.mention_html()}! Saya adalah bot moderator & asisten AI di grup ini. Ketik /help untuk bantuan."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        "<b>Perintah & Fitur Bot:</b>\n\n"
        "▫️ /start - Memulai bot\n"
        "▫️ /help - Bantuan\n"
        "▫️ /getid - (Admin) Mendapatkan ID & Link Contoh.\n\n"
        "<b>Fitur Otomatis:</b>\n"
        "▪️ Filter Kata Kasar\n"
        "▪️ Sistem Verifikasi Berlapis untuk Airdrop"
    )

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat.id
    thread_id = update.message.message_thread_id
    
    response_text = (
        f"<b>🛠️ Detail ID & Link 🛠️</b>\n\n"
        f"Gunakan info ini untuk mengisi konfigurasi di file kode bot.\n\n"
        f"<b>Chat ID:</b> <code>{chat_id}</code>\n"
    )

    if thread_id:
        response_text += f"<b>Message Thread ID (ID Topik):</b> <code>{thread_id}</code>\n\n"
        response_text += "<b>👇 SALIN SALAH SATU LINK DI BAWAH INI 👇</b>\n\n"
        response_text += f"▪️ <b>Link untuk Grup Private:</b>\n<code>https://t.me/c/{str(chat_id).replace('-100', '')}/{thread_id}</code>\n\n"
        if GROUP_USERNAME_FOR_GETID != "username_grup_public":
            response_text += f"▪️ <b>Link untuk Grup Public:</b>\n<code>https://t.me/{GROUP_USERNAME_FOR_GETID}/{thread_id}</code>"
        else:
            response_text += f"▪️ <b>Link untuk Grup Public:</b> (Isi GROUP_USERNAME_FOR_GETID di kode untuk melihat contoh)"
    else:
        response_text += "Perintah ini dijalankan di luar topik (General)."

    await update.message.reply_html(response_text)

# --- ALUR VERIFIKASI ---

async def send_airdrop_selection_message(update: Update, context: ContextTypes.DEFAULT_TYPE, member: User) -> None:
    chat_id = update.effective_chat.id
    welcome_text = (f"<b>WELCOME TO AIRDROP HUNTER, {member.mention_html()}!</b>\n\n"
                    "🚨 <b>ALERT! FREE AIRDROPS WAITING FOR YOU!</b> 🚨\n"
                    "CHOOSE & REGISTER NOW BEFORE IT'S GONE!\n\n"
                    "🔒 <b>CHAT FEATURE LOCKED</b> 🔒\n"
                    "To unlock access to Airdrop Hunter's chat group, you MUST select one of the airdrops below and register immediately!\n---\n\n"
                    "<b><u>🔥 TODAY'S HOT AIRDROP PICKS 🔥</u></b>\n\n"
                    "💎 <b>[INSTANT] CryptoX</b>\n<i>50 FREE TOKENS + Whitelist Spot</i>\n"
                    "<u>Quick Requirements:</u>\n- Follow @CryptoX on Twitter\n- Retweet pinned post\n\n"
                    "💰 <b>[GUARANTEED] BlockSeed</b>\n<i>10 USDT + 100 TOKENS (Limited!)</i>\n"
                    "<u>Requirements:</u>\n- 5-min KYC Verification\n- Join Telegram Group\n\n"
                    "🖼️ <b>[EXCLUSIVE] DeFiChain NFT</b>\n<i>Limited Edition NFT (Worth Millions!)</i>\n"
                    "<u>Requirements:</u>\n- Join Discord Server\n- Fill 3-min form\n\n---\n"
                    "<b>WHAT ARE YOU WAITING FOR?</b>\n\n<b>HURRY! Slots Filling Fast!</b>\n"
                    "After completing registration, you'll get UNLIMITED ACCESS to our exclusive airdrop chat!\n"
                    "<i>Discuss strategies, get insider tips, and join private giveaways!</i>\n"
                    "<u>No selection = No access!</u>\n\n<b>CLICK NOW BEFORE IT'S TOO LATE!</b>")
    
    keyboard = [[InlineKeyboardButton("✅ Choose CryptoX Airdrop", callback_data=f'unlock:{member.id}:cryptox')],
                [InlineKeyboardButton("✅ Choose BlockSeed Airdrop", callback_data=f'unlock:{member.id}:blockseed')],
                [InlineKeyboardButton("✅ Choose DeFiChain NFT Airdrop", callback_data=f'unlock:{member.id}:defichain')]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    mute_permissions = ChatPermissions(can_send_messages=False)
    
    for member in update.message.new_chat_members:
        try:
            await context.bot.restrict_chat_member(chat_id=chat_id, user_id=member.id, permissions=mute_permissions)
            logger.info(f"User {member.first_name} ({member.id}) telah dibisukan & menunggu verifikasi human.")
            
            emojis = ["✈️", "🚀", "🛸", "🛰️", "🚁", "⛵️", "🚗", "🚜", "🚲"]
            correct_emoji = random.choice(emojis)
            random.shuffle(emojis)
            
            context.user_data['correct_emoji'] = correct_emoji
            
            prompt_text = (
                f"Hi {member.mention_html()}, one last check to prove you're human.\n\n"
                f"Please press the <b>{correct_emoji}</b> button to get access."
            )
            
            buttons = [InlineKeyboardButton(e, callback_data=f"hverify:{member.id}:{e}") for e in emojis]
            keyboard = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=chat_id, text=prompt_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
            )
            await update.message.delete()
        except Exception as e:
            logger.error(f"Gagal memproses anggota baru untuk verifikasi human: {e}")

async def human_verification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_who_clicked = query.from_user
    try:
        parts = query.data.split(':')
        user_id_to_verify = int(parts[1])
        chosen_emoji = parts[2]
    except (ValueError, IndexError):
        await query.answer("Invalid button data. Please try again.", show_alert=True)
        return

    if user_who_clicked.id != user_id_to_verify:
        await query.answer("This verification is not for you.", show_alert=True)
        return

    correct_emoji = context.user_data.get('correct_emoji')

    if correct_emoji and chosen_emoji == correct_emoji:
        logger.info(f"User {user_who_clicked.first_name} ({user_who_clicked.id}) berhasil verifikasi human.")
        await query.answer("✅ Verification successful!", show_alert=False)
        del context.user_data['correct_emoji']
        await send_airdrop_selection_message(update, context, user_who_clicked)
    else:
        logger.warning(f"User {user_who_clicked.first_name} ({user_who_clicked.id}) gagal verifikasi human.")
        await query.answer("❌ Wrong answer. Please try again.", show_alert=True)

async def airdrop_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_who_clicked = query.from_user
    try:
        parts = query.data.split(':')
        user_id_to_verify = int(parts[1])
        airdrop_choice = parts[2]
    except (IndexError, ValueError):
        await query.answer("Invalid button data. Please contact an admin.", show_alert=True)
        return

    if user_who_clicked.id != user_id_to_verify:
        await query.answer(text="This is not for you!", show_alert=True)
        return

    unmute_permissions = ChatPermissions(can_send_messages=True,can_send_audios=True,can_send_documents=True,can_send_photos=True,can_send_videos=True,can_send_video_notes=True,can_send_voice_notes=True,can_send_polls=True,can_send_other_messages=True,can_add_web_page_previews=True)
    
    try:
        await context.bot.restrict_chat_member(chat_id=query.message.chat_id,user_id=user_id_to_verify,permissions=unmute_permissions)
        logger.info(f"User {user_who_clicked.first_name} ({user_id_to_verify}) telah di-unmute.")
        
        # --- LOGIKA BARU: MENGGUNAKAN LINK YANG SUDAH ANDA MASUKKAN MANUAL ---
        chosen_link = TOPIC_REDIRECT_LINKS.get(airdrop_choice, "https://t.me") # Fallback jika key salah

        airdrop_names = {'cryptox': "CryptoX", 'blockseed': "BlockSeed", 'defichain': "DeFiChain NFT"}
        chosen_name = airdrop_names.get(airdrop_choice, "the selected airdrop")
        
        confirmation_text = (f"✅ <b>ACCESS GRANTED! Welcome, {user_who_clicked.mention_html()}!</b> ✅\n\n"
                             f"Thank you for choosing the <b>{chosen_name}</b> airdrop.\n\n"
                             "Your chat access is now <b>UNLOCKED</b>. You can start discussing strategies and getting tips from other hunters!\n\n"
                             f"➡️ <b><a href='{chosen_link}'>Click here to go to the {chosen_name} topic</a></b> to complete your registration.\n\nHappy hunting!")
        
        await query.edit_message_text(text=confirmation_text,parse_mode=ParseMode.HTML,reply_markup=None,disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Gagal unmute atau edit pesan untuk user {user_id_to_verify}: {e}")

async def topic_verification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_who_clicked = query.from_user
    try:
        parts = query.data.split(':')
        user_id_to_verify = int(parts[1])
        topic_name = parts[2]
    except (IndexError, ValueError):
        await query.answer("Invalid button data. Please contact an admin.", show_alert=True)
        return

    if user_who_clicked.id != user_id_to_verify:
        await query.answer(text="This button is for the new member.", show_alert=True)
        return

    VERIFIED_USERS[topic_name].add(user_id_to_verify)
    logger.info(f"User {user_who_clicked.first_name} ({user_id_to_verify}) telah diverifikasi untuk topik '{topic_name}'.")
    
    await query.edit_message_text(
        text=f"✅ <b>Verification Successful!</b>\n\nThank you, {user_who_clicked.mention_html()}. You can now participate in this topic.",
        parse_mode=ParseMode.HTML,reply_markup=None
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or (not update.message.text and not update.message.caption):
        return
    user = update.effective_user
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id
    message_text = update.message.text or update.message.caption or ""
    
    if update.message.chat.type in ['group', 'supergroup'] and thread_id is not None:
        topic_name = TOPIC_ID_TO_NAME_MAP.get(thread_id)
        if topic_name:
            try:
                member = await context.bot.get_chat_member(chat_id, user.id)
                if member.status in ['creator', 'administrator'] or user.id in VERIFIED_USERS[topic_name]:
                    pass
                else:
                    await update.message.delete()
                    reg_link = AIRDROP_REGISTRATION_LINKS.get(topic_name, "https://google.com")
                    prompt_text = (f"Hi {user.mention_html()}, one more step!\n\n"
                                 f"To participate in the <b>{topic_name.capitalize()}</b> discussion, you must register for the airdrop first. This is to ensure our community is filled with serious hunters!\n\n"
                                 f"After registering, click the button below to unlock chat access for this topic.")
                    keyboard = [[InlineKeyboardButton(f"➡️ Register for {topic_name.capitalize()} Airdrop", url=reg_link)],
                                [InlineKeyboardButton(f"✅ I Have Registered, Verify Me!", callback_data=f"tverify:{user.id}:{topic_name}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(chat_id=chat_id,message_thread_id=thread_id,text=prompt_text,parse_mode=ParseMode.HTML,reply_markup=reply_markup)
                    return
            except Exception as e:
                logger.error(f"Error pada pengecekan verifikasi topik: {e}")

    message_text_lower = message_text.lower().strip()
    
    for word in KATA_FILTER:
      if word in message_text_lower:
        try:
            await update.message.delete()
            await context.bot.send_message(chat_id, message_thread_id=thread_id, text=f"Pesan dari {user.mention_html()} dihapus karena melanggar aturan.", parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            logger.error(f"Gagal hapus pesan kasar: {e}")
            return
    
    if message_text_lower in QUICK_REPLY_GREETING:
        await update.message.reply_text(f"Hai {get_time_based_greeting_en()}, how are you today?")
        return
    
    if message_text_lower in QUICK_REPLY_REACTION:
        try:
            await update.message.reply_sticker(sticker=REACTION_STICKER_ID)
        except Exception as e:
            logger.error(f"Gagal kirim stiker: {e}. Mengirim fallback text.")
            await update.message.reply_text("Oke, beres! 👍")
        return
    
    bot_info: Bot = context.bot
    bot_username = bot_info.username
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == bot_info.id
    is_mentioning_bot = f"@{bot_username}" in message_text
    triggered_by_keyword = False
    prompt = message_text
    for trigger in TRIGGER_WORDS:
        if message_text_lower.startswith(trigger):
            triggered_by_keyword = True
            prompt = message_text[len(trigger):].strip()
            break
            
    if update.message.chat.type == "private" or is_reply_to_bot or is_mentioning_bot or triggered_by_keyword:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing', message_thread_id=thread_id)
        if is_mentioning_bot:
            prompt = prompt.replace(f"@{bot_username}", "").strip()
        if not prompt: prompt = "Sapa aku kembali dalam bahasa Indonesia dan tanyakan kabarku"
        ai_response = await get_gemini_response(prompt)
        final_response = f"{get_time_based_greeting()}, {user.first_name}! 👋\n\n{ai_response}"
        await update.message.reply_text(final_response)


# --- FUNGSI UTAMA UNTUK MENJALANKAN BOT ---
def main() -> None:
    if not TELEGRAM_BOT_TOKEN: print("KRITIS: Token Telegram tidak ditemukan!"); return
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("getid", get_id_command))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    application.add_handler(CallbackQueryHandler(human_verification_handler, pattern=r'^hverify:'))
    application.add_handler(CallbackQueryHandler(airdrop_button_handler, pattern=r'^unlock:'))
    application.add_handler(CallbackQueryHandler(topic_verification_handler, pattern=r'^tverify:'))
    
    application.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    
    print("Bot versi final v8.1 (Manual Topic Redirect) sedang berjalan... Tekan Ctrl+C untuk berhenti.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()