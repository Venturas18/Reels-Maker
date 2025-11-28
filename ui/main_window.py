from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QListWidget,
                             QStackedWidget, QListWidgetItem, QFrame)
from ui.uniqualizer_tab import UniqualizerTab
from ui.ai_slicer_tab import AiSlicerTab

# Темная тема (Оптимизированная)
DARK_THEME = """
    QMainWindow { background-color: #1e1e23; color: #e0e0e0; }
    QWidget { font-family: 'Segoe UI', sans-serif; font-size: 13px; }

    /* Панели */
    QFrame#Panel { background-color: #25252b; border: 1px solid #383838; border-radius: 8px; }

    /* Сайдбар */
    QListWidget#Sidebar {
        background-color: #25252b; border: none; border-right: 1px solid #383838; outline: none; padding-top: 10px;
    }
    QListWidget#Sidebar::item {
        padding: 12px 20px; margin: 4px 8px; border-radius: 6px; color: #aaa; font-weight: bold;
    }
    QListWidget#Sidebar::item:selected { background-color: #3a86ff; color: white; }
    QListWidget#Sidebar::item:hover:!selected { background-color: #2d2d33; color: #ccc; }

    /* Общие элементы */
    QLabel { color: #e0e0e0; }
    QGroupBox { 
        border: 1px solid #383838; border-radius: 8px; margin-top: 15px; font-weight: bold;
        background-color: #2a2a30; padding-top: 25px; padding-bottom: 10px; 
    }
    QGroupBox::title {
        subcontrol-origin: margin; subcontrol-position: top center; 
        padding: 4px 10px; background-color: #3a86ff; color: white; border-radius: 4px;
    }

    /* Поля ввода */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
        background-color: #1e1e23; border: 1px solid #383838; padding: 5px; color: #eee; border-radius: 4px;
    }
    QLineEdit:read-only, QTextEdit:read-only { background-color: #1a1a1a; color: #777; }

    /* Кнопки */
    QPushButton {
        background-color: #3a3a42; color: #ccc; border: 1px solid #4a4a52; 
        border-radius: 4px; padding: 6px 12px; font-weight: bold;
    }
    QPushButton:hover { background-color: #4a4a52; color: #fff; }

    QPushButton#AccentButton { background-color: #3a86ff; color: white; border: none; font-size: 14px; }
    QPushButton#AccentButton:hover { background-color: #2a76ef; }
    QPushButton#AccentButton:disabled { background-color: #333; color: #555; }

    QPushButton#StopButton { background-color: #e74c3c; color: white; border: none; }
    QPushButton#StopButton:hover { background-color: #c0392b; }
    QPushButton#StopButton:disabled { background-color: #333; color: #555; }

    /* Скроллбар */
    QScrollBar:vertical { background: #1e1e23; width: 8px; }
    QScrollBar::handle:vertical { background: #383838; border-radius: 4px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoUniq Desktop Ultimate")
        self.resize(1350, 900)
        self.setStyleSheet(DARK_THEME)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Сайдбар
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)

        self.sidebar.addItem(QListWidgetItem("⚙️  Уникализация"))
        self.sidebar.addItem(QListWidgetItem("🎬  Reels Maker AI"))  # Переименовано

        # 2. Страницы
        self.pages = QStackedWidget()
        self.tab_uniq = UniqualizerTab()
        self.tab_slice = AiSlicerTab()

        self.pages.addWidget(self.tab_uniq)
        self.pages.addWidget(self.tab_slice)

        # Связь
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(1)  # Открываем сразу Reels Maker

        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages)