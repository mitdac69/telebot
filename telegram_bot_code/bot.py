
import random
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = 'YOUR_BOT_TOKEN'  # <-- Thay bằng Token Bot của bạn
ADMIN_ID = 123456789  # <-- Thay bằng ID Telegram của bạn
GROUP_ID = -1001234567890  # <-- ID nhóm mà bạn muốn quản lý

CODES_FILE = 'codes.txt'
USERS_FILE = 'users.txt'
REFS_FILE = 'referrals.txt'

LOW_CODE_THRESHOLD = 50  # Cảnh báo admin khi còn ít code

def get_and_remove_code():
    if not os.path.exists(CODES_FILE):
        return None
    with open(CODES_FILE, 'r') as f:
        codes = [line.strip() for line in f if line.strip()]
    if codes:
        code = random.choice(codes)
        codes.remove(code)
        with open(CODES_FILE, 'w') as f:
            for c in codes:
                f.write(c + '\n')
        return code
    else:
        return None

def has_received_code(user_id):
    if not os.path.exists(USERS_FILE):
        return False
    with open(USERS_FILE, 'r') as f:
        users = [line.strip() for line in f]
    return str(user_id) in users

def save_user(user_id):
    with open(USERS_FILE, 'a') as f:
        f.write(str(user_id) + '\n')

def count_codes():
    if not os.path.exists(CODES_FILE):
        return 0
    with open(CODES_FILE, 'r') as f:
        codes = [line.strip() for line in f if line.strip()]
    return len(codes)

def count_users():
    if not os.path.exists(USERS_FILE):
        return 0
    with open(USERS_FILE, 'r') as f:
        users = [line.strip() for line in f if line.strip()]
    return len(users)

def save_referral(referrer_id, new_user_id):
    with open(REFS_FILE, 'a') as f:
        f.write(f"{referrer_id},{new_user_id}\n")

def count_referrals(user_id):
    if not os.path.exists(REFS_FILE):
        return 0
    with open(REFS_FILE, 'r') as f:
        lines = f.readlines()
        return sum(1 for line in lines if line.strip().split(',')[0] == str(user_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if args and args[0].startswith('referral_'):
        referrer_id = int(args[0].split('_')[1])
        if referrer_id != user_id:
            save_referral(referrer_id, user_id)
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 Bạn vừa mời thành công 1 người mới! ID: {user_id}"
                )
            except Exception as e:
                print(f"Lỗi gửi thông báo referral: {e}")

    keyboard = [
        [InlineKeyboardButton("👉 Tham Gia Kênh 1 👈", url="https://t.me/kenh1")],
        [InlineKeyboardButton("👉 Tham Gia Kênh 2 👈", url="https://t.me/kenh2")],
        [InlineKeyboardButton("✅ Nhận Code Miễn Phí", callback_data='check_code')],
        [InlineKeyboardButton("📈 Kiểm Tra Người Mời", callback_data='check_myref')],
    ]

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📂 Upload Code", callback_data='upload_code')])
        keyboard.append([InlineKeyboardButton("📊 Kiểm Tra Thống Kê", callback_data='check_stats')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    ref_link = f"https://t.me/{context.bot.username}?start=referral_{user_id}"

    message = (
        "⭐️ Chào mừng đến với Bot Phát Code Free ⭐️\n\n"
        "✅ Tham gia kênh, mời bạn bè để nhận code miễn phí!\n\n"
        f"🔗 Link mời bạn bè của bạn: {ref_link}\n"
        "🚀 Mời bạn bè để nhận thưởng hấp dẫn!"
    )

    await update.message.reply_text(
        text=message,
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'check_code':
        if has_received_code(user_id):
            await query.edit_message_text(text="⚠️ Bạn đã nhận code trước đó rồi! Mỗi người chỉ nhận 1 lần nhé!")
        else:
            refs_count = count_referrals(user_id)

            if refs_count < 10:
                await query.edit_message_text(
                    text=f"🚫 Bạn mới mời {refs_count}/10 người!\n👉 Mời đủ 10 người để nhận code nhé!"
                )
                return

            code = get_and_remove_code()
            if code:
                save_user(user_id)
                await query.edit_message_text(text=f"🎉 Chúc mừng! Đây là code của bạn: {code} 🎉")

                codes_left = count_codes()
                if codes_left < LOW_CODE_THRESHOLD:
                    try:
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"⚠️ Cảnh báo: Số lượng code còn {codes_left} code! Hãy cập nhật thêm."
                        )
                    except Exception as e:
                        print(f"Không thể gửi tin cho admin: {e}")
            else:
                await query.edit_message_text(text="❌ Hết code mất rồi, đợi admin cập nhật nhé!")

    elif query.data == 'upload_code':
        if user_id == ADMIN_ID:
            await query.edit_message_text(text="📥 Gửi file .txt chứa danh sách code mới nhé (mỗi dòng 1 code)!")
        else:
            await query.edit_message_text(text="❌ Bạn không có quyền upload code!")

    elif query.data == 'check_stats':
        if user_id == ADMIN_ID:
            codes_count = count_codes()
            users_count = count_users()
            await query.edit_message_text(
                text=f"📊 Thống Kê Hiện Tại:\n\n🔢 Code còn lại: {codes_count}\n👤 Người dùng đã nhận code: {users_count}"
            )
        else:
            await query.edit_message_text(text="❌ Bạn không có quyền kiểm tra thống kê!")

    elif query.data == 'check_myref':
        refs_count = count_referrals(user_id)
        await query.edit_message_text(
            text=f"🧑‍🤝‍🧑 Bạn đã mời được {refs_count} người bạn!\n🎯 Mời đủ 10 người để nhận code miễn phí nhé!"
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Bạn không có quyền upload file!")
        return

    document = update.message.document
    if document.mime_type != 'text/plain':
        await update.message.reply_text("❌ Vui lòng gửi file .txt thôi nhé!")
        return

    file = await document.get_file()
    downloaded_file = await file.download_to_drive()

    os.replace(downloaded_file, CODES_FILE)

    await update.message.reply_text("✅ Upload code thành công! Code mới đã được cập nhật.")

async def myref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    refs_count = count_referrals(user_id)
    await update.message.reply_text(
        text=f"🧑‍🤝‍🧑 Bạn đã mời được {refs_count} người bạn!\n🎯 Mời đủ 10 người để nhận thưởng nhé!"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myref", myref))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.run_polling()

if __name__ == "__main__":
    main()
