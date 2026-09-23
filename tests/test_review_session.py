import unittest

from app.models.progress import ReviewMode, StudyStatus, WordListProgress
from app.models.word import Word, WordList, WordSense
from app.review_session import ReviewSession


def make_word(wid):
    return Word(
        wid=wid,
        word=wid,
        senses=[WordSense(chinese_meaning=wid)],
    )


class ReviewSessionTests(unittest.TestCase):
    def setUp(self):
        self.wordlist = WordList(
            schema_version=1,
            name="test",
            words=[make_word(f"w{i}") for i in range(8)],
        )
        self.progress = WordListProgress(current_index=5)
        self.session = ReviewSession(self.wordlist, self.progress)

        self.session.get_word_progress("w1").study_status = StudyStatus.RECOGNIZED
        self.session.get_word_progress("w3").study_status = StudyStatus.RECOGNIZED
        self.session.get_word_progress("w6").study_status = StudyStatus.RECOGNIZED

    def test_suggested_start_uses_previous_nearest_match(self):
        number = self.session.suggested_start_number(ReviewMode.RECOGNIZED)
        self.assertEqual(number, 2)

    def test_suggested_start_uses_first_match_when_no_previous_match(self):
        self.progress.current_index = 0
        number = self.session.suggested_start_number(ReviewMode.RECOGNIZED)
        self.assertEqual(number, 1)

    def test_start_filtered_mode_at_requested_position(self):
        found = self.session.start_review(ReviewMode.RECOGNIZED, 2)
        self.assertTrue(found)
        self.assertEqual(self.session.current_index, 3)
        self.assertEqual(self.progress.review_session.queue_position, 1)
        self.assertEqual(self.progress.review_session.indices, [1, 3, 6])

    def test_start_position_is_clamped_to_filtered_count(self):
        found = self.session.start_review(ReviewMode.RECOGNIZED, 99)
        self.assertTrue(found)
        self.assertEqual(self.session.current_index, 6)
        self.assertEqual(self.session.current_position_number(), 3)

    def test_zero_start_position_becomes_first_word(self):
        found = self.session.start_review(ReviewMode.RECOGNIZED, 0)
        self.assertTrue(found)
        self.assertEqual(self.session.current_index, 1)
        self.assertEqual(self.session.current_position_number(), 1)

    def test_all_mode_uses_original_wordlist_position(self):
        found = self.session.start_review(ReviewMode.ALL, 4)
        self.assertTrue(found)
        self.assertEqual(self.session.current_index, 3)
        self.assertEqual(self.session.current_position_number(), 4)

    def test_snapshot_does_not_rebuild_after_rating(self):
        self.session.start_review(ReviewMode.RECOGNIZED, 2)
        original_indices = list(self.progress.review_session.indices)
        self.session.mark_mastered()
        self.assertEqual(self.progress.review_session.indices, original_indices)
        self.assertEqual(self.session.current_index, 6)

    def test_review_count_increases_once(self):
        self.session.start_review(ReviewMode.RECOGNIZED, 2)
        wid = self.session.current_word.wid
        before = self.session.get_word_progress(wid).review_count
        self.session.mark_recognized()
        after = self.session.get_word_progress(wid).review_count
        self.assertEqual(after, before + 1)

    def test_all_mode_finishes_on_last_word(self):
        self.session.start_review(ReviewMode.ALL, 8)
        self.session.mark_mastered()
        self.assertTrue(self.session.completed)
        self.assertEqual(self.session.current_index, 7)
        self.assertEqual(self.session.current_position_number(), 8)

    def test_navigation_moves_inside_filtered_snapshot(self):
        self.session.start_review(ReviewMode.RECOGNIZED, 2)
        self.assertTrue(self.session.move_next())
        self.assertEqual(self.session.current_index, 6)
        self.assertEqual(self.session.current_position_number(), 3)
        self.assertTrue(self.session.move_previous())
        self.assertEqual(self.session.current_index, 3)
        self.assertEqual(self.session.current_position_number(), 2)

    def test_navigation_does_not_change_learning_progress(self):
        self.session.start_review(ReviewMode.RECOGNIZED, 2)
        wid = self.session.current_word.wid
        before_status = self.session.get_word_progress(wid).study_status
        before_count = self.session.get_word_progress(wid).review_count
        self.session.move_next()
        self.session.move_previous()
        item = self.session.get_word_progress(wid)
        self.assertEqual(item.study_status, before_status)
        self.assertEqual(item.review_count, before_count)

    def test_navigation_stops_at_boundaries_without_completing(self):
        self.session.start_review(ReviewMode.RECOGNIZED, 1)
        self.assertFalse(self.session.move_previous())
        self.assertFalse(self.session.completed)
        self.session.start_review(ReviewMode.RECOGNIZED, 3)
        self.assertFalse(self.session.move_next())
        self.assertFalse(self.session.completed)


if __name__ == "__main__":
    unittest.main()
