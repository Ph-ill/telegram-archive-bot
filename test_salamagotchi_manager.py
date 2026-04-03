import os
import tempfile
import unittest
from datetime import datetime

import pytz

from salamagotchi.manager import SalamagotchiManager


class TestSalamagotchiManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SalamagotchiManager(self.temp_dir, "America/Chicago")
        self.chat_id = 12345

    def tearDown(self):
        data_file = os.path.join(self.temp_dir, "salamagotchi.json")
        if os.path.exists(data_file):
            os.remove(data_file)
        temp_file = f"{data_file}.tmp"
        if os.path.exists(temp_file):
            os.remove(temp_file)
        os.rmdir(self.temp_dir)

    def _dt(self, year, month, day, hour=12):
        return pytz.UTC.localize(datetime(year, month, day, hour))

    def test_spawn_requires_name_and_blocks_when_alive(self):
        result = self.manager.spawn(self.chat_id, "Sal", "alice", now=self._dt(2026, 4, 3))
        self.assertTrue(result["success"])

        second = self.manager.spawn(self.chat_id, "New Sal", "bob", now=self._dt(2026, 4, 3, 13))
        self.assertFalse(second["success"])
        self.assertIn("still alive", second["message"])

    def test_status_includes_hints_for_remaining_requirements(self):
        self.manager.spawn(self.chat_id, "Sal", "alice", now=self._dt(2026, 4, 3))
        self.manager.perform_action(self.chat_id, "feed", "alice")
        self.manager.perform_action(self.chat_id, "play", "alice")

        status = self.manager.get_status_text(self.chat_id)
        self.assertIn("Feed: 1/2", status)
        self.assertIn("Play: 1/1", status)
        self.assertIn("Needs 1 more feeding today.", status)
        self.assertIn("Needs 2 more scoops today.", status)
        self.assertIn("Needs a wash today.", status)
        self.assertIn("Play completed for today.", status)

    def test_action_caps_at_daily_limit(self):
        self.manager.spawn(self.chat_id, "Sal", "alice", now=self._dt(2026, 4, 3))
        self.assertTrue(self.manager.perform_action(self.chat_id, "wash", "alice")["success"])
        result = self.manager.perform_action(self.chat_id, "wash", "alice")

        self.assertFalse(result["success"])
        self.assertIn("already has enough wash", result["message"])

    def test_rollover_ages_pet_when_all_requirements_met(self):
        self.manager.spawn(self.chat_id, "Sal", "alice", now=self._dt(2026, 4, 3))
        for _ in range(2):
            self.manager.perform_action(self.chat_id, "feed", "alice")
            self.manager.perform_action(self.chat_id, "scoop", "alice")
        self.manager.perform_action(self.chat_id, "play", "alice")
        self.manager.perform_action(self.chat_id, "wash", "alice")

        events = self.manager.process_daily_rollovers(now=self._dt(2026, 4, 4, 6))
        pet = self.manager.get_pet(self.chat_id)

        self.assertEqual(len(events), 1)
        self.assertTrue(pet["alive"])
        self.assertEqual(pet["age_days"], 1)
        self.assertEqual(pet["feed_count"], 0)
        self.assertEqual(pet["missed_feed_days"], 0)

    def test_neglect_one_day_warns_but_second_day_kills(self):
        self.manager.spawn(self.chat_id, "Sal", "alice", now=self._dt(2026, 4, 3))

        first_rollover = self.manager.process_daily_rollovers(now=self._dt(2026, 4, 4, 6))
        self.assertEqual(len(first_rollover), 1)
        pet = self.manager.get_pet(self.chat_id)
        self.assertTrue(pet["alive"])
        self.assertEqual(pet["missed_feed_days"], 1)

        status = self.manager.get_status_text(self.chat_id)
        self.assertIn("Warning: Feeding was missed yesterday.", status)

        second_rollover = self.manager.process_daily_rollovers(now=self._dt(2026, 4, 5, 6))
        pet = self.manager.get_pet(self.chat_id)
        self.assertEqual(len(second_rollover), 1)
        self.assertFalse(pet["alive"])
        self.assertEqual(pet["death_reason"], "starvation")

    def test_dead_pet_can_be_replaced(self):
        self.manager.spawn(self.chat_id, "Sal", "alice", now=self._dt(2026, 4, 3))
        self.manager.process_daily_rollovers(now=self._dt(2026, 4, 4, 6))
        self.manager.process_daily_rollovers(now=self._dt(2026, 4, 5, 6))

        result = self.manager.spawn(self.chat_id, "Sal Two", "bob", now=self._dt(2026, 4, 5, 7))
        self.assertTrue(result["success"])
        pet = self.manager.get_pet(self.chat_id)
        self.assertEqual(pet["name"], "Sal Two")
        self.assertTrue(pet["alive"])


if __name__ == "__main__":
    unittest.main()
