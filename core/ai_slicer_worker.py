import os
import json
import subprocess
import time
import datetime
import re
from PyQt6.QtCore import QThread, pyqtSignal
import google.generativeai as genai

# Попытка импорта стандартного Whisper
try:
    import whisper

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from ..utils.text_generator import TextGenerator


class AiSlicerWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, settings, mode='analyze'):
        super().__init__()
        self.s = settings
        self.mode = mode
        self.is_running = True
        self.current_process = None

        self.text_gen = TextGenerator(width=1080, height=1920)

        self.json_path = os.path.join(self.s['out'], "analysis_result.json")
        self.raw_cache_path = os.path.join(self.s['out'], "whisper_raw.json")
        self.review_txt_path = os.path.join(self.s['out'], "00_REVIEW_SEGMENTS.txt")

    def run(self):
        try:
            if self.mode == 'analyze':
                self.run_semantic_analysis()
            elif self.mode == 'slice':
                self.run_slicing()
        except Exception as e:
            self.log_signal.emit(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
            import traceback
            traceback.print_exc()

        self.finished_signal.emit()

    def stop(self):
        self.is_running = False
        if self.current_process:
            try:
                self.current_process.kill()
                self.log_signal.emit("⚠️ Процесс остановлен.")
            except:
                pass

    def format_ts_review(self, seconds):
        """Формат для отчета: 00:00:00"""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))

    # ==========================================
    # ЭТАП 1: УМНЫЙ АНАЛИЗ (ADAPTIVE AI)
    # ==========================================
    def run_semantic_analysis(self):
        video_path = self.s['video']
        os.makedirs(self.s['out'], exist_ok=True)
        whisper_segments = []

        # 0. FORCE
        if self.s.get('force_whisper') and os.path.exists(self.raw_cache_path):
            self.log_signal.emit("🔄 Удаляю старый кэш...")
            os.remove(self.raw_cache_path)

        # 1. ЗАГРУЗКА КЭША
        if os.path.exists(self.raw_cache_path):
            self.log_signal.emit("⏩ Загрузка текста из кэша...")
            try:
                with open(self.raw_cache_path, 'r', encoding='utf-8') as f:
                    whisper_segments = json.load(f)
                self.log_signal.emit(f"✅ Загружено {len(whisper_segments)} фраз.")
            except:
                whisper_segments = []

        # 2. WHISPER (если нет кэша)
        if not whisper_segments:
            if not self.is_running: return
            if not WHISPER_AVAILABLE:
                self.log_signal.emit("❌ Ошибка: Нет библиотеки whisper!")
                return

            model_name = self.s.get('whisper_model', 'medium')
            lang = self.s.get('whisper_lang')

            self.log_signal.emit(f"🎧 Запуск Whisper ({model_name})...")
            try:
                device = "cuda" if subprocess.run("nvidia-smi", shell=True).returncode == 0 else "cpu"
                model = whisper.load_model(model_name, device=device)

                lang_str = f"Lang: {lang}" if lang else "Auto"
                self.log_signal.emit(f"🎤 Транскрибация на {device.upper()} ({lang_str})...")

                result = model.transcribe(video_path, fp16=False, verbose=False, language=lang)

                if not self.is_running: return

                for i, seg in enumerate(result.get('segments', [])):
                    whisper_segments.append({
                        'id': i,
                        'start': seg['start'],
                        'end': seg['end'],
                        'text': seg['text'].strip()
                    })

                with open(self.raw_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(whisper_segments, f, ensure_ascii=False, indent=4)
                self.log_signal.emit("💾 Текст сохранен.")

            except Exception as e:
                self.log_signal.emit(f"⚠️ Ошибка Whisper: {e}")
                return

        self.progress_signal.emit(30)

        # 3. ПОДГОТОВКА ДАННЫХ ДЛЯ AI
        if not self.s['use_gemini'] or not self.s['gemini_key']:
            self.log_signal.emit("⚠️ Gemini выключен! Нарезка невозможна.")
            return

        self.log_signal.emit("🧠 Запуск AI-продюсера...")

        # Считаем общую длительность видео по последнему сегменту
        total_duration_sec = whisper_segments[-1]['end'] if whisper_segments else 0
        total_minutes = total_duration_sec / 60

        # --- АДАПТИВНАЯ ЛОГИКА КОЛИЧЕСТВА ---
        # Правило: ~1 клип на каждые 5 минут видео, но минимум 1
        if total_minutes < 6:
            target_qty_desc = "Select exactly 1 best segment (The viral highlight)."
        elif total_minutes < 20:
            target_qty_desc = "Select 2 to 4 viral segments. Only the best parts."
        elif total_minutes < 60:
            target_qty_desc = "Select 5 to 10 viral segments. Skip boring parts."
        else:
            target_qty_desc = "Select 10 to 20 viral segments. Focus on high engagement."

        self.log_signal.emit(f"📊 Длительность: {int(total_minutes)} мин. План: {target_qty_desc}")

        # Готовим текст с ID
        transcript_buffer = ""
        for seg in whisper_segments:
            ts = self.format_ts_review(seg['start'])
            transcript_buffer += f"[{seg['id']}] {ts}: {seg['text']}\n"

        min_d = self.s.get('min_duration', 60)
        max_d = self.s.get('max_duration', 180)
        user_prompt = self.s.get('ai_prompt', '')

        # --- ЖЕСТКИЙ ПРОМПТ (RUSSIAN ONLY) ---
        prompt = f"""
        Role: Expert Video Editor & Content Curator.
        Task: Analyze the transcript and extract viral clips for Reels/TikTok.

        Video Context: {user_prompt}
        Total Video Duration: {int(total_minutes)} minutes.
        QUANTITY GOAL: {target_qty_desc}

        STRICT RULES:
        1. DO NOT cover the whole video. IGNORE boring parts, intros, outros.
        2. Clip duration must be between {min_d} and {max_d} seconds.
        3. OUTPUT LANGUAGE: RUSSIAN (Русский) for Titles!
        4. Titles must be short (3-5 words), punchy, clickbait.
        5. Return ONLY valid JSON.

        Output JSON Format:
        [
            {{
                "start_id": <int: ID of the first phrase>,
                "end_id": <int: ID of the last phrase>,
                "title": "<RUSSIAN TITLE HERE>"
            }}
        ]

        TRANSCRIPT:
        {transcript_buffer}
        """

        # 4. ЗАПРОС К GEMINI
        genai.configure(api_key=self.s['gemini_key'])
        try:
            model_gemini = genai.GenerativeModel('gemini-2.5-flash')
        except:
            model_gemini = genai.GenerativeModel('gemini-1.5-pro')

        try:
            self.log_signal.emit("📡 Анализ смыслов (это может занять время)...")
            # Для очень больших видео (часовых) можно разбить на части,
            # но Gemini 1.5/2.5 имеет контекст 1М-2М токенов, так что 1 час влезет легко.

            response = model_gemini.generate_content(prompt)

            json_str = response.text.replace('```json', '').replace('```', '').strip()
            ai_clips = json.loads(json_str)

            self.log_signal.emit(f"🔥 AI отобрал {len(ai_clips)} топовых моментов!")

            final_segments = []
            for clip in ai_clips:
                s_id = clip.get('start_id')
                e_id = clip.get('end_id')

                # Валидация
                if s_id is None or e_id is None: continue
                if s_id >= len(whisper_segments) or e_id >= len(whisper_segments): continue
                if s_id > e_id: continue

                start_seg = whisper_segments[s_id]
                end_seg = whisper_segments[e_id]

                # Проверка длительности
                dur = end_seg['end'] - start_seg['start']
                if dur < 10: continue  # Мусор

                final_segments.append({
                    'start': start_seg['start'],
                    'end': end_seg['end'],
                    'title': clip.get('title', 'Интересный момент')
                })
                self.log_signal.emit(f"  🔹 {clip.get('title')} ({int(dur)}с)")

            self.save_results(final_segments)

        except Exception as e:
            self.log_signal.emit(f"⚠️ Ошибка AI: {e}")
            self.log_signal.emit("Попробуйте другой промпт или модель.")

        self.progress_signal.emit(100)

    def save_results(self, segments):
        # JSON для машины
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(segments, f, ensure_ascii=False, indent=4)

        # TXT для человека (ВАШ ФОРМАТ)
        with open(self.review_txt_path, 'w', encoding='utf-8') as f:
            for seg in segments:
                st = self.format_ts_review(seg['start'])
                en = self.format_ts_review(seg['end'])
                # Формат: 00:00:00 - 00:00:00 | Заголовок
                f.write(f"{st} - {en} | {seg.get('title', '---')}\n\n")

        self.log_signal.emit(f"✅ ОТЧЕТ ГОТОВ!")
        self.log_signal.emit(f"📄 Файл: {self.review_txt_path}")

    # ==========================================
    # ЭТАП 2: НАРЕЗКА (Без изменений)
    # ==========================================
    def detect_silence_segments(self, path, start, duration, db=-30, min_dur=0.5):
        try:
            cmd = ["ffmpeg", "-ss", str(start), "-t", str(duration), "-i", path, "-af",
                   f"silencedetect=noise={db}dB:d={min_dur}", "-f", "null", "-"]
            si = subprocess.STARTUPINFO();
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, startupinfo=si)
            _, stderr = p.communicate()
            log = stderr.decode('utf-8', errors='ignore')
            starts = [float(x) for x in re.findall(r"silence_start: ([\d\.]+)", log)]
            ends = [float(x) for x in re.findall(r"silence_end: ([\d\.]+)", log)]
            if not starts: return None
            keep = [];
            curr = 0.0
            for i in range(len(starts)):
                if starts[i] > curr: keep.append((curr, starts[i]))
                curr = ends[i] if i < len(ends) else duration
            if curr < duration: keep.append((curr, duration))
            return keep
        except:
            return None

    def run_slicing(self):
        if not os.path.exists(self.json_path): self.log_signal.emit("❌ Нет файла!"); return
        with open(self.json_path, 'r', encoding='utf-8') as f:
            segments = json.load(f)
        total = len(segments)
        video_path = self.s['video']
        temp_img = os.path.abspath("temp_ai_title.png")

        for i, seg in enumerate(segments):
            if not self.is_running: self.log_signal.emit("⛔ Стоп."); break

            safe_title = "".join([c for c in seg.get('title', 'No') if c.isalnum() or c in (' ', '-', '_')]).strip()[
                :50]
            out_name = f"{i + 1:02d}_{safe_title}.mp4"
            out_file = os.path.join(self.s['out'], out_name)

            if os.path.exists(out_file):
                self.progress_signal.emit(int(((i + 1) / total) * 100))
                continue

            self.log_signal.emit(f"🎬 Рендер [{i + 1}/{total}]: {safe_title}")

            # 1. ТЕКСТ
            has_text = not self.s.get('no_text_render', False)
            if has_text:
                disp = seg.get('title', '')
                if self.s['caps']: disp = disp.upper()
                font_src = self.s.get('font_source')
                self.text_gen.create_header_image(
                    text=disp, output_path=temp_img,
                    font_source=font_src if font_src else "impact.ttf",
                    max_font_size=self.s.get('max_font_size', 110),
                    text_color=self.s.get('text_color', '#FFD700'),
                    stroke_color=self.s.get('stroke_color', '#000000'),
                    stroke_width_pct=self.s.get('stroke_width_pct', 5),
                    y_top_limit=self.s.get('y_top', 150),
                    y_bottom_limit=self.s.get('y_bot', 600)
                )

            dur = seg['end'] - seg['start']

            # 2. ТИШИНА
            keep = None
            if self.s.get('silence_cut'):
                self.log_signal.emit("   ✂️ Поиск тишины...")
                keep = self.detect_silence_segments(video_path, seg['start'], dur, self.s.get('silence_db'),
                                                    self.s.get('silence_dur'))

            # 3. ФИЛЬТРЫ
            w, h = 1080, 1920
            visual_filter = f"[v_in]split=2[bg][fg];[bg]scale=iw/4:-1,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:10[bg_blur];[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fg_scaled];[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2[v_base]"

            if has_text:
                visual_filter += f";[v_base][1:v]overlay=0:0[v_out]"
            else:
                visual_filter += f"[v_out]"

            if keep and len(keep) > 1:
                concat_inputs = "";
                concat_map = ""
                for idx, (s, e) in enumerate(keep):
                    concat_inputs += f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{idx}];[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{idx}];"
                    concat_map += f"[v{idx}][a{idx}]"
                concat_filter = f"{concat_inputs}{concat_map}concat=n={len(keep)}:v=1:a=1[v_in][a_out];"
                full_filter = concat_filter + visual_filter
                map_audio = "[a_out]"
            else:
                full_filter = f"[0:v]copy[v_in];" + visual_filter
                map_audio = "0:a"

            cmd = ["ffmpeg", "-y", "-ss", str(seg['start']), "-i", video_path]
            if has_text: cmd += ["-i", temp_img]
            cmd += ["-t", str(dur), "-filter_complex", full_filter, "-map", "[v_out]", "-map", map_audio, "-c:v",
                    "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", out_file]

            si = subprocess.STARTUPINFO();
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=si)
            _, stderr = self.current_process.communicate()
            if self.current_process.returncode != 0 and self.is_running: self.log_signal.emit(
                f"⚠️ Ошибка рендера {out_name}")
            self.current_process = None
            self.progress_signal.emit(int(((i + 1) / total) * 100))

        if os.path.exists(temp_img): os.remove(temp_img)