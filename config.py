import os

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
BOT_NAME = "Tribo Slot Game"

ADMIN_USERNAME = "@Ortegaa13"
ADMIN_ID = 6969934886

ALLOWED_CHAT_USERNAME = "cryptodigitaltribe"
ALLOWED_THREAD_ID = 70447
ALLOWED_CHAT_ID = -1002615207374
ALLOWED_TOPIC_URL = "https://t.me/cryptodigitaltribe/70447"

MAINTENANCE_MODE = False

RPC_URL = os.getenv('RPC_URL', '')
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS', '')
CHAIN_ID = int(os.getenv('CHAIN_ID', '4801'))

SLOT_SYMBOLS = {
    'cherry': '🍒',
    'lemon': '🍋',
    'orange': '🍊',
    'watermelon': '🍉',
    'grape': '🍇',
    'bell': '🔔',
    'star': '⭐',
    'seven': '7️⃣',
    'diamond': '💎',
    'coin': '🪙'
}

PRIZES = [
    {
        'name': '1 CDT',
        'symbol': '🪙',
        'probability': 5.0,
        'message': '🪙 Nice! Triple Coins - You won 1 CDT! 🪙',
        'token': '0x3Cb880f7ac84950c369e700deE2778d023b0C52d',
        'amount': 10**18
    },
    {
        'name': '10 TSN',
        'symbol': '💎',
        'probability': 3.0,
        'message': '💎 Great! Triple Diamonds - You won 10 TSN! 💎',
        'token': '0xa25D59bf1e9ac8395b77E7807fB27eA0a48d7c55',
        'amount': 10 * 10**18
    },
    {
        'name': '0.01 WLD',
        'symbol': '🍉',
        'probability': 0.5,
        'message': '🍉 Lucky! Triple Watermelons — You won 0.01 WLD! 🍉',
        'token': '0x2cFc85d8E48F8EAB294be644d9E25C3030863003',
        'amount': int(0.01 * 10**18)
    },
    {
        'name': '0.01 USDC',
        'symbol': '⭐',
        'probability': 0.5,
        'message': '⭐ Lucky! Triple Stars - You won 0.01 USDC! ⭐',
        'token': '0x79A02482A880bCE3F13e09Da970dC34db4CD24d1',
        'amount': int(0.01 * 10**6)
    },
    {
        'name': '100 CDT',
        'symbol': '7️⃣',
        'probability': 0.2,
        'message': '🎉 JACKPOT! Triple 7 - You won 100 CDT! 🎉',
        'token': '0x3Cb880f7ac84950c369e700deE2778d023b0C52d',
        'amount': 100 * 10**18
    }
]

MAX_SPINS_PER_PERIOD = 15

# --- Cooldowns separados ---
WINNER_COOLDOWN_HOURS = 24     # Ganador debe esperar 24h
LOSER_COOLDOWN_HOURS = 15      # Perder todos los spins: 15h

SPINS_FILE = 'user_spins.json'
LOSERS_COOLDOWN_FILE = 'losers_cooldown.json'
WINNERS_COOLDOWN_FILE = 'winners_cooldown.json'
USERS_FILE = 'users.json'

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenAddress", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"}
        ],
        "name": "claim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "tokenAddress", "type": "address"}
        ],
        "name": "getBalance",
        "outputs": [
            {"internalType": "uint256", "name": "balance", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
