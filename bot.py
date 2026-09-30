import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ChatMemberStatus
from yt_dlp import YoutubeDL

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "").strip()

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
USERS = set()
DOWNLOADS = 0

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Video yuklash", callback_data="help_dl")],
        [InlineKeyboardButton(text="ℹ️ Qo'llanma", callback_data="help")],
    ])

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📣 Reklama", callback_data="broadcast")],
    ])

async def subscribed(user_id: int) -> bool:
    if not FORCE_CHANNEL:
        return True
    try:
        m = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        return m.status in {
            ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        }
    except Exception:
        return False

def sub_kb():
    channel = FORCE_CHANNEL.lstrip("@")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{channel}")],
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
    ])

@dp.message(CommandStart())
async def start(message: Message):
    USERS.add(message.from_user.id)
    if not await subscribed(message.from_user.id):
        await message.answer(
            "🔐 <b>Botdan foydalanish uchun kanalga obuna bo'ling.</b>\n\n"
            "Obuna bo'lgach, <b>Tekshirish</b> tugmasini bosing.",
            reply_markup=sub_kb(), parse_mode="HTML"
        )
        return
    await message.answer(
        "🚀 <b>Downloader Bot</b>\n\n"
        "Instagram, TikTok, YouTube va boshqa qo'llab-quvvatlanadigan "
        "havolani yuboring.\n\n"
        "🔗 Havolani shu yerga tashlang.",
        reply_markup=main_kb(), parse_mode="HTML"
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    if await subscribed(call.from_user.id):
        await call.message.edit_text(
            "✅ Obuna tasdiqlandi!\n\n🔗 Endi video havolasini yuboring.",
            reply_markup=main_kb()
        )
    else:
        await call.answer("❌ Avval kanalga obuna bo'ling.", show_alert=True)

@dp.callback_query(F.data == "help")
async def help_cb(call: CallbackQuery):
    await call.message.edit_text(
        "📖 <b>Qo'llanma</b>\n\n"
        "1️⃣ Video havolasini yuboring.\n"
        "2️⃣ Bot havolani tekshiradi.\n"
        "3️⃣ Video tayyor bo'lgach sizga yuboradi.\n\n"
        "⚠️ Faqat yuklashga ruxsatingiz bor kontentdan foydalaning.",
        reply_markup=main_kb(), parse_mode="HTML"
    )

@dp.callback_query(F.data == "help_dl")
async def help_dl(call: CallbackQuery):
    await call.message.answer("🔗 Video havolasini yuboring.")

def download_media(url: str, uid: int):
    os.makedirs("downloads", exist_ok=True)
    opts = {
        "outtmpl": f"downloads/{uid}_%(title).80s.%(ext)s",
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 50 * 1024 * 1024,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        return path, info.get("title", "Video")

@dp.message(F.text)
async def link_handler(message: Message):
    global DOWNLOADS
    USERS.add(message.from_user.id)
    if not await subscribed(message.from_user.id):
        await message.answer("🔐 Avval kanalga obuna bo'ling.", reply_markup=sub_kb())
        return

    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("🔗 Iltimos, video havolasini yuboring.")
        return

    status = await message.answer("⏳ <b>Yuklanmoqda...</b>", parse_mode="HTML")
    try:
        path, title = await asyncio.to_thread(download_media, url, message.from_user.id)
        size = os.path.getsize(path)
        if size > 50 * 1024 * 1024:
            os.remove(path)
            await status.edit_text("❌ Fayl 50 MB dan katta.")
            return
        await status.edit_text("📤 <b>Tayyor!</b>\nYuborilmoqda...", parse_mode="HTML")
        with open(path, "rb") as f:
            await message.answer_video(f, caption=f"🎬 <b>{title}</b>", parse_mode="HTML")
        os.remove(path)
        DOWNLOADS += 1
    except Exception as e:
        await status.edit_text(
            "❌ <b>Yuklab bo'lmadi.</b>\n"
            "Havola noto'g'ri yoki platforma bu kontentni bermayapti.",
            parse_mode="HTML"
        )

@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "👑 <b>ADMIN PANEL</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=admin_kb(), parse_mode="HTML"
    )

@dp.callback_query(F.data == "stats")
async def stats(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    await call.message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{len(USERS)}</b>\n"
        f"📥 Yuklamalar: <b>{DOWNLOADS}</b>",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "broadcast")
async def broadcast(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    await call.message.answer(
        "📣 Reklama funksiyasi uchun foydalanuvchi bazasini doimiy saqlashni "
        "SQLite bilan yoqing. Ushbu starter versiyada xavfsiz demo ko'rsatilgan."
    )

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
