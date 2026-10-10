"""
MemoryVault AI — Dialogue State Manager
=========================================
Phase 4

Finite-state conversational engine.  Each call to ``process_turn``
advances the dialogue by one state and returns the bot's response,
quick-reply options, and (once enough context is gathered) the ML
prediction and A* search route.

States
------
GREETING     → Ask what item is missing
ITEM_COLLECTED → Ask 1st clarifying question (time of day)
CONTEXT_Q1   → Ask 2nd clarifying question (weather + fatigue + baggage)
CONTEXT_Q2   → (automatic) Run ML + A* and present results
RESULT       → Present results, ask for feedback
FEEDBACK     → Session complete

Business Rules
--------------
- BR-01: Maximum 2 clarifying diagnostic questions per session.
- BR-04: Cold-start fallback not yet implemented (deferred to future).
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from app.ml.location_predictor import predict as ml_predict
from app.search.astar_router import compute_search_route, get_layout
from app.db_local import get_custom_locations

# ---------------------------------------------------------------------------
# Item aliases / canonical mapping
# ---------------------------------------------------------------------------

_ITEM_ALIASES: dict[str, str] = {
    "key": "keys",
    "keys": "keys",
    "wallet": "wallet",
    "purse": "wallet",
    "phone": "phone",
    "mobile": "phone",
    "cell": "phone",
    "spectacles": "spectacles",
    "glasses": "spectacles",
    "specs": "spectacles",
    "earphones": "earphones",
    "headphones": "earphones",
    "earbuds": "earphones",
    "airpods": "earphones",
    "backpack": "backpack",
    "bag": "backpack",
    "water bottle": "water_bottle",
    "water_bottle": "water_bottle",
    "bottle": "water_bottle",
    "charger": "charger",
    "charging cable": "charger",
    "cable": "charger",
}

_VALID_ITEMS = list(set(_ITEM_ALIASES.values()))

_WEATHER_ALIASES: dict[str, str] = {
    "sunny": "sunny",
    "clear": "sunny",
    "hot": "sunny",
    "rainy": "rainy",
    "rain": "rainy",
    "raining": "rainy",
    "wet": "rainy",
    "cold": "cold",
    "chilly": "cold",
    "winter": "cold",
    "humid": "humid",
    "muggy": "humid",
    "sticky": "humid",
}

# ---------------------------------------------------------------------------
# Bot message templates
# ---------------------------------------------------------------------------

_GREETING_MESSAGES = [
    "👋 Hi there! I'm MemoryVault AI, your intelligent item-finding assistant.\n\nWhat item are you looking for?",
    "🧠 Hello! I'm here to help you find your misplaced belongings.\n\nTell me — what item can't you find?",
]

_ITEM_CONFIRM = "Got it — you're looking for your **{item}**. Let me ask a couple of quick questions to narrow things down."

_Q1_TIME = "🕐 **Question 1 of 2**: Around what time did you last have it?\n\nYou can type a time (e.g., \"7 PM\", \"14:30\") or pick one of these:"

_Q2_CONTEXT = "🌤️ **Question 2 of 2**: A few more details to help me predict the location:"

_RESULT_INTRO = (
    "🎯 Based on your habits and context, here are the most likely places your **{item}** could be.\n\n"
    "I've also generated an **optimised search route** -- check the Route Inspector panel on the right!"
)

_FEEDBACK_ASK = "\n\nDid you find it? Click **\"Found Here\"** on the route card where you located it, or let me know!"

_SESSION_COMPLETE = "✅ Great — glad you found your **{item}** in the **{location}**! I've logged this session to improve future predictions. 🧠"

_SESSION_NOT_FOUND = "😔 Sorry we couldn't locate it this time. I've noted this session. Try checking less common spots, and I'll keep learning from your feedback!"


# ---------------------------------------------------------------------------
# Time parsing helper
# ---------------------------------------------------------------------------


def _parse_time(text: str) -> float | None:
    """Attempt to parse a time string into a 0-23.99 float."""
    text = text.strip().lower().replace(".", ":")

    # Handle quick-reply chip values
    chip_map = {
        "morning (6-9 am)": 7.5,
        "midday (11-2 pm)": 12.5,
        "afternoon (2-5 pm)": 15.5,
        "evening (5-9 pm)": 19.0,
        "late night (9 pm+)": 22.0,
        "not sure": None,
    }
    for chip, val in chip_map.items():
        if chip in text:
            return val

    # Try "7 pm", "7pm", "19:30"  etc.
    import re

    # Pattern: HH:MM AM/PM or HH AM/PM
    m = re.match(r"(\d{1,2}):?(\d{2})?\s*(am|pm)?", text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = m.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return round(hour + minute / 60.0, 2)

    return None


# ---------------------------------------------------------------------------
# State processor
# ---------------------------------------------------------------------------


def process_turn(
    session_id: str,
    message: str,
    state: str,
    context: dict[str, Any],
    username: str | None = None,
) -> dict[str, Any]:
    """
    Process one dialogue turn and return the next state + bot response.

    Returns a dict matching the ``ChatResponse`` schema.
    """

    msg_lower = message.strip().lower()

    # ── GREETING ──────────────────────────────────────────────────────
    if state == "GREETING":
        return {
            "session_id": session_id,
            "bot_message": random.choice(_GREETING_MESSAGES),
            "quick_replies": ["Keys", "Wallet", "Phone", "Spectacles", "Earphones", "Backpack", "Water Bottle", "Charger"],
            "state": "ITEM_COLLECT",
            "context": context,
        }

    # ── ITEM_COLLECT ──────────────────────────────────────────────────
    if state == "ITEM_COLLECT":
        # Resolve item
        item = None
        for alias, canonical in _ITEM_ALIASES.items():
            if alias in msg_lower:
                item = canonical
                break

        if item is None:
            return {
                "session_id": session_id,
                "bot_message": "🤔 I didn't quite catch that. Could you tell me which item you've misplaced?\n\nChoose from the options below or type the item name:",
                "quick_replies": ["Keys", "Wallet", "Phone", "Spectacles", "Earphones", "Backpack", "Water Bottle", "Charger"],
                "state": "ITEM_COLLECT",
                "context": context,
            }

        context["item_type"] = item
        return {
            "session_id": session_id,
            "bot_message": _ITEM_CONFIRM.format(item=item.replace("_", " ")) + "\n\n" + _Q1_TIME,
            "quick_replies": ["Morning (6-9 AM)", "Midday (11-2 PM)", "Afternoon (2-5 PM)", "Evening (5-9 PM)", "Late Night (9 PM+)", "Not sure"],
            "state": "CONTEXT_Q1",
            "context": context,
        }

    # ── CONTEXT_Q1 (Time of day) ──────────────────────────────────────
    if state == "CONTEXT_Q1":
        parsed_time = _parse_time(msg_lower)
        if parsed_time is None:
            # Default to current hour if user is unsure
            parsed_time = round(datetime.now().hour + datetime.now().minute / 60.0, 2)

        context["time_of_day"] = parsed_time

        # Infer day of week from today
        context["day_of_week"] = datetime.now().weekday()

        return {
            "session_id": session_id,
            "bot_message": _Q2_CONTEXT,
            "quick_replies": [
                "Sunny & carrying bag & tired",
                "Sunny & no bag & fresh",
                "Rainy & carrying bag & tired",
                "Rainy & no bag & fresh",
                "Cold & carrying bag & moderate",
                "Humid & no bag & moderate",
            ],
            "state": "CONTEXT_Q2",
            "context": context,
        }

    # ── CONTEXT_Q2 (Weather + baggage + fatigue) ──────────────────────
    if state == "CONTEXT_Q2":
        # Parse weather
        weather = "sunny"  # default
        for alias, canonical in _WEATHER_ALIASES.items():
            if alias in msg_lower:
                weather = canonical
                break
        context["weather_condition"] = weather

        # Parse baggage
        if "bag" in msg_lower and "no bag" not in msg_lower:
            context["carrying_baggage"] = True
        elif "no bag" in msg_lower:
            context["carrying_baggage"] = False
        else:
            context["carrying_baggage"] = False

        # Parse fatigue
        if "tired" in msg_lower or "exhausted" in msg_lower:
            context["fatigue_level"] = 4
        elif "fresh" in msg_lower or "energetic" in msg_lower:
            context["fatigue_level"] = 1
        elif "moderate" in msg_lower:
            context["fatigue_level"] = 3
        else:
            context["fatigue_level"] = 3

        # ── Run ML Prediction ──
        features = {
            "item_type": context["item_type"],
            "time_of_day": context["time_of_day"],
            "day_of_week": context["day_of_week"],
            "weather_condition": context["weather_condition"],
            "carrying_baggage": context["carrying_baggage"],
            "fatigue_level": context["fatigue_level"],
        }

        prediction = ml_predict(features)

        # ── Run A* Search Route ──
        route = compute_search_route(
            start="entrance_hallway",
            probabilities=prediction["probabilities"],
        )
        layout = get_layout()

        # ── Fetch User Custom Saved Locations ──
        custom_user_rooms: list[str] = []
        if username:
            saved_locs = get_custom_locations(username, context["item_type"])
            custom_user_rooms = [loc["room"] for loc in saved_locs]

        item_display = context["item_type"].replace("_", " ")
        bot_message = _RESULT_INTRO.format(item=item_display)

        # Add top predictions to the message
        for i, (room, prob) in enumerate(list(prediction["probabilities"].items())[:3]):
            emoji = ["🥇", "🥈", "🥉"][i]
            bot_message += f"\n{emoji} **{room.replace('_', ' ').title()}** — {prob*100:.1f}% probability"

        if custom_user_rooms:
            custom_display = ", ".join(r.replace("_", " ").title() for r in custom_user_rooms)
            bot_message += f"\n\n🌸 **User Saved Habit Location(s)**: {custom_display} (Highlighted in **Pink** on your Route Map!)"

        bot_message += _FEEDBACK_ASK

        return {
            "session_id": session_id,
            "bot_message": bot_message,
            "quick_replies": ["Found it!", "Not found", "Search again"],
            "state": "RESULT",
            "context": context,
            "route_data": route,
            "layout": layout,
            "prediction": prediction,
            "custom_user_rooms": custom_user_rooms,
        }

    # ── RESULT (awaiting feedback) ────────────────────────────────────
    if state == "RESULT":
        if "found" in msg_lower and "not" not in msg_lower:
            return {
                "session_id": session_id,
                "bot_message": _SESSION_COMPLETE.format(
                    item=context.get("item_type", "item").replace("_", " "),
                    location="the suggested location",
                ),
                "quick_replies": ["Start new search"],
                "state": "FEEDBACK",
                "context": context,
            }
        elif "not found" in msg_lower or "no" in msg_lower:
            return {
                "session_id": session_id,
                "bot_message": _SESSION_NOT_FOUND,
                "quick_replies": ["Start new search"],
                "state": "FEEDBACK",
                "context": context,
            }
        elif "search again" in msg_lower or "new" in msg_lower:
            return process_turn(session_id, "", "GREETING", {})
        else:
            return {
                "session_id": session_id,
                "bot_message": "Let me know if you found the item, or if you'd like to start a new search.",
                "quick_replies": ["Found it!", "Not found", "Start new search"],
                "state": "RESULT",
                "context": context,
            }

    # ── FEEDBACK / restart ────────────────────────────────────────────
    if state == "FEEDBACK":
        return process_turn(session_id, "", "GREETING", {})

    # ── Fallback ──────────────────────────────────────────────────────
    return process_turn(session_id, "", "GREETING", {})
