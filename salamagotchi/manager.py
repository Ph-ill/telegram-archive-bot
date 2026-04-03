"""
Salamagotchi manager - shared chat pet state, rollover logic, and UI rendering.
"""

from __future__ import annotations

import html
import json
import logging
import os
import threading
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytz

logger = logging.getLogger(__name__)


REQUIREMENTS = {
    "feed": 2,
    "scoop": 2,
    "play": 1,
    "wash": 1,
}

NEGLECT_FIELDS = {
    "feed": "missed_feed_days",
    "scoop": "missed_scoop_days",
    "play": "missed_play_days",
    "wash": "missed_wash_days",
}

DEATH_REASONS = {
    "feed": "starvation",
    "scoop": "filth",
    "play": "loneliness",
    "wash": "grime",
}

ACTION_LABELS = {
    "feed": "feeding",
    "scoop": "scoop",
    "play": "play session",
    "wash": "wash",
}

STAGES: List[Dict[str, Any]] = [
    {
        "name": "Eggling",
        "min_age": 0,
        "max_age": 2,
        "art": r"""
        .-'''-.
      .'  _ _  '.
     /   EYE     \
    |      ^      |
    |     MTH     |
    |             |
     \           /
      '.       .'
        '.___.'
""".strip("\n"),
    },
    {
        "name": "Baby",
        "min_age": 3,
        "max_age": 6,
        "art": r"""
        .-''''-.
      .'  __ __ '.
     /    EYE     \
    |      ^^      |
    |     MTH      |
    |              |
     \            /
      '.        .'
        '------'
""".strip("\n"),
    },
    {
        "name": "Child",
        "min_age": 7,
        "max_age": 13,
        "art": r"""
         .-''''-.
       .'  __ __ '.
      /    EYE     \
     |      ^^      |
     |     /  \     |
     |     MTH      |
      \            /
       '.        .'
         '------'
""".strip("\n"),
    },
    {
        "name": "Teen",
        "min_age": 14,
        "max_age": 29,
        "art": r"""
         .-''''''-.
       .'  __  __  '.
      /     EYE      \
     |       --       |
     |      /__\      |
     |      MTH       |
      \              /
       '.          .'
         '--------'
""".strip("\n"),
    },
    {
        "name": "Adult",
        "min_age": 30,
        "max_age": 59,
        "art": r"""
          .-''''''-.
        .'  _    _  '.
       /      EYE     \
      |       --       |
      |      |  |      |
      |      MTH       |
      |                |
       \              /
        '.          .'
          '--------'
""".strip("\n"),
    },
    {
        "name": "Elder",
        "min_age": 60,
        "max_age": 999999,
        "art": r"""
           .-''''''-.
         .'  _    _  '.
        /      EYE     \
       |       ..       |
       |      |__|      |
       |      MTH       |
       |       __       |
        \              /
         '.          .'
           '--------'
""".strip("\n"),
    },
]


class SalamagotchiManager:
    """Persistent shared-chat Salamagotchi manager."""

    def __init__(self, data_dir: str, timezone_name: str = "America/Chicago"):
        self.data_dir = data_dir
        self.data_file_path = os.path.join(data_dir, "salamagotchi.json")
        self.lock = threading.Lock()
        self.timezone_name = timezone_name
        self.timezone = pytz.timezone(timezone_name)

        os.makedirs(data_dir, exist_ok=True)
        if not os.path.exists(self.data_file_path):
            self._write_data({})

        logger.info(
            "SalamagotchiManager initialized with data file %s and timezone %s",
            self.data_file_path,
            self.timezone_name,
        )

    def _read_data(self) -> Dict[str, Any]:
        try:
            with open(self.data_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            logger.warning("Error reading salamagotchi data file: %s", e)
            return {}

    def _write_data(self, data: Dict[str, Any]) -> None:
        temp_file = f"{self.data_file_path}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, self.data_file_path)
        except (IOError, OSError) as e:
            logger.error("Error writing salamagotchi data file: %s", e)
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            raise

    def _default_state(self, name: str, user_display: str, now: datetime) -> Dict[str, Any]:
        now_iso = now.isoformat()
        local_date = self._local_date_str(now)
        return {
            "alive": True,
            "name": name,
            "spawned_at": now_iso,
            "age_days": 0,
            "last_rollover_date": local_date,
            "feed_count": 0,
            "scoop_count": 0,
            "play_count": 0,
            "wash_count": 0,
            "missed_feed_days": 0,
            "missed_scoop_days": 0,
            "missed_play_days": 0,
            "missed_wash_days": 0,
            "death_reason": None,
            "died_at": None,
            "spawned_by": user_display,
            "last_interaction_by": user_display,
        }

    def _local_date_str(self, now: Optional[datetime] = None) -> str:
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)
        return now.astimezone(self.timezone).date().isoformat()

    def _get_stage(self, age_days: int) -> Dict[str, Any]:
        for stage in STAGES:
            if stage["min_age"] <= age_days <= stage["max_age"]:
                return stage
        return STAGES[-1]

    def _join_phrases(self, phrases: List[str]) -> str:
        if not phrases:
            return ""
        if len(phrases) == 1:
            return phrases[0]
        if len(phrases) == 2:
            return f"{phrases[0]} and {phrases[1]}"
        return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"

    def _build_need_phrase(self, pet: Dict[str, Any]) -> Optional[str]:
        name = pet["name"]
        phrases: List[str] = []

        feed_remaining = max(0, REQUIREMENTS["feed"] - pet.get("feed_count", 0))
        if feed_remaining == 2:
            phrases.append("ravenous")
        elif feed_remaining == 1:
            phrases.append("hungry")

        scoop_remaining = max(0, REQUIREMENTS["scoop"] - pet.get("scoop_count", 0))
        if scoop_remaining == 2:
            phrases.append("absolutely filthy")
        elif scoop_remaining == 1:
            phrases.append("messy")

        if pet.get("play_count", 0) < REQUIREMENTS["play"]:
            phrases.append("restless")

        if pet.get("wash_count", 0) < REQUIREMENTS["wash"]:
            phrases.append("grimy")

        if not phrases:
            return f"{name} is all set for today and seems very pleased with the chat."

        return f"{name} is feeling {self._join_phrases(phrases)} today."

    def _render_stage_art(self, pet: Dict[str, Any], stage: Dict[str, Any]) -> str:
        feed_remaining = max(0, REQUIREMENTS["feed"] - pet.get("feed_count", 0))
        scoop_remaining = max(0, REQUIREMENTS["scoop"] - pet.get("scoop_count", 0))
        play_remaining = max(0, REQUIREMENTS["play"] - pet.get("play_count", 0))
        wash_remaining = max(0, REQUIREMENTS["wash"] - pet.get("wash_count", 0))
        unmet_needs = sum(
            1
            for remaining in [feed_remaining, scoop_remaining, play_remaining, wash_remaining]
            if remaining > 0
        )

        if not pet.get("alive", True):
            eyes = "x x"
            mouth = "___"
        elif unmet_needs >= 3:
            eyes = "; ;"
            mouth = "___"
        elif unmet_needs == 2:
            eyes = "- -"
            mouth = "_._"
        elif unmet_needs == 1:
            eyes = "o o"
            mouth = "._."
        else:
            eyes = "^ ^"
            mouth = "\\_/"

        lines = (
            stage["art"]
            .replace("EYE", eyes)
            .replace("MTH", mouth)
            .splitlines()
        )

        poop_pile = " /~\\ "
        bottom_left = poop_pile if scoop_remaining >= 1 else "      "
        bottom_right = poop_pile if scoop_remaining >= 2 else "      "

        decorated = []
        for idx, line in enumerate(lines):
            left = "      "
            right = "      "
            if idx == len(lines) - 1:
                left, right = bottom_left, bottom_right
            decorated.append(f"{left} {line:<22} {right}".rstrip())

        return "\n".join(decorated)

    def _build_hint_lines(self, pet: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        name = pet["name"]
        lines.append(self._build_need_phrase(pet))

        warning_phrases: List[str] = []
        for action, field in NEGLECT_FIELDS.items():
            if pet.get(field, 0) == 1:
                if action == "feed":
                    warning_phrases.append("feeding")
                elif action == "scoop":
                    warning_phrases.append("poop scooping")
                elif action == "play":
                    warning_phrases.append("playtime")
                elif action == "wash":
                    warning_phrases.append("washing")

        if warning_phrases:
            lines.append(
                f"Warning: {self._join_phrases(warning_phrases).capitalize()} was missed yesterday, so missing it again today will kill {name}."
            )

        return lines

    def _format_status_text(self, pet: Dict[str, Any]) -> str:
        stage = self._get_stage(pet.get("age_days", 0))
        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        status = "Alive" if pet.get("alive") else "Dead"

        lines = [
            f"🦎 <b>{safe_name}</b>",
            f"<b>Status:</b> {status}",
            f"<b>Age:</b> {pet.get('age_days', 0)} day{'s' if pet.get('age_days', 0) != 1 else ''}",
            f"<b>Stage:</b> {html.escape(stage['name'])}",
            "",
            f"<pre>{html.escape(self._render_stage_art(pet, stage))}</pre>",
        ]

        hint_lines = self._build_hint_lines(pet) if pet.get("alive") else [
            f"{safe_name} died of {html.escape(pet.get('death_reason', 'unknown causes'))}.",
            "A new Salamagotchi can be spawned in this chat.",
        ]
        lines.extend(html.escape(line) for line in hint_lines)

        return "\n".join(lines)

    def _apply_rollover(self, pet: Dict[str, Any], current_date: str) -> Tuple[Dict[str, Any], bool]:
        pet = deepcopy(pet)
        previous_stage = self._get_stage(pet.get("age_days", 0))["name"]

        for action, required in REQUIREMENTS.items():
            count = pet.get(f"{action}_count", 0)
            miss_field = NEGLECT_FIELDS[action]
            if count < required:
                pet[miss_field] = pet.get(miss_field, 0) + 1
            else:
                pet[miss_field] = 0

        death_reason = None
        for action, miss_field in NEGLECT_FIELDS.items():
            if pet.get(miss_field, 0) >= 2:
                death_reason = DEATH_REASONS[action]
                break

        if death_reason:
            pet["alive"] = False
            pet["death_reason"] = death_reason
            pet["died_at"] = datetime.now(pytz.UTC).isoformat()
            pet["last_rollover_date"] = current_date
            for action in REQUIREMENTS:
                pet[f"{action}_count"] = 0
            return pet, False

        pet["age_days"] = pet.get("age_days", 0) + 1
        pet["last_rollover_date"] = current_date
        for action in REQUIREMENTS:
            pet[f"{action}_count"] = 0

        new_stage = self._get_stage(pet.get("age_days", 0))["name"]
        return pet, new_stage != previous_stage

    def process_daily_rollovers(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now(pytz.UTC)
        current_date = self._local_date_str(now)
        events: List[Dict[str, Any]] = []

        with self.lock:
            data = self._read_data()
            changed = False

            for chat_id, pet in data.items():
                if not pet.get("alive", False):
                    continue
                if pet.get("last_rollover_date") == current_date:
                    continue

                updated_pet = deepcopy(pet)
                stage_changed = False
                last_rollover = datetime.strptime(
                    pet.get("last_rollover_date", current_date), "%Y-%m-%d"
                ).date()
                target_date = datetime.strptime(current_date, "%Y-%m-%d").date()

                while last_rollover < target_date and updated_pet.get("alive", False):
                    rollover_date = (last_rollover + timedelta(days=1)).isoformat()
                    updated_pet, rollover_stage_changed = self._apply_rollover(updated_pet, rollover_date)
                    stage_changed = stage_changed or rollover_stage_changed
                    last_rollover += timedelta(days=1)

                data[chat_id] = updated_pet
                changed = True

                event = {
                    "chat_id": int(chat_id),
                    "alive": updated_pet.get("alive", False),
                    "name": updated_pet.get("name", "Salamagotchi"),
                    "age_days": updated_pet.get("age_days", 0),
                    "stage": self._get_stage(updated_pet.get("age_days", 0))["name"],
                    "stage_changed": stage_changed,
                    "death_reason": updated_pet.get("death_reason"),
                }
                events.append(event)

            if changed:
                self._write_data(data)

        return events

    def spawn(self, chat_id: int, name: str, user_display: str, now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or datetime.now(pytz.UTC)
        cleaned_name = " ".join(name.split()).strip()
        if not cleaned_name:
            return {"success": False, "message": "Please provide a name for the Salamagotchi."}
        if len(cleaned_name) > 30:
            return {"success": False, "message": "Salamagotchi names must be 30 characters or fewer."}

        with self.lock:
            data = self._read_data()
            existing = data.get(str(chat_id))
            if existing and existing.get("alive", False):
                return {
                    "success": False,
                    "message": f"{existing.get('name', 'Your Salamagotchi')} is still alive in this chat. You cannot spawn another one yet.",
                }

            pet = self._default_state(cleaned_name, user_display, now)
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"🦎 <b>{html.escape(cleaned_name)}</b> has spawned! Keep it fed, clean, entertained, and washed every day.",
            "status_text": self._format_status_text(pet),
        }

    def get_pet(self, chat_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            data = self._read_data()
            pet = data.get(str(chat_id))
            return deepcopy(pet) if pet else None

    def get_status_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            return "No Salamagotchi exists in this chat yet. Use <code>/salamagotchi_spawn &lt;name&gt;</code> to create one."
        return self._format_status_text(pet)

    def perform_action(self, chat_id: int, action: str, user_display: str) -> Dict[str, Any]:
        if action not in REQUIREMENTS:
            return {"success": False, "message": "Unknown Salamagotchi action."}

        with self.lock:
            data = self._read_data()
            pet = data.get(str(chat_id))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet. Use /salamagotchi_spawn to create one.",
                }
            if not pet.get("alive", False):
                return {
                    "success": False,
                    "message": f"{pet.get('name', 'Your Salamagotchi')} is dead. Spawn a new one to continue.",
                }

            count_key = f"{action}_count"
            current = pet.get(count_key, 0)
            required = REQUIREMENTS[action]
            if current >= required:
                return {
                    "success": False,
                    "message": f"{pet['name']} already has enough {ACTION_LABELS[action]} for today.",
                    "status_text": self._format_status_text(pet),
                }

            pet[count_key] = current + 1
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"{html.escape(user_display)} gave {html.escape(pet['name'])} a {html.escape(ACTION_LABELS[action])}.",
            "status_text": self._format_status_text(pet),
        }

    def reset_daily_needs(self, chat_id: int, user_display: str) -> Dict[str, Any]:
        with self.lock:
            data = self._read_data()
            pet = data.get(str(chat_id))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet.",
                }

            for action in REQUIREMENTS:
                pet[f"{action}_count"] = 0
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"🔄 {html.escape(pet['name'])}'s daily care has been reset.",
            "status_text": self._format_status_text(pet),
        }

    def rename_pet(self, chat_id: int, new_name: str, user_display: str) -> Dict[str, Any]:
        cleaned_name = " ".join(new_name.split()).strip()
        if not cleaned_name:
            return {"success": False, "message": "Please provide a new name for the Salamagotchi."}
        if len(cleaned_name) > 30:
            return {"success": False, "message": "Salamagotchi names must be 30 characters or fewer."}

        with self.lock:
            data = self._read_data()
            pet = data.get(str(chat_id))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet.",
                }

            old_name = pet["name"]
            pet["name"] = cleaned_name
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"✏️ {html.escape(old_name)} has been renamed to <b>{html.escape(cleaned_name)}</b>.",
            "status_text": self._format_status_text(pet),
        }

    def force_kill(self, chat_id: int, user_display: str, reason: str = "admin intervention") -> Dict[str, Any]:
        with self.lock:
            data = self._read_data()
            pet = data.get(str(chat_id))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet.",
                }
            if not pet.get("alive", False):
                return {
                    "success": False,
                    "message": f"{pet['name']} is already dead.",
                    "status_text": self._format_status_text(pet),
                }

            pet["alive"] = False
            pet["death_reason"] = reason
            pet["died_at"] = datetime.now(pytz.UTC).isoformat()
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"💀 <b>{html.escape(pet['name'])}</b> has been killed.",
            "status_text": self._format_status_text(pet),
        }

    def get_help_text(self) -> str:
        return (
            "🦎 <b>Salamagotchi Help</b>\n\n"
            "<blockquote expandable>"
            "<b>Commands</b>\n"
            "<code>/salamagotchi status</code> - Show its status, age, and today's needs\n"
            "<code>/salamagotchi spawn &lt;name&gt;</code> - Spawn a new shared Salamagotchi\n"
            "<code>/salamagotchi feed</code> - Feed it (2 times per day)\n"
            "<code>/salamagotchi scoop</code> - Scoop poop (2 times per day)\n"
            "<code>/salamagotchi play</code> - Play with it (1 time per day)\n"
            "<code>/salamagotchi wash</code> - Wash it (1 time per day)\n"
            "<code>/salamagotchi help</code> - Show this help text\n\n"
            "<b>Admin Commands</b>\n"
            "<code>/salamagotchi reset</code> - Reset today's care counters\n"
            "<code>/salamagotchi rename &lt;name&gt;</code> - Rename the current pet\n"
            "<code>/salamagotchi kill</code> - Forcibly kill the current pet\n\n"
            "<b>Rules</b>\n"
            "• One shared Salamagotchi per chat\n"
            "• You cannot spawn a new one while the current one is alive\n"
            "• Each need can be missed for one day only\n"
            "• Miss the same need two days in a row and it dies\n"
            "• Every day it survives, it grows older and may change stage\n\n"
            "<b>Status Screen</b>\n"
            "The status command shows today's progress plus hints for what still needs to be done."
            "</blockquote>"
        )
