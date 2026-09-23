import json
from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile

from app.models.progress import (
    ReviewMode,
    ReviewSessionState,
    StudyStatus,
    WordListProgress,
    WordProgress,
)


class ProgressRepository:
    def progress_path(self, wordlist_path: Path) -> Path:
        return wordlist_path.parent / wordlist_path.stem / "progress.json"

    def load(self, wordlist_path: Path) -> WordListProgress:
        path = self.progress_path(wordlist_path)
        if not path.exists():
            return WordListProgress()

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError(f"学习记录文件格式错误: {path.name}") from exc

        return self._parse(data)

    def save(self, wordlist_path: Path, progress: WordListProgress):
        path = self.progress_path(wordlist_path)
        data = self._to_dict(progress)
        self._atomic_write(path, data)

    def _parse(self, data: dict) -> WordListProgress:
        if not isinstance(data, dict):
            raise ValueError("学习记录根节点必须是 JSON object")

        schema_version = data.get("schema_version")
        if schema_version != 1:
            raise ValueError(f"不支持的 progress schema_version: {schema_version}")

        current_index = data.get("current_index", 0)
        if not isinstance(current_index, int):
            current_index = 0

        session = self._parse_session(data.get("review_session", {}))
        words = {}

        raw_words = data.get("words", {})
        if isinstance(raw_words, dict):
            for wid, item in raw_words.items():
                if not isinstance(item, dict):
                    continue

                review_count = item.get("review_count", 0)
                if not isinstance(review_count, int) or review_count < 0:
                    review_count = 0

                status_value = item.get("study_status", 0)
                try:
                    status = StudyStatus(int(status_value))
                except (ValueError, TypeError):
                    status = StudyStatus.UNLEARNED

                words[str(wid)] = WordProgress(
                    review_count=review_count,
                    study_status=status,
                )

        return WordListProgress(
            schema_version=1,
            current_index=current_index,
            review_session=session,
            words=words,
        )

    def _parse_session(self, data) -> ReviewSessionState:
        if not isinstance(data, dict):
            return ReviewSessionState()

        try:
            mode = ReviewMode(int(data.get("mode", -1)))
        except (ValueError, TypeError):
            mode = ReviewMode.ALL

        queue_position = data.get("queue_position", 0)
        if not isinstance(queue_position, int) or queue_position < 0:
            queue_position = 0

        indices = data.get("indices", [])
        if not isinstance(indices, list):
            indices = []
        indices = [item for item in indices if isinstance(item, int)]

        completed = bool(data.get("completed", False))

        return ReviewSessionState(
            mode=mode,
            queue_position=queue_position,
            indices=indices,
            completed=completed,
        )

    def _to_dict(self, progress: WordListProgress) -> dict:
        return {
            "schema_version": 1,
            "current_index": progress.current_index,
            "review_session": {
                "mode": int(progress.review_session.mode),
                "queue_position": progress.review_session.queue_position,
                "indices": progress.review_session.indices,
                "completed": progress.review_session.completed,
            },
            "words": {
                wid: {
                    "review_count": item.review_count,
                    "study_status": int(item.study_status),
                }
                for wid, item in progress.words.items()
            },
        }

    @staticmethod
    def _atomic_write(path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        save_file = QSaveFile(str(path))

        if not save_file.open(QIODevice.WriteOnly | QIODevice.Text):
            raise OSError(f"无法写入文件: {path}")

        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        written = save_file.write(text.encode("utf-8"))

        if written < 0:
            save_file.cancelWriting()
            raise OSError(f"写入文件失败: {path}")

        if not save_file.commit():
            raise OSError(f"提交文件失败: {path}")
