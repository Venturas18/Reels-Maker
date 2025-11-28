#!/usr/bin/env python3
"""
Тест для проверки корректности импортов после изменения с относительных на абсолютные
"""

def test_imports():
    print("Проверка импортов...")
    
    try:
        # Проверим основные импорты
        from ui.main_window import MainWindow
        print("✓ from ui.main_window import MainWindow")
        
        from ui.uniqualizer_tab import UniqualizerTab
        print("✓ from ui.uniqualizer_tab import UniqualizerTab")
        
        from ui.ai_slicer_tab import AiSlicerTab
        print("✓ from ui.ai_slicer_tab import AiSlicerTab")
        
        from ui.slicer_tab import SlicerTab
        print("✓ from ui.slicer_tab import SlicerTab")
        
        from core.ffmpeg_worker import ProcessingWorker, PreviewWorker
        print("✓ from core.ffmpeg_worker import ProcessingWorker, PreviewWorker")
        
        from core.ai_slicer_worker import AiSlicerWorker
        print("✓ from core.ai_slicer_worker import AiSlicerWorker")
        
        from core.slicer_worker import SlicerWorker
        print("✓ from core.slicer_worker import SlicerWorker")
        
        from utils.text_generator import TextGenerator
        print("✓ from utils.text_generator import TextGenerator")
        
        # Проверим импорт в main.py
        from main import main
        print("✓ from main import main")
        
        print("\nВсе импорты прошли успешно!")
        return True
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n✓ Все тесты пройдены успешно. Проблема с импортами устранена.")
    else:
        print("\n✗ Тесты не пройдены. Остались проблемы с импортами.")