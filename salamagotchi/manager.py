"""
Salamagotchi manager - shared chat pet state, rollover logic, and UI rendering.
"""

from __future__ import annotations

import html
import json
import logging
import os
import random
import threading
from copy import deepcopy
from datetime import datetime, timedelta
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

import pytz

logger = logging.getLogger(__name__)


REQUIREMENTS = {
    "feed": 1,
    "scoop": 1,
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

SCHOOL_LEVELS = ["Diploma", "Degree", "Master's", "PhD"]

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
           ___
        _/EYE\__
       /   ^    \
       \__MTH__/
          /  \
""".strip("\n"),
    },
    {
        "name": "Child",
        "min_age": 7,
        "max_age": 13,
        "art": r"""
             ____
          __/EYE\__
         /    ^     `.
         \__ MTH   _/
           / /  \ \
        ~~'_'    '_~~
""".strip("\n"),
    },
    {
        "name": "Teen",
        "min_age": 14,
        "max_age": 29,
        "art": r"""
              ______
          ___/ EYE \___
         /      ^       `.
         \__   MTH     __/
            \__     __/
              / /| | \
         ~~~~~'_' ' '_`~~
""".strip("\n"),
    },
    {
        "name": "Adult",
        "min_age": 30,
        "max_age": 59,
        "art": r"""
               __/\__
          ____/ EYE \____
         /         ^       `.
        |        MTH        |
         \__               __/
            \___       ___/
               / /| |\ \
          ~~~~~'_' ' ' '_`~~
""".strip("\n"),
    },
    {
        "name": "Elder",
        "min_age": 60,
        "max_age": 999999,
        "art": r"""
               __/\__
          ____/ EYE \____
         /         ^       `.
        |        MTH        |
        |         ___        |
         \__               __/
            \___       ___/
          ~~~~~/ /|   |\ \~~~~
""".strip("\n"),
    },
]

STAGE_EMOJIS = {
    "Eggling": "🥚",
    "Baby": "🐣",
    "Child": "🦎",
    "Teen": "🦖",
    "Adult": "🐉",
    "Elder": "🐲",
}

STAGE_IMAGE_SLUGS = {
    "Eggling": "eggling",
    "Baby": "baby",
    "Child": "child",
    "Teen": "teen",
    "Adult": "adult",
    "Elder": "elder",
}

NEED_IMAGE_TOKENS = {
    "feed": "hungry",
    "scoop": "poopy",
    "wash": "dirty",
    "play": "restless",
}

EVOLUTION_FLAVOR = {
    "Baby": "The shell finally gives way and a tiny hatchling wriggles into the world.",
    "Child": "Its limbs steady, its tail lengthens, and it starts looking like a proper little salamander.",
    "Teen": "It shoots upward into an awkward, speedy adolescent with far too much energy.",
    "Adult": "It settles into its full shape at last, proud, long-tailed, and unmistakably grown.",
    "Elder": "Age lends it a strange dignity, as if it has become some ancient little marsh creature.",
}

ACTIVITY_VERBS = [
    "is lingering",
    "is loitering",
    "is lurking",
    "is drifting",
    "is hovering",
    "is haunting",
    "is browsing",
    "is sitting",
    "is standing",
    "is pacing",
    "is reading",
    "is pretending to read",
    "is smoking outside",
    "is waiting outside",
    "is wandering through",
    "is leafing through",
    "is picking through",
    "is buying far too much at",
    "is half-listening at",
    "is forming an opinion at",
]

ACTIVITY_PLACES = [
    "an arthouse matinee",
    "a gallery opening",
    "a farmer's market",
    "an independent bookstore",
    "a repertory cinema",
    "a museum gift shop",
    "a wine bar with bad lighting",
    "a cafe with tiny tables",
    "a record shop",
    "a thrift store",
    "a flea market",
    "a lecture on architecture",
    "a poetry reading",
    "a park full of extremely self-conscious people",
    "a brutalist plaza",
    "a screening of a film no one enjoyed out loud",
    "a boutique that only sells black clothing",
    "a dinner party that should have ended an hour ago",
    "a used magazine stall",
    "a suspiciously expensive bakery",
]

ACTIVITY_CLAUSES = [
    "pretending not to care very much.",
    "judging everyone's shoes in complete silence.",
    "taking the whole thing far too seriously.",
    "trying to look accidentally elegant.",
    "developing a strong and underinformed opinion.",
    "acting like this is all beneath them.",
    "quietly thriving, unfortunately.",
    "behaving as if they invented taste.",
    "waiting to be recognized as an icon.",
    "becoming impossible to talk to.",
    "turning mild boredom into a worldview.",
    "trying not to seem impressed.",
    "calling it spiritually necessary.",
    "treating a small outing like a vocation.",
    "refusing to admit they're having fun.",
    "looking for something obscure and severe.",
    "narrating the vibe internally.",
    "pretending this is research.",
    "making a spectacle of restraint.",
    "committing to the bit completely.",
]

CURATED_ACTIVITIES = [
    "is smoking outside a gallery opening and judging everyone's shoes.",
    "is buying overpriced cherries at the farmer's market with total conviction.",
    "is flipping through dog-eared paperbacks at an independent bookstore.",
    "is thrift shopping for something obscure and a little severe.",
    "is listening to Japanese jazz and staring out the window dramatically.",
    "is walking through a museum too quickly and forming strong opinions anyway.",
    "is sitting at a cafe with a tiny coffee and a large theory of culture.",
    "is loitering outside a repertory cinema like it's a vocation.",
    "is rearranging flowers from the market into something aggressively tasteful.",
    "is drinking a bitter aperitif and calling it character-building.",
    "is wearing knitwear in weather that does not justify it.",
    "is pretending to discover a director everyone else already discovered years ago.",
    "is reading criticism in the park and becoming impossible to talk to.",
    "is lingering in a record shop and pretending to hate whatever is popular.",
    "is composing a devastating but basically harmless opinion about the room.",
    "is buying tinned fish as if it were a moral decision.",
    "is treating a free screening like a sacred obligation.",
    "is at brunch saying \"decadent\" without irony.",
    "is staring at a building and calling it spiritually clarifying.",
    "is carrying a woven basket full of produce that may never get eaten.",
    "is trying to seem detached at a poetry reading.",
    "is at a cafe patio refusing to order anything sweet on principle.",
    "is walking home from a screening with a needlessly baroque interpretation.",
    "is shopping for sunglasses they absolutely do not need.",
    "is reading a paperback face-out to signal impeccable taste.",
]

STATUS_ACTIVITIES = [
    f"{{name}} {verb} {place}, {clause}"
    for verb in ACTIVITY_VERBS
    for place in ACTIVITY_PLACES
    for clause in ACTIVITY_CLAUSES
]

STATUS_ACTIVITIES.extend(f"{{name}} {activity}" for activity in CURATED_ACTIVITIES)

SPEECH_PREFIXES = [
    "please",
    "um",
    "hey",
    "excuse me",
    "hello",
    "listen",
    "hi",
    "dear chat",
    "tiny request",
    "important announcement",
]

HUNGER_LINES = [
    "my tummy feels empty",
    "i could really use a snack",
    "i am thinking about food again",
    "i would like something tasty",
    "i am waiting very politely for food",
    "my little belly is rumbling",
    "i need a nice meal",
    "food would improve everything",
]

SCOOP_LINES = [
    "my corner is getting embarrassing",
    "there is a situation on the floor",
    "someone should really deal with the poop",
    "things are getting messy over here",
    "the habitat needs attention",
    "i am surrounded by avoidable consequences",
    "the poop problem has become noticeable",
    "my room is no longer respectable",
]

PLAY_LINES = [
    "i need something fun to do",
    "i want attention right now",
    "i could use some playtime",
    "i am feeling bored and dramatic",
    "please entertain me",
    "i need a little adventure",
    "i want to be played with",
    "i am running low on enrichment",
]

WASH_LINES = [
    "i need a bath",
    "i do not feel fresh",
    "i could really use a wash",
    "i am feeling grubby",
    "bath time would help",
    "i am not at my cleanest",
    "i need to be rinsed off",
    "i am getting a bit stinky",
]

HAPPY_LINES = [
    "everything feels nice today",
    "i am feeling very well looked after",
    "today has been extremely comfortable",
    "i feel cherished and tidy",
    "i have no complaints at all",
    "life is going unusually well",
    "i am in excellent little-pet form",
    "today is treating me kindly",
]

SPEECH_CLOSERS = [
    "thank you",
    "please and thank you",
    "i would appreciate it",
    "that is all for now",
    "i am saying this with love",
    "kindly address this",
    "please respond accordingly",
    "do the right thing",
]


class SalamagotchiManager:
    """Persistent shared-chat Salamagotchi manager."""

    def __init__(self, data_dir: str, timezone_name: str = "America/Chicago"):
        self.data_dir = data_dir
        self.data_file_path = os.path.join(data_dir, "salamagotchi.json")
        self.image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pet_images")
        self.sticker_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pet_stickers")
        self.lock = threading.Lock()
        self.timezone_name = timezone_name
        self.timezone = pytz.timezone(timezone_name)
        self.speech_styler = None
        self.memorial_writer = None

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
            "graveyard": [],
            "graveyard_recorded": False,
            "education": {},
            "active_study": None,
            "command_log": [],
            "care_history": {
                "feed": {},
                "scoop": {},
                "play": {},
                "wash": {},
            },
            "speech_style_example": None,
            "speech_style_taught_by": None,
            "gender": None,
            "spawn_pending": False,
            "spawn_started_at": None,
            "spawn_complete_at": None,
            "evolution_pending": False,
            "evolution_started_at": None,
            "evolution_complete_at": None,
            "evolution_target_stage": None,
        }

    def _normalize_pet(self, pet: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if pet is None:
            return None

        normalized = deepcopy(pet)
        normalized.setdefault("graveyard", [])
        normalized.setdefault("graveyard_recorded", False)
        normalized.setdefault("spawned_at", None)
        normalized.setdefault("died_at", None)
        normalized.setdefault("death_reason", None)
        normalized.setdefault("education", {})
        normalized.setdefault("active_study", None)
        normalized.setdefault("command_log", [])
        normalized.setdefault("care_history", {})
        for action in REQUIREMENTS:
            if not isinstance(normalized["care_history"].get(action), dict):
                normalized["care_history"][action] = {}
        normalized.setdefault("speech_style_example", None)
        normalized.setdefault("speech_style_taught_by", None)
        normalized.setdefault("gender", None)
        normalized.setdefault("spawn_pending", False)
        normalized.setdefault("spawn_started_at", None)
        normalized.setdefault("spawn_complete_at", None)
        normalized.setdefault("evolution_pending", False)
        normalized.setdefault("evolution_started_at", None)
        normalized.setdefault("evolution_complete_at", None)
        normalized.setdefault("evolution_target_stage", None)
        return normalized

    def _format_date(self, iso_value: Optional[str]) -> str:
        if not iso_value:
            return "Unknown"
        try:
            dt = datetime.fromisoformat(iso_value)
            return dt.astimezone(self.timezone).strftime("%Y-%m-%d")
        except Exception:
            return "Unknown"

    def _format_lifetime(self, started_at: Optional[str], ended_at: Optional[str], fallback_days: int = 0) -> str:
        if started_at and ended_at:
            try:
                start_dt = datetime.fromisoformat(started_at)
                end_dt = datetime.fromisoformat(ended_at)
                total_seconds = max(0, int((end_dt - start_dt).total_seconds()))
                total_hours = total_seconds // 3600
                days = total_hours // 24
                hours = total_hours % 24

                if days == 0:
                    return f"{hours} hour{'s' if hours != 1 else ''}"
                return f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}"
            except Exception:
                pass

        return f"{fallback_days} day{'s' if fallback_days != 1 else ''}"

    def _create_graveyard_entry(self, pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": pet.get("name", "Unknown"),
            "age_days": pet.get("age_days", 0),
            "lived_for": self._format_lifetime(
                pet.get("spawned_at"),
                pet.get("died_at"),
                pet.get("age_days", 0),
            ),
            "born_on": self._format_date(pet.get("spawned_at")),
            "died_on": self._format_date(pet.get("died_at")),
            "death_reason": pet.get("death_reason", "unknown causes"),
            "education": deepcopy(pet.get("education", {})),
            "active_study": deepcopy(pet.get("active_study")),
            "gender": pet.get("gender"),
        }

    def _assign_gender(self) -> str:
        roll = random.random()
        if roll < 0.495:
            return "male"
        if roll < 0.99:
            return "female"
        return "intersex"

    def _record_graveyard_entry(self, pet: Dict[str, Any]) -> Dict[str, Any]:
        pet = self._normalize_pet(pet)
        if pet.get("graveyard_recorded"):
            return pet

        pet["graveyard"].append(self._create_graveyard_entry(pet))
        pet["graveyard_recorded"] = True
        return pet

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

    def _clean_subject_name(self, subject: str) -> str:
        return " ".join(subject.split()).strip()

    def _get_next_level(self, current_level: str) -> Optional[str]:
        try:
            idx = SCHOOL_LEVELS.index(current_level)
        except ValueError:
            return None
        if idx + 1 >= len(SCHOOL_LEVELS):
            return None
        return SCHOOL_LEVELS[idx + 1]

    def _format_education_summary(self, education: Dict[str, str]) -> str:
        if not education:
            return "None yet"
        parts = [f"{subject} ({level})" for subject, level in sorted(education.items())]
        return ", ".join(parts)

    def _format_active_study(self, active_study: Optional[Dict[str, Any]]) -> Optional[str]:
        if not active_study:
            return None
        return (
            f"{active_study['subject']} ({active_study['target_level']}) "
            f"{active_study['progress_days']}/5"
        )

    def _format_command_timestamp(self, iso_value: Optional[str]) -> str:
        if not iso_value:
            return "Unknown time"
        try:
            dt = datetime.fromisoformat(iso_value)
            return dt.astimezone(self.timezone).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "Unknown time"

    def _increment_care_history(self, pet: Dict[str, Any], action: str, user_display: str) -> None:
        care_history = pet.setdefault("care_history", {})
        action_history = care_history.setdefault(action, {})
        action_history[user_display] = action_history.get(user_display, 0) + 1

    def _get_top_caregiver(self, pet: Dict[str, Any], action: str) -> Optional[Tuple[str, int]]:
        action_history = pet.get("care_history", {}).get(action, {})
        if not action_history:
            return None
        top_user, top_count = max(
            action_history.items(),
            key=lambda item: (item[1], item[0].lower()),
        )
        return top_user, top_count

    def _build_memories_lines(self, pet: Dict[str, Any]) -> List[str]:
        memory_specs = [
            ("feed", "Most feedings"),
            ("scoop", "Most scooping"),
            ("play", "Most playtime"),
            ("wash", "Most baths"),
        ]
        lines: List[str] = []
        for action, label in memory_specs:
            top_caregiver = self._get_top_caregiver(pet, action)
            if top_caregiver:
                user_display, count = top_caregiver
                lines.append(
                    f"{label}: {html.escape(user_display)} ({count})"
                )
            else:
                lines.append(f"{label}: No one")

        speech_lessons = sum(
            1
            for entry in pet.get("command_log", [])
            if str(entry.get("command", "")).startswith("teach_speak sample:")
        )
        learned_subjects = len(pet.get("education", {}))
        lines.append(f"Speech lessons: {speech_lessons}")
        lines.append(f"Learned subjects: {learned_subjects}")
        return lines

    def _format_command_entry_line(self, pet_name: str, entry: Dict[str, Any]) -> str:
        timestamp = self._format_command_timestamp(entry.get("created_at"))
        user_text = html.escape(entry.get("user", "Unknown user"))
        command_text = html.escape(entry.get("command", ""))
        return f"[{timestamp}] {user_text} commanded {html.escape(pet_name)} to {command_text}."

    def _build_fallback_obituary_text(self, pet: Dict[str, Any]) -> str:
        education = pet.get("education", {})
        subject_count = len(education)
        speech_lessons = sum(
            1
            for entry in pet.get("command_log", [])
            if str(entry.get("command", "")).startswith("teach_speak sample:")
        )
        top_actions = []
        for action in ("feed", "play", "wash", "scoop"):
            top_caregiver = self._get_top_caregiver(pet, action)
            if top_caregiver:
                label = {
                    "feed": "well fed",
                    "play": "well entertained",
                    "wash": "very clean",
                    "scoop": "patiently tidied after",
                }[action]
                top_actions.append(label)

        descriptors = self._join_phrases(top_actions[:3]) if top_actions else "closely watched over"
        gender = pet.get("gender")
        if gender:
            article = "an" if gender == "intersex" else "a"
            opening_line = f"{pet.get('name', 'This pet')} was {article} {gender} pet who was {descriptors} by the chat."
        else:
            opening_line = f"{pet.get('name', 'This pet')} was a pet who was {descriptors} by the chat."
        lines = [opening_line]
        custom_commands = []
        built_in_prefixes = {
            "status",
            "spawn",
            "teach_speak",
            "commands",
            "graveyard",
            "help",
            "feed",
            "scoop",
            "play",
            "wash",
            "reset",
            "rename",
            "kill",
            "graveyard_remove_last",
            "memorial_preview",
            "stage_art",
            "school",
        }
        for entry in pet.get("command_log", []):
            command_text = str(entry.get("command", "")).strip()
            if not command_text:
                continue
            first_word = command_text.split(" ", 1)[0]
            if first_word not in built_in_prefixes:
                custom_commands.append(command_text)
        if custom_commands:
            notable_custom = custom_commands[-1]
            lines.append(f"It was once sent off to {notable_custom}.")
        if subject_count:
            lines.append(f"It completed {subject_count} subject{'s' if subject_count != 1 else ''} before its passing.")
        if speech_lessons:
            lines.append(f"It was taught to speak {speech_lessons} time{'s' if speech_lessons != 1 else ''}.")
        return " ".join(lines)

    def _build_memorial_tombstone(self, name: str) -> str:
        display_name = " ".join(name.split()).strip() or "Sal"
        display_name = display_name[:14]
        name_line = display_name.center(14)
        return (
            "      _.---._\n"
            "    .'       '.\n"
            "   /  R. I. P.  \\\n"
            "  |              |\n"
            f"  |{name_line}|\n"
            "  |              |\n"
            "  |______________|\n"
            "     /_/   \\_\\"
        )

    def build_stage_evolution_text(self, pet: Dict[str, Any], stage_name: str) -> str:
        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        stage = next((stage for stage in STAGES if stage["name"] == stage_name), self._get_stage(pet.get("age_days", 0)))
        stage_emoji = STAGE_EMOJIS.get(stage_name, "🦎")
        flavor = EVOLUTION_FLAVOR.get(stage_name, f"{safe_name} has reached a new stage of life.")
        preview_pet = {
            "alive": True,
            "feed_count": REQUIREMENTS["feed"],
            "scoop_count": REQUIREMENTS["scoop"],
            "play_count": REQUIREMENTS["play"],
            "wash_count": REQUIREMENTS["wash"],
        }
        gender_line = ""
        if stage_name == "Baby" and pet.get("gender"):
            announcement_map = {
                "male": "It's a baby boy!",
                "female": "It's a baby girl!",
                "intersex": "It's an intersex baby!",
            }
            announcement_text = announcement_map.get(str(pet["gender"]).lower(), "It's a baby!")
            gender_line = f"\n<b>{html.escape(announcement_text)}</b>"
        return (
            f"{stage_emoji} <b>{safe_name}</b> has evolved into the <b>{html.escape(stage_name)}</b> stage!\n"
            f"<pre>{html.escape(self._render_stage_art(preview_pet, stage))}</pre>\n"
            f"<blockquote expandable>{html.escape(flavor)}{gender_line}</blockquote>"
        )

    def _parse_iso_datetime(self, iso_value: Optional[str]) -> Optional[datetime]:
        if not iso_value:
            return None
        try:
            parsed = datetime.fromisoformat(iso_value)
            if parsed.tzinfo is None:
                return pytz.UTC.localize(parsed)
            return parsed.astimezone(pytz.UTC)
        except Exception:
            return None

    def _format_duration_text(self, total_seconds: int) -> str:
        total_seconds = max(0, int(total_seconds))
        if total_seconds % 3600 == 0 and total_seconds >= 3600:
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        if total_seconds % 60 == 0 and total_seconds >= 60:
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        return f"{total_seconds} second{'s' if total_seconds != 1 else ''}"

    def _build_baby_gender_line(self, pet: Dict[str, Any], stage_name: str) -> str:
        if stage_name != "Baby" or not pet.get("gender"):
            return ""
        announcement_map = {
            "male": "It's a baby boy!",
            "female": "It's a baby girl!",
            "intersex": "It's an intersex baby!",
        }
        announcement_text = announcement_map.get(str(pet["gender"]).lower(), "It's a baby!")
        return f"\n<b>{html.escape(announcement_text)}</b>"

    def _build_spawn_start_text(self, pet_name: str, duration_seconds: int = 300) -> str:
        safe_name = html.escape(pet_name or "Salamagotchi")
        duration_text = self._format_duration_text(duration_seconds)
        return (
            "📦 <b>Your new Salamagotchi™ is on its way.</b>\n"
            f"<blockquote expandable><b>{safe_name}</b> is being delivered now. It should arrive in about {html.escape(duration_text)}.</blockquote>"
        )

    def _build_spawn_arrival_text(self, pet_name: str) -> str:
        safe_name = html.escape(pet_name or "Salamagotchi")
        return (
            f"🥚 <b>{safe_name}</b> has arrived and needs your help.\n"
            f"<blockquote expandable>Feed {safe_name}, scoop poop, play with it, and wash it before neglect starts piling up.</blockquote>"
        )

    def _start_pending_spawn(
        self,
        pet: Dict[str, Any],
        now: Optional[datetime] = None,
        duration_seconds: int = 300,
    ) -> Dict[str, Any]:
        pet = self._normalize_pet(pet)
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)
        pet["spawn_pending"] = True
        pet["spawn_started_at"] = now.isoformat()
        pet["spawn_complete_at"] = (now + timedelta(seconds=duration_seconds)).isoformat()
        return pet

    def _clear_pending_spawn(self, pet: Dict[str, Any]) -> Dict[str, Any]:
        pet = self._normalize_pet(pet)
        pet["spawn_pending"] = False
        pet["spawn_started_at"] = None
        pet["spawn_complete_at"] = None
        return pet

    def _build_evolution_start_text(self, pet: Dict[str, Any], duration_seconds: int = 3600) -> str:
        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        duration_text = self._format_duration_text(duration_seconds)
        return (
            f"🌀 <b>{safe_name}</b> is evolving!\n"
            f"<blockquote expandable>{safe_name} is in the middle of a transformation and cannot be interacted with for {html.escape(duration_text)}.</blockquote>"
        )

    def _build_evolution_complete_text(self, pet: Dict[str, Any], stage_name: str) -> str:
        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        gender_line = self._build_baby_gender_line(pet, stage_name)
        return (
            f"✨ <b>{safe_name}</b> has evolved successfully and is now a <b>{html.escape(stage_name)}</b>.{gender_line}"
        )

    def _start_pending_evolution(
        self,
        pet: Dict[str, Any],
        target_stage: str,
        now: Optional[datetime] = None,
        duration_seconds: int = 3600,
    ) -> Dict[str, Any]:
        pet = self._normalize_pet(pet)
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)
        pet["evolution_pending"] = True
        pet["evolution_started_at"] = now.isoformat()
        pet["evolution_complete_at"] = (now + timedelta(seconds=duration_seconds)).isoformat()
        pet["evolution_target_stage"] = target_stage
        return pet

    def _clear_pending_evolution(self, pet: Dict[str, Any]) -> Dict[str, Any]:
        pet = self._normalize_pet(pet)
        pet["evolution_pending"] = False
        pet["evolution_started_at"] = None
        pet["evolution_complete_at"] = None
        pet["evolution_target_stage"] = None
        return pet

    def build_death_memorial_text(self, pet: Dict[str, Any]) -> str:
        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        death_reason = html.escape(pet.get("death_reason", "unknown causes"))
        stage_name = html.escape(self._get_stage(pet.get("age_days", 0))["name"])
        memories = "\n".join(self._build_memories_lines(pet))
        obituary_text = self._build_fallback_obituary_text(pet)
        if callable(self.memorial_writer):
            try:
                written_obituary = self.memorial_writer(pet)
                if written_obituary:
                    obituary_text = written_obituary
            except Exception as e:
                logger.warning("Failed to build memorial obituary text: %s", e)
        return (
            f"💀 <b>{safe_name}</b> has died of {death_reason}.\n"
            f"<i>{html.escape(obituary_text)}</i>\n"
            f"<blockquote expandable><b>Memories of {safe_name}</b>\n"
            f"Stage: {stage_name}\n"
            f"{memories}\n\n"
            "A new Salamagotchi can be spawned with <code>/pet spawn &lt;name&gt;</code>.</blockquote>"
        )

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

    def _build_activity_phrase(self, pet: Dict[str, Any]) -> str:
        template = random.choice(STATUS_ACTIVITIES)
        return template.format(name=pet["name"])

    def _build_pet_speech_base(self, pet: Dict[str, Any]) -> str:
        needs: List[str] = []
        if pet.get("feed_count", 0) < REQUIREMENTS["feed"]:
            needs.append(random.choice(HUNGER_LINES))
        if pet.get("scoop_count", 0) < REQUIREMENTS["scoop"]:
            needs.append(random.choice(SCOOP_LINES))
        if pet.get("play_count", 0) < REQUIREMENTS["play"]:
            needs.append(random.choice(PLAY_LINES))
        if pet.get("wash_count", 0) < REQUIREMENTS["wash"]:
            needs.append(random.choice(WASH_LINES))

        if not needs:
            return (
                f"{random.choice(SPEECH_PREFIXES)}, {random.choice(HAPPY_LINES)}, "
                f"{random.choice(SPEECH_CLOSERS)}."
            )

        return (
            f"{random.choice(SPEECH_PREFIXES)}, "
            f"{self._join_phrases(needs)}, "
            f"{random.choice(SPEECH_CLOSERS)}."
        )

    def _build_status_phrase(self, pet: Dict[str, Any]) -> str:
        speech_style_example = pet.get("speech_style_example")
        if speech_style_example and callable(self.speech_styler):
            base_line = self._build_pet_speech_base(pet)
            try:
                styled_line = self.speech_styler(base_line, speech_style_example)
                if styled_line:
                    return styled_line
            except Exception as e:
                logger.warning("Failed to style pet speech: %s", e)
            return base_line
        return self._build_activity_phrase(pet)

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

    def _build_status_body_lines(self, pet: Dict[str, Any]) -> List[str]:
        stage = self._get_stage(pet.get("age_days", 0))
        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        stage_emoji = STAGE_EMOJIS.get(stage["name"], "🦎")

        body_lines: List[str] = []
        body_lines.extend([
            f"{stage_emoji} <b>{safe_name}</b>",
            f"<b>Age:</b> {pet.get('age_days', 0)} day{'s' if pet.get('age_days', 0) != 1 else ''}",
            f"<b>Stage:</b> {html.escape(stage['name'])}",
        ])

        active_study_text = self._format_active_study(pet.get("active_study"))
        if active_study_text:
            body_lines.append(f"<b>Studying:</b> {html.escape(active_study_text)}")
            body_lines.append("")

        if pet.get("education"):
            body_lines.append(f"<b>Learned:</b> {html.escape(self._format_education_summary(pet['education']))}")

        if pet.get("alive"):
            body_lines.append(f"<i>{html.escape(self._build_status_phrase(pet))}</i>")
            body_lines.append("")

        hint_lines = self._build_hint_lines(pet) if pet.get("alive") else [
            f"{safe_name} died of {html.escape(pet.get('death_reason', 'unknown causes'))}.",
            "A new Salamagotchi can be spawned in this chat.",
        ]
        body_lines.extend(html.escape(line) for line in hint_lines)
        return body_lines

    def _format_status_text(self, pet: Dict[str, Any]) -> str:
        stage = self._get_stage(pet.get("age_days", 0))
        art_block = f"<pre>{html.escape(self._render_stage_art(pet, stage))}</pre>"
        body_lines = self._build_status_body_lines(pet)

        return f"{art_block}<blockquote expandable>{chr(10).join(body_lines)}</blockquote>"

    def _format_status_message_text(self, pet: Dict[str, Any], leading_message: Optional[str] = None) -> str:
        body = f"<blockquote expandable>{chr(10).join(self._build_status_body_lines(pet))}</blockquote>"
        if leading_message:
            return f"{leading_message}\n\n{body}"
        return body

    def _get_need_image_tokens(self, pet: Dict[str, Any]) -> List[str]:
        tokens: List[str] = []
        for action, token in NEED_IMAGE_TOKENS.items():
            remaining = max(0, REQUIREMENTS[action] - pet.get(f"{action}_count", 0))
            if remaining > 0:
                tokens.append(token)
        return tokens

    def _candidate_state_names(self, pet: Dict[str, Any]) -> List[str]:
        if not pet.get("alive", True):
            return ["dead"]

        tokens = self._get_need_image_tokens(pet)
        if not tokens:
            return ["healthy"]

        state_names = ["_".join(tokens)]
        if len(tokens) >= 3:
            state_names.append("critical")

        for subset_size in range(len(tokens) - 1, 0, -1):
            for subset in combinations(tokens, subset_size):
                candidate = "_".join(subset)
                if candidate not in state_names:
                    state_names.append(candidate)

        if "critical" not in state_names and len(tokens) >= 2:
            state_names.append("critical")

        state_names.append("healthy")
        return state_names

    def _get_state_image_path(self, pet: Dict[str, Any]) -> Optional[str]:
        stage = self._get_stage(pet.get("age_days", 0))
        stage_slug = STAGE_IMAGE_SLUGS.get(stage["name"])
        if not stage_slug:
            return None

        for state_name in self._candidate_state_names(pet):
            candidate_path = os.path.join(self.image_dir, f"{stage_slug}_{state_name}.png")
            if os.path.exists(candidate_path):
                return candidate_path
        return None

    def _get_action_image_path(self, action_name: Optional[str]) -> Optional[str]:
        if not action_name:
            return None
        stage_slug = None
        candidate_path = os.path.join(self.image_dir, f"action_{action_name}.png")
        if os.path.exists(candidate_path):
            return candidate_path
        return None

    def _get_state_sticker_path(self, pet: Dict[str, Any]) -> Optional[str]:
        stage = self._get_stage(pet.get("age_days", 0))
        stage_slug = STAGE_IMAGE_SLUGS.get(stage["name"])
        if not stage_slug:
            return None

        for state_name in self._candidate_state_names(pet):
            candidate_path = os.path.join(self.sticker_dir, f"{stage_slug}_{state_name}.webp")
            if os.path.exists(candidate_path):
                return candidate_path
        return None

    def _get_action_sticker_path(self, pet: Dict[str, Any], action_name: Optional[str]) -> Optional[str]:
        if not action_name:
            return None

        stage = self._get_stage(pet.get("age_days", 0))
        stage_slug = STAGE_IMAGE_SLUGS.get(stage["name"])
        if not stage_slug:
            return None

        candidates = []
        if action_name == "iran_flag":
            candidates.append(os.path.join(self.sticker_dir, f"{stage_slug}_iran_flag.webp"))
        elif action_name == "usa_flag":
            candidates.append(os.path.join(self.sticker_dir, f"{stage_slug}_usa_flag.webp"))
        elif action_name == "russia_flag":
            candidates.append(os.path.join(self.sticker_dir, f"{stage_slug}_russia_flag.webp"))
        elif action_name == "china_flag":
            candidates.append(os.path.join(self.sticker_dir, f"{stage_slug}_china_flag.webp"))
        else:
            candidates.append(os.path.join(self.sticker_dir, f"{stage_slug}_action_{action_name}.webp"))

        candidates.append(os.path.join(self.sticker_dir, f"action_{action_name}.webp"))

        for candidate_path in candidates:
            if os.path.exists(candidate_path):
                return candidate_path
        return None

    def _get_named_action_sticker_path(self, action_name: Optional[str]) -> Optional[str]:
        if not action_name:
            return None
        candidate_path = os.path.join(self.sticker_dir, f"action_{action_name}.webp")
        if os.path.exists(candidate_path):
            return candidate_path
        return None

    def get_memorial_payload(self, chat_id: int, memorial_text: str) -> Optional[Dict[str, str]]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        sticker_path = self._get_named_action_sticker_path("memorial")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": memorial_text,
        }

    def get_spawn_start_payload(self, chat_id: int, duration_seconds: int = 300) -> Optional[Dict[str, str]]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        sticker_path = self._get_named_action_sticker_path("spawn")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._build_spawn_start_text(pet.get("name", "Salamagotchi"), duration_seconds=duration_seconds),
        }

    def get_spawn_start_preview_payload(self, pet_name: str, duration_seconds: int = 30) -> Optional[Dict[str, str]]:
        sticker_path = self._get_named_action_sticker_path("spawn")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._build_spawn_start_text(pet_name, duration_seconds=duration_seconds),
        }

    def get_spawn_arrival_payload(self, chat_id: int) -> Optional[Dict[str, str]]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        sticker_path = self._get_stage_state_sticker_path("Eggling", "hungry_poopy_dirty_restless")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._build_spawn_arrival_text(pet.get("name", "Salamagotchi")),
        }

    def get_spawn_arrival_preview_payload(self, pet_name: str) -> Optional[Dict[str, str]]:
        sticker_path = self._get_stage_state_sticker_path("Eggling", "hungry_poopy_dirty_restless")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._build_spawn_arrival_text(pet_name),
        }

    def get_spawn_status(self, chat_id: int, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        pet = self.get_pet(chat_id)
        if not pet or not pet.get("alive", False) or not pet.get("spawn_pending"):
            return None

        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        complete_at = self._parse_iso_datetime(pet.get("spawn_complete_at"))
        is_ready = complete_at is not None and now >= complete_at
        return {
            "pet": pet,
            "ready": is_ready,
            "complete_at": complete_at,
        }

    def _get_stage_state_sticker_path(self, stage_name: str, state_name: str = "healthy") -> Optional[str]:
        stage_slug = STAGE_IMAGE_SLUGS.get(stage_name)
        if not stage_slug:
            return None
        candidate_path = os.path.join(self.sticker_dir, f"{stage_slug}_{state_name}.webp")
        if os.path.exists(candidate_path):
            return candidate_path
        return None

    def get_status_photo_payload(
        self,
        chat_id: int,
        leading_message: Optional[str] = None,
        preferred_action: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        sticker_path = self._get_action_sticker_path(pet, preferred_action) or self._get_state_sticker_path(pet)
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._format_status_message_text(pet, leading_message),
        }

    def get_evolution_start_payload(
        self,
        chat_id: int,
        duration_seconds: int = 3600,
    ) -> Optional[Dict[str, str]]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        sticker_path = self._get_named_action_sticker_path("evolve")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._build_evolution_start_text(pet, duration_seconds=duration_seconds),
        }

    def get_evolution_complete_payload(self, chat_id: int) -> Optional[Dict[str, str]]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        stage_name = pet.get("evolution_target_stage") or self._get_stage(pet.get("age_days", 0))["name"]
        sticker_path = self._get_stage_state_sticker_path(stage_name, "healthy")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._build_evolution_complete_text(pet, stage_name),
        }

    def get_stage_completion_preview_payload(self, chat_id: int, stage_name: str) -> Optional[Dict[str, str]]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        preview_pet = deepcopy(pet)
        if stage_name == "Baby" and not preview_pet.get("gender"):
            preview_pet["gender"] = self._assign_gender()

        sticker_path = self._get_stage_state_sticker_path(stage_name, "healthy")
        if not sticker_path:
            return None

        return {
            "sticker_path": sticker_path,
            "text": self._build_evolution_complete_text(preview_pet, stage_name),
        }

    def get_evolution_status(self, chat_id: int, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        pet = self.get_pet(chat_id)
        if not pet or not pet.get("alive", False) or not pet.get("evolution_pending"):
            return None

        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        complete_at = self._parse_iso_datetime(pet.get("evolution_complete_at"))
        is_ready = complete_at is not None and now >= complete_at
        return {
            "pet": pet,
            "ready": is_ready,
            "target_stage": pet.get("evolution_target_stage") or self._get_stage(pet.get("age_days", 0))["name"],
            "complete_at": complete_at,
        }

    def _apply_rollover(self, pet: Dict[str, Any], current_date: str) -> Tuple[Dict[str, Any], bool]:
        pet = deepcopy(pet)
        previous_stage = self._get_stage(pet.get("age_days", 0))["name"]
        previous_date = (datetime.strptime(current_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()

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
            pet = self._record_graveyard_entry(pet)
            return pet, False

        active_study = pet.get("active_study")
        if active_study and active_study.get("last_study_date") != previous_date:
            pet["active_study"] = None

        pet["age_days"] = pet.get("age_days", 0) + 1
        pet["last_rollover_date"] = current_date
        for action in REQUIREMENTS:
            pet[f"{action}_count"] = 0

        new_stage = self._get_stage(pet.get("age_days", 0))["name"]
        if previous_stage == "Eggling" and new_stage == "Baby" and not pet.get("gender"):
            pet["gender"] = self._assign_gender()
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
                if pet.get("spawn_pending"):
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
                if not updated_pet.get("alive", False):
                    event["memorial_text"] = self.build_death_memorial_text(updated_pet)
                elif stage_changed:
                    updated_pet = self._start_pending_evolution(updated_pet, event["stage"], now=now, duration_seconds=3600)
                    data[chat_id] = updated_pet
                    event["evolution_pending"] = True
                    event["evolution_duration_seconds"] = 3600
                events.append(event)

            if changed:
                self._write_data(data)

        return events

    def complete_ready_evolution(self, chat_id: int, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet or not pet.get("alive", False) or not pet.get("evolution_pending"):
                return None

            complete_at = self._parse_iso_datetime(pet.get("evolution_complete_at"))
            if complete_at and now < complete_at:
                return None

            target_stage = pet.get("evolution_target_stage") or self._get_stage(pet.get("age_days", 0))["name"]
            result = {
                "chat_id": int(chat_id),
                "name": pet.get("name", "Salamagotchi"),
                "stage": target_stage,
            }

            pet = self._clear_pending_evolution(pet)
            data[str(chat_id)] = pet
            self._write_data(data)
            return result

    def process_completed_evolutions(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        events: List[Dict[str, Any]] = []
        with self.lock:
            data = self._read_data()
            changed = False

            for chat_id, pet in data.items():
                pet = self._normalize_pet(pet)
                if not pet or not pet.get("alive", False) or not pet.get("evolution_pending"):
                    continue

                complete_at = self._parse_iso_datetime(pet.get("evolution_complete_at"))
                if complete_at and now < complete_at:
                    continue

                target_stage = pet.get("evolution_target_stage") or self._get_stage(pet.get("age_days", 0))["name"]
                pet = self._clear_pending_evolution(pet)
                data[chat_id] = pet
                changed = True
                events.append(
                    {
                        "chat_id": int(chat_id),
                        "name": pet.get("name", "Salamagotchi"),
                        "stage": target_stage,
                    }
                )

            if changed:
                self._write_data(data)

        return events

    def get_pending_evolutions(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        pending: List[Dict[str, Any]] = []
        with self.lock:
            data = self._read_data()
            for chat_id, pet in data.items():
                pet = self._normalize_pet(pet)
                if not pet or not pet.get("alive", False) or not pet.get("evolution_pending"):
                    continue

                complete_at = self._parse_iso_datetime(pet.get("evolution_complete_at"))
                if complete_at:
                    remaining_seconds = max(0, int((complete_at - now).total_seconds()))
                else:
                    remaining_seconds = 0

                pending.append(
                    {
                        "chat_id": int(chat_id),
                        "remaining_seconds": remaining_seconds,
                        "target_stage": pet.get("evolution_target_stage") or self._get_stage(pet.get("age_days", 0))["name"],
                    }
                )
        return pending

    def complete_ready_spawn(self, chat_id: int, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet or not pet.get("alive", False) or not pet.get("spawn_pending"):
                return None

            complete_at = self._parse_iso_datetime(pet.get("spawn_complete_at"))
            if complete_at and now < complete_at:
                return None

            pet = self._clear_pending_spawn(pet)
            data[str(chat_id)] = pet
            self._write_data(data)
            return {
                "chat_id": int(chat_id),
                "name": pet.get("name", "Salamagotchi"),
            }

    def process_completed_spawns(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        events: List[Dict[str, Any]] = []
        with self.lock:
            data = self._read_data()
            changed = False

            for chat_id, pet in data.items():
                pet = self._normalize_pet(pet)
                if not pet or not pet.get("alive", False) or not pet.get("spawn_pending"):
                    continue

                complete_at = self._parse_iso_datetime(pet.get("spawn_complete_at"))
                if complete_at and now < complete_at:
                    continue

                pet = self._clear_pending_spawn(pet)
                data[chat_id] = pet
                changed = True
                events.append(
                    {
                        "chat_id": int(chat_id),
                        "name": pet.get("name", "Salamagotchi"),
                    }
                )

            if changed:
                self._write_data(data)

        return events

    def get_pending_spawns(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now(pytz.UTC)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        pending: List[Dict[str, Any]] = []
        with self.lock:
            data = self._read_data()
            for chat_id, pet in data.items():
                pet = self._normalize_pet(pet)
                if not pet or not pet.get("alive", False) or not pet.get("spawn_pending"):
                    continue

                complete_at = self._parse_iso_datetime(pet.get("spawn_complete_at"))
                if complete_at:
                    remaining_seconds = max(0, int((complete_at - now).total_seconds()))
                else:
                    remaining_seconds = 0

                pending.append(
                    {
                        "chat_id": int(chat_id),
                        "remaining_seconds": remaining_seconds,
                        "name": pet.get("name", "Salamagotchi"),
                    }
                )

        return pending

    def spawn(self, chat_id: int, name: str, user_display: str, now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or datetime.now(pytz.UTC)
        cleaned_name = " ".join(name.split()).strip()
        if not cleaned_name:
            return {"success": False, "message": "Please provide a name for the Salamagotchi."}
        if len(cleaned_name) > 30:
            return {"success": False, "message": "Salamagotchi names must be 30 characters or fewer."}

        with self.lock:
            data = self._read_data()
            existing = self._normalize_pet(data.get(str(chat_id)))
            if existing and existing.get("alive", False):
                return {
                    "success": False,
                    "message": f"{existing.get('name', 'Your Salamagotchi')} is still alive in this chat. You cannot spawn another one yet.",
                }

            pet = self._default_state(cleaned_name, user_display, now)
            pet = self._start_pending_spawn(pet, now=now, duration_seconds=300)
            if existing:
                pet["graveyard"] = existing.get("graveyard", [])
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": self._build_spawn_start_text(cleaned_name, duration_seconds=300),
            "spawn_pending": True,
            "spawn_duration_seconds": 300,
        }

    def get_pet(self, chat_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            return deepcopy(pet) if pet else None

    def get_status_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            return "No Salamagotchi exists in this chat yet. Use <code>/pet spawn &lt;name&gt;</code> to create one."
        if pet.get("spawn_pending"):
            return self._build_spawn_start_text(pet.get("name", "Salamagotchi"), duration_seconds=300)
        return self._format_status_text(pet)

    def get_status_message_text(self, chat_id: int, leading_message: Optional[str] = None) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            if leading_message:
                return f"{leading_message}\n\nNo Salamagotchi exists in this chat yet. Use <code>/pet spawn &lt;name&gt;</code> to create one."
            return "No Salamagotchi exists in this chat yet. Use <code>/pet spawn &lt;name&gt;</code> to create one."
        if pet.get("spawn_pending"):
            return self._build_spawn_start_text(pet.get("name", "Salamagotchi"), duration_seconds=300)
        return self._format_status_message_text(pet, leading_message)

    def get_compact_status_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            return "No Salamagotchi exists in this chat yet."

        stage = self._get_stage(pet.get("age_days", 0))
        status = "Alive" if pet.get("alive") else "Dead"
        stage_emoji = STAGE_EMOJIS.get(stage["name"], "🦎")
        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        age_text = f"{pet.get('age_days', 0)} day{'s' if pet.get('age_days', 0) != 1 else ''}"

        lines = [
            f"{stage_emoji} <b>{safe_name}</b>",
            f"<b>Status:</b> {status}  <b>Age:</b> {age_text}",
            f"<b>Stage:</b> {html.escape(stage['name'])}",
        ]

        active_study_text = self._format_active_study(pet.get("active_study"))
        if active_study_text:
            lines.append(f"<b>Studying:</b> {html.escape(active_study_text)}")

        need_phrase = self._build_need_phrase(pet) if pet.get("alive") else f"{safe_name} died of {html.escape(pet.get('death_reason', 'unknown causes'))}."
        lines.append(html.escape(need_phrase))
        return "\n".join(lines)

    def set_speech_style(self, chat_id: int, style_example: str, user_display: str) -> Dict[str, Any]:
        cleaned_example = " ".join(style_example.split()).strip()
        if not cleaned_example:
            return {
                "success": False,
                "message": "Please send a rewritten sentence so I can learn the pet's speaking style.",
            }

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet.",
                }
            if not pet.get("alive", False):
                return {
                    "success": False,
                    "message": f"{pet['name']} is dead and cannot learn a new speaking style.",
                }

            pet["speech_style_example"] = cleaned_example
            pet["speech_style_taught_by"] = user_display
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"🗣️ {html.escape(pet['name'])} has learned a new way of speaking from {html.escape(user_display)}.",
            "status_text": self._format_status_text(pet),
        }

    def perform_action(self, chat_id: int, action: str, user_display: str) -> Dict[str, Any]:
        if action not in REQUIREMENTS:
            return {"success": False, "message": "Unknown Salamagotchi action."}

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet. Use /pet spawn <name> to create one.",
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
            self._increment_care_history(pet, action, user_display)
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"{html.escape(user_display)} gave {html.escape(pet['name'])} a {html.escape(ACTION_LABELS[action])}.",
            "status_text": self._format_status_text(pet),
        }

    def start_school_subject(self, chat_id: int, subject: str, user_display: str) -> Dict[str, Any]:
        cleaned_subject = self._clean_subject_name(subject)
        if not cleaned_subject:
            return {"success": False, "message": "Please provide a subject to study."}
        if len(cleaned_subject) > 40:
            return {"success": False, "message": "Subject names must be 40 characters or fewer."}

        today = self._local_date_str()

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet:
                return {"success": False, "message": "No Salamagotchi exists in this chat yet."}
            if not pet.get("alive", False):
                return {"success": False, "message": f"{pet['name']} is dead and cannot go to school."}
            if pet.get("active_study"):
                current = pet["active_study"]
                return {
                    "success": False,
                    "message": f"{pet['name']} is already studying {current['subject']} toward a {current['target_level']}.",
                }
            if cleaned_subject in pet.get("education", {}):
                return {
                    "success": False,
                    "message": f"{pet['name']} already studied {cleaned_subject}. Use /pet school upgrade {cleaned_subject} to keep going.",
                }

            pet["active_study"] = {
                "subject": cleaned_subject,
                "target_level": "Diploma",
                "progress_days": 1,
                "last_study_date": today,
            }
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"🎓 {html.escape(pet['name'])} started studying <b>{html.escape(cleaned_subject)}</b> toward a <b>Diploma</b>.",
            "status_text": self._format_status_text(pet),
        }

    def continue_school(self, chat_id: int, user_display: str) -> Dict[str, Any]:
        today = self._local_date_str()

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet:
                return {"success": False, "message": "No Salamagotchi exists in this chat yet."}
            if not pet.get("alive", False):
                return {"success": False, "message": f"{pet['name']} is dead and cannot go to school."}

            active_study = pet.get("active_study")
            if not active_study:
                return {"success": False, "message": f"{pet['name']} is not currently studying anything."}
            if active_study.get("last_study_date") == today:
                return {"success": False, "message": f"{pet['name']} already went to school today."}

            active_study["progress_days"] += 1
            active_study["last_study_date"] = today
            pet["last_interaction_by"] = user_display

            completed = False
            completed_subject = active_study["subject"]
            completed_level = active_study["target_level"]
            if active_study["progress_days"] >= 5:
                pet["education"][completed_subject] = completed_level
                pet["active_study"] = None
                completed = True

            data[str(chat_id)] = pet
            self._write_data(data)

        if completed:
            return {
                "success": True,
                "message": f"🎓 {html.escape(pet['name'])} completed a <b>{html.escape(completed_level)}</b> in <b>{html.escape(completed_subject)}</b>.",
                "status_text": self._format_status_text(pet),
            }

        return {
            "success": True,
            "message": f"📚 {html.escape(pet['name'])} continued studying <b>{html.escape(active_study['subject'])}</b> ({active_study['progress_days']}/5).",
            "status_text": self._format_status_text(pet),
        }

    def upgrade_school_subject(self, chat_id: int, subject: str, user_display: str) -> Dict[str, Any]:
        cleaned_subject = self._clean_subject_name(subject)
        if not cleaned_subject:
            return {"success": False, "message": "Please provide a subject to upgrade."}
        today = self._local_date_str()

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet:
                return {"success": False, "message": "No Salamagotchi exists in this chat yet."}
            if not pet.get("alive", False):
                return {"success": False, "message": f"{pet['name']} is dead and cannot go to school."}
            if pet.get("active_study"):
                current = pet["active_study"]
                return {
                    "success": False,
                    "message": f"{pet['name']} is already studying {current['subject']} toward a {current['target_level']}.",
                }

            education = pet.get("education", {})
            current_level = education.get(cleaned_subject)
            if not current_level:
                return {
                    "success": False,
                    "message": f"{pet['name']} has not learned {cleaned_subject} yet. Start it with /pet school start {cleaned_subject}.",
                }

            next_level = self._get_next_level(current_level)
            if not next_level:
                return {
                    "success": False,
                    "message": f"{pet['name']} already has the highest qualification in {cleaned_subject}.",
                }

            pet["active_study"] = {
                "subject": cleaned_subject,
                "target_level": next_level,
                "progress_days": 1,
                "last_study_date": today,
            }
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"🎓 {html.escape(pet['name'])} started working toward a <b>{html.escape(next_level)}</b> in <b>{html.escape(cleaned_subject)}</b>.",
            "status_text": self._format_status_text(pet),
        }

    def get_school_subjects_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            return "No Salamagotchi exists in this chat yet."

        education = pet.get("education", {})
        active_study = pet.get("active_study")
        lines = ["🎓 <b>School Subjects</b>"]
        if education:
            lines.append(f"<blockquote expandable><b>Learned:</b>\n{html.escape(self._format_education_summary(education))}")
        else:
            lines.append("<blockquote expandable><b>Learned:</b>\nNone yet")

        if active_study:
            lines.append(
                f"\n\n<b>Currently Studying:</b>\n{html.escape(self._format_active_study(active_study))}"
            )

        lines.append("</blockquote>")
        return "".join(lines)

    def get_school_status_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            return "No Salamagotchi exists in this chat yet."
        active_study = pet.get("active_study")
        if active_study:
            return (
                "🎓 <b>School Status</b>\n\n"
                f"<blockquote expandable><b>Current Track:</b>\n{html.escape(self._format_active_study(active_study))}\n\n"
                "Miss a day and this streak is lost.</blockquote>"
            )
        return (
            "🎓 <b>School Status</b>\n\n"
            "<blockquote expandable>No active study streak right now.</blockquote>"
        )

    def add_command_log(
        self,
        chat_id: int,
        user_display: str,
        command_text: str,
        created_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        cleaned_command = " ".join(command_text.split()).strip()
        if not cleaned_command:
            return {"success": False, "message": "There was no custom command to log."}

        created_at = created_at or datetime.now(pytz.UTC)

        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet.",
                }
            if not pet.get("alive", False):
                return {
                    "success": False,
                    "message": f"{pet['name']} is dead, so no new commands can be logged.",
                }

            pet["command_log"].append(
                {
                    "user": user_display,
                    "command": cleaned_command,
                    "created_at": created_at.isoformat(),
                }
            )
            pet["command_log"] = pet["command_log"][-250:]
            pet["last_interaction_by"] = user_display
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"{html.escape(user_display)} commanded {html.escape(pet['name'])} to {html.escape(cleaned_command)}.",
            "status_text": self._format_status_text(pet),
        }

    def add_custom_command_log(
        self,
        chat_id: int,
        user_display: str,
        command_text: str,
        created_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return self.add_command_log(chat_id, user_display, command_text, created_at)

    def get_command_log_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            return "No Salamagotchi exists in this chat yet."

        command_log = pet.get("command_log", [])
        if not command_log:
            return f"📜 <b>{html.escape(pet['name'])}'s Command Log</b>\n\n<blockquote expandable>No one has sent {html.escape(pet['name'])} any custom commands yet.</blockquote>"

        entries = []
        for entry in reversed(command_log):
            entries.append(self._format_command_entry_line(pet['name'], entry))

        return (
            f"📜 <b>{html.escape(pet['name'])}'s Command Log</b>\n\n"
            f"<blockquote expandable>{chr(10).join(entries)}</blockquote>"
        )

    def reset_daily_needs(self, chat_id: int, user_display: str) -> Dict[str, Any]:
        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
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
            pet = self._normalize_pet(data.get(str(chat_id)))
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
            pet = self._normalize_pet(data.get(str(chat_id)))
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
            pet = self._record_graveyard_entry(pet)
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "memorial_text": self.build_death_memorial_text(pet),
        }

    def get_death_memorial_preview(self, chat_id: int) -> Dict[str, Any]:
        pet = self.get_pet(chat_id)
        if not pet:
            return {
                "success": False,
                "message": "No Salamagotchi exists in this chat yet.",
            }

        preview_pet = deepcopy(pet)
        if preview_pet.get("alive", False):
            preview_pet["death_reason"] = preview_pet.get("death_reason") or "admin intervention"
        preview_pet["alive"] = False
        preview_pet["died_at"] = preview_pet.get("died_at") or datetime.now(pytz.UTC).isoformat()

        return {
            "success": True,
            "memorial_text": self.build_death_memorial_text(preview_pet),
        }

    def get_stage_art_preview_text(self) -> str:
        preview_pet = {
            "alive": True,
            "feed_count": REQUIREMENTS["feed"],
            "scoop_count": REQUIREMENTS["scoop"],
            "play_count": REQUIREMENTS["play"],
            "wash_count": REQUIREMENTS["wash"],
        }

        lines = ["🖼️ <b>Salamagotchi Stage Art Preview</b>"]
        for stage in STAGES:
            lines.append(
                f"\n<b>{html.escape(stage['name'])}</b>\n<pre>{html.escape(self._render_stage_art(preview_pet, stage))}</pre>"
            )
        return "\n".join(lines)

    def get_evolution_preview_text(self, chat_id: int, stage_name: Optional[str] = None) -> Dict[str, Any]:
        pet = self.get_pet(chat_id)
        if not pet:
            return {"success": False, "message": "No Salamagotchi exists in this chat yet."}

        preview_pet = deepcopy(pet)
        selected_stage = None
        if stage_name:
            stage_name = stage_name.strip().lower()
            for stage in STAGES:
                if stage["name"].lower() == stage_name:
                    selected_stage = stage["name"]
                    break
            if not selected_stage:
                valid = ", ".join(stage["name"] for stage in STAGES)
                return {"success": False, "message": f"Unknown stage. Use one of: {valid}."}
        else:
            current_age = pet.get("age_days", 0)
            next_stage = next((stage for stage in STAGES if stage["min_age"] > current_age), None)
            selected_stage = next_stage["name"] if next_stage else self._get_stage(current_age)["name"]

        if selected_stage == "Baby" and not preview_pet.get("gender"):
            preview_pet["gender"] = self._assign_gender()

        return {
            "success": True,
            "preview_text": self.build_stage_evolution_text(preview_pet, selected_stage),
        }

    def get_time_to_evolve_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet:
            return "No Salamagotchi exists in this chat yet."

        age_days = pet.get("age_days", 0)
        current_stage = self._get_stage(age_days)
        next_stage = None
        for stage in STAGES:
            if stage["min_age"] > age_days:
                next_stage = stage
                break

        safe_name = html.escape(pet.get("name", "Salamagotchi"))
        if not next_stage:
            return (
                f"🐲 <b>{safe_name}</b>\n"
                f"<blockquote expandable><b>Current Stage:</b> {html.escape(current_stage['name'])}\n"
                "This pet has already reached its final evolution stage.</blockquote>"
            )

        days_remaining = next_stage["min_age"] - age_days
        now = datetime.now(pytz.UTC).astimezone(self.timezone)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        evolution_time = next_midnight + timedelta(days=max(0, days_remaining - 1))
        remaining_delta = evolution_time - now
        total_minutes = max(0, int(remaining_delta.total_seconds() // 60))
        remaining_days = total_minutes // (24 * 60)
        remaining_hours = (total_minutes % (24 * 60)) // 60
        remaining_minutes = total_minutes % 60
        remaining_text = (
            f"{remaining_days} day{'s' if remaining_days != 1 else ''}, "
            f"{remaining_hours} hour{'s' if remaining_hours != 1 else ''}, "
            f"{remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
        )
        return (
            f"⏳ <b>{safe_name}</b>\n"
            f"<blockquote expandable><b>Current Stage:</b> {html.escape(current_stage['name'])}\n"
            f"<b>Next Stage:</b> {html.escape(next_stage['name'])}\n"
            f"<b>Current Age:</b> {age_days} day{'s' if age_days != 1 else ''}\n"
            f"<b>Time Remaining:</b> {remaining_text}</blockquote>"
        )

    def get_next_stage_name(self, chat_id: int) -> Optional[str]:
        pet = self.get_pet(chat_id)
        if not pet:
            return None

        current_age = pet.get("age_days", 0)
        next_stage = next((stage for stage in STAGES if stage["min_age"] > current_age), None)
        if not next_stage:
            return None
        return next_stage["name"]

    def get_graveyard_text(self, chat_id: int) -> str:
        pet = self.get_pet(chat_id)
        if not pet or not pet.get("graveyard"):
            return "⚰️ No Salamagotchis have been buried in this chat yet."

        tombstone = (
            "      _.---._\n"
            "    .'       '.\n"
            "   /  R. I. P.  \\\n"
            "  | Salamagotchi |\n"
            "  |   Graveyard  |\n"
            "  |______________|\n"
            "     /_/   \\_\\"
        )

        lines = [
            "⚰️ <b>Salamagotchi Graveyard</b>",
            f"<pre>{html.escape(tombstone)}</pre>",
        ]

        for idx, entry in enumerate(reversed(pet["graveyard"][-10:]), 1):
            learned_text = self._format_education_summary(entry.get("education", {}))
            active_text = self._format_active_study(entry.get("active_study"))
            active_suffix = ""
            if active_text:
                active_suffix = f"\nWas studying: {html.escape(active_text)}"
            lines.append(
                (
                    f"<blockquote expandable><b>{idx}. {html.escape(entry['name'])}</b>\n"
                    f"Lived: {html.escape(entry.get('lived_for', str(entry['age_days'])))}\n"
                    f"Born: {html.escape(entry['born_on'])}\n"
                    f"Died: {html.escape(entry['died_on'])}\n"
                    f"Cause: {html.escape(entry['death_reason'])}\n"
                    f"Learned: {html.escape(learned_text)}"
                    f"{active_suffix}</blockquote>"
                )
            )

        return "\n".join(lines)

    def remove_latest_graveyard_entry(self, chat_id: int) -> Dict[str, Any]:
        with self.lock:
            data = self._read_data()
            pet = self._normalize_pet(data.get(str(chat_id)))
            if not pet:
                return {
                    "success": False,
                    "message": "No Salamagotchi exists in this chat yet.",
                }

            graveyard = pet.get("graveyard", [])
            if not graveyard:
                return {
                    "success": False,
                    "message": "⚰️ The graveyard is already empty.",
                }

            removed_entry = graveyard.pop()
            pet["graveyard"] = graveyard
            data[str(chat_id)] = pet
            self._write_data(data)

        return {
            "success": True,
            "message": f"🧹 Removed the most recent graveyard entry for <b>{html.escape(removed_entry['name'])}</b>.",
            "graveyard_text": self.get_graveyard_text(chat_id),
        }

    def get_help_text(self, bot_username: Optional[str] = None, is_group_chat: bool = False) -> str:
        command_prefix = f"/pet@{bot_username}" if bot_username and is_group_chat else "/pet"
        return (
            "🦎 <b>Salamagotchi Help</b>\n\n"
            "<blockquote expandable>"
            "<b>Commands</b>\n"
            f"<code>{command_prefix} status</code> - Show its status, age, and today's needs\n"
            f"<code>{command_prefix} commands</code> - Show the custom command history\n"
            f"<code>{command_prefix} teach_speak</code> - Teach the pet a custom speaking style by replying to its prompt\n"
            f"<code>{command_prefix} evolve_in</code> - Show how long remains until the next evolution\n"
            f"<code>{command_prefix} spawn &lt;name&gt;</code> - Order a new shared Salamagotchi that arrives in 5 minutes\n"
            f"<code>{command_prefix} feed</code> - Feed it (1 time per day)\n"
            f"<code>{command_prefix} scoop</code> - Scoop poop (1 time per day)\n"
            f"<code>{command_prefix} play</code> - Play with it (1 time per day)\n"
            f"<code>{command_prefix} wash</code> - Wash it (1 time per day)\n"
            f"<code>{command_prefix} help</code> - Show this help text\n\n"
            f"<code>{command_prefix} graveyard</code> - Show previous pets buried in this chat\n\n"
            f"<code>{command_prefix} school start &lt;subject&gt;</code> - Start a new subject toward a diploma\n"
            f"<code>{command_prefix} school continue</code> - Continue today's study streak\n"
            f"<code>{command_prefix} school upgrade &lt;subject&gt;</code> - Upgrade an earned subject to the next level\n"
            f"<code>{command_prefix} school subjects</code> - Show learned subjects\n"
            f"<code>{command_prefix} school status</code> - Show the current study streak\n\n"
            f"<code>{command_prefix} iran</code> - Show the pet enthusiastically supporting Iran\n"
            f"<code>{command_prefix} usa</code> - Show the pet enthusiastically supporting the USA\n"
            f"<code>{command_prefix} russia</code> - Show the pet enthusiastically supporting Russia\n"
            f"<code>{command_prefix} china</code> - Show the pet enthusiastically supporting China\n\n"
            "<b>Admin Commands</b>\n"
            f"<code>{command_prefix} reset</code> - Reset today's care counters\n"
            f"<code>{command_prefix} rename &lt;name&gt;</code> - Rename the current pet\n"
            f"<code>{command_prefix} kill</code> - Forcibly kill the current pet\n\n"
            f"<code>{command_prefix} memorial_preview</code> - Preview the memorial sticker and obituary for 30 seconds\n\n"
            f"<code>{command_prefix} evolution_preview [stage]</code> - Preview a stage evolution announcement\n\n"
            f"<code>{command_prefix} evolution_test</code> - Preview the timed evolution lock and completion flow with a 30-second delay\n\n"
            f"<code>{command_prefix} spawn_test [name]</code> - Preview the delayed spawn flow with a 30-second delay, without storing data\n\n"
            f"<code>{command_prefix} stage_art</code> - Preview the ASCII art for every life stage\n\n"
            f"<code>{command_prefix} graveyard_remove_last</code> - Remove the newest graveyard entry\n\n"
            "<b>Rules</b>\n"
            "• One shared Salamagotchi per chat\n"
            "• You cannot spawn a new one while the current one is alive\n"
            "• A newly spawned pet spends 5 minutes on the way before it arrives as an eggling\n"
            "• Each need can be missed for one day only\n"
            "• Miss the same need two days in a row and it dies\n"
            "• Every day it survives, it grows older and may change stage\n"
            "• During evolution it cannot be interacted with until the transformation completes\n\n"
            "<b>Speaking Style</b>\n"
            "Reply directly to the teach_speak prompt with your rewritten training sentence and the pet will copy that voice in status messages.\n\n"
            "<b>Memorials</b>\n"
            "Death memorials include top caregivers, speech lessons, learned subjects, and the pet's command history.\n\n"
            "<b>Status Screen</b>\n"
            "The status command shows today's progress plus hints for what still needs to be done."
            "</blockquote>"
        )
