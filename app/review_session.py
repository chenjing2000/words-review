from app.models.progress import (
    ReviewMode,
    ReviewSessionState,
    StudyStatus,
    WordListProgress,
    WordProgress,
)
from app.models.word import Word, WordList


class ReviewSession:
    def __init__(self, wordlist: WordList, progress: WordListProgress):
        self.wordlist = wordlist
        self.progress = progress
        self._repair_progress()

    @property
    def current_word(self) -> Word | None:
        if not self.wordlist.words:
            return None
        return self.wordlist.words[self.progress.current_index]

    @property
    def current_index(self) -> int:
        return self.progress.current_index

    @property
    def mode(self) -> ReviewMode:
        return self.progress.review_session.mode

    @property
    def completed(self) -> bool:
        return self.progress.review_session.completed

    def mode_word_count(self, mode: ReviewMode) -> int:
        if mode == ReviewMode.ALL:
            return len(self.wordlist.words)
        return len(self._build_indices(mode))

    def suggested_start_number(self, mode: ReviewMode) -> int:
        """Return a 1-based start number for the selected review mode."""
        if not self.wordlist.words:
            return 0

        if mode == ReviewMode.ALL:
            return self.progress.current_index + 1

        indices = self._build_indices(mode)
        if not indices:
            return 0

        queue_position = self._find_start_position(
            indices,
            self.progress.current_index,
        )
        return queue_position + 1

    def current_position_number(self) -> int:
        """Return the current 1-based position inside the active review mode."""
        if not self.wordlist.words:
            return 0

        state = self.progress.review_session
        if state.mode == ReviewMode.ALL:
            return self.progress.current_index + 1

        if not state.indices:
            return 0

        if state.completed:
            return len(state.indices)

        if 0 <= state.queue_position < len(state.indices):
            return state.queue_position + 1

        return self.suggested_start_number(state.mode)

    def start_review(self, mode: ReviewMode, start_number: int) -> bool:
        if not self.wordlist.words:
            return False

        if mode == ReviewMode.ALL:
            count = len(self.wordlist.words)
            start_number = self._clamp_start_number(start_number, count)
            self.progress.current_index = start_number - 1
            self.progress.review_session = ReviewSessionState(
                mode=ReviewMode.ALL,
                completed=False,
            )
            return True

        indices = self._build_indices(mode)
        if not indices:
            self.progress.review_session = ReviewSessionState(
                mode=mode,
                indices=[],
                completed=True,
            )
            return False

        start_number = self._clamp_start_number(start_number, len(indices))
        queue_position = start_number - 1

        self.progress.current_index = indices[queue_position]
        self.progress.review_session = ReviewSessionState(
            mode=mode,
            queue_position=queue_position,
            indices=indices,
            completed=False,
        )
        return True

    def mark_uncertain(self):
        self._mark(StudyStatus.UNCERTAIN)

    def mark_recognized(self):
        self._mark(StudyStatus.RECOGNIZED)

    def mark_mastered(self):
        self._mark(StudyStatus.MASTERED)

    def get_word_progress(self, word_id: str) -> WordProgress:
        item = self.progress.words.get(word_id)
        if item is None:
            item = WordProgress()
            self.progress.words[word_id] = item
        return item

    def _build_indices(self, mode: ReviewMode) -> list[int]:
        target = StudyStatus(int(mode))
        indices = []

        for index, word in enumerate(self.wordlist.words):
            item = self.progress.words.get(word.id)
            status = StudyStatus.UNLEARNED if item is None else item.study_status
            if status == target:
                indices.append(index)

        return indices

    @staticmethod
    def _find_start_position(indices: list[int], anchor_index: int) -> int:
        previous_position = None

        for position, index in enumerate(indices):
            if index <= anchor_index:
                previous_position = position
            else:
                break

        if previous_position is not None:
            return previous_position

        return 0

    @staticmethod
    def _clamp_start_number(start_number: int, count: int) -> int:
        if count <= 0:
            return 0
        if start_number < 1:
            return 1
        if start_number > count:
            return count
        return start_number

    def _mark(self, status: StudyStatus):
        if self.completed or self.current_word is None:
            return

        word = self.current_word
        item = self.get_word_progress(word.id)
        item.review_count += 1
        item.study_status = status

        state = self.progress.review_session

        if state.mode == ReviewMode.ALL:
            if self.progress.current_index >= len(self.wordlist.words) - 1:
                state.completed = True
            else:
                self.progress.current_index += 1
            return

        next_position = state.queue_position + 1
        if next_position >= len(state.indices):
            state.queue_position = len(state.indices)
            state.completed = True
            return

        state.queue_position = next_position
        self.progress.current_index = state.indices[next_position]

    def _repair_progress(self):
        count = len(self.wordlist.words)
        if count == 0:
            self.progress.current_index = 0
            self.progress.review_session = ReviewSessionState(completed=True)
            return

        if self.progress.current_index < 0:
            self.progress.current_index = 0
        if self.progress.current_index >= count:
            self.progress.current_index = count - 1

        state = self.progress.review_session

        if state.mode == ReviewMode.ALL:
            state.indices = []
            state.queue_position = 0
            return

        valid_indices = []
        seen = set()
        for index in state.indices:
            if 0 <= index < count and index not in seen:
                valid_indices.append(index)
                seen.add(index)

        valid_indices.sort()
        state.indices = valid_indices

        if state.completed:
            if state.queue_position > len(valid_indices):
                state.queue_position = len(valid_indices)
            return

        if not valid_indices:
            self.progress.review_session = ReviewSessionState()
            return

        if 0 <= state.queue_position < len(valid_indices):
            self.progress.current_index = valid_indices[state.queue_position]
            return

        if self.progress.current_index in valid_indices:
            state.queue_position = valid_indices.index(self.progress.current_index)
            return

        self.progress.review_session = ReviewSessionState()
