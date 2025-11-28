import os
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLabel,
    QScrollArea, QCheckBox, QGroupBox, QProgressBar, QFileDialog, QTextEdit,
    QFrame, QComboBox, QLineEdit, QSlider, QTabWidget, QRadioButton,
    QSpinBox, QButtonGroup, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from ..core.ffmpeg_worker import ProcessingWorker, PreviewWorker


# --- ВИДЖЕТ ДИАПАЗОНА ---
class RangeWidget(QGroupBox):
    def __init__(self, title, suffix="%"):
        super().__init__()
        self.setTitle(title)
        self.setProperty("class", "Card")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Ряд 1: Переключатель
        row1 = QHBoxLayout()
        self.rb_static = QRadioButton("Статическое")
        self.rb_range = QRadioButton("Диапазон (Рандом)")
        self.rb_static.setChecked(True)

        self.group = QButtonGroup(self)
        self.group.addButton(self.rb_static)
        self.group.addButton(self.rb_range)

        row1.addWidget(self.rb_static)
        row1.addWidget(self.rb_range)
        row1.addStretch()
        layout.addLayout(row1)

        # Ряд 2: Значения
        row2 = QHBoxLayout()

        # Статик
        self.w_static = QWidget()
        ls = QHBoxLayout(self.w_static)
        ls.setContentsMargins(0, 0, 0, 0)
        self.spin_static = QSpinBox()
        self.spin_static.setRange(1, 400)
        self.spin_static.setSuffix(suffix)
        self.spin_static.setFixedWidth(100)
        ls.addWidget(self.spin_static)
        ls.addStretch()

        # Рандом
        self.w_range = QWidget()
        lr = QHBoxLayout(self.w_range)
        lr.setContentsMargins(0, 0, 0, 0)
        self.spin_min = QSpinBox()
        self.spin_min.setRange(1, 400)
        self.spin_min.setSuffix(suffix)
        self.spin_min.setPrefix("Мин: ")
        self.spin_min.setFixedWidth(100)

        self.spin_max = QSpinBox()
        self.spin_max.setRange(1, 400)
        self.spin_max.setSuffix(suffix)
        self.spin_max.setPrefix("Макс: ")
        self.spin_max.setFixedWidth(100)

        lr.addWidget(self.spin_min)
        lr.addSpacing(10)
        lr.addWidget(self.spin_max)
        lr.addStretch()

        row2.addWidget(self.w_static)
        row2.addWidget(self.w_range)
        layout.addLayout(row2)

        self.rb_static.toggled.connect(self.update_view)
        self.update_view()

    def update_view(self):
        is_static = self.rb_static.isChecked()
        self.w_static.setVisible(is_static)
        self.w_range.setVisible(not is_static)

    def get_data(self):
        return {
            'is_static': self.rb_static.isChecked(),
            'val': self.spin_static.value(),
            'min': self.spin_min.value(),
            'max': self.spin_max.value()
        }


# --- ОСНОВНОЙ КЛАСС ВКЛАДКИ ---
class UniqualizerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.files = []
        self.out_dir = os.path.abspath("output")
        self.audio_path = ""
        # Важно: храним ссылки на воркеры, чтобы их не убил сборщик мусора
        self.worker = None
        self.preview_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        content_layout = QHBoxLayout()

        # === 1. ЛЕВАЯ КОЛОНКА (Очередь) ===
        col_left = QFrame()
        col_left.setObjectName("Panel")
        col_left.setFixedWidth(280)
        layout_left = QVBoxLayout(col_left)

        layout_left.addWidget(QLabel("<b>📂 ОЧЕРЕДЬ ФАЙЛОВ</b>"))
        self.list_widget = QListWidget()
        layout_left.addWidget(self.list_widget)

        btn_add = QPushButton("➕ Добавить видео")
        btn_add.clicked.connect(self.add_video)
        btn_folder = QPushButton("📁 Добавить папку")
        btn_folder.clicked.connect(self.add_folder)
        btn_clear = QPushButton("🗑 Очистить список")
        btn_clear.clicked.connect(self.clear_list)

        layout_left.addWidget(btn_add)
        layout_left.addWidget(btn_folder)
        layout_left.addWidget(btn_clear)
        content_layout.addWidget(col_left)

        # === 2. ЦЕНТРАЛЬНАЯ КОЛОНКА (Превью) ===
        col_center = QFrame()
        col_center.setObjectName("Panel")
        layout_center = QVBoxLayout(col_center)

        layout_center.addWidget(QLabel("<b>👁 ПРЕДПРОСМОТР</b>"))

        self.preview_lbl = QLabel("Выберите файл...")
        self.preview_lbl.setObjectName("PreviewBox")
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setMinimumHeight(350)
        layout_center.addWidget(self.preview_lbl)

        # Кнопки
        btns_layout = QHBoxLayout()
        self.btn_preview = QPushButton("🔄 Обновить превью")
        self.btn_preview.setFixedHeight(35)
        self.btn_preview.clicked.connect(self.update_preview)

        self.btn_stop = QPushButton("⛔ ОСТАНОВИТЬ ПРОЦЕСС")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setFixedHeight(35)
        self.btn_stop.clicked.connect(self.kill_process)
        self.btn_stop.setEnabled(False)

        btns_layout.addWidget(self.btn_preview)
        btns_layout.addWidget(self.btn_stop)
        layout_center.addLayout(btns_layout)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(200)
        self.log_box.setPlaceholderText("Лог событий...")
        layout_center.addWidget(QLabel("<b>📝 СИСТЕМНЫЙ ЛОГ</b>"))
        layout_center.addWidget(self.log_box)

        content_layout.addWidget(col_center, 1)

        # === 3. ПРАВАЯ КОЛОНКА (Вкладки) ===
        col_right = QFrame()
        col_right.setObjectName("Panel")
        col_right.setFixedWidth(430)
        layout_right = QVBoxLayout(col_right)

        self.tabs = QTabWidget()
        layout_right.addWidget(self.tabs)

        # --- TAB 1: ОСНОВА ---
        tab_base = QWidget()
        scroll_base = QScrollArea()
        scroll_base.setWidgetResizable(True)
        scroll_base.setFrameShape(QFrame.Shape.NoFrame)
        scroll_base.setWidget(tab_base)

        layout_base = QVBoxLayout(tab_base)
        layout_base.setSpacing(15)

        self.wdg_quality = RangeWidget("💎 Качество / Битрейт")
        self.wdg_quality.spin_static.setValue(85)
        self.wdg_quality.spin_min.setValue(75)
        self.wdg_quality.spin_max.setValue(95)
        self.wdg_quality.rb_range.setChecked(True)
        layout_base.addWidget(self.wdg_quality)

        self.wdg_zoom = RangeWidget("🔍 Zoom")
        self.wdg_zoom.spin_static.setValue(100)
        self.wdg_zoom.spin_max.setValue(120)
        layout_base.addWidget(self.wdg_zoom)

        self.wdg_speed = RangeWidget("⚡ Скорость")
        self.wdg_speed.spin_static.setRange(20, 400)
        self.wdg_speed.spin_min.setRange(20, 400)
        self.wdg_speed.spin_max.setRange(20, 400)
        self.wdg_speed.spin_static.setValue(100)
        self.wdg_speed.spin_min.setValue(95)
        self.wdg_speed.spin_max.setValue(105)
        self.wdg_speed.rb_range.setChecked(True)
        layout_base.addWidget(self.wdg_speed)

        grp_add = QGroupBox("Дополнительно")
        layout_add = QVBoxLayout(grp_add)
        self.chk_mirror = QCheckBox("Mirror (Отражение)")
        self.chk_trim = QCheckBox("Smart Trim (Срезать начало)")
        self.chk_trim.setChecked(True)
        self.chk_meta = QCheckBox("Spoofing (Метаданные)")
        self.chk_meta.setChecked(True)
        self.chk_name = QCheckBox("Rename (Hash)")
        self.chk_name.setChecked(True)

        layout_add.addWidget(self.chk_mirror)
        layout_add.addWidget(self.chk_trim)
        layout_add.addWidget(self.chk_meta)
        layout_add.addWidget(self.chk_name)
        layout_base.addWidget(grp_add)
        layout_base.addStretch()
        self.tabs.addTab(scroll_base, "Основа")

        # --- TAB 2: ЭФФЕКТЫ ---
        tab_fx = QWidget()
        layout_fx = QVBoxLayout(tab_fx)

        grp_filter = QGroupBox("Цвет и Фильтры")
        layout_filter = QVBoxLayout(grp_filter)
        self.combo_fx = QComboBox()
        self.combo_fx.addItems([
            "Нет фильтра", "Случайный", "Черно-белое", "Сепия",
            "Размытие: Легкое", "Размытие: Сильное", "VHS Шум",
            "Повышенный контраст", "Пониженный контраст",
            "Повышенная яркость", "Пониженная яркость",
            "Теплый фильтр", "Холодный фильтр"
        ])
        layout_filter.addWidget(self.combo_fx)
        layout_fx.addWidget(grp_filter)

        grp_hard = QGroupBox("🔥 Хардкорная уникализация")
        layout_hard = QVBoxLayout(grp_hard)
        self.chk_vignette = QCheckBox("Виньетка (Затемнение углов)")
        self.chk_rotate = QCheckBox("Микро-поворот (±1°)")
        self.chk_fps = QCheckBox("Сменить FPS (24/25/30)")
        layout_hard.addWidget(self.chk_vignette)
        layout_hard.addWidget(self.chk_rotate)
        layout_hard.addWidget(self.chk_fps)
        layout_fx.addWidget(grp_hard)

        grp_bg = QGroupBox("Фон (9:16)")
        layout_bg = QVBoxLayout(grp_bg)
        self.chk_blur = QCheckBox("Размытый фон (Blur)")
        self.chk_blur.setChecked(True)
        layout_bg.addWidget(self.chk_blur)
        layout_fx.addWidget(grp_bg)
        layout_fx.addStretch()
        self.tabs.addTab(tab_fx, "Эффекты")

        # --- TAB 3: АУДИО ---
        tab_audio = QWidget()
        scroll_audio = QScrollArea()
        scroll_audio.setWidgetResizable(True)
        scroll_audio.setFrameShape(QFrame.Shape.NoFrame)
        scroll_audio.setWidget(tab_audio)

        layout_audio = QVBoxLayout(tab_audio)
        layout_audio.setSpacing(15)

        # 1. Оригинал
        grp_orig = QGroupBox("Оригинал")
        layout_orig = QVBoxLayout(grp_orig)
        self.chk_mute = QCheckBox("Удалить звук")
        self.chk_mute.toggled.connect(lambda c: [self.sl_orig.setEnabled(not c), self.lb_orig.setEnabled(not c)])
        layout_orig.addWidget(self.chk_mute)

        hbox_orig = QHBoxLayout()
        self.sl_orig = QSlider(Qt.Orientation.Horizontal)
        self.sl_orig.setRange(0, 200)
        self.sl_orig.setValue(100)
        self.lb_orig = QLabel("100%")
        self.sl_orig.valueChanged.connect(lambda v: self.lb_orig.setText(f"{v}%"))
        hbox_orig.addWidget(QLabel("Громкость:"))
        hbox_orig.addWidget(self.sl_orig)
        hbox_orig.addWidget(self.lb_orig)
        layout_orig.addLayout(hbox_orig)
        layout_audio.addWidget(grp_orig)

        # 2. Эффекты Аудио
        grp_afx = QGroupBox("🎹 Аудио эффекты")
        layout_afx = QVBoxLayout(grp_afx)
        self.chk_echo = QCheckBox("Эхо / Реверберация")
        self.chk_pitch = QCheckBox("Сдвиг тона (Pitch ±5%)")
        layout_afx.addWidget(self.chk_echo)
        layout_afx.addWidget(self.chk_pitch)
        layout_audio.addWidget(grp_afx)

        # 3. Музыка
        grp_music = QGroupBox("Наложение музыки")
        layout_music = QVBoxLayout(grp_music)

        h_file = QHBoxLayout()
        self.txt_mus = QLineEdit()
        self.txt_mus.setReadOnly(True)
        self.txt_mus.setPlaceholderText("Файл...")
        btn_mus = QPushButton("...")
        btn_mus.clicked.connect(self.sel_music)
        btn_clear_mus = QPushButton("x")
        btn_clear_mus.clicked.connect(lambda: self.txt_mus.clear())
        h_file.addWidget(self.txt_mus)
        h_file.addWidget(btn_mus)
        h_file.addWidget(btn_clear_mus)
        layout_music.addLayout(h_file)

        h_mus_vol = QHBoxLayout()
        self.sl_mus = QSlider(Qt.Orientation.Horizontal)
        self.sl_mus.setRange(0, 200)
        self.sl_mus.setValue(30)
        self.lb_mus = QLabel("30%")
        self.sl_mus.valueChanged.connect(lambda v: self.lb_mus.setText(f"{v}%"))
        h_mus_vol.addWidget(QLabel("Громкость:"))
        h_mus_vol.addWidget(self.sl_mus)
        h_mus_vol.addWidget(self.lb_mus)
        layout_music.addLayout(h_mus_vol)

        self.chk_eq = QCheckBox("Random EQ")
        self.chk_eq.setChecked(True)
        layout_music.addWidget(self.chk_eq)
        layout_audio.addWidget(grp_music)

        # 4. Тишина
        grp_silence = QGroupBox("✂️ Удаление тишины")
        layout_silence = QVBoxLayout(grp_silence)
        self.chk_silence = QCheckBox("Включить")
        layout_silence.addWidget(self.chk_silence)

        h_sil = QHBoxLayout()
        self.spin_sil_db = QSpinBox()
        self.spin_sil_db.setRange(-60, -10)
        self.spin_sil_db.setValue(-30)
        self.spin_sil_db.setSuffix(" dB")

        self.spin_sil_dur = QDoubleSpinBox()
        self.spin_sil_dur.setRange(0.1, 5.0)
        self.spin_sil_dur.setValue(0.5)
        self.spin_sil_dur.setSuffix(" с")

        h_sil.addWidget(QLabel("Порог:"))
        h_sil.addWidget(self.spin_sil_db)
        h_sil.addWidget(QLabel("Длит:"))
        h_sil.addWidget(self.spin_sil_dur)
        layout_silence.addLayout(h_sil)

        self.chk_silence.toggled.connect(lambda c: [self.spin_sil_db.setEnabled(c), self.spin_sil_dur.setEnabled(c)])
        self.spin_sil_db.setEnabled(False)
        self.spin_sil_dur.setEnabled(False)
        layout_audio.addWidget(grp_silence)

        # 5. Системная
        grp_sys = QGroupBox("🔒 Системная уникализация")
        layout_sys = QVBoxLayout(grp_sys)
        self.chk_ar = QCheckBox("Сменить Sample Rate (44.1kHz ↔ 48kHz)")
        self.chk_ar.setChecked(True)
        self.chk_br = QCheckBox("Рандомный битрейт (120k - 140k)")
        self.chk_br.setChecked(True)
        self.chk_ghost = QCheckBox("Добавить пустой аудио-трек (Ghost Track)")
        layout_sys.addWidget(self.chk_ar)
        layout_sys.addWidget(self.chk_br)
        layout_sys.addWidget(self.chk_ghost)
        layout_audio.addWidget(grp_sys)

        layout_audio.addStretch()
        self.tabs.addTab(scroll_audio, "Аудио")

        # --- TAB 4: ЭКСПОРТ ---
        tab_export = QWidget()
        layout_export = QVBoxLayout(tab_export)

        grp_codec = QGroupBox("Настройки кодировщика")
        layout_codec = QVBoxLayout(grp_codec)

        layout_codec.addWidget(QLabel("Формат:"))
        self.cb_fmt = QComboBox()
        self.cb_fmt.addItems(["Оригинал", "Reels (9:16)"])
        layout_codec.addWidget(self.cb_fmt)

        layout_codec.addWidget(QLabel("Кодек:"))
        self.cb_codec = QComboBox()
        self.cb_codec.addItems([
            "NVIDIA NVENC H.264", "NVIDIA NVENC HEVC",
            "CPU x264", "CPU x265"
        ])
        layout_codec.addWidget(self.cb_codec)
        layout_export.addWidget(grp_codec)

        grp_path = QGroupBox("Папка")
        layout_path = QVBoxLayout(grp_path)
        self.lb_path = QLabel(self.out_dir)
        self.lb_path.setStyleSheet("color: #aaa; border: 1px dashed #555; padding: 5px;")
        btn_path = QPushButton("Изменить...")
        btn_path.clicked.connect(self.sel_path)
        layout_path.addWidget(self.lb_path)
        layout_path.addWidget(btn_path)
        layout_export.addWidget(grp_path)

        layout_export.addStretch()
        self.tabs.addTab(tab_export, "Экспорт")

        content_layout.addWidget(col_right)
        main_layout.addLayout(content_layout)

        # === ФУТЕР ===
        footer = QFrame()
        footer.setObjectName("Panel")
        footer.setFixedHeight(80)
        layout_footer = QVBoxLayout(footer)
        layout_footer.setContentsMargins(20, 10, 20, 10)

        self.lbl_status = QLabel("Готов")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_footer.addWidget(self.lbl_status)

        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.setTextVisible(True)
        self.prog.setFixedHeight(20)
        layout_footer.addWidget(self.prog)

        self.btn_run = QPushButton("ЗАПУСТИТЬ ОБРАБОТКУ 🚀")
        self.btn_run.setObjectName("AccentButton")
        self.btn_run.setFixedHeight(40)
        self.btn_run.clicked.connect(self.run_process)
        layout_footer.addWidget(self.btn_run)

        main_layout.addWidget(footer)

    # --- HANDLERS ---
    def add_video(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Video", "", "*.mp4 *.mov *.avi")
        for f in fs:
            if f not in self.files:
                self.files.append(f)
                self.list_widget.addItem(os.path.basename(f))

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self)
        if d:
            for n in os.listdir(d):
                if n.lower().endswith(('.mp4', '.mov', '.avi')):
                    self.files.append(os.path.join(d, n))
                    self.list_widget.addItem(n)

    def clear_list(self):
        self.files = []
        self.list_widget.clear()

    def sel_music(self):
        f, _ = QFileDialog.getOpenFileName(self, "Music", "", "*.mp3")
        if f:
            self.audio_path = f
            self.txt_mus.setText(os.path.basename(f))

    def sel_path(self):
        d = QFileDialog.getExistingDirectory(self)
        if d:
            self.out_dir = d
            self.lb_path.setText(d)

    def kill_process(self):
        if self.worker and self.worker.isRunning():
            self.log_box.append("⛔ Остановка...")
            self.worker.stop()
            self.btn_run.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.lbl_status.setText("Остановлено")
            self.prog.setValue(0)

    def on_status(self, msg):
        self.lbl_status.setText(msg)

    def get_config(self):
        ct = self.cb_codec.currentText()
        codec = "h264_nvenc" if "H.264" in ct else "hevc_nvenc" if "HEVC" in ct else "libx265" if "x265" in ct else "libx264"
        return {
            'out_dir': self.out_dir, 'zoom': self.wdg_zoom.get_data(), 'speed': self.wdg_speed.get_data(),
            'quality': self.wdg_quality.get_data(),
            'silence_cut': self.chk_silence.isChecked(), 'silence_db': self.spin_sil_db.value(),
            'silence_dur': self.spin_sil_dur.value(),
            'mirror': self.chk_mirror.isChecked(), 'trim': self.chk_trim.isChecked(), 'meta': self.chk_meta.isChecked(),
            'rename': self.chk_name.isChecked(),
            'filter': self.combo_fx.currentText(), 'blur': self.chk_blur.isChecked(), 'mute': self.chk_mute.isChecked(),
            'vol_orig': self.sl_orig.value() / 100.0, 'music': self.audio_path if self.txt_mus.text() else "",
            'vol_mus': self.sl_mus.value() / 100.0,
            'eq': self.chk_eq.isChecked(), 'codec': codec,
            'fmt': 'reels' if 'Reels' in self.cb_fmt.currentText() else 'orig',
            'vignette': self.chk_vignette.isChecked(), 'rotate': self.chk_rotate.isChecked(),
            'fps_change': self.chk_fps.isChecked(),
            'echo': self.chk_echo.isChecked(), 'pitch': self.chk_pitch.isChecked(),
            'sys_ar': self.chk_ar.isChecked(), 'sys_br': self.chk_br.isChecked(),
            'sys_ghost': self.chk_ghost.isChecked()
        }

    def update_preview(self):
        r = self.list_widget.currentRow()
        if r < 0:
            self.log_box.append("⚠️ Выберите файл!")
            return

        self.btn_preview.setEnabled(False)
        self.lbl_status.setText("Генерация превью...")

        self.preview_worker = PreviewWorker(self.files[r], self.get_config())
        self.preview_worker.result_signal.connect(self.show_img)
        self.preview_worker.error_signal.connect(self.on_preview_error)
        self.preview_worker.start()

    def show_img(self, p):
        self.btn_preview.setEnabled(True)
        self.lbl_status.setText("Превью готово")
        self.preview_lbl.setPixmap(QPixmap(p).scaled(self.preview_lbl.size(), Qt.AspectRatioMode.KeepAspectRatio))
        self.log_box.append("✅ Превью обновлено")

    def on_preview_error(self, err):
        self.btn_preview.setEnabled(True)
        self.log_box.append(f"ERR: {err}")

    def run_process(self):
        if not self.files:
            self.log_box.append("⚠️ Пусто!")
            return
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.prog.setValue(0)
        self.log_box.clear()
        self.lbl_status.setText("Старт...")

        self.worker = ProcessingWorker(self.files, self.get_config())
        self.worker.log_signal.connect(self.log_box.append)
        self.worker.progress_signal.connect(self.prog.setValue)
        self.worker.status_signal.connect(self.on_status)
        self.worker.finished_signal.connect(self.done)
        self.worker.start()

    def done(self):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("Готово!")
        self.log_box.append("🎉 Завершено!")
        if os.name == 'nt':
            os.startfile(self.out_dir)