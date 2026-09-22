import json
from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile


class AppStateRepository:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_last_wordlist(self) -> str:
        if not self.path.exists():
            return ""

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError, UnicodeError):
            return ""

        if not isinstance(data, dict):
            return ""
        if data.get("schema_version") != 1:
            return ""

        return str(data.get("last_wordlist", "")).strip()

    def save_last_wordlist(self, filename: str):
        data = {
            "schema_version": 1,
            "last_wordlist": filename,
        }
        self._atomic_write(data)

    def _atomic_write(self, data: dict):
        save_file = QSaveFile(str(self.path))

        if not save_file.open(QIODevice.WriteOnly | QIODevice.Text):
            raise OSError(f"无法写入文件: {self.path}")

        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        written = save_file.write(text.encode("utf-8"))

        if written < 0:
            save_file.cancelWriting()
            raise OSError(f"写入文件失败: {self.path}")

        if not save_file.commit():
            raise OSError(f"提交文件失败: {self.path}")
