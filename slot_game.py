import random
from config import SLOT_SYMBOLS, PRIZES
from global_stats import get_adjusted_probabilities, record_spin, record_prize

def get_random_symbol(exclude_symbols=None):
    """Get a random slot symbol, optionally excluding certain symbols"""
    symbols = list(SLOT_SYMBOLS.values())
    if exclude_symbols:
        symbols = [s for s in symbols if s not in exclude_symbols]
    return random.choice(symbols)

def generate_slot_result():
    """
    Generate slot result with multiple prize tiers using GLOBAL probabilities
    Returns: (prize_data or None, symbols)
    """
    # Get globally adjusted probabilities
    adjusted_probs = get_adjusted_probabilities()

    # Generate random number
    rand = random.random() * 100
    cumulative_prob = 0

    # Check each prize with adjusted probabilities
    for prize in PRIZES:
        prize_name = prize['name']
        adjusted_prob = adjusted_probs.get(prize_name, prize['probability'])
        cumulative_prob += adjusted_prob

        if rand < cumulative_prob:
            symbol = prize['symbol']
            return prize, [symbol, symbol, symbol]

    # No prize - generate losing symbols
    prize_symbols = [p['symbol'] for p in PRIZES]
    symbols = [get_random_symbol(exclude_symbols=prize_symbols) for _ in range(3)]

    # Make sure we don't accidentally create a winning combination
    while symbols[0] == symbols[1] == symbols[2] and symbols[0] in prize_symbols:
        symbols = [get_random_symbol(exclude_symbols=prize_symbols) for _ in range(3)]

    return None, symbols

def spin_slot():
    """Execute a slot spin and return result"""
    # Record this spin in global stats
    record_spin()

    # Generate result with global probabilities
    prize, symbols = generate_slot_result()

    # If prize won, record it globally
    if prize:
        record_prize(prize['name'])

    return prize, symbols
