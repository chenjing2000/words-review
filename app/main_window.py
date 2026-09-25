import html
import unicodedata
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QGuiApplication, QIcon, QIntValidator, QTextCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.example_audio import load_example_audio
from app.models.progress import ReviewMode
from app.models.word import Word
from app.pronunciation import find_audio_path, load_pronunciations
from app.repositories.app_state_repository import AppStateRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.wordlist_repository import WordListRepository
from app.review_session import ReviewSession


REVIEW_MODE_ITEMS = [
    ("全部单词", ReviewMode.ALL),
    ("待学习", ReviewMode.UNLEARNED),
    ("不懂", ReviewMode.UNCERTAIN),
    ("认识", ReviewMode.RECOGNIZED),
    ("熟悉", ReviewMode.MASTERED),
]


class MainWindow(QMainWindow):
    def __init__(self, root_dir: Path, settings: QSettings):
        super().__init__()

        self.settings = settings
        self.default_wordlist_folder = (root_dir / "wordlist").resolve()
        self.current_wordlist_folder = self.default_wordlist_folder
        self.wordlist_repository = WordListRepository(self.default_wordlist_folder)
        self.progress_repository = ProgressRepository()
        self.app_state_repository = AppStateRepository(root_dir / "data" / "app_state.json")
        self.icons_dir = root_dir / "resources" / "icons"

        self.current_wordlist_path = None
        self.current_wordlist = None
        self.progress = None
        self.session = None
        self.progress_locked = False
        self.pronunciations = {}
        self.example_audio = {}
        self.uk_audio_path = None
        self.us_audio_path = None
        self.selected_newword_text = ""
        self._screen_signal_connected = False

        self.audio_output = QAudioOutput(self)
        self.audio_player = QMediaPlayer(self)
        self.audio_player.setAudioOutput(self.audio_output)
        self.audio_player.errorOccurred.connect(self._on_audio_error)

        self.setWindowTitle("Words Review")
        self._build_ui()
        self._apply_initial_window_geometry()
        self._load_wordlists()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 18, 20, 8)
        root_layout.setSpacing(10)

        self.base_font_size = max(1, self.font().pointSize())

        control_grid = QGridLayout()
        control_grid.setHorizontalSpacing(12)
        control_grid.setVerticalSpacing(10)

        control_grid.addWidget(QLabel("单词本："), 0, 0)

        top_controls_widget = QWidget()
        top_controls_layout = QHBoxLayout(top_controls_widget)
        top_controls_layout.setContentsMargins(0, 0, 0, 0)
        top_controls_layout.setSpacing(10)

        self.wordlist_combo = QComboBox()
        top_controls_layout.addWidget(self.wordlist_combo, 1)

        self.word_count_label = QLabel("")
        self.word_count_label.setAlignment(Qt.AlignCenter)
        self.word_count_label.setToolTip("单词数量")
        word_count_width = self.fontMetrics().horizontalAdvance("999") + 12
        self.word_count_label.setFixedWidth(word_count_width)
        self.word_count_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        top_controls_layout.addWidget(self.word_count_label)

        self.select_folder_button = QPushButton("文件夹")
        self.select_folder_button.setFixedWidth(96)
        top_controls_layout.addWidget(self.select_folder_button)

        control_grid.addWidget(top_controls_widget, 0, 1, 1, 4)

        self.review_mode_combo = QComboBox()
        for text, mode in REVIEW_MODE_ITEMS:
            self.review_mode_combo.addItem(text, int(mode))
        control_grid.addWidget(self.review_mode_combo, 1, 1)

        position_widget = QWidget()
        position_layout = QHBoxLayout(position_widget)
        position_layout.setContentsMargins(0, 0, 0, 0)
        position_layout.setSpacing(6)
        position_layout.addWidget(QLabel("从第"))

        self.position_edit = QLineEdit("1")
        self.position_edit.setValidator(QIntValidator(0, 2147483647, self))
        self.position_edit.setAlignment(Qt.AlignCenter)
        self.position_edit.setFixedWidth(48)
        position_layout.addWidget(self.position_edit)
        position_layout.addWidget(QLabel("个开始"))
        position_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        position_widget.setMinimumWidth(position_layout.sizeHint().width())
        control_grid.addWidget(position_widget, 1, 2)

        navigation_widget = QWidget()
        navigation_layout = QHBoxLayout(navigation_widget)
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(4)

        self.previous_button = QPushButton("‹")
        self.previous_button.setObjectName("navigationButton")
        self.previous_button.setFixedWidth(32)
        self.next_button = QPushButton("›")
        self.next_button.setObjectName("navigationButton")
        self.next_button.setFixedWidth(32)
        navigation_layout.addWidget(self.previous_button)
        navigation_layout.addWidget(self.next_button)
        control_grid.addWidget(navigation_widget, 1, 3)

        action_button_width = 96
        self.start_review_button = QPushButton("复习")
        self.start_review_button.setObjectName("primaryAction")
        self.start_review_button.setFixedWidth(action_button_width)
        control_grid.addWidget(self.start_review_button, 1, 4)
        control_grid.setColumnStretch(1, 1)
        root_layout.addLayout(control_grid)

        word_row = QGridLayout()
        word_row.setContentsMargins(0, 0, 0, 0)
        word_row.setHorizontalSpacing(0)

        self.reveal_button = QPushButton("释义")
        self.reveal_button.setObjectName("primaryAction")
        self.reveal_button.setFixedWidth(action_button_width)

        left_placeholder = QWidget()
        left_placeholder.setFixedWidth(action_button_width)
        word_row.addWidget(left_placeholder, 0, 0)

        word_info_widget = QWidget()
        word_info_layout = QHBoxLayout(word_info_widget)
        word_info_layout.setContentsMargins(0, 0, 0, 0)
        word_info_layout.setSpacing(8)

        self.word_label = QLabel("")
        self.word_label.setAlignment(Qt.AlignVCenter)
        self._set_word_label_style(is_word=True)
        word_info_layout.addWidget(self.word_label)

        self.phonetic_label = QLabel("")
        self.phonetic_label.setAlignment(Qt.AlignVCenter)
        word_info_layout.addWidget(self.phonetic_label)

        audio_buttons_widget = QWidget()
        audio_buttons_layout = QHBoxLayout(audio_buttons_widget)
        audio_buttons_layout.setContentsMargins(0, 0, 0, 0)
        audio_buttons_layout.setSpacing(5)

        self.uk_audio_button = self._create_audio_button(
            "speaker_uk.svg", "英/Br", "ukAudioButton"
        )
        self.us_audio_button = self._create_audio_button(
            "speaker_us.svg", "美/Am", "usAudioButton"
        )
        audio_buttons_layout.addWidget(self.uk_audio_button)
        audio_buttons_layout.addWidget(self.us_audio_button)
        word_info_layout.addWidget(audio_buttons_widget)

        word_row.addWidget(word_info_widget, 0, 1, 1, 1, Qt.AlignCenter)
        word_row.addWidget(self.reveal_button, 0, 2, 1, 1, Qt.AlignRight)
        word_row.setColumnStretch(1, 1)
        root_layout.addLayout(word_row)

        detail_card = QFrame()
        detail_card.setObjectName("detailCard")
        detail_card_layout = QVBoxLayout(detail_card)
        detail_card_layout.setContentsMargins(0, 0, 0, 0)

        self.detail_stack = QStackedWidget()
        self.detail_stack.setObjectName("detailStack")
        self.blank_detail = QWidget()
        self.detail_browser = QTextBrowser()
        self.detail_browser.setObjectName("detailBrowser")
        self.detail_browser.setOpenLinks(False)
        self.detail_browser.setOpenExternalLinks(False)
        self.detail_browser.setContextMenuPolicy(Qt.NoContextMenu)

        self.newword_button = QToolButton(self.detail_browser.viewport())
        self.newword_button.setToolTip("添加到生词本")
        self.newword_button.setFocusPolicy(Qt.NoFocus)
        self.newword_button.setIcon(QIcon(str(self.icons_dir / "add_newword.svg")))
        self.newword_button.setIconSize(QSize(16, 16))
        self.newword_button.setFixedSize(18, 18)
        self.newword_button.setStyleSheet(
            "QToolButton { border:none; background:transparent; padding:0; }"
        )
        self.newword_button.hide()

        self.detail_stack.addWidget(self.blank_detail)
        self.detail_stack.addWidget(self.detail_browser)
        detail_card_layout.addWidget(self.detail_stack)
        root_layout.addWidget(detail_card, 6)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.uncertain_button = QPushButton("不懂")
        self.uncertain_button.setObjectName("reviewUncertain")
        self.recognized_button = QPushButton("认识")
        self.recognized_button.setObjectName("reviewRecognized")
        self.mastered_button = QPushButton("理解")
        self.mastered_button.setObjectName("reviewMastered")
        action_row.addWidget(self.uncertain_button, 1)
        action_row.addWidget(self.recognized_button, 1)
        action_row.addWidget(self.mastered_button, 1)
        root_layout.addLayout(action_row)

        status_bar = self.statusBar()
        status_bar.setObjectName("statusBar")
        status_bar.messageChanged.connect(self._on_status_message_changed)
        status_bar.hide()

        self.wordlist_combo.currentIndexChanged.connect(self._on_wordlist_changed)
        self.select_folder_button.clicked.connect(self._choose_wordlist_folder)
        self.review_mode_combo.currentIndexChanged.connect(self._on_review_mode_changed)
        self.position_edit.editingFinished.connect(self._normalize_position_input)
        self.start_review_button.clicked.connect(self._start_review)
        self.previous_button.clicked.connect(self._move_previous)
        self.next_button.clicked.connect(self._move_next)
        self.reveal_button.clicked.connect(self._show_definition)
        self.detail_browser.anchorClicked.connect(self._on_detail_link_clicked)
        self.detail_browser.selectionChanged.connect(self._on_detail_selection_changed)
        self.newword_button.clicked.connect(self._add_selected_newword)
        self.uk_audio_button.clicked.connect(lambda: self._play_audio(self.uk_audio_path))
        self.us_audio_button.clicked.connect(lambda: self._play_audio(self.us_audio_path))
        self.mastered_button.clicked.connect(self._mark_mastered)
        self.recognized_button.clicked.connect(self._mark_recognized)
        self.uncertain_button.clicked.connect(self._mark_uncertain)

    def _create_audio_button(self, icon_name: str, tooltip: str, object_name: str):
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setIcon(QIcon(str(self.icons_dir / icon_name)))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(24, 24)
        button.setEnabled(False)
        return button

    def _set_word_label_style(self, is_word: bool):
        font = self.word_label.font()
        if is_word:
            font.setPointSize(self.base_font_size + 1)
            font.setBold(True)
            self.word_label.setStyleSheet("color: #0077be;")
        else:
            font.setPointSize(self.base_font_size)
            font.setBold(False)
            self.word_label.setStyleSheet("color: #000000;")
        self.word_label.setFont(font)

    def show_status(self, message: str, timeout: int = 5000):
        status_bar = self.statusBar()
        status_bar.show()
        status_bar.showMessage(message, timeout)

    def _on_status_message_changed(self, message: str):
        self.statusBar().setVisible(bool(message))

    def _load_wordlists(self):
        paths = self.wordlist_repository.scan()
        self._populate_wordlist_combo(paths)

        if not paths:
            self._show_no_wordlist("默认 wordlist 文件夹中没有 JSON 单词本")
            return

        last_name = self.app_state_repository.load_last_wordlist()
        preferred_index = 0
        if last_name:
            for i, path in enumerate(paths):
                if path.name == last_name:
                    preferred_index = i
                    break

        indices = [preferred_index] + [
            i for i in range(len(paths)) if i != preferred_index
        ]
        for index in indices:
            if self._activate_wordlist(index):
                self.wordlist_combo.blockSignals(True)
                self.wordlist_combo.setCurrentIndex(index)
                self.wordlist_combo.blockSignals(False)
                return

        self._show_no_wordlist("默认 wordlist 文件夹中没有可用的 WordList")
        self.wordlist_combo.setEnabled(True)
        self.wordlist_combo.blockSignals(True)
        self.wordlist_combo.setCurrentIndex(-1)
        self.wordlist_combo.blockSignals(False)

    def _populate_wordlist_combo(self, paths):
        self.wordlist_combo.blockSignals(True)
        self.wordlist_combo.clear()
        for path in paths:
            self.wordlist_combo.addItem(path.stem, str(path))
        self.wordlist_combo.blockSignals(False)

    def _choose_wordlist_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择 WordList 文件夹",
            str(self.current_wordlist_folder),
        )
        if not folder:
            return

        if self.current_wordlist_path is not None:
            if not self._save_current_progress(show_error=True):
                return

        selected_folder = Path(folder).resolve()
        try:
            repository = WordListRepository(selected_folder)
            paths = repository.scan()
        except OSError as exc:
            self.show_status(f"无法读取所选文件夹：{exc}", 8000)
            return

        self.current_wordlist_folder = selected_folder
        self.wordlist_repository = repository
        self._reset_current_wordlist()
        self._populate_wordlist_combo(paths)

        if not paths:
            self._show_no_wordlist("所选文件夹中没有 JSON 单词本")
            return

        for index in range(len(paths)):
            if self._activate_wordlist(index):
                self.wordlist_combo.blockSignals(True)
                self.wordlist_combo.setCurrentIndex(index)
                self.wordlist_combo.blockSignals(False)
                self.show_status(f"已发现 {len(paths)} 个 WordList 文件")
                return

        self._show_no_wordlist("所选文件夹中没有可用的 WordList")
        self.wordlist_combo.setEnabled(True)
        self.wordlist_combo.blockSignals(True)
        self.wordlist_combo.setCurrentIndex(-1)
        self.wordlist_combo.blockSignals(False)

    def _reset_current_wordlist(self):
        self.audio_player.stop()
        self.current_wordlist_path = None
        self.current_wordlist = None
        if hasattr(self, "word_count_label"):
            self.word_count_label.setText("")
        self.progress = None
        self.session = None
        self.progress_locked = False
        self.pronunciations = {}
        self.example_audio = {}
        self.uk_audio_path = None
        self.us_audio_path = None
        self.selected_newword_text = ""
        if hasattr(self, "newword_button"):
            self.newword_button.hide()
        if hasattr(self, "uk_audio_button"):
            self.uk_audio_button.setEnabled(False)
            self.us_audio_button.setEnabled(False)
        if hasattr(self, "previous_button"):
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)

    def _on_wordlist_changed(self, index: int):
        if index < 0 or index >= self.wordlist_combo.count():
            return

        if self.current_wordlist_path is not None:
            if not self._save_current_progress(show_error=True):
                self._restore_combo_to_current_wordlist()
                return

        if not self._activate_wordlist(index):
            if self.current_wordlist_path is not None:
                self._restore_combo_to_current_wordlist()
            else:
                self.wordlist_combo.blockSignals(True)
                self.wordlist_combo.setCurrentIndex(-1)
                self.wordlist_combo.blockSignals(False)

    def _activate_wordlist(self, index: int) -> bool:
        path_text = self.wordlist_combo.itemData(index)
        if not path_text:
            return False
        path = Path(path_text)

        try:
            wordlist = self.wordlist_repository.load(path)
        except (OSError, ValueError, UnicodeError) as exc:
            self.show_status(f"WordList 加载失败：{path.name}：{exc}", 8000)
            return False

        try:
            progress = self.progress_repository.load(path)
        except (OSError, ValueError) as exc:
            self.show_status(f"学习记录加载失败：{exc}", 8000)
            return False

        self.current_wordlist_path = path
        self.current_wordlist = wordlist
        self.word_count_label.setText(str(len(wordlist.words)))
        self.progress = progress
        self.session = ReviewSession(wordlist, progress)
        self.progress_locked = False

        try:
            self.pronunciations = load_pronunciations(path)
        except (OSError, ValueError) as exc:
            self.pronunciations = {}
            self.show_status(f"发音配置加载失败：{exc}", 8000)

        try:
            self.example_audio = load_example_audio(path)
        except (OSError, ValueError) as exc:
            self.example_audio = {}
            self.show_status(f"例句音频配置加载失败：{exc}", 8000)

        self._set_review_mode_combo(self.session.mode)
        self._render_current_state()
        self._set_learning_controls_enabled(True)

        if self.current_wordlist_folder == self.default_wordlist_folder:
            try:
                self.app_state_repository.save_last_wordlist(path.name)
            except OSError as exc:
                self.show_status(str(exc))

        return True

    def _start_review(self):
        if self.session is None:
            return

        mode = self._selected_review_mode()
        start_number = self._normalize_position_input()
        if start_number <= 0:
            self._show_empty_review_mode()
            return

        found = self.session.start_review(mode, start_number)

        if not self._save_current_progress(show_error=True):
            self._reload_current_progress()
            return

        if not found:
            self._show_empty_review_mode()
        else:
            self._render_current_state()

    def _show_definition(self):
        if self.session is None or self.session.current_word is None:
            return
        self.detail_stack.setCurrentWidget(self.detail_browser)

    def _move_previous(self):
        self._move_current(self.session.move_previous if self.session else None)

    def _move_next(self):
        self._move_current(self.session.move_next if self.session else None)

    def _move_current(self, action):
        if action is None or not action():
            return

        if not self._save_current_progress(show_error=True):
            self._reload_current_progress()
            return

        self._render_current_state()

    def _mark_mastered(self):
        self._mark_current(self.session.mark_mastered if self.session else None)

    def _mark_recognized(self):
        self._mark_current(self.session.mark_recognized if self.session else None)

    def _mark_uncertain(self):
        self._mark_current(self.session.mark_uncertain if self.session else None)

    def _mark_current(self, action):
        if action is None or self.session.completed:
            return

        action()

        if not self._save_current_progress(show_error=True):
            self._reload_current_progress()
            return

        self._render_current_state()

    def _render_current_state(self):
        if self.session is None:
            return

        self._hide_newword_button()
        self.audio_player.stop()

        if self.session.completed:
            self._set_word_label_style(is_word=False)
            self.word_label.setText("本轮复习完成")
            self.phonetic_label.setText("")
            self._update_audio_buttons(None)
            self._sync_position_edit_to_session()
            self.detail_stack.setCurrentWidget(self.blank_detail)
            self.detail_browser.clear()
            return

        word = self.session.current_word
        if word is None:
            self._show_no_wordlist()
            return

        self._set_word_label_style(is_word=True)
        self.word_label.setText(word.word)
        self.phonetic_label.setText(word.phonetic)
        self._update_audio_buttons(word)
        self._sync_position_edit_to_session()
        self.detail_browser.setHtml(
            build_word_html(
                word,
                self.example_audio,
                QUrl.fromLocalFile(str(self.icons_dir / "speaker_uk.svg")).toString(),
                QUrl.fromLocalFile(str(self.icons_dir / "speaker_us.svg")).toString(),
            )
        )
        self._format_detail_paragraphs()
        self.detail_browser.verticalScrollBar().setValue(0)
        self.detail_stack.setCurrentWidget(self.blank_detail)

    def _format_detail_paragraphs(self):
        document = self.detail_browser.document()
        indent = self.detail_browser.fontMetrics().horizontalAdvance("MM")
        paragraph_gap = self.detail_browser.fontMetrics().height() * 0.55

        block = document.begin()
        while block.isValid():
            if block.text().strip():
                block_format = block.blockFormat()
                block_format.setLeftMargin(indent)
                block_format.setTextIndent(-indent)
                block_format.setTopMargin(0)
                block_format.setBottomMargin(paragraph_gap)
                cursor = QTextCursor(block)
                cursor.setBlockFormat(block_format)
            block = block.next()

    def _update_audio_buttons(self, word: Word | None):
        self.uk_audio_path = None
        self.us_audio_path = None

        if word is not None and self.current_wordlist_path is not None:
            self.uk_audio_path = find_audio_path(
                self.current_wordlist_path, self.pronunciations, word.word, "uk"
            )
            self.us_audio_path = find_audio_path(
                self.current_wordlist_path, self.pronunciations, word.word, "us"
            )

        self.uk_audio_button.setEnabled(self.uk_audio_path is not None)
        self.us_audio_button.setEnabled(self.us_audio_path is not None)

    def _on_detail_link_clicked(self, url: QUrl):
        if url.scheme() != "example-audio":
            return

        self.detail_browser.clearFocus()

        accent = url.host()
        eid = url.path().lstrip("/")
        if accent not in {"uk", "us"} or not eid:
            return

        item = self.example_audio.get(eid)
        if not isinstance(item, dict):
            return

        self._play_audio(item.get(accent))

    def _normalize_newword_text(self, text: str) -> str:
        text = " ".join(text.split()).lower()
        if not text:
            return ""

        chars = []
        for index, char in enumerate(text):
            if unicodedata.category(char).startswith("P"):
                previous_is_word = index > 0 and text[index - 1].isalnum()
                next_is_word = index + 1 < len(text) and text[index + 1].isalnum()
                if char in {"-", "'", "’"} and previous_is_word and next_is_word:
                    chars.append(char)
                else:
                    chars.append(" ")
            else:
                chars.append(char)

        return " ".join("".join(chars).split())

    def _on_detail_selection_changed(self):
        cursor = self.detail_browser.textCursor()
        if not cursor.hasSelection():
            self._hide_newword_button()
            return

        text = self._normalize_newword_text(cursor.selectedText())
        if not text:
            self._hide_newword_button()
            return

        self.selected_newword_text = text

        end_position = cursor.selectionEnd()
        end_cursor = QTextCursor(cursor)
        end_cursor.setPosition(end_position)
        end_rect = self.detail_browser.cursorRect(end_cursor)

        x_anchor = end_rect.right()
        y_anchor = end_rect.bottom()

        # At a soft-wrap boundary, selectionEnd() can belong to the next visual
        # line even though the last selected character is still on the line above.
        # In that case, anchor the button to the last selected character instead.
        if end_position > cursor.selectionStart():
            previous_cursor = QTextCursor(cursor)
            previous_cursor.setPosition(end_position - 1)
            previous_rect = self.detail_browser.cursorRect(previous_cursor)
            if end_rect.top() > previous_rect.top():
                last_char = self.detail_browser.document().characterAt(end_position - 1)
                char_width = self.detail_browser.fontMetrics().horizontalAdvance(last_char)
                x_anchor = previous_rect.left() + max(1, char_width)
                y_anchor = previous_rect.bottom()

        viewport = self.detail_browser.viewport()
        x = min(x_anchor + 4, max(0, viewport.width() - self.newword_button.width()))
        y = min(y_anchor + 3, max(0, viewport.height() - self.newword_button.height()))
        self.newword_button.move(max(0, x), max(0, y))
        self.newword_button.raise_()
        self.newword_button.show()

    def _hide_newword_button(self):
        self.selected_newword_text = ""
        self.newword_button.hide()

    def _add_selected_newword(self):
        text = self.selected_newword_text
        if not text or self.current_wordlist_path is None:
            self._hide_newword_button()
            return

        self.newword_button.hide()
        cursor = self.detail_browser.textCursor()
        cursor.clearSelection()
        self.detail_browser.setTextCursor(cursor)
        self.selected_newword_text = ""

        newwords_path = (
            self.current_wordlist_path.parent
            / self.current_wordlist_path.stem
            / "newwords.txt"
        )

        try:
            newwords_path.parent.mkdir(parents=True, exist_ok=True)
            if newwords_path.exists():
                existing_text = newwords_path.read_text(encoding="utf-8-sig")
            else:
                existing_text = ""

            existing = {
                normalized
                for line in existing_text.splitlines()
                if (normalized := self._normalize_newword_text(line))
            }

            if text in existing:
                self.show_status(f"已存在：{text}")
                return

            with newwords_path.open("a", encoding="utf-8") as file:
                if existing_text and not existing_text.endswith(("\n", "\r")):
                    file.write("\n")
                file.write(text + "\n")

            self.show_status(f"已添加：{text}")
        except (OSError, UnicodeError) as exc:
            self.show_status(f"生词本保存失败：{exc}", 8000)

    def _play_audio(self, path: Path | None):
        if path is None:
            return
        if not path.is_file():
            self.show_status("音频文件不存在")
            self._update_audio_buttons(self.session.current_word if self.session else None)
            return

        self.audio_player.stop()
        self.audio_player.setSource(QUrl.fromLocalFile(str(path)))
        self.audio_player.play()

    def _on_audio_error(self, _error, error_string: str):
        if error_string:
            self.show_status(f"音频播放失败：{error_string}")

    def _show_empty_review_mode(self):
        self._hide_newword_button()
        self.audio_player.stop()
        self._set_word_label_style(is_word=False)
        self.word_label.setText("")
        self.phonetic_label.setText("")
        self._update_audio_buttons(None)
        self.detail_stack.setCurrentWidget(self.blank_detail)
        self.detail_browser.clear()
        self.position_edit.setText("1")
        self._update_review_start_controls()
        self._set_review_action_enabled(False)

    def _show_no_wordlist(self, message: str = "当前文件夹中没有有效的 WordList"):
        self._reset_current_wordlist()
        self._set_word_label_style(is_word=False)
        self.word_label.setText(message)
        self.phonetic_label.setText("")
        self._update_audio_buttons(None)
        self.show_status(message, 8000)
        self.position_edit.setText("0")
        self.detail_stack.setCurrentWidget(self.blank_detail)
        self.detail_browser.clear()
        self._set_learning_controls_enabled(False)

    def _set_review_action_enabled(self, enabled: bool):
        self.reveal_button.setEnabled(enabled)
        self.mastered_button.setEnabled(enabled)
        self.recognized_button.setEnabled(enabled)
        self.uncertain_button.setEnabled(enabled)

    def _set_learning_controls_enabled(self, enabled: bool):
        self.wordlist_combo.setEnabled(enabled)
        self.review_mode_combo.setEnabled(enabled)
        self.position_edit.setEnabled(enabled)
        self.start_review_button.setEnabled(enabled)
        if enabled:
            self._update_review_start_controls()
        else:
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self._set_review_action_enabled(False)

    def _selected_review_mode(self) -> ReviewMode:
        value = self.review_mode_combo.currentData()
        return ReviewMode(int(value))

    def _set_review_mode_combo(self, mode: ReviewMode):
        index = self.review_mode_combo.findData(int(mode))
        if index >= 0:
            self.review_mode_combo.blockSignals(True)
            self.review_mode_combo.setCurrentIndex(index)
            self.review_mode_combo.blockSignals(False)

    def _on_review_mode_changed(self, _index: int):
        if self.session is None:
            return

        mode = self._selected_review_mode()
        self.position_edit.setText("1")
        found = self.session.start_review(mode, 1)

        if not self._save_current_progress(show_error=True):
            self._reload_current_progress()
            return

        if found:
            self._render_current_state()
        else:
            self._show_empty_review_mode()

    def _normalize_position_input(self) -> int:
        if self.session is None:
            return 0

        mode = self._selected_review_mode()
        count = self.session.mode_word_count(mode)
        if count <= 0:
            self.position_edit.setText("0")
            self._update_review_start_controls()
            return 0

        text = self.position_edit.text().strip()
        if text:
            number = int(text)
        else:
            number = self.session.suggested_start_number(mode)

        if number < 1:
            number = 1
            self.show_status("起始位置已调整为第 1 个")
        elif number > count:
            number = count
            self.show_status(f"输入位置超过当前模式范围，已调整为第 {count} 个")

        self.position_edit.setText(str(number))
        return number

    def _sync_position_edit_to_session(self):
        if self.session is None:
            return
        if self._selected_review_mode() == self.session.mode:
            self.position_edit.setText(str(self.session.current_position_number()))
        self._update_review_start_controls()

    def _update_review_start_controls(self):
        if self.session is None:
            self.position_edit.setEnabled(False)
            self.start_review_button.setEnabled(False)
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self._set_review_action_enabled(False)
            return

        if self.progress_locked:
            self.review_mode_combo.setEnabled(False)
            self.position_edit.setEnabled(False)
            self.start_review_button.setEnabled(False)
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.mastered_button.setEnabled(False)
            self.recognized_button.setEnabled(False)
            self.uncertain_button.setEnabled(False)
            self.reveal_button.setEnabled(self.session.current_word is not None)
            return

        self.review_mode_combo.setEnabled(True)
        mode = self._selected_review_mode()
        has_words = self.session.mode_word_count(mode) > 0
        self.position_edit.setEnabled(has_words)
        self.start_review_button.setEnabled(has_words)

        active_mode = mode == self.session.mode
        can_review = active_mode and not self.session.completed and self.session.current_word is not None
        self.previous_button.setEnabled(can_review and self.session.can_move_previous())
        self.next_button.setEnabled(can_review and self.session.can_move_next())
        self._set_review_action_enabled(can_review)

    def _save_current_progress(self, show_error: bool) -> bool:
        if self.progress_locked:
            return True
        if self.current_wordlist_path is None or self.progress is None:
            return True

        try:
            self.progress_repository.save(self.current_wordlist_path, self.progress)
            return True
        except OSError as exc:
            if show_error:
                self.show_status(f"学习记录保存失败：{exc}")
            return False

    def _reload_current_progress(self):
        if self.current_wordlist_path is None or self.current_wordlist is None:
            return

        try:
            progress = self.progress_repository.load(self.current_wordlist_path)
        except (OSError, ValueError):
            self.progress_locked = True
            self.show_status(
                "学习记录无法读取或保存，请检查 progress.json 或文件夹权限。",
                8000,
            )
            self._update_review_start_controls()
            return

        self.progress_locked = False
        self.progress = progress
        self.session = ReviewSession(self.current_wordlist, self.progress)
        self._set_review_mode_combo(self.session.mode)
        self._render_current_state()

    def _restore_combo_to_current_wordlist(self):
        if self.current_wordlist_path is None:
            return

        index = self.wordlist_combo.findData(str(self.current_wordlist_path))
        if index >= 0:
            self.wordlist_combo.blockSignals(True)
            self.wordlist_combo.setCurrentIndex(index)
            self.wordlist_combo.blockSignals(False)

    def _apply_initial_window_geometry(self):
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        self._apply_screen_constraints(screen)

        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
            if self._is_window_on_a_screen():
                return

        available = screen.availableGeometry()
        width = int(available.width() * 0.60)
        height = int(width * 9 / 16)

        width = min(width, self.maximumWidth())
        height = min(height, self.maximumHeight())
        width = max(width, self.minimumWidth())
        height = max(height, self.minimumHeight())

        self.resize(width, height)
        x = available.left() + (available.width() - width) // 2
        y = available.top() + (available.height() - height) // 2
        self.move(x, y)

    def _apply_screen_constraints(self, screen):
        available = screen.availableGeometry()
        min_width = max(int(available.width() * 0.10), 480)
        min_height = max(int(available.height() * 0.20), 320)
        max_width = int(available.width() * 0.80)
        max_height = available.height()

        if min_width > max_width:
            min_width = max_width
        if min_height > max_height:
            min_height = max_height

        self.setMinimumSize(min_width, min_height)
        self.setMaximumSize(max_width, max_height)

    def _is_window_on_a_screen(self) -> bool:
        frame = self.frameGeometry()
        for screen in QGuiApplication.screens():
            if frame.intersects(screen.availableGeometry()):
                return True
        return False

    def attach_screen_tracking(self):
        if self.windowHandle() is None or self._screen_signal_connected:
            return
        self.windowHandle().screenChanged.connect(self._on_screen_changed)
        self._screen_signal_connected = True

    def _on_screen_changed(self, screen):
        if screen is not None:
            self._apply_screen_constraints(screen)

    def closeEvent(self, event: QCloseEvent):
        if not self._save_current_progress(show_error=False):
            self.show_status("学习记录保存失败，程序未关闭")
            event.ignore()
            return

        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("ui/font_size", self.font().pointSize())
        self.settings.sync()
        event.accept()


def _example_audio_links(
    eid: str,
    audio: dict[str, Path],
    uk_icon_url: str,
    us_icon_url: str,
) -> str:
    links = []

    if "uk" in audio:
        links.append(
            '<a href="example-audio://uk/'
            + html.escape(eid, quote=True)
            + '" style="text-decoration:none;">'
            + '<img src="'
            + html.escape(uk_icon_url, quote=True)
            + '" width="16" height="16" style="vertical-align:middle;" />'
            + "</a>"
        )

    if "us" in audio:
        links.append(
            '<a href="example-audio://us/'
            + html.escape(eid, quote=True)
            + '" style="text-decoration:none;">'
            + '<img src="'
            + html.escape(us_icon_url, quote=True)
            + '" width="16" height="16" style="vertical-align:middle;" />'
            + "</a>"
        )

    if not links:
        return ""

    return ' <span style="white-space:nowrap;">' + "&nbsp;".join(links) + "</span>"


def build_word_html(
    word: Word,
    example_audio: dict[str, dict[str, Path]] | None = None,
    uk_icon_url: str = "",
    us_icon_url: str = "",
) -> str:
    paragraph_style = "margin:0; line-height:1.45;"
    parts = ['<div style="color:#000000;">']
    example_audio = example_audio or {}

    for index, sense in enumerate(word.senses, start=1):
        pos = html.escape(sense.pos)
        english_meaning = html.escape(sense.english_meaning)
        chinese_meaning = html.escape(sense.chinese_meaning)

        if len(word.senses) > 1:
            label = f"{index}. {pos}" if pos else f"{index}."
        else:
            label = pos

        meaning_parts = []
        if label:
            meaning_parts.append(f"<b>{label}</b>")
        if english_meaning:
            meaning_parts.append(english_meaning)
        if chinese_meaning:
            meaning_parts.append(chinese_meaning)

        if meaning_parts:
            parts.append(
                f'<p style="{paragraph_style}">'
                + "&nbsp;&nbsp;".join(meaning_parts)
                + "</p>"
            )

        example_parts = []
        if sense.example:
            example_parts.append(html.escape(sense.example))
        if sense.example_translation:
            example_parts.append(html.escape(sense.example_translation))

        if example_parts:
            example_text = "&nbsp;&nbsp;".join(example_parts)
            audio = example_audio.get(sense.eid, {}) if sense.eid else {}
            if audio and uk_icon_url and us_icon_url:
                example_text += _example_audio_links(
                    sense.eid, audio, uk_icon_url, us_icon_url
                )

            parts.append(
                f'<p style="{paragraph_style}"><b>Example:</b>&nbsp;&nbsp;'
                + example_text
                + "</p>"
            )

        if sense.synonyms:
            synonyms = " · ".join(html.escape(item) for item in sense.synonyms)
            parts.append(
                f'<p style="{paragraph_style}"><b>Synonyms:</b>&nbsp;&nbsp;'
                f"{synonyms}</p>"
            )

        if sense.collocations:
            collocations = " · ".join(
                html.escape(item) for item in sense.collocations
            )
            parts.append(
                f'<p style="{paragraph_style}"><b>Collocations:</b>&nbsp;&nbsp;'
                f"{collocations}</p>"
            )

    if word.notes:
        parts.append(
            f'<p style="{paragraph_style}"><b>Notes:</b>&nbsp;&nbsp;'
            + html.escape(word.notes)
            + "</p>"
        )

    parts.append("</div>")
    return "\n".join(parts)
