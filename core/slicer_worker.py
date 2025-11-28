import os
import subprocess
import re
import textwrap
import shutil  # Добавил для надежности
from PyQt6.QtCore import QThread, pyqtSignal
from utils.text_generator import TextGenerator


class SlicerWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    result_signal = pyqtSignal(str)

    def __init__(self, settings, preview=False):
        super().__init__()
        self.s = settings
        self.preview = preview
        self.is_running = True

        font = self.s.get('font', '')
        if not font: font = "arialbd.ttf"
        self.text_gen = TextGenerator(font_path=font)

    def parse_time(self, time_str):
        parts = time_str.strip().split(':')
        try:
            if len(parts) == 4:
                h, m, s, f = map(int, parts); return h * 3600 + m * 60 + s
            elif len(parts) == 3:
                h, m, s = map(int, parts); return h * 3600 + m * 60 + s
        except:
            pass
        return 0

    def prepare_text(self, text):
        if self.s['caps']: text = text.upper()
        text = text.replace(":", "\:").replace("'", "").replace("%", "\\%")
        return textwrap.fill(text, width=20)

    def get_drawtext_filter(self, text):
        font = self.s['font']
        if not font or not os.path.exists(font):
            font = "C\:/Windows/Fonts/arialbd.ttf"
        else:
            font = font.replace("\\", "/").replace(":", "\\:")

        col = self.s['color'].replace("#", "0x")
        size = self.s['size']
        y_top = self.s['y']
        h_zone = self.s['h']

        return (f"drawtext=fontfile='{font}':text='{text}':"
                f"fontcolor={col}:fontsize={size}:"
                f"x=(w-text_w)/2:y={y_top}+({h_zone}-text_h)/2:"
                f"borderw=3:bordercolor=black:shadowx=2:shadowy=2")

    def run(self):
        # --- ПРЕВЬЮ ---
        if self.preview:
            try:
                # Используем АБСОЛЮТНЫЕ пути от текущей рабочей директории
                base_dir = os.getcwd()
                header_img = os.path.join(base_dir, "temp_header.png")
                out_preview = os.path.join(base_dir, "slice_preview.jpg")

                # Удаляем старые файлы, если есть
                if os.path.exists(out_preview): os.remove(out_preview)
                if os.path.exists(header_img): os.remove(header_img)

                txt = self.s['static_text'] if self.s['static_text'] else "ТЕСТОВЫЙ ЗАГОЛОВОК"

                # 1. Создаем картинку текста
                self.text_gen.create_header_image(
                    text=txt,
                    output_path=header_img,
                    font_size=self.s['size'],
                    text_color=self.s['color'],
                    y_pos=self.s['y']
                )

                # 2. Запускаем FFmpeg
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", "10", "-i", self.s['video'],
                    "-i", header_img,
                    "-filter_complex", "[0:v][1:v]overlay=0:0[v_out]",
                    "-map", "[v_out]",
                    "-frames:v", "1", "-q:v", "2", "-update", "1", out_preview
                ]

                si = subprocess.STARTUPINFO();
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(cmd, startupinfo=si, check=True)

                # 3. Проверяем и отдаем результат
                if os.path.exists(out_preview):
                    self.result_signal.emit(out_preview)
                else:
                    self.log_signal.emit("❌ Файл превью не был создан!")

                # Чистим мусор
                if os.path.exists(header_img): os.remove(header_img)

            except Exception as e:
                self.log_signal.emit(f"❌ Ошибка превью: {e}")

            self.finished_signal.emit()
            return

        # --- НАРЕЗКА (ОСНОВНОЙ ПРОЦЕСС) ---
        os.makedirs(self.s['out'], exist_ok=True)
        segments = []
        try:
            with open(self.s['txt'], 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines:
                match = re.match(r'([\d:]+)-([\d:]+)\s*\|\s*(.+)', line.strip())
                if match:
                    start, end, txt = match.groups()
                    s_sec = self.parse_time(start);
                    e_sec = self.parse_time(end)
                    if e_sec > s_sec: segments.append((s_sec, e_sec, txt.strip()))
        except Exception as e:
            self.log_signal.emit(f"Ошибка TXT: {e}"); self.finished_signal.emit(); return

        total = len(segments)
        self.log_signal.emit(f"Найдено сегментов: {total}")

        # Генерируем пути для временной картинки заголовка (в цикле она будет перезаписываться)
        base_dir = os.getcwd()
        temp_png = os.path.join(base_dir, "temp_header_render.png")

        for i, (start, end, raw_text) in enumerate(segments):
            if not self.is_running: break

            duration = end - start
            safe_name = re.sub(r'[\\/*?:"<>|]', "", raw_text)[:50]
            out_path = os.path.join(self.s['out'], f"{i + 1:02d}_{safe_name}.mp4")

            self.log_signal.emit(f"✂️ [{i + 1}/{total}] {safe_name}")

            # Текст: либо общий из настроек, либо из файла
            header_text = self.s['static_text'] if self.s['static_text'] else raw_text

            # Создаем PNG
            self.text_gen.create_header_image(
                text=header_text,
                output_path=temp_png,
                font_size=self.s['size'],
                text_color=self.s['color'],
                y_pos=self.s['y']
            )

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start), "-i", self.s['video'],
                "-i", temp_png,
                "-t", str(duration),
                "-filter_complex", "[0:v][1:v]overlay=0:0[v_out]",
                "-map", "[v_out]", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac",
                out_path
            ]

            si = subprocess.STARTUPINFO();
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=si)
            _, stderr = p.communicate()

            if p.returncode != 0:
                self.log_signal.emit(f"⚠️ Ошибка: {stderr}")

            self.progress_signal.emit(int(((i + 1) / total) * 100))

        # Удаляем времянку после всего
        if os.path.exists(temp_png): os.remove(temp_png)

        self.finished_signal.emit()

    def stop(self):
        self.is_running = False