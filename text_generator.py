from PIL import Image, ImageDraw, ImageFont
import os
import textwrap


class TextGenerator:
    def __init__(self, width=1080, height=1920):
        self.width = width
        self.height = height

    def load_dynamic_font(self, font_path_or_name, size):
        """Надежная загрузка шрифта с фолбэком"""
        # 1. Прямой путь к файлу
        if font_path_or_name and os.path.exists(font_path_or_name):
            try:
                return ImageFont.truetype(font_path_or_name, size)
            except:
                pass

        # 2. Системный шрифт Windows
        try:
            return ImageFont.truetype("arialbd.ttf", size)
        except:
            pass

        # 3. Дефолтный
        return ImageFont.load_default()

    def fit_text_to_box(self, draw, text, max_width, max_height, font_source, max_font_size):
        """Рекурсивный подбор размера шрифта под коробку"""
        size = max_font_size
        min_size = 20

        # Инициализация
        font = self.load_dynamic_font(font_source, size)
        final_lines = textwrap.wrap(text, width=20)

        while size >= min_size:
            font = self.load_dynamic_font(font_source, size)
            try:
                test_len = draw.textlength("A", font=font)
                avg_char_width = test_len if test_len > 0 else size * 0.5
            except:
                avg_char_width = size * 0.5

            chars_per_line = max(5, int(max_width / avg_char_width))
            wrapper = textwrap.TextWrapper(width=chars_per_line, break_long_words=False)
            lines = wrapper.wrap(text)

            total_h = 0
            valid = True

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                # Высота строки + 20% межстрочный интервал
                total_h += h + (size * 0.2)

                if w > max_width:
                    valid = False
                    break

            if valid and total_h <= max_height:
                return font, lines

            size -= 5  # Уменьшаем размер

        return font, final_lines

    def create_header_image(self, text, output_path,
                            font_source="arialbd.ttf",
                            max_font_size=120,
                            text_color="#FFD700",
                            stroke_color="#000000",
                            stroke_width_pct=5,
                            y_top_limit=150,
                            y_bottom_limit=600):

        # Прозрачный холст
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        box_width = self.width * 0.9
        box_height = y_bottom_limit - y_top_limit

        font, lines = self.fit_text_to_box(draw, text, box_width, box_height, font_source, max_font_size)

        current_y = y_top_limit + 10

        try:
            real_size = font.size
        except:
            real_size = 20

        stroke_w = max(2, int(real_size * (stroke_width_pct / 100.0)))

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]

            x_pos = (self.width - text_w) / 2

            # Рисуем текст с обводкой
            draw.text(
                (x_pos, current_y),
                line,
                font=font,
                fill=text_color,
                stroke_width=stroke_w,
                stroke_fill=stroke_color
            )
            current_y += line_h + (real_size * 0.2)

        img.save(output_path, "PNG")
        return output_path