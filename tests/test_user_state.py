import json
import tempfile
import unittest
from pathlib import Path

import user_state


class UserStateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config_path = Path(self.directory.name) / "config.json"

    def tearDown(self):
        self.directory.cleanup()

    def files(self):
        return sorted(path.name for path in Path(self.directory.name).iterdir())

    def test_older_config_is_split_into_its_own_files_once(self):
        slot = {"type": "fixed", "url": "https://example.test/a"}
        self.config_path.write_text(json.dumps({
            "poster_theme": "dark",
            "slots": [slot],
            "shortlist": [{"url": "https://example.test/b"}],
            "subscription_metadata": {"https://example.test/feed.xml": {"tags": ["Climate"]}},
        }), encoding="utf-8")

        self.assertTrue(user_state.migrate(self.config_path))
        self.assertFalse(user_state.migrate(self.config_path))

        self.assertEqual(self.files(), ["channel-notes.json", "config.json", "draft.json", "shortlist.json"])
        self.assertEqual(json.loads(self.config_path.read_text(encoding="utf-8")), {"poster_theme": "dark"})
        loaded = user_state.load(self.config_path)
        self.assertEqual(loaded["slots"], [slot])
        self.assertEqual(loaded["subscription_metadata"]["https://example.test/feed.xml"]["tags"], ["Climate"])

    def test_missing_files_load_as_empty_and_saving_writes_them(self):
        self.config_path.write_text(json.dumps({"poster_theme": "dark"}), encoding="utf-8")

        loaded = user_state.load(self.config_path)
        self.assertEqual((loaded["slots"], loaded["shortlist"], loaded["subscription_metadata"]), ([], [], {}))
        loaded["shortlist"].append({"url": "https://example.test/c"})
        user_state.save(self.config_path, loaded)

        self.assertEqual(json.loads((Path(self.directory.name) / "shortlist.json").read_text(encoding="utf-8")), [{"url": "https://example.test/c"}])
        self.assertNotIn("shortlist", json.loads(self.config_path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
