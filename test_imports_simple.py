#!/usr/bin/env python3
"""
Тест для проверки корректности импортов модулей, не зависящих от PyQt6
"""

def test_core_imports():
    print("Проверка основных импортов (без PyQt6)...")
    
    try:
        # Проверим импорты, не зависящие от GUI
        from core.ffmpeg_worker import ProcessingWorker, PreviewWorker
        print("✓ from core.ffmpeg_worker import ProcessingWorker, PreviewWorker")
        
        from core.ai_slicer_worker import AiSlicerWorker
        print("✓ from core.ai_slicer_worker import AiSlicerWorker")
        
        from core.slicer_worker import SlicerWorker
        print("✓ from core.slicer_worker import SlicerWorker")
        
        from utils.text_generator import TextGenerator
        print("✓ from utils.text_generator import TextGenerator")
        
        # Также проверим, что в этих модулях нет ошибок импорта
        from utils import generators
        print("✓ from utils import generators")
        
        print("\nВсе основные импорты прошли успешно!")
        return True
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_relative_imports_fixed():
    print("\nПроверка, что больше нет относительных импортов за пределы пакета...")
    
    import subprocess
    # Ищем только импорты вида "from .." (относительные импорты за пределы текущего пакета)
    result = subprocess.run(['find', '/workspace', '-name', '*.py', '-not', '-path', '*/test_*', '-exec', 'grep', '-l', 'from \\..\\.', '{}', ';'], 
                           capture_output=True, text=True)
    
    if result.stdout.strip() == "":
        print("✓ Больше нет файлов с относительными импортами 'from ..' (за пределы пакета)")
        return True
    else:
        print(f"✗ Найдены файлы с относительными импортами за пределы пакета: {result.stdout}")
        return False

if __name__ == "__main__":
    success1 = test_core_imports()
    success2 = test_relative_imports_fixed()
    
    if success1 and success2:
        print("\n✓ Все тесты пройдены успешно. Проблема с относительными импортами устранена.")
    else:
        print("\n✗ Тесты не пройдены.")