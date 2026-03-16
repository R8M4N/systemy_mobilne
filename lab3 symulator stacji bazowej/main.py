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
