import asyncio
import logging
import json
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PRIZES, ALLOWED_CHAT_ID, ALLOWED_THREAD_ID

logger = logging.getLogger(__name__)

RECURRING_MESSAGE_INTERVAL_HOURS = 3 # Send message every 3 hours
LAST_MESSAGE_FILE = 'last_recurring_message.json'

last_message_data = {"message_id": None}

def get_recurring_message():
    """Generate the recurring promotional message"""

    prize_list = "\n".join([
        f"• {p['name']} - {p['symbol']}{p['symbol']}{p['symbol']}"
        for p in PRIZES
    ])

    message = f"""🎁 <b><u>TRIBO SLOT GAME</u></b> 🎁

🎰 Spin the slot machine and test your luck! 

⚡️NEW VERSION! (BETA)⚡️

<blockquote>💡 How to play:

1️⃣ Type /slot in the group to spin the slot machine.

2️⃣ Match three identical symbols to win a prize!

🏆 Prizes:
{prize_list}</blockquote>

<blockquote>✨ Commands:
/slot → Spin the slot machine</blockquote>

Good luck! 🍀"""

    keyboard = [[InlineKeyboardButton("🎰 Spin Now!", callback_data="reroll")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return message, reply_markup

async def send_recurring_message(bot):
    """Send a recurring message to the configured chat"""
    global last_message_data

    try:
        if last_message_data["message_id"]:
            try:
                await bot.delete_message(
                    chat_id=ALLOWED_CHAT_ID,
                    message_id=last_message_data["message_id"]
                )
                logger.info(f"🗑️ Deleted previous recurring message (ID: {last_message_data['message_id']})")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete previous message: {e}")

        message, reply_markup = get_recurring_message()

        sent_message = await bot.send_photo(
            chat_id=ALLOWED_CHAT_ID,
            message_thread_id=ALLOWED_THREAD_ID,
            photo="https://files.catbox.moe/wacjw8.jpg",
            caption=message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        last_message_data["message_id"] = sent_message.message_id

        logger.info(f"✅ Recurring message sent successfully at {datetime.now()} (ID: {sent_message.message_id})")
    except Exception as e:
        logger.error(f"❌ Error sending recurring message: {e}")

async def start_scheduler(bot):
    """Start the recurring message scheduler"""
    interval_seconds = RECURRING_MESSAGE_INTERVAL_HOURS * 3600

    logger.info(f"📅 Scheduler started - sending messages every {RECURRING_MESSAGE_INTERVAL_HOURS} hour(s)")
 
    # 🔹 Enviar el primer mensaje inmediatamente al iniciar
    await send_recurring_message(bot)
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await send_recurring_message(bot)
        except Exception as e:
            logger.error(f"❌ Scheduler error: {e}")
            await asyncio.sleep(60)
