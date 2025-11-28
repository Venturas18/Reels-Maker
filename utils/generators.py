import os
import time
import random
import string
from datetime import datetime


def generate_unique_filename(original_filename, mode="date_random"):
    """
    Генерирует уникальное имя файла на основе оригинального имени
    :param original_filename: Оригинальное имя файла
    :param mode: Режим генерации ("date_random", "random", "timestamp")
    :return: Уникальное имя файла
    """
    name, ext = os.path.splitext(original_filename)
    
    if mode == "date_random":
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{date_str}_{random_str}{ext}"
    elif mode == "random":
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{random_str}{ext}"
    elif mode == "timestamp":
        timestamp = int(time.time())
        return f"{timestamp}{ext}"
    else:
        return original_filename


def get_random_device_metadata():
    """
    Возвращает случайные метаданные устройства для подмены
    :return: Словарь с метаданными устройства
    """
    devices = [
        {
            "model": "SM-G991B",
            "manufacturer": "Samsung",
            "software": "One UI 4.1"
        },
        {
            "model": "SM-N986B",
            "manufacturer": "Samsung",
            "software": "One UI 3.1"
        },
        {
            "model": "iPhone14,3",
            "manufacturer": "Apple",
            "software": "iOS 15.3"
        },
        {
            "model": "Pixel 6 Pro",
            "manufacturer": "Google",
            "software": "Android 12"
        },
        {
            "model": "Redmi Note 11",
            "manufacturer": "Xiaomi",
            "software": "MIUI 13"
        }
    ]
    
    return random.choice(devices)


if __name__ == "__main__":
    # Тестирование функций
    print("Тест генерации уникального имени файла:")
    print(generate_unique_filename("test.mp4"))
    print(generate_unique_filename("test.mp4", "random"))
    print(generate_unique_filename("test.mp4", "timestamp"))
    
    print("\nТест метаданных устройства:")
    print(get_random_device_metadata())