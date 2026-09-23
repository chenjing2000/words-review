import json
import tempfile
import unittest
from pathlib import Path

from app.pronunciation import find_audio_path, load_pronunciations, pronunciation_path


class PronunciationTests(unittest.TestCase):
    def test_pronunciation_path_uses_audio_json_in_wordlist_resource_folder(self):
        path = Path("/tmp/education.json")
        self.assertEqual(
            pronunciation_path(path),
            Path("/tmp/education/audio.json"),
        )

    def test_load_existing_format_and_find_first_existing_audio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            wordlist_path = folder / "education.json"
            resource_dir = folder / "education"
            audio_dir = resource_dir / "audio"
            audio_dir.mkdir(parents=True)

            second_audio = audio_dir / "research_uk_2.mp3"
            second_audio.write_bytes(b"test")

            data = {
                "schema_version": 1,
                "words": {
                    "research": {
                        "uk": [
                            "audio/research_uk_1.mp3",
                            "audio/research_uk_2.mp3",
                        ],
                        "us": [],
                    }
                },
            }
            (resource_dir / "audio.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

            pronunciations = load_pronunciations(wordlist_path)
            result = find_audio_path(wordlist_path, pronunciations, "research", "uk")
            self.assertEqual(result, second_audio)

    def test_find_audio_falls_back_to_casefold_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            wordlist_path = folder / "education.json"
            audio_dir = folder / "education" / "audio"
            audio_dir.mkdir(parents=True)
            audio = audio_dir / "MOOC_us.mp3"
            audio.write_bytes(b"test")

            pronunciations = {
                "MOOC": {
                    "uk": [],
                    "us": ["audio/MOOC_us.mp3"],
                }
            }
            result = find_audio_path(wordlist_path, pronunciations, "mooc", "us")
            self.assertEqual(result, audio)

    def test_old_pronunciation_json_is_not_used(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            wordlist_path = folder / "words.json"
            resource_dir = folder / "words"
            resource_dir.mkdir()
            (resource_dir / "pronunciation.json").write_text(
                json.dumps({"schema_version": 1, "words": {"old": {}}}),
                encoding="utf-8",
            )

            self.assertEqual(load_pronunciations(wordlist_path), {})


if __name__ == "__main__":
    unittest.main()
