import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from gui import MainWindow


DARK_STYLESHEET = """
    * {
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }
    QMainWindow {
        background: #0d1117;
    }
    QWidget {
        background: #0d1117;
        color: #e6edf3;
    }
    QScrollBar:vertical {
        background: #161b22;
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #30363d;
        border-radius: 5px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: #484f58;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: #161b22;
        height: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background: #30363d;
        border-radius: 5px;
        min-width: 30px;
    }
    QToolTip {
        background: #1c2128;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 4px;
        padding: 4px;
    }
"""


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
