import json
import os
from datetime import datetime, timezone, timedelta
from config import (
    SPINS_FILE,
    MAX_SPINS_PER_PERIOD,
    LOSERS_COOLDOWN_FILE,
    WINNERS_COOLDOWN_FILE
)

# -------------------- Helpers JSON --------------------

def _load_json(filepath):
    """Load JSON file, create empty dict if not exists"""
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        with open(filepath, "w") as f:
            json.dump({}, f, indent=2)
        return {}
    with open(filepath, "r") as f:
        return json.load(f)

def _save_json(data, filepath):
    """Save data to JSON file"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# -------------------- Period calculation --------------------

def _get_period_start(period_hours):
    """
    Calculate the start of the current cooldown period based on period_hours.
    Works for any number of hours (no need to divide 24)
    """
    now = datetime.now(timezone.utc)
    total_seconds = period_hours * 3600
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    elapsed = (now - epoch).total_seconds()
    periods_passed = int(elapsed // total_seconds)
    period_start_seconds = periods_passed * total_seconds
    period_start = epoch + timedelta(seconds=period_start_seconds)
    return period_start

# -------------------- Cooldowns --------------------

def _check_winner_cooldown(user_id):
    """Check if user is in winners cooldown (24h)"""
    winners = _load_json(WINNERS_COOLDOWN_FILE)
    user_key = str(user_id)

    if user_key in winners:
        ts = winners[user_key]
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        last_win_time = datetime.fromisoformat(ts)
        cooldown_seconds = 24 * 3600  # 24h for winners
        elapsed_seconds = (datetime.now(timezone.utc) - last_win_time).total_seconds()
        remaining = cooldown_seconds - elapsed_seconds
        if remaining > 0:
            return True, remaining
        else:
            del winners[user_key]
            _save_json(winners, WINNERS_COOLDOWN_FILE)

    return False, 0

def _check_loser_cooldown(user_id):
    """Check if user is in losers cooldown (15h)"""
    losers = _load_json(LOSERS_COOLDOWN_FILE)
    user_key = str(user_id)

    if user_key in losers:
        ts = losers[user_key]
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        last_time = datetime.fromisoformat(ts)
        cooldown_seconds = 15 * 3600  # 15h for losers
        elapsed_seconds = (datetime.now(timezone.utc) - last_time).total_seconds()
        remaining = cooldown_seconds - elapsed_seconds
        if remaining > 0:
            return True, remaining
        else:
            del losers[user_key]
            _save_json(losers, LOSERS_COOLDOWN_FILE)

    return False, 0

# -------------------- Funciones principales --------------------

def can_spin(user_id):
    """
    Check if user can spin.
    Returns: (can_spin: bool, time_remaining: float, reason: str)
    """
    # Revisar cooldown de ganador
    in_winner_cooldown, winner_time = _check_winner_cooldown(user_id)
    if in_winner_cooldown:
        return False, winner_time, "winner_cooldown"

    # Revisar cooldown de perdedor
    in_loser_cooldown, loser_time = _check_loser_cooldown(user_id)
    if in_loser_cooldown:
        return False, loser_time, "max_spins"

    # Revisar spins del periodo actual
    spins = _load_json(SPINS_FILE)
    period_start = _get_period_start(15)  # 15h period para conteo de spins
    period_key = period_start.isoformat()
    user_key = str(user_id)

    user_data = spins.get(user_key, {})
    if user_data.get("period") != period_key:
        return True, 0, "ok"

    spin_count = user_data.get("count", 0)
    if spin_count >= MAX_SPINS_PER_PERIOD:
        losers = _load_json(LOSERS_COOLDOWN_FILE)
        losers[user_key] = datetime.now(timezone.utc).isoformat()
        _save_json(losers, LOSERS_COOLDOWN_FILE)
        return False, 15 * 3600, "max_spins"

    return True, 0, "ok"

def record_spin(user_id):
    """Record a user spin"""
    spins = _load_json(SPINS_FILE)
    period_start = _get_period_start(15)  # 15h period para conteo de spins
    period_key = period_start.isoformat()
    user_key = str(user_id)

    user_data = spins.get(user_key, {})
    if user_data.get("period") != period_key:
        user_data = {"period": period_key, "count": 0}

    user_data["count"] = user_data.get("count", 0) + 1
    spins[user_key] = user_data
    _save_json(spins, SPINS_FILE)

def record_winner(user_id):
    """Record a winner and put them in 24h cooldown"""
    winners = _load_json(WINNERS_COOLDOWN_FILE)
    losers = _load_json(LOSERS_COOLDOWN_FILE)
    user_key = str(user_id)

    winners[user_key] = datetime.now(timezone.utc).isoformat()
    _save_json(winners, WINNERS_COOLDOWN_FILE)

    if user_key in losers:
        del losers[user_key]
        _save_json(losers, LOSERS_COOLDOWN_FILE)

def spins_left(user_id):
    """Get remaining spins for current period"""
    spins = _load_json(SPINS_FILE)
    period_start = _get_period_start(15)
    period_key = period_start.isoformat()
    user_key = str(user_id)

    user_data = spins.get(user_key, {})
    if user_data.get("period") != period_key:
        return MAX_SPINS_PER_PERIOD

    return MAX_SPINS_PER_PERIOD - user_data.get("count", 0)
