import json
import tempfile
import unittest
from pathlib import Path

from app.models.progress import (
    ReviewMode,
    ReviewSessionState,
    StudyStatus,
    WordListProgress,
    WordProgress,
)
from app.repositories.progress_repository import ProgressRepository


class ProgressRepositoryTests(unittest.TestCase):
    def test_progress_path_uses_wordlist_stem_folder(self):
        repository = ProgressRepository()
        path = Path("/tmp/education.json")
        self.assertEqual(
            repository.progress_path(path),
            Path("/tmp/education/progress.json"),
        )

    def test_missing_progress_returns_default_progress(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ProgressRepository()
            progress = repository.load(Path(temp_dir) / "education.json")

            self.assertEqual(progress.schema_version, 1)
            self.assertEqual(progress.current_index, 0)
            self.assertEqual(progress.words, {})
            self.assertEqual(progress.review_session.mode, ReviewMode.ALL)

    def test_save_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ProgressRepository()
            wordlist_path = Path(temp_dir) / "education.json"
            progress = WordListProgress(
                current_index=8,
                review_session=ReviewSessionState(
                    mode=ReviewMode.UNCERTAIN,
                    queue_position=2,
                    indices=[1, 5, 8, 12],
                    completed=False,
                ),
                words={
                    "research_001": WordProgress(
                        review_count=3,
                        study_status=StudyStatus.UNCERTAIN,
                    )
                },
            )

            repository.save(wordlist_path, progress)
            loaded = repository.load(wordlist_path)

            self.assertEqual(loaded.current_index, 8)
            self.assertEqual(loaded.review_session.mode, ReviewMode.UNCERTAIN)
            self.assertEqual(loaded.review_session.queue_position, 2)
            self.assertEqual(loaded.review_session.indices, [1, 5, 8, 12])
            self.assertFalse(loaded.review_session.completed)
            self.assertEqual(loaded.words["research_001"].review_count, 3)
            self.assertEqual(
                loaded.words["research_001"].study_status,
                StudyStatus.UNCERTAIN,
            )

    def test_malformed_json_raises_value_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ProgressRepository()
            wordlist_path = Path(temp_dir) / "education.json"
            path = repository.progress_path(wordlist_path)
            path.parent.mkdir(parents=True)
            path.write_text("{bad json", encoding="utf-8")

            with self.assertRaises(ValueError):
                repository.load(wordlist_path)

    def test_wrong_schema_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ProgressRepository()
            wordlist_path = Path(temp_dir) / "education.json"
            path = repository.progress_path(wordlist_path)
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps({"schema_version": 2}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                repository.load(wordlist_path)

    def test_save_raises_if_resource_directory_cannot_be_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ProgressRepository()
            wordlist_path = Path(temp_dir) / "education.json"
            resource_path = Path(temp_dir) / "education"
            resource_path.write_text("not a directory", encoding="utf-8")

            with self.assertRaises(OSError):
                repository.save(wordlist_path, WordListProgress())


if __name__ == "__main__":
    unittest.main()
