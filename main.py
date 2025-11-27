import sys
import os
import traceback
from PyQt6.QtWidgets import QApplication

# Настройка путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'src'))

try:
    from ui.main_window import MainWindow
except ImportError as e:
    print(f"!!! ОШИБКА ИМПОРТА !!!\n{e}")
    traceback.print_exc()
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Сразу запускаем главное окно без ожиданий
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()