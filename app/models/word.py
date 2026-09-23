from dataclasses import dataclass, field


@dataclass
class WordSense:
    pos: str = ""
    english_meaning: str = ""
    chinese_meaning: str = ""
    eid: str = ""
    example: str = ""
    example_translation: str = ""
    synonyms: list[str] = field(default_factory=list)
    collocations: list[str] = field(default_factory=list)


@dataclass
class Word:
    wid: str
    word: str
    phonetic: str = ""
    senses: list[WordSense] = field(default_factory=list)
    notes: str = ""


@dataclass
class WordList:
    schema_version: int
    name: str
    description: str = ""
    words: list[Word] = field(default_factory=list)
