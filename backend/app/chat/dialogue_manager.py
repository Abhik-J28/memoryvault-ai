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
from app.db_local import get_custom_locations, get_item_findings

# ---------------------------------------------------------------------------
# Item aliases / canonical mapping
# ---------------------------------------------------------------------------

_ITEM_ALIASES: dict[str, str] = {
    # keys
    "key": "keys",
    "keys": "keys",
    "house key": "keys",
    "house keys": "keys",
    "car key": "keys",
    # wallet
    "wallet": "wallet",
    "purse": "wallet",
    "billfold": "wallet",
    "money clip": "wallet",
    # spectacles
    "spectacles": "spectacles",
    "glasses": "spectacles",
    "specs": "spectacles",
    "eyeglasses": "spectacles",
    "sunglasses": "spectacles",
    # earphones
    "earphones": "earphones",
    "headphones": "earphones",
    "earbuds": "earphones",
    "airpods": "earphones",
    "earpods": "earphones",
    # backpack
    "backpack": "backpack",
    "bag": "backpack",
    "rucksack": "backpack",
    "satchel": "backpack",
    "knapsack": "backpack",
}

_VALID_ITEMS = list(set(_ITEM_ALIASES.values()))

# Dataset weather conditions: clear, rain, extreme_heat, snow
_WEATHER_ALIASES: dict[str, str] = {
    "clear": "clear",
    "sunny": "clear",
    "bright": "clear",
    "fair": "clear",
    "fine": "clear",
    "hot": "extreme_heat",
    "extreme heat": "extreme_heat",
    "extreme_heat": "extreme_heat",
    "scorching": "extreme_heat",
    "blazing": "extreme_heat",
    "heatwave": "extreme_heat",
    "very hot": "extreme_heat",
    "rain": "rain",
    "rainy": "rain",
    "raining": "rain",
    "wet": "rain",
    "drizzle": "rain",
    "shower": "rain",
    "stormy": "rain",
    "snow": "snow",
    "snowy": "snow",
    "snowing": "snow",
    "cold": "snow",
    "chilly": "snow",
    "freezing": "snow",
    "winter": "snow",
}

# ---------------------------------------------------------------------------
# Bot message templates
# ---------------------------------------------------------------------------

_GREETING_MESSAGES = [
    "👋 Hi there! I'm MemoryVault AI, your intelligent item-finding assistant.\n\nWhat item are you looking for?",
    "🧠 Hello! I'm here to help you find your misplaced belongings.\n\nTell me — what item can't you find?",
]

_ITEM_CONFIRM = "Got it — you're looking for your **{item}**. Let me ask a couple of quick questions to narrow things down."

_Q1_TIME = "🕐 **Question 1 of 2**: Around what time of day do you usually place this item?\n\nYou can type a time (e.g., \"7 PM\", \"14:30\") or pick one of these:"

_Q2_CONTEXT = "🌤️ **Question 2 of 2**: A couple more details about your situation:"

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


def _parse_time(text: str) -> tuple[float | None, bool]:
    """
    Attempt to parse a time string.
    Returns: (hour_val, is_valid_input)
      - If user said 'not sure' or similar, returns (None, True).
      - If text contains a valid time expression, returns (float, True).
      - If text is completely unrelated/gibberish, returns (None, False).
    """
    import re
    text = text.strip().lower().replace(".", ":")

    unsure_phrases = [
        "not sure", "dont know", "don't know", "unsure", "no idea",
        "skip", "any time", "cannot remember", "can't remember", "unknown"
    ]
    for phrase in unsure_phrases:
        if phrase in text:
            return None, True

    chip_map = {
        # Dataset-aligned time ranges (matching training data distribution)
        "early morning (0-6)": 3.0,
        "morning (6-9)": 7.5,
        "midday (9-14)": 11.5,
        "afternoon (14-18)": 16.0,
        "evening (18-21)": 19.5,
        "night (21-24)": 22.5,
        # Legacy chips for backward compatibility
        "morning (6-9 am)": 7.5,
        "morning": 7.5,
        "midday (11-2 pm)": 12.5,
        "midday": 11.5,
        "noon": 12.0,
        "afternoon (2-5 pm)": 15.5,
        "afternoon": 16.0,
        "evening (5-9 pm)": 19.0,
        "evening": 19.5,
        "late night (9 pm+)": 22.0,
        "late night": 22.0,
        "night": 22.5,
        "midnight": 0.0,
    }
    for chip, val in chip_map.items():
        if chip in text:
            return val, True

    # Try "7 pm", "7pm", "19:30", "14:00" etc.
    m = re.search(r"\b(\d{1,2}):?(\d{2})?\s*(am|pm)?\b", text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = m.group(3)
        if ampm or ":" in text or ("am" in text or "pm" in text):
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            if 0 <= hour <= 24 and 0 <= minute < 60:
                return round(hour + minute / 60.0, 2), True
        elif 0 <= hour <= 24 and ("hour" in text or "o'clock" in text or "oclock" in text):
            return round(float(hour), 2), True

    # Relative time expressions
    if any(k in text for k in ["hour ago", "hours ago", "recently", "just now", "earlier today", "today"]):
        return round(datetime.now().hour + datetime.now().minute / 60.0, 2), True

    return None, False


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
            "quick_replies": ["Keys", "Wallet", "Spectacles", "Earphones", "Backpack"],
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
                "quick_replies": ["Keys", "Wallet", "Spectacles", "Earphones", "Backpack"],
                "state": "ITEM_COLLECT",
                "context": context,
            }

        context["item_type"] = item

        # ── Proactive Reminder: fetch previous findings & habits for this item ──
        # Strictly isolated per authenticated user; guest users are explicitly excluded.
        user_key = (username or "").strip().lower()
        is_authenticated = bool(user_key and user_key != "guest")
        early_repeated_rooms: list[str] = []
        early_finding_counts: dict[str, int] = {}
        early_custom_rooms: list[str] = []
        reminder_text = ""

        if is_authenticated:
            try:
                past_findings = get_item_findings(user_key, item)
                for f in past_findings:
                    r = f["room"]
                    cnt = f.get("found_count", 1)
                    early_finding_counts[r] = cnt
                    if cnt >= 1:
                        early_repeated_rooms.append(r)
            except Exception:
                pass

            try:
                early_custom_rooms = [
                    loc["room"] for loc in get_custom_locations(user_key, item)
                ]
            except Exception:
                pass

        # Build proactive reminder strings
        if early_repeated_rooms:
            spots = ", ".join(
                f"**{r.replace('_', ' ').title()}** ({early_finding_counts[r]}x)"
                for r in early_repeated_rooms
            )
            reminder_text = (
                f"\n\n🔥 **Empirical Habit Reminder**: You previously found your "
                f"**{item.replace('_', ' ')}** at {spots}!\n"
                f"_(Highlighted in **Orange 🔥** on your Route Map below)_"
            )

        if early_custom_rooms:
            custom_spots = ", ".join(f"**{r.replace('_', ' ').title()}**" for r in early_custom_rooms)
            reminder_text += (
                f"\n\n🌸 **Saved Habit Spot**: {custom_spots}\n"
                f"_(Highlighted in **Pink 🌸** on your Route Map)_"
            )

        context["_repeated_finding_rooms"] = early_repeated_rooms
        context["_finding_counts"] = early_finding_counts
        context["_custom_user_rooms"] = early_custom_rooms

        home_layout = get_layout()

        return {
            "session_id": session_id,
            "bot_message": _ITEM_CONFIRM.format(item=item.replace("_", " ")) + reminder_text + "\n\n" + _Q1_TIME,
            "quick_replies": ["Early Morning (0-6)", "Morning (6-9)", "Midday (9-14)", "Afternoon (14-18)", "Evening (18-21)", "Night (21-24)", "Not sure"],
            "state": "CONTEXT_Q1",
            "context": context,
            "layout": home_layout,
            "custom_user_rooms": early_custom_rooms,
            "repeated_finding_rooms": early_repeated_rooms,
            "finding_counts": early_finding_counts,
        }


    # ── CONTEXT_Q1 (Time of day) ──────────────────────────────────────
    if state == "CONTEXT_Q1":
        curr_item_display = context.get("item_type", "item").replace("_", " ")

        # Guard: Check if user accidentally selected/typed an item name (e.g. 'Earphones', 'Backpack')
        for item_key in ["keys", "wallet", "phone", "spectacles", "earphones", "backpack", "charger", "water bottle"]:
            if item_key in msg_lower and len(msg_lower.split()) <= 2:
                return {
                    "session_id": session_id,
                    "bot_message": f"We're currently searching for your **{curr_item_display}**! ⏱️ Could you let me know approximately what time you last had it?\n\nYou can pick one of the options below or type 'Not sure':",
                    "quick_replies": ["Early Morning (0-6)", "Morning (6-9)", "Midday (9-14)", "Afternoon (14-18)", "Evening (18-21)", "Night (21-24)", "Not sure"],
                    "state": "CONTEXT_Q1",
                    "context": context,
                    "layout": get_layout(),
                    "repeated_finding_rooms": context.get("_repeated_finding_rooms", []),
                    "finding_counts": context.get("_finding_counts", {}),
                    "custom_user_rooms": context.get("_custom_user_rooms", []),
                }

        parsed_time, is_valid_time = _parse_time(msg_lower)
        if not is_valid_time:
            return {
                "session_id": session_id,
                "bot_message": f"🤔 I didn't recognize a time from that. Around what time did you last have your **{curr_item_display}**?\n\nYou can type a time (e.g. \"7 PM\", \"14:30\") or pick one of these options:",
                "quick_replies": ["Early Morning (0-6)", "Morning (6-9)", "Midday (9-14)", "Afternoon (14-18)", "Evening (18-21)", "Night (21-24)", "Not sure"],
                "state": "CONTEXT_Q1",
                "context": context,
                "layout": get_layout(),
                "repeated_finding_rooms": context.get("_repeated_finding_rooms", []),
                "finding_counts": context.get("_finding_counts", {}),
                "custom_user_rooms": context.get("_custom_user_rooms", []),
            }

        if parsed_time is None:
            # Explicitly unsure — default to current hour
            parsed_time = round(datetime.now().hour + datetime.now().minute / 60.0, 2)

        context["time_of_day"] = parsed_time
        context["day_of_week"] = datetime.now().weekday()

        return {
            "session_id": session_id,
            "bot_message": _Q2_CONTEXT,
            "quick_replies": [
                "Clear & with bag & very tired (5)",
                "Clear & no bag & fresh (1)",
                "Rain & with bag & tired (4)",
                "Rain & no bag & moderate (3)",
                "Extreme heat & with bag & very tired (5)",
                "Snow & no bag & moderate (2)",
                "Just predict for me",
            ],
            "state": "CONTEXT_Q2",
            "context": context,
            "layout": get_layout(),
            "repeated_finding_rooms": context.get("_repeated_finding_rooms", []),
            "finding_counts": context.get("_finding_counts", {}),
            "custom_user_rooms": context.get("_custom_user_rooms", []),
        }

    # ── CONTEXT_Q2 (Weather + baggage + fatigue) ──────────────────────
    if state == "CONTEXT_Q2":
        curr_item_display = context.get("item_type", "item").replace("_", " ")

        # Match dataset weather: clear, rain, extreme_heat, snow
        weather_signals = [
            "clear", "sunny", "bright", "fine", "fair",
            "rain", "rainy", "raining", "wet", "drizzle", "shower",
            "extreme heat", "extreme_heat", "hot", "scorching", "heatwave",
            "snow", "snowy", "cold", "chilly", "freezing", "winter"
        ]
        baggage_signals = ["bag", "backpack", "carrying", "luggage", "purse", "without bag", "no bag", "with bag"]
        # Fatigue 1-5 (1=fresh, 5=very tired)
        fatigue_signals = ["tired", "exhausted", "sleepy", "fresh", "energetic", "moderate", "normal", "active", "ok", "very tired"]
        skip_signals = ["not sure", "dont know", "don't know", "skip", "any", "predict", "just predict", "default"]

        has_weather = any(w in msg_lower for w in weather_signals)
        has_baggage = any(b in msg_lower for b in baggage_signals)
        has_fatigue = any(f in msg_lower for f in fatigue_signals)
        has_skip = any(s in msg_lower for s in skip_signals)

        # Guard: Check if user sent an isolated item name (e.g. 'Backpack', 'Keys')
        is_isolated_item = False
        for item_key in ["keys", "wallet", "phone", "spectacles", "earphones", "backpack", "charger", "water bottle"]:
            if item_key in msg_lower and not has_weather and not has_fatigue and len(msg_lower.split()) <= 2:
                is_isolated_item = True
                break

        if is_isolated_item or not (has_weather or has_baggage or has_fatigue or has_skip):
            return {
                "session_id": session_id,
                "bot_message": f"🤔 Please provide a bit more detail about your situation when you last had your **{curr_item_display}** (e.g., weather, whether you were carrying a bag, or how tired you were).\n\nYou can also pick one of the quick combinations below:",
                "quick_replies": [
                    "Clear & with bag & very tired (5)",
                    "Clear & no bag & fresh (1)",
                    "Rain & with bag & tired (4)",
                    "Rain & no bag & moderate (3)",
                    "Extreme heat & with bag & very tired (5)",
                    "Snow & no bag & moderate (2)",
                    "Just predict for me",
                ],
                "state": "CONTEXT_Q2",
                "context": context,
            }

        # Valid context signals present! Parse them:
        weather = "sunny"
        for alias, canonical in _WEATHER_ALIASES.items():
            if alias in msg_lower:
                weather = canonical
                break
        context["weather_condition"] = weather

        if "bag" in msg_lower and "no bag" not in msg_lower:
            context["carrying_baggage"] = True
        else:
            context["carrying_baggage"] = False

        if "tired" in msg_lower or "exhausted" in msg_lower or "sleepy" in msg_lower:
            context["fatigue_level"] = 4
        elif "fresh" in msg_lower or "energetic" in msg_lower:
            context["fatigue_level"] = 1
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

        # ── 1. Fetch User Habit Locations & Empirical Findings ──
        # Strictly isolated per authenticated user; guest users are explicitly excluded.
        user_key = (username or "").strip().lower()
        is_authenticated = bool(user_key and user_key != "guest")

        custom_user_rooms: list[str] = []
        repeated_finding_rooms: list[str] = []
        finding_counts: dict[str, int] = {}

        if is_authenticated:
            try:
                saved_locs = get_custom_locations(user_key, context["item_type"])
                custom_user_rooms = [loc["room"] for loc in saved_locs]
            except Exception:
                pass

            try:
                item_findings = get_item_findings(user_key, context["item_type"])
                for f in item_findings:
                    r = f["room"]
                    cnt = f.get("found_count", 1)
                    finding_counts[r] = cnt
                    if cnt >= 1:
                        repeated_finding_rooms.append(r)
            except Exception:
                pass

        # ── 2. Blend Empirical Habits into Prediction Probabilities ──
        if repeated_finding_rooms:
            total_findings = sum(finding_counts.values())
            # Adaptive weight: up to 50% based on user finding count
            alpha = min(0.50, 0.15 * total_findings)
            empirical_probs = {r: count / total_findings for r, count in finding_counts.items()}

            blended_probs = {}
            all_rooms = set(prediction["probabilities"].keys()) | set(empirical_probs.keys())
            for r in all_rooms:
                ml_p = prediction["probabilities"].get(r, 0.0)
                emp_p = empirical_probs.get(r, 0.0)
                blended_probs[r] = (1.0 - alpha) * ml_p + alpha * emp_p

            total_p = sum(blended_probs.values()) or 1.0
            blended_probs = {r: round(p / total_p, 4) for r, p in blended_probs.items()}
            blended_probs = dict(sorted(blended_probs.items(), key=lambda kv: kv[1], reverse=True))

            prediction["probabilities"] = blended_probs
            prediction["predicted_location"] = next(iter(blended_probs.keys()))
            prediction["top3"] = list(blended_probs.keys())[:3]

        # ── 3. Run A* Search Route with blended probabilities ──
        route = compute_search_route(
            start="entrance_hallway",
            probabilities=prediction["probabilities"],
        )
        layout = get_layout()

        context["_top_predicted_location"] = prediction["predicted_location"]
        context["_repeated_finding_rooms"] = repeated_finding_rooms
        context["_finding_counts"] = finding_counts
        context["_custom_user_rooms"] = custom_user_rooms

        item_display = context["item_type"].replace("_", " ")
        bot_message = _RESULT_INTRO.format(item=item_display)

        # Prominently suggest empirical habits alongside prediction
        if repeated_finding_rooms:
            top_spot = repeated_finding_rooms[0]
            top_count = finding_counts[top_spot]
            findings_desc = ", ".join(
                f"**{r.replace('_', ' ').title()}** ({finding_counts[r]}x)"
                for r in repeated_finding_rooms
            )
            bot_message += (
                f"\n\n🔥 **Empirical Habit Suggestion**: Based on your personal habit history, "
                f"you frequently find your **{item_display}** in {findings_desc}! "
                f"I have factored this into your route and highlighted it in **Orange 🔥** on your floor plan."
            )

        bot_message += "\n\n**Search Route Probability Breakdown**:"
        # Add top predictions to the message
        for i, (room, prob) in enumerate(list(prediction["probabilities"].items())[:3]):
            emoji = ["🥇", "🥈", "🥉"][i]
            is_habit = room in repeated_finding_rooms
            habit_tag = f" 🔥 *(Empirical Habit — {finding_counts[room]}x)*" if is_habit else ""
            bot_message += f"\n{emoji} **{room.replace('_', ' ').title()}** — {prob*100:.1f}% probability{habit_tag}"

        # Present manual saved habits in Pink
        if custom_user_rooms:
            custom_display = ", ".join(r.replace("_", " ").title() for r in custom_user_rooms)
            bot_message += f"\n\n🌸 **User Saved Habit Spot(s)**: {custom_display} (Highlighted in **Pink 🌸**)"

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
            "repeated_finding_rooms": repeated_finding_rooms,
            "finding_counts": finding_counts,
        }

    # ── RESULT (awaiting feedback) ────────────────────────────────────
    if state == "RESULT":
        user_key = (username or "").strip().lower()
        if "found" in msg_lower and "not" not in msg_lower:
            # If authenticated user says "Found it!", record finding
            if user_key and user_key != "guest":
                found_rm = None
                layout = get_layout()
                for rk in layout.get("rooms", {}).keys():
                    if rk.replace("_", " ") in msg_lower or rk in msg_lower:
                        found_rm = rk
                        break
                if not found_rm:
                    found_rm = context.get("_top_predicted_location") or context.get("predicted_location")
                if found_rm and context.get("item_type"):
                    try:
                        record_item_finding(user_key, context["item_type"], found_rm)
                    except Exception:
                        pass

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
