import json
from pathlib import Path

from app.models.word import Word, WordList, WordSense


class WordListRepository:
    def __init__(self, folder: Path):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)

    def scan(self):
        wordlists = []
        errors = []

        for path in sorted(self.folder.glob("*.json"), key=lambda p: p.name.lower()):
            try:
                wordlists.append((path, self.load(path)))
            except (OSError, ValueError, UnicodeError) as exc:
                errors.append((path, str(exc)))

        return wordlists, errors

    def load(self, path: Path) -> WordList:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return self._parse_wordlist(data)

    def _parse_wordlist(self, data: dict) -> WordList:
        if not isinstance(data, dict):
            raise ValueError("WordList 根节点必须是 JSON object")

        schema_version = data.get("schema_version", 1)
        if schema_version != 1:
            raise ValueError(f"不支持的 schema_version: {schema_version}")

        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("缺少 WordList name")

        raw_words = data.get("words")
        if not isinstance(raw_words, list) or not raw_words:
            raise ValueError("words 必须是非空数组")

        words = []
        ids = set()

        for index, item in enumerate(raw_words):
            word = self._parse_word(item, index)
            if word.id in ids:
                raise ValueError(f"Word.id 重复: {word.id}")
            ids.add(word.id)
            words.append(word)

        return WordList(
            schema_version=1,
            name=name,
            description=str(data.get("description", "")),
            words=words,
        )

    def _parse_word(self, data: dict, index: int) -> Word:
        if not isinstance(data, dict):
            raise ValueError(f"第 {index + 1} 个 Word 必须是 object")

        word_id = str(data.get("id", "")).strip()
        text = str(data.get("word", "")).strip()

        if not word_id:
            raise ValueError(f"第 {index + 1} 个 Word 缺少 id")
        if not text:
            raise ValueError(f"第 {index + 1} 个 Word 缺少 word")

        raw_senses = data.get("senses")
        if not isinstance(raw_senses, list) or not raw_senses:
            raise ValueError(f"Word '{text}' 缺少 senses")

        senses = []
        for sense_index, item in enumerate(raw_senses):
            senses.append(self._parse_sense(item, text, sense_index))

        return Word(
            id=word_id,
            word=text,
            phonetic=str(data.get("phonetic", "")),
            senses=senses,
            notes=str(data.get("notes", "")),
        )

    def _parse_sense(self, data: dict, word: str, index: int) -> WordSense:
        if not isinstance(data, dict):
            raise ValueError(f"Word '{word}' 的第 {index + 1} 个 sense 必须是 object")

        chinese_meaning = str(data.get("chinese_meaning", "")).strip()
        if not chinese_meaning:
            raise ValueError(
                f"Word '{word}' 的第 {index + 1} 个 sense 缺少 chinese_meaning"
            )

        return WordSense(
            pos=str(data.get("pos", "")),
            english_meaning=str(data.get("english_meaning", "")).strip(),
            chinese_meaning=chinese_meaning,
            example=str(data.get("example", "")).strip(),
            example_translation=str(data.get("example_translation", "")).strip(),
            synonyms=self._string_list(data.get("synonyms")),
            collocations=self._string_list(data.get("collocations")),
        )

    @staticmethod
    def _string_list(value):
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
