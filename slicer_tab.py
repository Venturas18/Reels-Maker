import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTextEdit, QProgressBar,
    QGroupBox, QCheckBox, QColorDialog, QFrame, QSpinBox, QSlider
)
from PyQt6.QtCore import Qt
from core.slicer_worker import SlicerWorker


class SlicerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.video_path = ""
        self.txt_path = ""
        self.out_path = os.path.abspath("output_slices")
        self.font_path = ""
        self.worker = None
        self.header_color = "#FFD700"  # Желтый

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. Исходные данные
        grp_in = QGroupBox("1. Исходные данные")
        l_in = QVBoxLayout(grp_in)

        h_vid = QHBoxLayout()
        self.txt_vid = QLineEdit();
        self.txt_vid.setPlaceholderText("Видеофайл...");
        self.txt_vid.setReadOnly(True)
        btn_vid = QPushButton("📂 Видео");
        btn_vid.clicked.connect(self.sel_video)
        h_vid.addWidget(self.txt_vid);
        h_vid.addWidget(btn_vid)

        h_txt = QHBoxLayout()
        self.txt_file = QLineEdit();
        self.txt_file.setPlaceholderText("Таймкоды (.txt)...");
        self.txt_file.setReadOnly(True)
        btn_txt = QPushButton("📄 TXT");
        btn_txt.clicked.connect(self.sel_txt)
        h_txt.addWidget(self.txt_file);
        h_txt.addWidget(btn_txt)

        l_in.addLayout(h_vid);
        l_in.addLayout(h_txt)
        layout.addWidget(grp_in)

        # 2. Стиль Заголовка
        grp_head = QGroupBox("2. Дизайн Заголовка")
        l_head = QVBoxLayout(grp_head)

        h_inp = QHBoxLayout()
        h_inp.addWidget(QLabel("Текст:"))
        self.inp_header = QLineEdit()
        self.inp_header.setPlaceholderText("Оставьте пустым, чтобы брать из TXT, или впишите общий")
        self.inp_header.setText("ТЕСТОВЫЙ ЗАГОЛОВОК")
        h_inp.addWidget(self.inp_header)

        self.btn_color = QPushButton("🎨 Цвет")
        self.btn_color.setFixedWidth(60)
        self.btn_color.setStyleSheet(f"background-color: {self.header_color}; color: black; font-weight: bold;")
        self.btn_color.clicked.connect(self.sel_color)
        h_inp.addWidget(self.btn_color)
        l_head.addLayout(h_inp)

        h_font = QHBoxLayout()
        self.btn_font = QPushButton("🔤 Шрифт (Arial Bold)");
        self.btn_font.clicked.connect(self.sel_font)

        self.spin_size = QSpinBox();
        self.spin_size.setRange(20, 200);
        self.spin_size.setValue(75);
        self.spin_size.setSuffix(" px")
        self.chk_caps = QCheckBox("CAPS");
        self.chk_caps.setChecked(True)

        h_font.addWidget(self.btn_font);
        h_font.addWidget(QLabel("Размер:"));
        h_font.addWidget(self.spin_size);
        h_font.addWidget(self.chk_caps)
        l_head.addLayout(h_font)

        # Позиция
        l_head.addWidget(QLabel("Позиция по вертикали (Y) и Высота зоны:"))
        h_pos = QHBoxLayout()
        self.slider_y = QSlider(Qt.Orientation.Horizontal);
        self.slider_y.setRange(0, 500);
        self.slider_y.setValue(100)
        self.lbl_y = QLabel("Y: 100");
        self.lbl_y.setFixedWidth(50)
        self.slider_y.valueChanged.connect(lambda v: self.lbl_y.setText(f"Y: {v}"))

        self.slider_h = QSlider(Qt.Orientation.Horizontal);
        self.slider_h.setRange(50, 600);
        self.slider_h.setValue(200)
        self.lbl_h = QLabel("H: 200");
        self.lbl_h.setFixedWidth(50)
        self.slider_h.valueChanged.connect(lambda v: self.lbl_h.setText(f"H: {v}"))

        h_pos.addWidget(self.slider_y)
        h_pos.addWidget(self.lbl_y);
        h_pos.addWidget(self.slider_h);
        h_pos.addWidget(self.lbl_h)
        l_head.addLayout(h_pos)

        layout.addWidget(grp_head)

        # 3. Сохранение
        grp_out = QGroupBox("3. Сохранение")
        l_out = QHBoxLayout(grp_out)
        self.txt_out = QLineEdit(self.out_path);
        self.txt_out.setReadOnly(True)
        btn_out = QPushButton("📂 Папка");
        btn_out.clicked.connect(self.sel_out)
        l_out.addWidget(self.txt_out);
        l_out.addWidget(btn_out)
        layout.addWidget(grp_out)

        # 4. Управление
        layout.addStretch()

        # Кнопка превью
        self.btn_prev = QPushButton("👁 Тест Превью (Создать кадр)")
        self.btn_prev.clicked.connect(self.test_preview)
        layout.addWidget(self.btn_prev)

        self.log_box = QTextEdit();
        self.log_box.setReadOnly(True);
        self.log_box.setMaximumHeight(100)
        layout.addWidget(self.log_box)

        self.prog = QProgressBar();
        self.prog.setValue(0)
        self.prog.setFixedHeight(10);
        self.prog.setTextVisible(False)
        layout.addWidget(self.prog)

        self.btn_run = QPushButton("✂️ НАРЕЗАТЬ ВСЁ")
        self.btn_run.setObjectName("AccentButton");
        self.btn_run.setMinimumHeight(50)
        self.btn_run.clicked.connect(self.start)
        layout.addWidget(self.btn_run)

    # --- LOGIC ---
    def sel_video(self):
        f, _ = QFileDialog.getOpenFileName(self, "Видео", "", "*.mp4 *.mov *.mkv");
        if f: self.video_path = f; self.txt_vid.setText(os.path.basename(f))

    def sel_txt(self):
        f, _ = QFileDialog.getOpenFileName(self, "TXT", "", "*.txt");
        if f: self.txt_path = f; self.txt_file.setText(os.path.basename(f))

    def sel_out(self):
        d = QFileDialog.getExistingDirectory(self);
        if d: self.out_path = d; self.txt_out.setText(d)

    def sel_font(self):
        f, _ = QFileDialog.getOpenFileName(self, "Font", "", "*.ttf *.otf");
        if f: self.font_path = f; self.btn_font.setText(os.path.basename(f))

    def sel_color(self):
        c = QColorDialog.getColor()
        if c.isValid(): self.header_color = c.name(); self.btn_color.setStyleSheet(f"background-color: {c.name()};")

    def get_settings(self):
        return {
            'video': self.video_path, 'txt': self.txt_path, 'out': self.out_path,
            'font': self.font_path, 'color': self.header_color,
            'size': self.spin_size.value(), 'caps': self.chk_caps.isChecked(),
            'y': self.slider_y.value(), 'h': self.slider_h.value(),
            'static_text': self.inp_header.text()
        }

    def test_preview(self):
        if not self.video_path: self.log_box.append("❌ Выберите видео!"); return
        self.btn_prev.setEnabled(False)
        self.log_box.append("📸 Создаю превью...")
        self.worker = SlicerWorker(self.get_settings(), preview=True)
        self.worker.log_signal.connect(self.log_box.append)
        self.worker.finished_signal.connect(lambda: self.btn_prev.setEnabled(True))
        self.worker.start()

    def start(self):
        if not self.video_path or not self.txt_path: self.log_box.append("❌ Нет файлов!"); return
        self.btn_run.setEnabled(False);
        self.log_box.clear();
        self.log_box.append("🚀 Старт...")
        self.worker = SlicerWorker(self.get_settings(), preview=False)
        self.worker.log_signal.connect(self.log_box.append);
        self.worker.progress_signal.connect(self.prog.setValue)
        self.worker.finished_signal.connect(lambda: [self.btn_run.setEnabled(True), self.log_box.append("✅ Готово!"),
                                                     os.startfile(self.out_path) if os.name == 'nt' else None])
        self.worker.start()