import json
import tempfile
import unittest
from pathlib import Path

from app.repositories.wordlist_repository import WordListRepository


class WordListRepositoryTests(unittest.TestCase):
    def test_english_meaning_is_optional(self):
        data = {
            "schema_version": 1,
            "name": "test",
            "words": [
                {
                    "id": "test_001",
                    "word": "test",
                    "senses": [
                        {
                            "pos": "n.",
                            "chinese_meaning": "测试",
                            "example": "This is a test.",
                            "example_translation": "这是一个测试。",
                            "synonyms": [],
                            "collocations": [],
                        }
                    ],
                }
            ],
        }

        repository = WordListRepository.__new__(WordListRepository)
        wordlist = repository._parse_wordlist(data)

        sense = wordlist.words[0].senses[0]
        self.assertEqual(sense.english_meaning, "")
        self.assertEqual(sense.chinese_meaning, "测试")

    def test_chinese_meaning_is_required(self):
        data = {
            "schema_version": 1,
            "name": "test",
            "words": [
                {
                    "id": "test_001",
                    "word": "test",
                    "senses": [
                        {
                            "pos": "n.",
                            "english_meaning": "an examination or check",
                            "synonyms": [],
                            "collocations": [],
                        }
                    ],
                }
            ],
        }

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaises(ValueError):
            repository._parse_wordlist(data)

    def test_string_lists_ignore_non_string_items(self):
        values = [" tackle ", 123, None, "", "confront"]
        result = WordListRepository._string_list(values)
        self.assertEqual(result, ["tackle", "confront"])

    def test_scan_loads_only_valid_json_in_selected_folder(self):
        valid_data = {
            "schema_version": 1,
            "name": "valid",
            "words": [
                {
                    "id": "word_001",
                    "word": "word",
                    "senses": [{"chinese_meaning": "单词"}],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            (folder / "valid.json").write_text(
                json.dumps(valid_data, ensure_ascii=False), encoding="utf-8"
            )
            (folder / "invalid.json").write_text('{"name": "invalid"}', encoding="utf-8")

            nested = folder / "nested"
            nested.mkdir()
            (nested / "nested.json").write_text(
                json.dumps(valid_data, ensure_ascii=False), encoding="utf-8"
            )

            repository = WordListRepository(folder)
            entries, errors = repository.scan()

            self.assertEqual([path.name for path, _ in entries], ["valid.json"])
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0][0].name, "invalid.json")


if __name__ == "__main__":
    unittest.main()
