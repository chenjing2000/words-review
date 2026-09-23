import json
import tempfile
import unittest
from pathlib import Path

from app.example_audio import examples_path, load_example_audio


class ExampleAudioTests(unittest.TestCase):
    def test_examples_path_uses_wordlist_resource_folder(self):
        path = Path("/tmp/education.json")
        self.assertEqual(
            examples_path(path),
            Path("/tmp/education/examples.json"),
        )

    def test_loads_audio_by_eid_and_keeps_only_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            wordlist_path = folder / "education.json"
            resource_dir = folder / "education"
            examples_dir = resource_dir / "examples"
            examples_dir.mkdir(parents=True)

            uk = examples_dir / "articulate_e01_uk.mp3"
            uk.write_bytes(b"test")

            data = {
                "schema_version": 1,
                "words": {
                    "articulate": [
                        {
                            "eid": "501372",
                            "text": "He is a highly articulate speaker.",
                            "uk": "examples/articulate_e01_uk.mp3",
                            "us": "examples/articulate_e01_us.mp3",
                        }
                    ]
                },
            }
            (resource_dir / "examples.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

            result = load_example_audio(wordlist_path)
            self.assertEqual(
                result,
                {"501372": {"uk": uk}},
            )

    def test_missing_examples_json_returns_empty_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wordlist_path = Path(temp_dir) / "education.json"
            self.assertEqual(load_example_audio(wordlist_path), {})

    def test_old_entries_without_eid_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            resource_dir = folder / "education"
            resource_dir.mkdir()
            (resource_dir / "examples.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "words": {
                            "old": [
                                {
                                    "text": "Old format has no eid.",
                                    "uk": "examples/old_e01_uk.mp3",
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_example_audio(folder / "education.json")

    def test_non_six_digit_eid_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            resource_dir = folder / "education"
            resource_dir.mkdir()
            (resource_dir / "examples.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "words": {
                            "bad": [{"eid": "bad_123456", "text": "Bad."}]
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_example_audio(folder / "education.json")

    def test_duplicate_eid_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            resource_dir = folder / "education"
            resource_dir.mkdir()
            (resource_dir / "examples.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "words": {
                            "a": [{"eid": "123456", "text": "A"}],
                            "b": [{"eid": "123456", "text": "B"}],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_example_audio(folder / "education.json")


if __name__ == "__main__":
    unittest.main()
