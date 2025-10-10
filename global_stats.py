"""
Global statistics tracker for slot game
Tracks total spins and prizes awarded globally across all users
"""
import json
import os
from datetime import datetime, timedelta
from config import PRIZES

GLOBAL_STATS_FILE = 'global_stats.json'
RESET_PERIOD_HOURS = 48  # Reset stats every 24 hours

def _load_stats():
    """Load global stats from file"""
    if not os.path.exists(GLOBAL_STATS_FILE) or os.path.getsize(GLOBAL_STATS_FILE) == 0:
        initial_stats = {
            "last_reset": datetime.now().isoformat(),
            "total_spins": 0,
            "prizes_awarded": {p['name']: 0 for p in PRIZES}
        }
        _save_stats(initial_stats)
        return initial_stats
    
    with open(GLOBAL_STATS_FILE, "r") as f:
        stats = json.load(f)
        
    # Check if we need to reset (24h period passed)
    last_reset = datetime.fromisoformat(stats["last_reset"])
    if datetime.now() - last_reset > timedelta(hours=RESET_PERIOD_HOURS):
        stats = {
            "last_reset": datetime.now().isoformat(),
            "total_spins": 0,
            "prizes_awarded": {p['name']: 0 for p in PRIZES}
        }
        _save_stats(stats)
    
    return stats

def _save_stats(stats):
    """Save global stats to file"""
    with open(GLOBAL_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def record_spin():
    """Record a global spin"""
    stats = _load_stats()
    stats["total_spins"] += 1
    _save_stats(stats)

def record_prize(prize_name):
    """Record a prize being awarded"""
    stats = _load_stats()
    if prize_name in stats["prizes_awarded"]:
        stats["prizes_awarded"][prize_name] += 1
    else:
        stats["prizes_awarded"][prize_name] = 1
    _save_stats(stats)

def get_adjusted_probabilities():
    """
    Calculate adjusted probabilities based on global stats
    Returns dict of {prize_name: adjusted_probability}
    """
    stats = _load_stats()
    total_spins = stats["total_spins"]
    
    # If very few spins, use base probabilities
    if total_spins < 10:
        return {p['name']: p['probability'] for p in PRIZES}
    
    adjusted_probs = {}
    
    for prize in PRIZES:
        prize_name = prize['name']
        base_prob = prize['probability']
        awarded = stats["prizes_awarded"].get(prize_name, 0)
        
        # Expected number of prizes that should have been awarded by now
        expected = (base_prob / 100) * total_spins
        
        # If we've awarded more than expected, reduce probability
        # If we've awarded less than expected, increase probability
        if awarded > expected:
            # Reduce probability
            adjustment_factor = max(0.3, 1 - ((awarded - expected) / max(expected, 1)))
        else:
            # Increase probability
            adjustment_factor = min(2.0, 1 + ((expected - awarded) / max(expected, 1)))
        
        adjusted_prob = base_prob * adjustment_factor
        adjusted_probs[prize_name] = max(0.1, min(adjusted_prob, base_prob * 1.5))
    
    return adjusted_probs

def get_stats():
    """Get current global stats"""
    return _load_stats()
