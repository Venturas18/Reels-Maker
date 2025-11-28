#!/usr/bin/env python3
"""
Тест для проверки корректности запуска приложения без GUI
Проверяет все импорты, которые происходят при запуске main.py
"""
import sys
import os

def test_app_startup():
    """Проверяет, что все импорты в main.py работают корректно"""
    print("Тестирование импортов при запуске приложения...")
    
    try:
        # Имитируем импорты из main.py
        print("Проверка базовых импортов...")
        import sys
        import os
        import traceback
        from PyQt6.QtWidgets import QApplication
        print("✓ Базовые импорты")
        
        # Проверяем импорт главного окна (основной момент, вызывающий ошибки)
        print("Проверка импорта MainWindow...")
        from ui.main_window import MainWindow
        print("✓ from ui.main_window import MainWindow")
        
        # Проверяем, что все зависимости MainWindow также работают
        print("Проверка зависимостей MainWindow...")
        from ui.uniqualizer_tab import UniqualizerTab
        from ui.ai_slicer_tab import AiSlicerTab
        print("✓ Зависимости MainWindow работают")
        
        # Проверяем зависимости вкладок
        print("Проверка зависимостей вкладок...")
        from core.ffmpeg_worker import ProcessingWorker, PreviewWorker
        from core.ai_slicer_worker import AiSlicerWorker
        from utils.text_generator import TextGenerator
        print("✓ Зависимости вкладок работают")
        
        print("\n✓ Все импорты при запуске приложения прошли успешно!")
        print("Приложение должно запускаться без ошибок импорта.")
        return True
        
    except ImportError as e:
        print(f"✗ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_function_exists():
    """Проверяет, что функция main существует в main.py"""
    print("\nПроверка существования функции main...")
    
    try:
        # Динамический импорт функции main из main.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_module", "/workspace/main.py")
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        if hasattr(main_module, 'main'):
            print("✓ Функция main существует в main.py")
            return True
        else:
            print("✗ Функция main не найдена в main.py")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка при проверке функции main: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ: Проверка корректности запуска приложения")
    print("=" * 60)
    
    test1_result = test_app_startup()
    test2_result = test_main_function_exists()
    
    print("\n" + "=" * 60)
    if test1_result and test2_result:
        print("РЕЗУЛЬТАТ: ✓ Все тесты пройдены! Приложение готово к запуску.")
        sys.exit(0)
    else:
        print("РЕЗУЛЬТАТ: ✗ Тесты не пройдены! Есть проблемы с импортами.")
        sys.exit(1)