import os
import subprocess
import random
import re
from PyQt6.QtCore import QThread, pyqtSignal
from utils.generators import generate_unique_filename, get_random_device_metadata


class ProcessingWorker(QThread):
    # ... (Сигналы и __init__ без изменений) ...
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, file_list, settings):
        super().__init__()
        self.file_list = file_list
        self.settings = settings
        self.is_running = True
        self.current_process = None

    # ... (stop, check_has_audio, get_quality_params, get_filter, detect_silence - БЕЗ ИЗМЕНЕНИЙ) ...
    def stop(self):
        self.is_running = False
        if self.current_process:
            try:
                self.current_process.kill()
            except:
                pass

    def check_has_audio(self, path):
        try:
            si = subprocess.STARTUPINFO();
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            p = subprocess.Popen(["ffmpeg", "-i", path], stderr=subprocess.PIPE, stdout=subprocess.PIPE, startupinfo=si)
            _, stderr = p.communicate()
            return "Audio:" in stderr.decode('utf-8', errors='ignore')
        except:
            return False

    def get_quality_params(self, codec):
        q_data = self.settings['quality']
        if q_data['is_static']:
            pct = q_data['val']
        else:
            pct = random.randint(q_data['min'], q_data['max'])
        pct = max(1, min(100, pct))
        crf = int(51 - (pct * 0.33))
        if "nvenc" in codec:
            return ["-rc", "vbr", "-cq", str(crf), "-qmin", str(crf), "-qmax", str(crf)]
        else:
            return ["-crf", str(crf)]

    def get_filter(self, name):
        chain = []
        if "Случайный" in name: name = random.choice(
            ["Черно-белое", "Сепия", "Размытие: Легкое", "VHS", "Повышенный контраст"])
        if "Яркость" in name:
            chain.append(f"eq=contrast={random.uniform(0.9, 1.1):.2f}:brightness={random.uniform(-0.05, 0.05):.2f}")
        elif "Черно-белое" in name:
            chain.append("hue=s=0")
        elif "Сепия" in name:
            chain.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        elif "Размытие: Легкое" in name:
            chain.append("boxblur=2:1")
        elif "Размытие: Сильное" in name:
            chain.append("boxblur=10:5")
        elif "VHS" in name:
            chain.append("noise=alls=20:allf=t+u,eq=saturation=1.4,chromashift=cbh=3:crh=-3")
        elif "Повышенный" in name:
            chain.append("eq=contrast=1.3")
        elif "Пониженный" in name:
            chain.append("eq=contrast=0.7")
        elif "Теплый" in name:
            chain.append("eq=gamma_r=1.1:gamma_b=0.9")
        elif "Холодный" in name:
            chain.append("eq=gamma_r=0.9:gamma_b=1.1")

        # Новые эффекты
        s = self.settings
        if s.get('vignette'): chain.append("vignette=PI/4")
        if s.get('rotate'): chain.append(
            f"scale=iw*1.05:-1,rotate={random.uniform(0.5, 1.5) * random.choice([-1, 1])}*PI/180")
        if s.get('fps_change'): chain.append(f"fps={random.choice([24, 25, 30])}")
        return chain

    def detect_silence(self, path, db, dur):
        # ... (Код детекции тишины без изменений) ...
        self.log_signal.emit(f"🔍 Ищу тишину ({db}dB)...")
        try:
            si = subprocess.STARTUPINFO();
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            p = subprocess.Popen(
                ["ffmpeg", "-i", path, "-af", f"silencedetect=noise={db}dB:d={dur}", "-f", "null", "-"],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE, startupinfo=si)
            _, stderr = p.communicate()
            log = stderr.decode('utf-8', errors='ignore')
            dur_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", log)
            if not dur_match: return None
            h, m, s = dur_match.groups();
            duration = float(h) * 3600 + float(m) * 60 + float(s)
            starts = [float(x) for x in re.findall(r"silence_start: ([\d\.]+)", log)]
            ends = [float(x) for x in re.findall(r"silence_end: ([\d\.]+)", log)]
            if not starts: return None
            keep = [];
            curr = 0.0
            for i in range(len(starts)):
                if starts[i] > curr: keep.append((curr, starts[i]))
                curr = ends[i] if i < len(ends) else duration
            if curr < duration: keep.append((curr, duration))
            self.log_signal.emit(f"✂️ Найдено {len(starts)} пауз.")
            return keep
        except:
            return None

    def run(self):
        total = len(self.file_list)
        os.makedirs(self.settings['out_dir'], exist_ok=True)
        for i, path in enumerate(self.file_list):
            if not self.is_running: break
            try:
                self.status_signal.emit(f"Обработка [{i + 1}/{total}]: {os.path.basename(path)}")
                self.process(path)
                self.progress_signal.emit(int(((i + 1) / total) * 100))
                self.log_signal.emit(f"✅ Готово: {os.path.basename(path)}")
            except Exception as e:
                self.log_signal.emit(f"❌ ОШИБКА: {e}")
        self.finished_signal.emit()

    def process(self, f_in):
        s = self.settings
        has_audio = self.check_has_audio(f_in)

        segments = []
        if s['silence_cut'] and has_audio:
            segments = self.detect_silence(f_in, s['silence_db'], s['silence_dur'])
            if segments and len(segments) > 50: segments = segments[:50]

        if not self.is_running: return

        cmd = ["ffmpeg", "-y", "-i", f_in]
        if s['music']: cmd.extend(["-stream_loop", "-1", "-i", s['music']])

        # --- СИСТЕМНАЯ АУДИО УНИКАЛИЗАЦИЯ (ЧАСТЬ 1: GHOST TRACK) ---
        if s.get('sys_ghost'):
            # Генерируем бесконечную тишину как вход №2 (или №1 если нет музыки)
            # anullsrc создает тихий аудио поток
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

        fc = ""
        # TRIM, VIDEO FX, FORMAT - (Код без изменений)
        if segments:
            parts = ""
            for idx, (st, en) in enumerate(segments):
                fc += f"[0:v]trim={st}:{en},setpts=PTS-STARTPTS[v{idx}];[0:a]atrim={st}:{en},asetpts=PTS-STARTPTS[a{idx}];";
                parts += f"[v{idx}][a{idx}]"
            fc += f"{parts}concat=n={len(segments)}:v=1:a=1[v_base][a_base];";
            cv, ca = "[v_base]", "[a_base]"
        else:
            if s['trim']:
                fc += "[0:v]trim=start=0.2,setpts=PTS-STARTPTS[v_base];"; fc += "[0:a]atrim=start=0.2,asetpts=PTS-STARTPTS[a_base];" if has_audio else ""; cv = "[v_base]"; ca = "[a_base]" if has_audio else None
            else:
                cv, ca = "0:v", "0:a" if has_audio else None

        vf = self.get_filter(s['filter'])
        if s['mirror']: vf.append("hflip")
        z = s['zoom'];
        zv = z['val'] if z['is_static'] else random.randint(z['min'], z['max']);
        zf = zv / 100.0
        if zf != 1.0: vf.append(
            f"scale=iw*{zf}:-2,crop=iw:ih" if zf > 1 else f"scale=iw*{zf}:-2,pad=iw:ih:(ow-iw)/2:(oh-ih)/2")
        sp = s['speed'];
        spv = sp['val'] if sp['is_static'] else random.randint(sp['min'], sp['max']);
        spf = spv / 100.0
        if spf != 1.0: vf.append(f"setpts={1 / spf}*PTS")
        if vf: src = cv if "[" in cv else f"[{cv}]"; fc += f"{src}{','.join(vf)}[v_fx];"; cv = "[v_fx]"

        if s['fmt'] == 'reels':
            src = cv if "[" in cv else f"[{cv}]";
            w, h = 1080, 1920
            if s['blur']:
                fc += f"{src}split=2[bg][fg];[bg]scale=iw/4:-1,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=10:5[b];[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[f];[b][f]overlay=(W-w)/2:(H-h)/2[v_out];"
            else:
                fc += f"{src}scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[v_out];"
            cv = "[v_out]"

        # AUDIO FX
        af = []
        if spf != 1.0:
            tmp = spf
            while tmp > 2.0: af.append("atempo=2.0"); tmp /= 2.0
            while tmp < 0.5: af.append("atempo=0.5"); tmp /= 0.5
            if abs(tmp - 1.0) > 0.01: af.append(f"atempo={tmp}")
        if s.get('echo') and ca: af.append("aecho=0.8:0.9:60:0.3")
        if s.get('pitch') and ca: pf = random.uniform(0.95, 1.05); af.append(f"asetrate=44100*{pf},atempo={1 / pf}")

        if ca:
            src_a = ca if "[" in ca else f"[{ca}]";
            vol0 = 0 if s['mute'] else s['vol_orig']
            if af:
                fc += f"{src_a}{','.join(af)},volume={vol0}[a_proc];"
            else:
                fc += f"{src_a}volume={vol0}[a_proc];"
            ca = "[a_proc]"

        if s['music']:
            if ca:
                fc += f"[1:a]volume={s['vol_mus']}[a_mus];[{ca}][a_mus]amix=inputs=2:duration=first[a_fin];"; ca = "[a_fin]"
            else:
                fc += f"[1:a]volume={s['vol_mus']}[a_fin];"; ca = "[a_fin]"

        if s['eq'] and ca:
            eq_src = ca if "[" in ca else f"[{ca}]";
            g1 = random.uniform(-5, 5);
            g2 = random.uniform(-5, 5)
            fc += f"{eq_src}lowshelf=g={g1}:f=100,highshelf=g={g2}:f=10000[a_eq];";
            ca = "[a_eq]"

        # ФИНАЛЬНЫЙ СБОР
        fv = cv if "[" in cv else "[0:v]"
        cmd.extend(["-filter_complex", fc, "-map", fv])
        if ca:
            fa = ca if "[" in ca else f"[{ca}]"
            cmd.extend(["-map", fa])

        # --- СИСТЕМНАЯ АУДИО УНИКАЛИЗАЦИЯ (ЧАСТЬ 2: ПАРАМЕТРЫ) ---
        # Ghost Track
        if s.get('sys_ghost'):
            # Мапим последний добавленный вход (anullsrc) как вторую аудиодорожку
            ghost_idx = 2 if s['music'] else 1
            cmd.extend(["-map", f"{ghost_idx}:a"])

        # Sample Rate (AR)
        if s.get('sys_ar'):
            new_ar = random.choice([44100, 48000])
            cmd.extend(["-ar", str(new_ar)])

        # Bitrate (AB)
        if s.get('sys_br'):
            new_br = random.randint(120, 140)
            cmd.extend(["-b:a", f"{new_br}k"])

        # Meta & Codec
        if s['meta']: dev = get_random_device_metadata(); cmd.extend(["-metadata", f"model={dev['model']}"])
        cmd.extend(["-c:v", s['codec'], "-preset", "fast" if "nvenc" in s['codec'] else "ultrafast"])
        cmd.extend(self.get_quality_params(s['codec']))
        name = generate_unique_filename(os.path.basename(f_in), "date_random") if s['rename'] else os.path.basename(
            f_in)
        cmd.extend(["-c:a", "aac", os.path.join(s['out_dir'], name)])

        si = subprocess.STARTUPINFO();
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=si)
        _, stderr = self.current_process.communicate()

        if self.current_process.returncode != 0 and self.is_running: raise Exception(
            f"FFmpeg Error: {stderr.decode('utf-8', errors='ignore')}")


# PreviewWorker без изменений
class PreviewWorker(ProcessingWorker):
    result_signal = pyqtSignal(str);
    error_signal = pyqtSignal(str)

    def __init__(self, path, settings):
        super().__init__([], settings); self.path = path

    def run(self):
        try:
            out = os.path.abspath("temp_preview.jpg");
            s = self.settings;
            vf = self.get_filter(s['filter'])
            fc = "";
            current_v = "[0:v]"
            if vf: fc += f"{current_v}{','.join(vf)}[v_fx];"; current_v = "[v_fx]"
            if s['fmt'] == 'reels':
                w, h = 1080, 1920;
                src = current_v if "[" in current_v else f"[{current_v}]"
                if s['blur']:
                    fc += f"{src}split=2[bg][fg];[bg]scale=iw/4:-1,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=10:5[b];[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[f];[b][f]overlay=(W-w)/2:(H-h)/2[v_out];"
                else:
                    fc += f"{src}scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[v_out];"
                current_v = "[v_out]"
            cmd = ["ffmpeg", "-y", "-ss", "2", "-i", self.path]
            if fc: final_map = current_v if "[" in current_v else f"[{current_v}]"; cmd.extend(
                ["-filter_complex", fc, "-map", final_map])
            cmd.extend(["-frames:v", "1", "-q:v", "2", "-update", "1", out])
            si = subprocess.STARTUPINFO();
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, startupinfo=si, check=True)
            self.result_signal.emit(out)
        except Exception as e:
            self.error_signal.emit(str(e))