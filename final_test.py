#!/usr/bin/env python3
"""
Финальный тест для проверки полной работоспособности приложения после рефакторинга
"""
import sys
import subprocess

def run_all_tests():
    """Запускает все тесты для проверки состояния проекта"""
    print("🔍 ФИНАЛЬНАЯ ПРОВЕРКА СОСТОЯНИЯ ПРОЕКТА")
    print("="*60)
    
    tests = [
        ("Проверка основных импортов", "python test_imports.py"),
        ("Проверка относительных импортов", "python test_imports_simple.py"),
        ("Проверка запуска приложения", "python test_app_startup.py"),
        ("Проверка импорта всех модулей", 'python -c "import ui.main_window; import core.ffmpeg_worker; import utils.text_generator; print(\'OK\')"'),
    ]
    
    results = []
    
    for test_name, command in tests:
        print(f"\n🧪 {test_name}")
        print(f"   Команда: {command}")
        
        try:
            result = subprocess.run(
                command.split(), 
                cwd="/workspace",
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                print("   ✅ УСПЕШНО")
                results.append(True)
            else:
                print(f"   ❌ ОШИБКА")
                print(f"   stderr: {result.stderr}")
                results.append(False)
                
        except subprocess.TimeoutExpired:
            print("   ⏰ ТАЙМАУТ")
            results.append(False)
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅" if results[i] else "❌"
        print(f"  {status} {test_name}")
    
    print(f"\nИтого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Проект полностью готов к работе.")
        print("📌 Все проблемы с импортами устранены, структура пакетов корректна.")
        return True
    else:
        print(f"\n💥 {total-passed} ТЕСТОВ НЕ ПРОЙДЕНО! Требуется дополнительная работа.")
        return False

def check_project_structure():
    """Проверяет структуру проекта"""
    print("\n🏗️  ПРОВЕРКА СТРУКТУРЫ ПРОЕКТА")
    
    import os
    expected_dirs = ['/workspace/ui', '/workspace/core', '/workspace/utils']
    expected_files = [
        '/workspace/ui/__init__.py',
        '/workspace/core/__init__.py', 
        '/workspace/utils/__init__.py',
        '/workspace/main.py'
    ]
    
    all_good = True
    
    for d in expected_dirs:
        if not os.path.isdir(d):
            print(f"   ❌ Папка не найдена: {d}")
            all_good = False
        else:
            print(f"   ✅ Папка найдена: {d}")
    
    for f in expected_files:
        if not os.path.isfile(f):
            print(f"   ❌ Файл не найден: {f}")
            all_good = False
        else:
            print(f"   ✅ Файл найден: {f}")
    
    if all_good:
        print("   ✅ Структура проекта корректна")
    else:
        print("   ❌ Структура проекта требует исправления")
    
    return all_good

if __name__ == "__main__":
    structure_ok = check_project_structure()
    tests_ok = run_all_tests()
    
    print("\n" + "🎯 ИТОГОВАЯ ОЦЕНКА:")
    if structure_ok and tests_ok:
        print("✅ ПРОЕКТ ПОЛНОСТЬЮ ГОТОВ К РАБОТЕ")
        print("✅ Все импорты работают корректно")
        print("✅ Структура пакетов правильная")
        print("✅ Приложение готово к запуску")
        sys.exit(0)
    else:
        print("❌ ПРОЕКТ ТРЕБУЕТ ДОПОЛНИТЕЛЬНОЙ РАБОТЫ")
        sys.exit(1)