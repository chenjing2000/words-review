import json
import tempfile
import unittest
from pathlib import Path

from app.repositories.wordlist_repository import WordListRepository


class WordListRepositoryTests(unittest.TestCase):
    def _valid_data(self):
        return {
            "schema_version": 1,
            "name": "test (1)",
            "description": "",
            "words": [
                {
                    "wid": "test",
                    "word": "test",
                    "phonetic": "/test/",
                    "senses": [
                        {
                            "pos": "n.",
                            "english_meaning": "an examination or check",
                            "chinese_meaning": "测试",
                            "eid": "123456",
                            "example": "This is a test.",
                            "example_translation": "这是一个测试。",
                            "synonyms": [],
                            "collocations": [],
                        }
                    ],
                    "notes": "",
                }
            ],
        }

    def test_english_meaning_is_optional(self):
        data = self._valid_data()
        del data["words"][0]["senses"][0]["english_meaning"]

        repository = WordListRepository.__new__(WordListRepository)
        wordlist = repository._parse_wordlist(data)

        sense = wordlist.words[0].senses[0]
        self.assertEqual(sense.english_meaning, "")
        self.assertEqual(sense.chinese_meaning, "测试")

    def test_chinese_meaning_is_required(self):
        data = self._valid_data()
        del data["words"][0]["senses"][0]["chinese_meaning"]

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaises(ValueError):
            repository._parse_wordlist(data)

    def test_schema_version_must_be_explicit_integer_one(self):
        repository = WordListRepository.__new__(WordListRepository)

        missing = self._valid_data()
        del missing["schema_version"]
        with self.assertRaises(ValueError):
            repository._parse_wordlist(missing)

        wrong_type = self._valid_data()
        wrong_type["schema_version"] = "1"
        with self.assertRaises(ValueError):
            repository._parse_wordlist(wrong_type)

    def test_required_word_fields_must_be_strings(self):
        repository = WordListRepository.__new__(WordListRepository)

        bad_wid = self._valid_data()
        bad_wid["words"][0]["wid"] = 123
        with self.assertRaises(ValueError):
            repository._parse_wordlist(bad_wid)

        bad_word = self._valid_data()
        bad_word["words"][0]["word"] = None
        with self.assertRaises(ValueError):
            repository._parse_wordlist(bad_word)

    def test_optional_string_field_rejects_wrong_type(self):
        data = self._valid_data()
        data["words"][0]["notes"] = ["not", "a", "string"]

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaises(ValueError):
            repository._parse_wordlist(data)

    def test_synonyms_and_collocations_must_be_string_lists(self):
        repository = WordListRepository.__new__(WordListRepository)

        bad_list = self._valid_data()
        bad_list["words"][0]["senses"][0]["synonyms"] = ["check", 123]
        with self.assertRaises(ValueError):
            repository._parse_wordlist(bad_list)

        wrong_type = self._valid_data()
        wrong_type["words"][0]["senses"][0]["collocations"] = "take a test"
        with self.assertRaises(ValueError):
            repository._parse_wordlist(wrong_type)


    def test_old_id_field_is_not_accepted(self):
        data = self._valid_data()
        word = data["words"][0]
        word["id"] = word.pop("wid")

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaises(ValueError):
            repository._parse_wordlist(data)

    def test_eid_is_optional_when_example_is_empty(self):
        data = self._valid_data()
        sense = data["words"][0]["senses"][0]
        sense["example"] = ""
        sense["example_translation"] = ""
        del sense["eid"]

        repository = WordListRepository.__new__(WordListRepository)
        wordlist = repository._parse_wordlist(data)
        self.assertEqual(wordlist.words[0].senses[0].eid, "")

    def test_eid_must_be_string_when_present(self):
        data = self._valid_data()
        data["words"][0]["senses"][0]["eid"] = 123456

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaises(ValueError):
            repository._parse_wordlist(data)

    def test_example_requires_six_digit_eid(self):
        repository = WordListRepository.__new__(WordListRepository)

        missing = self._valid_data()
        missing["words"][0]["senses"][0]["eid"] = ""
        with self.assertRaises(ValueError):
            repository._parse_wordlist(missing)

        wrong_format = self._valid_data()
        wrong_format["words"][0]["senses"][0]["eid"] = "test_123456"
        with self.assertRaises(ValueError):
            repository._parse_wordlist(wrong_format)

        too_short = self._valid_data()
        too_short["words"][0]["senses"][0]["eid"] = "12345"
        with self.assertRaises(ValueError):
            repository._parse_wordlist(too_short)

    def test_eid_may_start_with_zero(self):
        data = self._valid_data()
        data["words"][0]["senses"][0]["eid"] = "001234"

        repository = WordListRepository.__new__(WordListRepository)
        wordlist = repository._parse_wordlist(data)
        self.assertEqual(wordlist.words[0].senses[0].eid, "001234")

    def test_non_empty_eid_is_rejected_when_example_is_empty(self):
        data = self._valid_data()
        sense = data["words"][0]["senses"][0]
        sense["example"] = ""
        sense["example_translation"] = ""
        sense["eid"] = "123456"

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaises(ValueError):
            repository._parse_wordlist(data)

    def test_duplicate_word_is_rejected_case_insensitively(self):
        data = self._valid_data()
        second = dict(data["words"][0])
        second["wid"] = "test2"
        second["word"] = "TEST"
        second["senses"] = [dict(data["words"][0]["senses"][0])]
        second["senses"][0]["eid"] = "654321"
        data["words"].append(second)

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaisesRegex(ValueError, r"Word\.word 重复"):
            repository._parse_wordlist(data)

    def test_duplicate_non_empty_eid_is_rejected(self):
        data = self._valid_data()
        second = dict(data["words"][0])
        second["wid"] = "test2"
        second["word"] = "test2"
        second["senses"] = [dict(data["words"][0]["senses"][0])]
        data["words"].append(second)

        repository = WordListRepository.__new__(WordListRepository)
        with self.assertRaises(ValueError):
            repository._parse_wordlist(data)

    def test_scan_loads_only_valid_json_in_selected_folder(self):
        valid_data = self._valid_data()

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
