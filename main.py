import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def main():
    root_dir = Path(__file__).resolve().parent

    app = QApplication(sys.argv)
    app.setApplicationName("words_review")
    app.setOrganizationName("words_review")

    icon_path = root_dir / "resources" / "icons" / "app.ico"
    if not icon_path.exists():
        icon_path = root_dir / "resources" / "icons" / "app.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    style_path = root_dir / "resources" / "styles" / "light.qss"
    if style_path.exists():
        style = style_path.read_text(encoding="utf-8")
        arrow_path = (root_dir / "resources" / "icons" / "chevron-down.svg").as_posix()
        style = style.replace("__COMBO_ARROW__", arrow_path)
        app.setStyleSheet(style)

    settings = QSettings("words_review", "words_review")

    font_size = settings.value("ui/font_size", 12, type=int)
    app_font = app.font()
    app_font.setPointSize(font_size)
    app.setFont(app_font)

    window = MainWindow(root_dir, settings)
    window.show()
    QTimer.singleShot(0, window.attach_screen_tracking)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
