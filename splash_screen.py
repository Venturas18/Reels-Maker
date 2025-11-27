from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        # Убираем рамки окна и делаем его поверх всех окон
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()

    def init_ui(self):
        self.setFixedSize(450, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Основной контейнер с закругленными краями
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #2b2b36;
                border-radius: 15px;
                border: 1px solid #444;
            }
        """)
        l_cont = QVBoxLayout(container)
        l_cont.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_cont.setSpacing(20)

        # Иконка (можно заменить на картинку, пока эмодзи)
        lbl_icon = QLabel("🎬")
        lbl_icon.setStyleSheet("font-size: 70px; border: none; background: transparent;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_cont.addWidget(lbl_icon)

        # Название
        lbl_title = QLabel("VideoUniq Desktop")
        lbl_title.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: white; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_cont.addWidget(lbl_title)

        # Статус
        self.lbl_status = QLabel("Инициализация...")
        self.lbl_status.setStyleSheet("font-size: 14px; color: #888; border: none; background: transparent;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_cont.addWidget(self.lbl_status)

        layout.addWidget(container)

    def set_status(self, text):
        self.lbl_status.setText(text)
        QApplication.processEvents()