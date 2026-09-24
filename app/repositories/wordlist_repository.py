import json
from pathlib import Path

from app.models.word import Word, WordList, WordSense


class WordListRepository:
    def __init__(self, folder: Path):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)

    def scan(self):
        return sorted(self.folder.glob("*.json"), key=lambda p: p.name.lower())

    def load(self, path: Path) -> WordList:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return self._parse_wordlist(data)

    def _parse_wordlist(self, data: dict) -> WordList:
        if not isinstance(data, dict):
            raise ValueError("WordList 根节点必须是 JSON object")

        schema_version = data.get("schema_version")
        if type(schema_version) is not int or schema_version != 1:
            raise ValueError(f"不支持的 schema_version: {schema_version}")

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("WordList name 必须是非空字符串")
        name = name.strip()

        description = data.get("description", "")
        if not isinstance(description, str):
            raise ValueError("WordList description 必须是字符串")

        raw_words = data.get("words")
        if not isinstance(raw_words, list) or not raw_words:
            raise ValueError("words 必须是非空数组")

        words = []
        wids = set()
        word_keys = set()
        eids = set()

        for index, item in enumerate(raw_words):
            word = self._parse_word(item, index)
            if word.wid in wids:
                raise ValueError(f"Word.wid 重复: {word.wid}")
            wids.add(word.wid)

            word_key = word.word.casefold()
            if word_key in word_keys:
                raise ValueError(f"Word.word 重复（忽略大小写）: {word.word}")
            word_keys.add(word_key)

            for sense in word.senses:
                if sense.eid:
                    if sense.eid in eids:
                        raise ValueError(f"sense.eid 重复: {sense.eid}")
                    eids.add(sense.eid)

            words.append(word)

        return WordList(
            schema_version=1,
            name=name,
            description=description,
            words=words,
        )

    def _parse_word(self, data: dict, index: int) -> Word:
        if not isinstance(data, dict):
            raise ValueError(f"第 {index + 1} 个 Word 必须是 object")

        wid = data.get("wid")
        text = data.get("word")

        if not isinstance(wid, str) or not wid.strip():
            raise ValueError(f"第 {index + 1} 个 Word 的 wid 必须是非空字符串")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"第 {index + 1} 个 Word 的 word 必须是非空字符串")

        wid = wid.strip()
        text = text.strip()

        phonetic = data.get("phonetic", "")
        notes = data.get("notes", "")
        if not isinstance(phonetic, str):
            raise ValueError(f"Word '{text}' 的 phonetic 必须是字符串")
        if not isinstance(notes, str):
            raise ValueError(f"Word '{text}' 的 notes 必须是字符串")

        raw_senses = data.get("senses")
        if not isinstance(raw_senses, list) or not raw_senses:
            raise ValueError(f"Word '{text}' 缺少 senses")

        senses = []
        for sense_index, item in enumerate(raw_senses):
            senses.append(self._parse_sense(item, text, sense_index))

        return Word(
            wid=wid,
            word=text,
            phonetic=phonetic.strip(),
            senses=senses,
            notes=notes.strip(),
        )

    def _parse_sense(self, data: dict, word: str, index: int) -> WordSense:
        if not isinstance(data, dict):
            raise ValueError(f"Word '{word}' 的第 {index + 1} 个 sense 必须是 object")

        fields = {}
        for key in (
            "pos",
            "english_meaning",
            "chinese_meaning",
            "eid",
            "example",
            "example_translation",
        ):
            value = data.get(key, "")
            if not isinstance(value, str):
                raise ValueError(
                    f"Word '{word}' 的第 {index + 1} 个 sense 的 {key} 必须是字符串"
                )
            fields[key] = value.strip()

        if not fields["chinese_meaning"]:
            raise ValueError(
                f"Word '{word}' 的第 {index + 1} 个 sense 缺少 chinese_meaning"
            )

        if fields["example"]:
            if len(fields["eid"]) != 6 or not fields["eid"].isdigit():
                raise ValueError(
                    f"Word '{word}' 的第 {index + 1} 个 sense 的 eid 必须是 6 位数字"
                )
        elif fields["eid"]:
            raise ValueError(
                f"Word '{word}' 的第 {index + 1} 个 sense 无例句但存在 eid"
            )

        return WordSense(
            pos=fields["pos"],
            english_meaning=fields["english_meaning"],
            chinese_meaning=fields["chinese_meaning"],
            eid=fields["eid"],
            example=fields["example"],
            example_translation=fields["example_translation"],
            synonyms=self._string_list(
                data.get("synonyms", []), word, index, "synonyms"
            ),
            collocations=self._string_list(
                data.get("collocations", []), word, index, "collocations"
            ),
        )

    @staticmethod
    def _string_list(value, word: str, index: int, field_name: str):
        if not isinstance(value, list):
            raise ValueError(
                f"Word '{word}' 的第 {index + 1} 个 sense 的 {field_name} 必须是字符串数组"
            )

        result = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError(
                    f"Word '{word}' 的第 {index + 1} 个 sense 的 {field_name} 必须是字符串数组"
                )
            if item.strip():
                result.append(item.strip())
        return result
