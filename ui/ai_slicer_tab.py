import os
import subprocess
import json
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTextEdit, QProgressBar,
    QGroupBox, QCheckBox, QFrame, QSpinBox, QComboBox,
    QTabWidget, QDialog, QMessageBox, QDoubleSpinBox, QGridLayout,
    QColorDialog, QSlider, QSizePolicy, QPlainTextEdit, QSpacerItem
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPixmap
from core.ai_slicer_worker import AiSlicerWorker
from utils.text_generator import TextGenerator


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки API")
        self.setFixedSize(400, 150)
        self.settings = QSettings("VideoUniq", "AiSlicer")

        # Стили
        self.setStyleSheet("""
            QDialog { background-color: #2b2b36; color: #fff; }
            QLineEdit { background-color: #1e1e23; color: #fff; border: 1px solid #555; padding: 5px; }
            QPushButton { background-color: #3a86ff; color: white; border: none; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #2a76ef; }
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("🔑 Google Gemini API Key:"))
        self.txt_key = QLineEdit()
        self.txt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_key.setText(self.settings.value("gemini_key", ""))
        layout.addWidget(self.txt_key)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

    def save_and_close(self):
        self.settings.setValue("gemini_key", self.txt_key.text().strip())
        self.accept()


class AiSlicerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.video_path = ""
        self.out_path = os.path.abspath("output_reels")
        self.worker = None
        self.app_settings = QSettings("VideoUniq", "AiSlicer")

        # Настройки текста
        self.text_color = "#FFD700"
        self.stroke_color = "#000000"
        self.custom_font_path = None
        self.preview_frame_path = "temp_frame_preview.jpg"

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === 1. ВЕРХНЯЯ ПАНЕЛЬ ===
        top_frame = QFrame()
        top_frame.setObjectName("Panel")
        top_frame.setStyleSheet("#Panel { background-color: #25252b; border-radius: 8px; border: 1px solid #383838; }")

        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 10, 10, 10)

        self.txt_vid = QLineEdit()
        self.txt_vid.setPlaceholderText("Выберите исходное видео...")
        self.txt_vid.setReadOnly(True)

        btn_vid = QPushButton("📂")
        btn_vid.setToolTip("Выбрать видео файл")
        btn_vid.setFixedWidth(40)
        btn_vid.clicked.connect(self.select_video)

        btn_open = QPushButton("Папка")
        btn_open.setToolTip("Открыть папку сохранения")
        btn_open.clicked.connect(self.open_output_folder)

        btn_settings = QPushButton("API")
        btn_settings.setFixedWidth(50)
        btn_settings.clicked.connect(self.open_settings)

        top_layout.addWidget(self.txt_vid)
        top_layout.addWidget(btn_vid)
        top_layout.addWidget(btn_open)
        top_layout.addWidget(btn_settings)

        main_layout.addWidget(top_frame)

        self.lbl_video_info = QLabel("ℹ️ Файл не выбран")
        self.lbl_video_info.setStyleSheet("color: #888; margin-left: 5px;")
        main_layout.addWidget(self.lbl_video_info)

        # === 2. ТАБЫ ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #383838; background: #1e1e23; border-radius: 5px; top: -1px; } 
            QTabBar::tab { background: #25252b; color: #aaa; padding: 8px 20px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #3a86ff; color: white; font-weight: bold; }
            QTabBar::tab:hover:!selected { background: #333; }
        """)

        self.tab_ai = QWidget()
        self.tab_slice = QWidget()
        self.tab_visual = QWidget()
        self.tab_text = QWidget()

        self.init_tab_ai()
        self.init_tab_slice()
        self.init_tab_visual()
        self.init_tab_text()

        self.tabs.addTab(self.tab_ai, "1. Транскрибация и AI")
        self.tabs.addTab(self.tab_slice, "2. Нарезка")
        self.tabs.addTab(self.tab_visual, "3. Визуал")
        self.tabs.addTab(self.tab_text, "4. Текст")

        main_layout.addWidget(self.tabs)

        # === 3. ЗОНА ЛОГОВ (УВЕЛИЧЕНА) ===
        log_group = QGroupBox("Журнал событий")
        log_group.setStyleSheet(
            "QGroupBox { border: 1px solid #383838; border-radius: 5px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")

        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 15, 5, 5)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(250)  # УВЕЛИЧИЛ ВЫСОТУ ТУТ
        self.log_box.setStyleSheet(
            "background-color: #111; color: #0f0; font-family: Consolas; font-size: 12px; border: none;")
        log_layout.addWidget(self.log_box)

        self.prog = QProgressBar()
        self.prog.setTextVisible(False)
        self.prog.setFixedHeight(5)
        self.prog.setStyleSheet(
            "QProgressBar { background: #333; border: none; } QProgressBar::chunk { background: #3a86ff; }")
        log_layout.addWidget(self.prog)

        main_layout.addWidget(log_group)

        # === 4. ФУТЕР ===
        footer_frame = QFrame()
        footer_frame.setObjectName("Panel")
        footer_frame.setStyleSheet(
            "#Panel { background-color: #25252b; border-radius: 8px; border: 1px solid #383838; }")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(10, 10, 10, 10)

        self.btn_analyze = QPushButton("1. АНАЛИЗ")
        self.btn_analyze.setMinimumHeight(45)
        self.btn_analyze.setObjectName("AccentButton")
        self.btn_analyze.clicked.connect(self.start_analysis)
        footer_layout.addWidget(self.btn_analyze)

        self.btn_stop = QPushButton("СТОП")
        self.btn_stop.setMinimumHeight(45)
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_process)
        footer_layout.addWidget(self.btn_stop)

        self.btn_slice = QPushButton("2. НАРЕЗКА")
        self.btn_slice.setMinimumHeight(45)
        self.btn_slice.setObjectName("AccentButton")
        self.btn_slice.setEnabled(False)
        self.btn_slice.clicked.connect(self.start_slicing)
        footer_layout.addWidget(self.btn_slice)

        main_layout.addWidget(footer_frame)

    # --- ИНИЦИАЛИЗАЦИЯ ВКЛАДОК ---

    def init_tab_ai(self):
        main_l = QHBoxLayout(self.tab_ai)
        main_l.setSpacing(20)

        # КОЛОНКА 1: WHISPER
        col1 = QVBoxLayout()
        grp_w = QGroupBox("Настройки Whisper")
        gw = QGridLayout(grp_w)
        gw.setSpacing(10)

        gw.addWidget(QLabel("Модель:"), 0, 0)
        self.combo_model = QComboBox()
        self.combo_model.addItems(["medium", "large-v3", "small", "base"])
        self.combo_model.setCurrentText("medium")
        gw.addWidget(self.combo_model, 0, 1)

        gw.addWidget(QLabel("Язык:"), 1, 0)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Auto", "Russian", "English", "Ukrainian", "Spanish"])
        gw.addWidget(self.combo_lang, 1, 1)

        self.chk_whisper = QCheckBox("Включить транскрибацию")
        self.chk_whisper.setChecked(True)
        gw.addWidget(self.chk_whisper, 2, 0, 1, 2)

        self.chk_force_whisper = QCheckBox("Перезаписать кэш (Force)")
        gw.addWidget(self.chk_force_whisper, 3, 0, 1, 2)

        col1.addWidget(grp_w)
        col1.addStretch()

        # КОЛОНКА 2: GEMINI
        col2 = QVBoxLayout()
        grp_g = QGroupBox("Настройки AI (Смыслы)")
        gg = QVBoxLayout(grp_g)
        gg.setSpacing(10)

        self.chk_gemini = QCheckBox("Включить AI-анализ (Gemini)")
        self.chk_gemini.setChecked(True)
        gg.addWidget(self.chk_gemini)

        gg.addWidget(QLabel("Промпт:"))
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlaceholderText("О чем видео (для лучшего понимания контекста)...")
        self.txt_prompt.setMaximumHeight(80)
        gg.addWidget(self.txt_prompt)

        col2.addWidget(grp_g)
        col2.addStretch()

        main_l.addLayout(col1, 1)
        main_l.addLayout(col2, 1)

    def init_tab_slice(self):
        l = QVBoxLayout(self.tab_slice)
        l.setSpacing(15)

        # Импорт
        grp_imp = QGroupBox("Ручной импорт")
        li = QHBoxLayout(grp_imp)
        li.addWidget(QLabel("Есть готовый TXT с таймкодами?"))
        btn_imp = QPushButton("📄 Загрузить список")
        btn_imp.clicked.connect(self.import_manual_txt)
        li.addWidget(btn_imp)
        l.addWidget(grp_imp)

        # Авто
        grp_auto = QGroupBox("Параметры нарезки")
        la = QVBoxLayout(grp_auto)

        h_preset = QHBoxLayout()
        h_preset.addWidget(QLabel("Длительность:"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(
            ["🤖 АВТО (Умный подбор 1-2 мин)", "⚡ Короткие Reels (60-90 сек)", "📹 Средние (1.5 - 3 минуты)",
             "🎞 Длинные (3 - 5 минут)"])
        h_preset.addWidget(self.combo_preset, 1)
        la.addLayout(h_preset)

        self.chk_auto_split = QCheckBox("Искать смысловые паузы")
        self.chk_auto_split.setChecked(True)
        la.addWidget(self.chk_auto_split)
        l.addWidget(grp_auto)

        # Jump Cuts
        grp_jc = QGroupBox("✂️ Jump Cuts (Удаление тишины)")
        grp_jc.setCheckable(True)
        grp_jc.setChecked(False)
        self.grp_silence = grp_jc

        lj = QHBoxLayout(grp_jc)
        lj.addWidget(QLabel("Порог:"))
        self.spin_sil_db = QSpinBox()
        self.spin_sil_db.setRange(-60, -10);
        self.spin_sil_db.setValue(-30);
        self.spin_sil_db.setSuffix(" dB")
        lj.addWidget(self.spin_sil_db)
        lj.addSpacing(20)
        lj.addWidget(QLabel("Длит >"))
        self.spin_sil_dur = QDoubleSpinBox()
        self.spin_sil_dur.setRange(0.1, 5.0);
        self.spin_sil_dur.setValue(0.50);
        self.spin_sil_dur.setSuffix(" с")
        lj.addWidget(self.spin_sil_dur)
        lj.addStretch()
        l.addWidget(grp_jc)
        l.addStretch()

    def init_tab_visual(self):
        l = QVBoxLayout(self.tab_visual)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)

        container = QWidget()
        lc = QVBoxLayout(container)
        lc.setSpacing(20)

        grp_v = QGroupBox("Настройки видео")
        lv = QVBoxLayout(grp_v)

        h = QHBoxLayout()
        h.addWidget(QLabel("Формат:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["9:16 (Vertical)", "1:1 (Square)", "16:9 (Horizontal)"])
        h.addWidget(self.combo_format)
        lv.addLayout(h)

        self.chk_blur_bg = QCheckBox("Blur Background (Размытый фон)")
        self.chk_blur_bg.setChecked(True)
        lv.addWidget(self.chk_blur_bg)

        self.chk_face_track = QCheckBox("Face Tracking (Авто-центровка)")
        self.chk_face_track.setChecked(True)
        lv.addWidget(self.chk_face_track)

        lc.addWidget(grp_v)
        l.addWidget(container)

    def init_tab_text(self):
        l = QHBoxLayout(self.tab_text)
        left_col = QVBoxLayout()

        self.chk_no_text_render = QCheckBox("🚫 НЕ НАКЛАДЫВАТЬ ТЕКСТ (Чистое видео)")
        self.chk_no_text_render.setStyleSheet("color: #ff5555; font-weight: bold; margin-bottom: 10px;")
        self.chk_no_text_render.toggled.connect(self.update_preview)
        left_col.addWidget(self.chk_no_text_render)

        grp_style = QGroupBox("Стиль текста")
        ls = QGridLayout(grp_style)

        ls.addWidget(QLabel("Шрифт:"), 0, 0)
        h_font = QHBoxLayout()
        self.lbl_font_name = QLabel("Стандартный")
        self.lbl_font_name.setStyleSheet("color: #888; border: 1px solid #444; padding: 4px; border-radius: 4px;")
        btn_font = QPushButton("📂")
        btn_font.setFixedWidth(30)
        btn_font.clicked.connect(self.select_custom_font)
        h_font.addWidget(self.lbl_font_name);
        h_font.addWidget(btn_font)
        ls.addLayout(h_font, 0, 1)

        b_txt = QPushButton("Цвет Текста");
        b_txt.clicked.connect(lambda: self.pick_color('t'));
        ls.addWidget(b_txt, 1, 0)
        b_str = QPushButton("Цвет Контура");
        b_str.clicked.connect(lambda: self.pick_color('s'));
        ls.addWidget(b_str, 1, 1)

        ls.addWidget(QLabel("Обводка:"), 2, 0)
        self.sl_stroke = QSlider(Qt.Orientation.Horizontal);
        self.sl_stroke.setRange(0, 15);
        self.sl_stroke.setValue(5);
        self.sl_stroke.valueChanged.connect(self.update_preview);
        ls.addWidget(self.sl_stroke, 2, 1)

        ls.addWidget(QLabel("Размер:"), 3, 0)
        self.sb_font_size = QSpinBox();
        self.sb_font_size.setRange(40, 300);
        self.sb_font_size.setValue(110);
        self.sb_font_size.valueChanged.connect(self.update_preview);
        ls.addWidget(self.sb_font_size, 3, 1)

        self.chk_caps = QCheckBox("CAPS LOCK");
        self.chk_caps.setChecked(True);
        self.chk_caps.toggled.connect(self.update_preview);
        ls.addWidget(self.chk_caps, 4, 0)
        left_col.addWidget(grp_style)

        grp_zone = QGroupBox("Позиция")
        lz = QVBoxLayout(grp_zone)
        lz.addWidget(QLabel("Верх / Низ:"))
        self.sl_top = QSlider(Qt.Orientation.Horizontal);
        self.sl_top.setRange(0, 800);
        self.sl_top.setValue(150);
        self.sl_top.valueChanged.connect(self.update_preview);
        lz.addWidget(self.sl_top)
        self.sl_bot = QSlider(Qt.Orientation.Horizontal);
        self.sl_bot.setRange(200, 1800);
        self.sl_bot.setValue(600);
        self.sl_bot.valueChanged.connect(self.update_preview);
        lz.addWidget(self.sl_bot)
        left_col.addWidget(grp_zone)
        left_col.addStretch()
        l.addLayout(left_col, 3)

        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_p = QLabel("ПРЕДПРОСМОТР");
        lbl_p.setAlignment(Qt.AlignmentFlag.AlignCenter);
        right_col.addWidget(lbl_p)
        self.lbl_preview = QLabel("Нет видео");
        self.lbl_preview.setFixedSize(270, 480);
        self.lbl_preview.setStyleSheet("background: #000; border: 2px solid #555;");
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter);
        right_col.addWidget(self.lbl_preview)
        btn_upd = QPushButton("🔄 Обновить");
        btn_upd.clicked.connect(self.update_preview);
        right_col.addWidget(btn_upd)
        l.addLayout(right_col, 2)
        self.update_preview()

    # --- ЛОГИКА ---
    def parse_timestamp(self, ts_str):
        try:
            parts = re.split(r'[:\.]', ts_str.strip())
            if len(parts) >= 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except:
            pass
        return 0

    def import_manual_txt(self):
        f, _ = QFileDialog.getOpenFileName(self, "Выбрать TXT", "", "Text (*.txt)")
        if not f: return
        try:
            segments = []
            with open(f, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            pattern = re.compile(
                r'(\d+[:\.]\d+[:\.]\d+(?:[:\.]\d+)?)\s*[-–]\s*(\d+[:\.]\d+[:\.]\d+(?:[:\.]\d+)?)\s*\|\s*(.*)')
            for line in lines:
                match = pattern.search(line)
                if match:
                    s = self.parse_timestamp(match.group(1));
                    e = self.parse_timestamp(match.group(2));
                    t = match.group(3).strip()
                    if e > s: segments.append({'start': s, 'end': e, 'title': t})

            if not segments: QMessageBox.warning(self, "Ошибка",
                                                 "Не найдены таймкоды.\nФормат: 00:00:00 - 00:00:10 | Заголовок"); return

            json_path = os.path.join(self.out_path, "analysis_result.json")
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(segments, jf, ensure_ascii=False, indent=4)
            self.log_box.append(f"✅ Импорт: {len(segments)} сегментов.")
            self.btn_slice.setEnabled(True)
            self.tabs.setCurrentIndex(1)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def pick_color(self, t):
        c = QColorDialog.getColor()
        if c.isValid():
            if t == 't':
                self.text_color = c.name()
            else:
                self.stroke_color = c.name()
            self.update_preview()

    def select_custom_font(self):
        f, _ = QFileDialog.getOpenFileName(self, "Шрифт", "", "Fonts (*.ttf *.otf)")
        if f:
            self.custom_font_path = f
            self.lbl_font_name.setText(os.path.basename(f))
            self.update_preview()

    def update_preview(self):
        try:
            w, h = 270, 480
            scale = w / 1080
            bg_path = None
            if self.video_path and os.path.exists(self.video_path):
                if not os.path.exists(self.preview_frame_path):
                    subprocess.run(["ffmpeg", "-y", "-ss", "15", "-i", self.video_path, "-vf",
                                    f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", "-vframes", "1",
                                    "-f", "image2", self.preview_frame_path], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                bg_path = self.preview_frame_path

            tg = TextGenerator(width=w, height=h)
            txt = "ЗАГОЛОВОК ВИДЕО"
            if self.chk_caps.isChecked(): txt = txt.upper()
            if self.chk_no_text_render.isChecked(): txt = ""

            tg.create_header_image(
                txt, "preview_txt.png",
                font_source=self.custom_font_path,
                max_font_size=int(self.sb_font_size.value() * scale),
                text_color=self.text_color,
                stroke_color=self.stroke_color,
                stroke_width_pct=self.sl_stroke.value(),
                y_top_limit=int(self.sl_top.value() * scale),
                y_bottom_limit=int(self.sl_bot.value() * scale)
            )

            from PyQt6.QtGui import QPainter
            final_pix = QPixmap(w, h);
            final_pix.fill(Qt.GlobalColor.black)
            painter = QPainter(final_pix)
            if bg_path and os.path.exists(bg_path): painter.drawPixmap(0, 0, QPixmap(bg_path))
            if os.path.exists("preview_txt.png"): painter.drawPixmap(0, 0, QPixmap("preview_txt.png"))
            painter.end()
            self.lbl_preview.setPixmap(final_pix)
        except Exception as e:
            self.lbl_preview.setText(f"Wait...")

    def open_settings(self):
        ApiKeyDialog(self).exec()

    def open_output_folder(self):
        if os.path.exists(self.out_path): os.startfile(self.out_path)

    def select_video(self):
        f, _ = QFileDialog.getOpenFileName(self, "", "", "*.mp4 *.mov")
        if f:
            self.video_path = f;
            self.txt_vid.setText(os.path.basename(f))
            self.analyze_video_info(f)
            if os.path.exists(self.preview_frame_path): os.remove(self.preview_frame_path)
            self.update_preview()

    def select_output(self):
        d = QFileDialog.getExistingDirectory(self);
        if d: self.out_path = d; self.txt_out.setText(d)

    def analyze_video_info(self, path):
        try:
            si = subprocess.STARTUPINFO();
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                  "default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True,
                                 startupinfo=si)
            mins = int(float(res.stdout.strip()) // 60)
            self.lbl_video_info.setText(f"✅ {mins} мин. | Готово")
        except:
            self.lbl_video_info.setText("⚠️ Загружено")

    def get_settings(self):
        key = self.app_settings.value("gemini_key", "")
        presets = [(60, 120, 90), (60, 90, 75), (90, 180, 150), (180, 300, 240), (300, 480, 400)]
        d = presets[self.combo_preset.currentIndex()]
        lang_map = {"Auto": None, "Russian": "ru", "English": "en", "Ukrainian": "uk", "Spanish": "es"}
        w_lang = lang_map.get(self.combo_lang.currentText())

        return {
            'video': self.video_path, 'out': self.out_path, 'gemini_key': key,
            'use_whisper': self.chk_whisper.isChecked(),
            'whisper_model': self.combo_model.currentText(),
            'whisper_lang': w_lang,
            'force_whisper': self.chk_force_whisper.isChecked(),
            'use_gemini': self.chk_gemini.isChecked(),
            'ai_prompt': self.txt_prompt.toPlainText().strip(),
            'no_text_render': self.chk_no_text_render.isChecked(),
            'text_color': self.text_color, 'stroke_color': self.stroke_color,
            'stroke_width_pct': self.sl_stroke.value(),
            'caps': self.chk_caps.isChecked(),
            'font_source': self.custom_font_path,
            'max_font_size': self.sb_font_size.value(),
            'y_top': self.sl_top.value(), 'y_bot': self.sl_bot.value(),
            'min_duration': d[0], 'max_duration': d[1], 'target_duration': d[2],
            'auto_split': self.chk_auto_split.isChecked(),
            'silence_cut': self.grp_silence.isChecked(),
            'silence_db': self.spin_sil_db.value(), 'silence_dur': self.spin_sil_dur.value(),
            'format': self.combo_format.currentText(),
            'blur_bg': self.chk_blur_bg.isChecked(),
            'face_track': self.chk_face_track.isChecked(),
        }

    def lock_interface(self, locked):
        self.btn_analyze.setEnabled(not locked);
        self.btn_slice.setEnabled(not locked);
        self.btn_stop.setEnabled(locked)
        if not locked and os.path.exists(
            os.path.join(self.out_path, "analysis_result.json")): self.btn_slice.setEnabled(True)

    def start_analysis(self):
        if not self.video_path: self.log_box.append("❌ Нет видео!"); return
        s = self.get_settings()
        if s['use_gemini'] and not s['gemini_key']: QMessageBox.warning(self, "Ошибка",
                                                                        "Нужен API ключ Gemini!"); return
        self.log_box.clear();
        self.log_box.append("🚀 Старт анализа...")
        self.lock_interface(True)
        self.worker = AiSlicerWorker(s, mode='analyze')
        self.worker.log_signal.connect(self.log_box.append)
        self.worker.progress_signal.connect(self.prog.setValue)
        self.worker.finished_signal.connect(lambda: [self.lock_interface(False), self.open_output_folder()])
        self.worker.start()

    def start_slicing(self):
        self.log_box.append("✂️ Старт нарезки...");
        self.lock_interface(True)
        self.worker = AiSlicerWorker(self.get_settings(), mode='slice')
        self.worker.log_signal.connect(self.log_box.append);
        self.worker.progress_signal.connect(self.prog.setValue)
        self.worker.finished_signal.connect(self.on_slice_done)
        self.worker.start()

    def stop_process(self):
        if self.worker: self.log_box.append("⛔ Стоп..."); self.worker.stop()

    def on_slice_done(self):
        self.lock_interface(False);
        self.log_box.append("🏁 Готово.");
        self.open_output_folder()