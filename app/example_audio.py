import json
from pathlib import Path


def resource_folder(wordlist_path: Path) -> Path:
    return wordlist_path.parent / wordlist_path.stem


def examples_path(wordlist_path: Path) -> Path:
    return resource_folder(wordlist_path) / "examples.json"


def load_example_audio(wordlist_path: Path) -> dict[str, dict[str, Path]]:
    path = examples_path(wordlist_path)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"例句音频配置文件格式错误: {path.name}") from exc

    if not isinstance(data, dict):
        raise ValueError("例句音频配置文件根节点必须是 JSON object")
    if data.get("schema_version") != 1:
        raise ValueError(
            f"不支持的 examples schema_version: {data.get('schema_version')}"
        )

    raw_words = data.get("words")
    if not isinstance(raw_words, dict):
        raise ValueError("examples.json 缺少 words object")

    base = resource_folder(wordlist_path)
    result: dict[str, dict[str, Path]] = {}
    seen = set()

    for entries in raw_words.values():
        if not isinstance(entries, list):
            continue

        for item in entries:
            if not isinstance(item, dict):
                continue

            eid = item.get("eid")
            if not isinstance(eid, str):
                raise ValueError("examples.json 条目缺少有效 eid")
            eid = eid.strip()
            if len(eid) != 6 or not eid.isdigit():
                raise ValueError("examples.json eid 必须是 6 位数字")

            if eid in seen:
                raise ValueError(f"examples.json eid 重复: {eid}")
            seen.add(eid)

            accents: dict[str, Path] = {}
            for accent in ("uk", "us"):
                relative_path = item.get(accent)
                if not isinstance(relative_path, str) or not relative_path.strip():
                    continue

                audio_path = base / relative_path.strip()
                if audio_path.is_file():
                    accents[accent] = audio_path

            if accents:
                result[eid] = accents

    return result
