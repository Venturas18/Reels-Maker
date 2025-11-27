import random
import string
import datetime
import hashlib


def generate_unique_filename(original_name: str, pattern: str = "hash") -> str:
    """
    Генерирует уникальное имя файла на основе паттерна.
    """
    name, ext = original_name.rsplit('.', 1)

    if pattern == "hash":
        # MD5 хеш от времени + имени
        raw_str = f"{name}{datetime.datetime.now().timestamp()}"
        hash_str = hashlib.md5(raw_str.encode()).hexdigest()[:12]
        return f"{hash_str}.{ext}"

    elif pattern == "date_random":
        # VID_YYYYMMDD_RANDOM
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        rand_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"VID_{date_str}_{rand_suffix}.{ext}"

    return f"processed_{original_name}"


def get_random_speed(min_val=0.95, max_val=1.05):
    return round(random.uniform(min_val, max_val), 3)


def get_random_zoom(min_percent=1, max_percent=3):
    # Возвращает коэффициент масштабирования (например 1.02)
    val = random.uniform(min_percent, max_percent) / 100.0
    return 1.0 + val


def get_random_contrast(min_val=0.95, max_val=1.05):
    return round(random.uniform(min_val, max_val), 2)


def get_random_brightness(min_val=-0.05, max_val=0.05):
    return round(random.uniform(min_val, max_val), 2)


# --- НОВОЕ: Генераторы для звука ---
def get_random_eq_gain():
    # Случайное усиление/ослабление частот от -3dB до +3dB
    return round(random.uniform(-3, 3), 1)


def get_random_volume_factor():
    # Случайная громкость от 90% до 110%
    return round(random.uniform(0.9, 1.1), 2)


# --- Генератор фейковых устройств ---
def get_random_device_metadata():
    devices = [
        {"make": "Apple", "model": "iPhone 13 Pro", "software": "15.1"},
        {"make": "Apple", "model": "iPhone 14", "software": "16.0"},
        {"make": "Apple", "model": "iPhone 15 Pro Max", "software": "17.2"},
        {"make": "Samsung", "model": "SM-S901B (Galaxy S22)", "software": "Android 12"},
        {"make": "Samsung", "model": "SM-S911B (Galaxy S23)", "software": "Android 13"},
        {"make": "Google", "model": "Pixel 7", "software": "Android 13"},
        {"make": "Xiaomi", "model": "M2102K1G (Mi 11 Ultra)", "software": "Android 11"},
    ]
    return random.choice(devices)