import random
from config import ADMIN_USERNAME, PRIZES

SPIN_ANIMATION = "🎰 Spinning the slot...\n\n[▓▓▓▓▓▓▓▓▓] 100%\nGood luck! 🍀"

LOSE_MESSAGES = [
    "❌ You didn't win this time.\nTry your luck again!",
    "❌ Almost there! Not quite a winning combination.\nSpin again!",
    "❌ No luck this round!\nGive it another shot!",
    "❌ Not the winning combination.\nKeep trying!",
    "❌ So close!\nTry again!"
]

def get_spin_animation():
    """Return spinning animation message"""
    return SPIN_ANIMATION

def get_random_lose_message():
    """Return a random losing message"""
    return random.choice(LOSE_MESSAGES)

def format_result_message(prize, symbols, username, user_id):
    """
    Format the result message for a spin
    Args:
        prize: Prize dict or None if lost
        symbols: List of 3 slot symbols
        username: User's username or first name
        user_id: User's Telegram ID
    """
    divider = "───────────────"
    slot_display = f"{symbols[0]} | {symbols[1]} | {symbols[2]}"
    base_message = f"{divider}\n🎰 Result:\n{slot_display}\n{divider}\n\n"

    user_link = f'<a href="tg://user?id={user_id}">{username}</a>'

    if prize:
        message = prize['message']
        footer = f"\n\n<blockquote>Spin by: {user_link}</blockquote>"
    else:
        message = get_random_lose_message()
        footer = f"\n\n<blockquote>Spin by: {user_link}</blockquote>"

    return base_message + message + footer

def get_cooldown_message(time_remaining, username, user_id, is_winner=False):
    """Format cooldown message"""
    minutes, seconds = divmod(int(time_remaining), 60)
    hours, minutes = divmod(minutes, 60)
    time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

    user_link = f'<a href="tg://user?id={user_id}">{username}</a>'

    if is_winner:
        return f"🎉 {user_link}, you already won a prize!\n\nYou can play again in: {time_str}"
    else:
        return f"⏳ {user_link}, you reached the max spins for today!\n\nYou can play again in: {time_str}"

def get_start_message():
    """Get the start message with all prizes"""
    prize_list = "\n".join([f"• {p['name']} - {p['symbol']}{p['symbol']}{p['symbol']}" for p in PRIZES])

    return f"""
🎰 **Welcome to Tribo Slot Game!** 🎰

Ready to test your luck? 🍀

**Available Prizes:**
{prize_list}

Use /slot to spin the reels!

Good luck! 🎯
"""
