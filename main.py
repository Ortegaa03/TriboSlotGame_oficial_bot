import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from scheduler import start_scheduler
from config import (
    BOT_TOKEN, 
    BOT_NAME, 
    ALLOWED_CHAT_USERNAME, 
    ALLOWED_THREAD_ID, 
    ALLOWED_CHAT_ID, 
    ALLOWED_TOPIC_URL, 
    ADMIN_ID,
    ADMIN_USERNAME,
    MAINTENANCE_MODE
)
from slot_game import spin_slot
from cooldown import can_spin, record_spin, spins_left, record_winner
from messages import (
    format_result_message, 
    get_spin_animation, 
    get_cooldown_message, 
    get_start_message
)
from wallet_manager import register_user, set_user_wallet, get_user_wallet
from web3_payment import init_web3, validate_address, process_claim

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Short cooldown 5s ----------------
last_spin_times = {}
SHORT_COOLDOWN = 3

def can_spin_short(user_id):
    now = datetime.now()
    last = last_spin_times.get(user_id)
    if last is None:
        return True, 0
    elapsed = (now - last).total_seconds()
    if elapsed >= SHORT_COOLDOWN:
        return True, 0
    return False, SHORT_COOLDOWN - elapsed

def record_spin_short(user_id):
    last_spin_times[user_id] = datetime.now()

# ---------------- Topic check ----------------
def _is_allowed_topic(update: Update) -> bool:
    if update.callback_query:
        chat = update.callback_query.message.chat
        thread_id = getattr(update.callback_query.message, 'message_thread_id', None)
    else:
        chat = update.effective_chat
        thread_id = getattr(update.effective_message, 'message_thread_id', None) if update.effective_message else None

    if chat is None:
        return False
    if ALLOWED_CHAT_ID is not None:
        if chat.id != ALLOWED_CHAT_ID:
            return False
        if ALLOWED_THREAD_ID is not None:
            return thread_id == ALLOWED_THREAD_ID
        return True
    if ALLOWED_CHAT_USERNAME:
        chat_username = getattr(chat, 'username', None)
        if chat_username != ALLOWED_CHAT_USERNAME.lstrip('@'):
            return False
        if ALLOWED_THREAD_ID is not None:
            return thread_id == ALLOWED_THREAD_ID
        return True
    return False

last_winner_id = None

# ---------------- Claim memory ----------------
claimed_messages = {}  # message_id -> {"user_id": int, "prize_name": str}
pending_claims = {}  # user_id -> {"prize_name": str, "message_id": int}
failed_claims = {}  # user_id -> {"prize_name": str, "wallet": str, "error": str, "error_message_id": int}

# ---------------- Commands ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username or user.first_name)
    await update.message.reply_text(get_start_message(), parse_mode='Markdown')

async def prizes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import PRIZES
    prize_list = "\n".join([
        f"• {p['name']} - {p['symbol']}{p['symbol']}{p['symbol']} (Probability: {p['probability']}%)" 
        for p in PRIZES
    ])
    message = f"""
🎰 **Tribo Slot Game - Available Prizes** 🎰

{prize_list}

Use /slot to spin and try your luck! 🍀
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register or update wallet address"""
    global last_winner_id
    
    user = update.effective_user
    user_id = user.id
    
    # Check if this is a private message
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "⚠️ For security, please send your wallet address via private message to the bot.",
            parse_mode='HTML'
        )
        return
    
    # Check if wallet address was provided
    args = context.args
    if not args:
        current_wallet = get_user_wallet(user_id)
        if current_wallet:
            await update.message.reply_text(
                f"Your current wallet: `{current_wallet}`\n\n"
                f"To update it, use: /wallet <new_wallet_address>",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "Usage: /wallet <wallet_address>\n\n"
                "Example: /wallet 0x1234567890abcdef...",
                parse_mode='HTML'
            )
        return
    
    wallet = validate_address(args[0])
    if not wallet:
        await update.message.reply_text(
            "❌ Invalid wallet address. Please provide a valid Ethereum address.",
            parse_mode='HTML'
        )
        return
    
    # Register user and set wallet
    register_user(user_id, user.username or user.first_name)
    set_user_wallet(user_id, wallet)
    
    await update.message.reply_text(
        f"✅ Wallet registered successfully!\n\n"
        f"Address: `{wallet}`\n\n"
        f"You can now claim your prizes automatically via blockchain.",
        parse_mode='Markdown'
    )
    
    if user_id in pending_claims:
        claim_info = pending_claims[user_id]
        prize_name = claim_info['prize_name']
        
        await update.message.reply_text(
            f"🔄 Processing your pending claim for {prize_name}...",
            parse_mode='HTML'
        )
        
        # Process the claim
        success, message, tx_hash = await process_claim(
            prize_name,
            wallet,
            context.bot,
            user_id  # Send to private chat
        )
        
        username = user.first_name or user.username or "Player"
        user_link = f'<a href="tg://user?id={user_id}">{username}</a>'
        
        if success:
            success_msg = (
                f"✅ {user_link}, your claim was successful!\n\n"
                f"🎁 Prize: {prize_name}\n"
                f"👛 Sent to: `{wallet}`\n"
                f"🔗 TxHash: `{tx_hash}`\n\n"
                f"Check your wallet!"
            )
            await update.message.reply_text(success_msg, parse_mode='HTML')
            
            # Notify admin
            from config import ADMIN_ID
            admin_msg = (
                f"💰 Prize Claimed Successfully\n\n"
                f"Winner: {user_link}\n"
                f"Prize: {prize_name}\n"
                f"Wallet: `{wallet}`\n"
                f"TxHash: `{tx_hash}`"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='HTML'
            )
        else:
            from config import ADMIN_USERNAME
            
            keyboard = [
                [InlineKeyboardButton("🔄 Retry Claim", callback_data=f"retry_claim_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            error_msg = (
                f"❌ {user_link}, there was an error processing your claim:\n\n"
                f"{message}\n\n"
                f"Please contact {ADMIN_USERNAME} for assistance.\n\n"
                f"You can also try again by clicking the button below:"
            )
            error_message = await update.message.reply_text(error_msg, parse_mode='HTML', reply_markup=reply_markup)
            
            # Store failed claim with error message ID for later editing
            failed_claims[user_id] = {
                "prize_name": prize_name,
                "wallet": wallet,
                "error": message,
                "error_message_id": error_message.message_id
            }
            
            # Notify admin
            admin_msg = (
                f"⚠️ Claim Error (Pending Claim)\n\n"
                f"Winner: {user_link}\n"
                f"Prize: {prize_name}\n"
                f"Wallet: `{wallet}`\n"
                f"Error: {message}"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='HTML'
            )
        
        # Remove from pending claims
        del pending_claims[user_id]

# ---------------- Slot spin ----------------
async def slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        user = query.from_user
        message_func = query.message.reply_text
    else:
        user = update.effective_user
        message_func = update.message.reply_text

    user_id = user.id
    username = user.first_name or user.username or "Player"
    
    register_user(user_id, username)

    if MAINTENANCE_MODE:
        await message_func("🔧 Tribo Slot Game is under maintenance. Try later.", parse_mode='HTML')
        return

    # --- Cooldown largo (max spins o ganador) antes de girar ---
    can_play_now, time_remaining, reason = can_spin(user_id)
    if not can_play_now:
        is_winner = (reason == "winner_cooldown")
        await message_func(
            get_cooldown_message(time_remaining, username, user_id, is_winner),
            parse_mode='HTML'
        )
        return

    # --- Cooldown corto 5s ---
    can_spin_now, time_remaining_short = can_spin_short(user_id)
    if not can_spin_now:
        user_link = f'<a href="tg://user?id={user_id}">{username}</a>'
        await message_func(
            f"⏱️ Please wait {int(time_remaining_short+1)}s before spinning again, {user_link}",
            parse_mode='HTML'
        )
        return
    record_spin_short(user_id)

    # --- Topic permitido ---
    if not _is_allowed_topic(update):
        url = ALLOWED_TOPIC_URL or "the allowed Tribo topic"
        await message_func(f"⛔ Please use the correct topic for Tribo Slot Game:\n{url}")
        return

    # --- Spin animation ---
    sent_message = await message_func(get_spin_animation())
    await asyncio.sleep(1)

    # --- Spin resultado ---
    prize, symbols = spin_slot()
    result_message = format_result_message(prize, symbols, username, user_id)
    remaining = spins_left(user_id) if not prize else 0

    # --- Registrar spin y ganador ---
    record_spin(user_id)
    if prize:
        record_winner(user_id)
        global last_winner_id
        last_winner_id = user_id

    # --- Preparar teclado ---
    if prize:
        keyboard = [
            [InlineKeyboardButton("🎰 Spin", callback_data="reroll")],
            [InlineKeyboardButton("💰 Claim", callback_data=f"claim_{user_id}_{prize['name']}")]
        ]
    else:
        result_message += f"\n\n🎰 Spins Left: {remaining}"
        keyboard = [[InlineKeyboardButton("🎰 Spin Again", callback_data="reroll")]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_text(
        chat_id=sent_message.chat_id,
        message_id=sent_message.message_id,
        text=result_message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# ---------------- Button callbacks ----------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "reroll":
        await query.answer()
        await slot(update, context)
        return
    
    elif query.data.startswith("retry_claim_"):
        parts = query.data.split("_", 2)
        if len(parts) < 3:
            await query.answer("Invalid callback data", show_alert=True)
            return
            
        user_id = int(parts[2])
        clicker_id = query.from_user.id
        
        if clicker_id != user_id:
            await query.answer("⛔ This is not for you!", show_alert=True)
            return
        
        # Check if there's a failed claim to retry
        if user_id not in failed_claims:
            await query.answer("✅ This claim was already completed successfully!", show_alert=True)
            return
        
        await query.answer()
        
        claim_info = failed_claims[user_id]
        prize_name = claim_info['prize_name']
        wallet = claim_info['wallet']
        error_message_id = claim_info.get('error_message_id')
        
        user = query.from_user
        username = user.first_name or user.username or "Player"
        user_link = f'<a href="tg://user?id={user_id}">{username}</a>'
        
        loading_msg = await query.message.reply_text(
            f"🔄 Retrying claim for {prize_name}...\n"
            f"Please wait, this may take a few moments...",
            parse_mode='HTML'
        )
        
        # Process blockchain claim
        try:
            success, message, tx_hash = await process_claim(
                prize_name, 
                wallet, 
                context.bot, 
                query.message.chat_id
            )
        except Exception as e:
            import traceback
            success = False
            message = f"Unexpected error: {str(e)}"
            tx_hash = None
        
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=loading_msg.message_id
            )
        except:
            pass
        
        if success:
            del failed_claims[user_id]
            
            if error_message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=query.message.chat_id,
                        message_id=error_message_id,
                        text=(
                            f"❌ {user_link}, there was an error processing your claim.\n\n"
                            f"✅ <b>This claim was successfully retried!</b>"
                        ),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"[v0] Could not edit error message: {e}")
            
            success_msg = (
                f"✅ {user_link}, your claim was successful!\n\n"
                f"🎁 Prize: {prize_name}\n"
                f"👛 Sent to: <code>{wallet}</code>\n"
                f"🔗 TxHash: <code>{tx_hash}</code>\n\n"
                f"Check your wallet!"
            )
            await query.message.reply_text(success_msg, parse_mode='HTML')
            
            promo_keyboard = [
                [InlineKeyboardButton("🏦 Tribo Vault", url="https://worldcoin.org/mini-app?app_id=app_adf5744abe7aef9fe2a5841d4f1552d3&path=/?ref=Ortegaa")],
                [InlineKeyboardButton("🔄 Tribo Swap", url="https://world.org/mini-app?app_id=app_06c91355851c7bcacf352395ef93a51c")]
            ]
            promo_markup = InlineKeyboardMarkup(promo_keyboard)
            
            promo_msg = (
                f"💡 <b>Don't forget!</b>\n\n"
                f"🏦 Enter <b>Tribo Vault</b> every day to claim your WLD for holding CDT!\n\n"
                f"🛒 Use your TSN to buy more NFTs in <b>Tribo Swap & NFT</b>!"
            )
            await query.message.reply_text(promo_msg, parse_mode='HTML', reply_markup=promo_markup)
            
            # Notify admin
            admin_msg = (
                f"💰 Prize Claimed Successfully (Retry)\n\n"
                f"Winner: {user_link}\n"
                f"Prize: {prize_name}\n"
                f"Wallet: <code>{wallet}</code>\n"
                f"TxHash: <code>{tx_hash}</code>"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='HTML'
            )
        else:
            failed_claims[user_id]['error'] = message
            
            keyboard = [
                [InlineKeyboardButton("🔄 Retry Claim", callback_data=f"retry_claim_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            error_msg = (
                f"❌ {user_link}, there was an error processing your claim:\n\n"
                f"{message}\n\n"
                f"Please contact {ADMIN_USERNAME} for assistance.\n\n"
                f"You can also try again by clicking the button below:"
            )
            new_error_msg = await query.message.reply_text(error_msg, parse_mode='HTML', reply_markup=reply_markup)
            failed_claims[user_id]['error_message_id'] = new_error_msg.message_id
            
            admin_msg = (
                f"⚠️ Claim Error (Retry Failed)\n\n"
                f"Winner: {user_link}\n"
                f"Prize: {prize_name}\n"
                f"Wallet: <code>{wallet}</code>\n"
                f"Error: {message}"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='HTML'
            )
        
        return
    
    elif query.data.startswith("register_wallet_"):
        parts = query.data.split("_", 2)
        if len(parts) < 3:
            await query.answer("Invalid callback data", show_alert=True)
            return
            
        user_id = int(parts[2])
        clicker_id = query.from_user.id
        
        if clicker_id != user_id:
            await query.answer("⛔ This is not for you!", show_alert=True)
            return
        
        await query.answer()
        
        user = query.from_user
        user_id = user.id
        username = user.first_name or user.username or "Player"
        
        bot_username = (await context.bot.get_me()).username
        
        instructions = (
            f"👋 Hi {username}!\n\n"
            f"To claim your prize, you need to register your wallet address.\n\n"
            f"📝 Steps:\n"
            f"1. Click here to message me privately: @{bot_username}\n"
            f"2. Send me your wallet address using:\n"
            f"   <code>/wallet your_wallet_address</code>\n\n"
            f"Example:\n"
            f"<code>/wallet 0x1234567890abcdef1234567890abcdef12345678</code>\n\n"
            f"⚠️ Make sure to send it in PRIVATE MESSAGE for security!\n\n"
            f"After registering, your prize will be automatically sent to your wallet."
        )
        
        await query.message.reply_text(instructions, parse_mode='HTML')
        return

    elif query.data.startswith("claim_"):
        parts = query.data.split("_", 2)
        winner_id = int(parts[1])
        prize_name = parts[2] if len(parts) > 2 else "Unknown"
        
        clicker_id = query.from_user.id
        msg_id = query.message.message_id

        if msg_id in claimed_messages:
            await query.answer("⛔ This prize has already been claimed!", show_alert=True)
            return

        if clicker_id != winner_id:
            await query.answer("⛔ This is not your prize!", show_alert=True)
            return

        await query.answer()
        
        user = query.from_user
        user_id = user.id
        username = user.first_name or user.username or "Player"
        user_link = f'<a href="tg://user?id={user_id}">{username}</a>'
        
        wallet = get_user_wallet(user_id)
        
        if not wallet:
            pending_claims[user_id] = {
                "prize_name": prize_name,
                "message_id": msg_id
            }
            
            keyboard = [
                [InlineKeyboardButton("📝 How to Register Wallet", callback_data=f"register_wallet_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                f"⚠️ {user_link}, you need to register your wallet first!\n\n"
                f"🔐 For security, wallet registration must be done via PRIVATE MESSAGE.\n\n"
                f"Click the button below for instructions:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return
        
        print(f"[v0] Processing claim for user {user_id}, prize: {prize_name}, wallet: {wallet}")
        
        claimed_messages[msg_id] = {
            "user_id": user_id,
            "prize_name": prize_name
        }
        
        loading_msg = await query.message.reply_text(
            f"⏳ Processing your claim for {prize_name}...\n"
            f"Please wait, this may take a few moments...",
            parse_mode='HTML'
        )
        
        try:
            print(f"[v0] Calling process_claim with prize_name={prize_name}, wallet={wallet}")
            success, message, tx_hash = await process_claim(
                prize_name, 
                wallet, 
                context.bot, 
                query.message.chat_id
            )
            print(f"[v0] process_claim returned: success={success}, message={message}, tx_hash={tx_hash}")
        except Exception as e:
            print(f"[v0] Exception in process_claim: {str(e)}")
            import traceback
            print(f"[v0] Traceback: {traceback.format_exc()}")
            success = False
            message = f"Unexpected error: {str(e)}"
            tx_hash = None
        
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=loading_msg.message_id
            )
        except:
            pass
        
        if success:
            success_msg = (
                f"✅ {user_link}, your claim was successful!\n\n"
                f"🎁 Prize: {prize_name}\n"
                f"👛 Sent to: <code>{wallet}</code>\n"
                f"🔗 TxHash: <code>{tx_hash}</code>\n\n"
                f"Check your wallet!"
            )
            await query.message.reply_text(success_msg, parse_mode='HTML')
            
            promo_keyboard = [
                [InlineKeyboardButton("🏦 Tribo Vault", url="https://worldcoin.org/mini-app?app_id=app_adf5744abe7aef9fe2a5841d4f1552d3&path=/?ref=Ortegaa")],
                [InlineKeyboardButton("🔄 Tribo Swap", url="https://world.org/mini-app?app_id=app_06c91355851c7bcacf352395ef93a51c")]
            ]
            promo_markup = InlineKeyboardMarkup(promo_keyboard)
            
            promo_msg = (
                f"💡 <b>Don't forget!</b>\n\n"
                f"🏦 Enter <b>Tribo Vault</b> every day to claim your WLD for holding CDT!\n\n"
                f"🛒 Use your TSN to buy more NFTs in <b>Tribo Swap & NFT</b>!"
            )
            await query.message.reply_text(promo_msg, parse_mode='HTML', reply_markup=promo_markup)
            
            # Notify admin
            admin_msg = (
                f"💰 Prize Claimed Successfully\n\n"
                f"Winner: {user_link}\n"
                f"Prize: {prize_name}\n"
                f"Wallet: <code>{wallet}</code>\n"
                f"TxHash: <code>{tx_hash}</code>"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='HTML'
            )
        else:
            if msg_id in claimed_messages:
                del claimed_messages[msg_id]
            
            keyboard = [
                [InlineKeyboardButton("🔄 Retry Claim", callback_data=f"retry_claim_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            error_msg = (
                f"❌ {user_link}, there was an error processing your claim:\n\n"
                f"{message}\n\n"
                f"Please contact {ADMIN_USERNAME} for assistance.\n\n"
                f"You can also try again by clicking the button below:"
            )
            error_message = await query.message.reply_text(error_msg, parse_mode='HTML', reply_markup=reply_markup)
            
            failed_claims[user_id] = {
                "prize_name": prize_name,
                "wallet": wallet,
                "error": message,
                "error_message_id": error_message.message_id
            }
            
            admin_msg = (
                f"⚠️ Claim Error\n\n"
                f"Winner: {user_link}\n"
                f"Prize: {prize_name}\n"
                f"Wallet: <code>{wallet}</code>\n"
                f"Error: {message}"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='HTML'
            )

# ---------------- Admin IDs ----------------
async def ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return

    chat = update.effective_chat
    message = update.effective_message
    chat_id = getattr(chat, "id", None)
    chat_username = getattr(chat, "username", None)
    thread_id = getattr(message, 'message_thread_id', None) if message else None

    if chat_username and thread_id is not None:
        topic_url = f"https://t.me/{chat_username}/{thread_id}"
    elif chat_username:
        topic_url = f"https://t.me/{chat_username}"
    else:
        topic_url = "N/A (group has no username)"

    info = (
        f"🆔 chat.id: {chat_id}\n"
        f"🔤 chat.username: {chat_username}\n"
        f"🔢 message_thread_id: {thread_id}\n"
        f"🔗 Topic URL: {topic_url}"
    )
    await update.message.reply_text(info)

# ---------------- Scheduler ----------------
async def post_init(application):
    init_web3()
    asyncio.create_task(start_scheduler(application.bot))
    logger.info("📅 Scheduler initialized")

# ---------------- Main ----------------
def main():
    if not BOT_TOKEN:
        logger.error("ERROR: TELEGRAM_BOT_TOKEN is not configured!")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("slot", slot))
    application.add_handler(CommandHandler("prizes", prizes))
    application.add_handler(CommandHandler("wallet", wallet_cmd))
    application.add_handler(CommandHandler("ids", ids))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.post_init = post_init

    logger.info(f"🎰 {BOT_NAME} started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
