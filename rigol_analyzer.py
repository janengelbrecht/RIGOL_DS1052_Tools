"""
rigol_analyzer.py
=================
Rigol DS1052E Oscilloscope Data Analyzer
PySide6 Desktop Application — CSV import only.
"""

# ── Standardbiblioteker ──────────────────────────────────────────────────────
import sys
import os
import struct
import numpy as np
from pathlib import Path

# ── PySide6 GUI-widgets ──────────────────────────────────────────────────────
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QFrame, QGridLayout, QPushButton, QSlider,
    QGroupBox, QSizePolicy, QStatusBar, QMessageBox,
)
from PySide6.QtCore import (
    Qt, QTimer, QRectF, QSize,
)
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QPainterPath, QAction, QKeySequence,
)


# ── DARK THEME STYLESHEET ────────────────────────────────────────────────────
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #0d1117;
}
QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 20px;
    border: 1px solid #30363d;
    border-bottom: none;
    min-width: 140px;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #58a6ff;
    border-top: 2px solid #58a6ff;
}
QTabBar::tab:hover {
    background-color: #1c2128;
    color: #c9d1d9;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 4px;
    margin-top: 16px;
    padding: 8px;
    font-size: 11px;
    color: #8b949e;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    color: #c9d1d9;
    padding: 6px 14px;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #58a6ff;
    color: #58a6ff;
}
QPushButton:pressed {
    background-color: #388bfd26;
}
QLabel { color: #c9d1d9; }
QSlider::groove:horizontal {
    background: #21262d;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #58a6ff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #388bfd; border-radius: 2px; }
QStatusBar {
    background-color: #161b22;
    border-top: 1px solid #30363d;
    color: #8b949e;
    font-size: 11px;
}
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #30363d; }
"""


# ── DATA PARSING ─────────────────────────────────────────────────────────────
class OscilloscopeData:
    """Container for oscilloscope channel data"""

    def __init__(self):
        self.ch1_voltage: np.ndarray | None = None
        self.ch2_voltage: np.ndarray | None = None
        self.time: np.ndarray | None = None
        self.sample_rate: float = 1e6
        self.dt: float = 1e-6
        self.ch1_scale: float = 1.0
        self.ch2_scale: float = 1.0
        self.ch1_offset: float = 0.0
        self.ch2_offset: float = 0.0
        self.time_scale: float = 1e-3
        self.filename: str = ""
        self.ch1_active: bool = False
        self.ch2_active: bool = False

    def load_csv(self, path: str) -> bool:
        """Parse Rigol CSV export.
        Understøtter:
          2-kol:  Time, CH1
          3-kol:  Time, CH1, CH2
          4-kol:  Time_CH1, V_CH1, Time_CH2, V_CH2
        Returnerer True ved succes.
        """
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()

            # Find første datalinje (starter med tal eller minus)
            data_start = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    continue
                # Fjern eventuelle citattegn
                cleaned = stripped.replace('"', '')
                parts = [p.strip() for p in cleaned.split(',') if p.strip()]
                if not parts:
                    continue
                try:
                    float(parts[0])
                    data_start = i
                    break
                except ValueError:
                    continue

            # Saml data fra alle linjer
            times, ch1s, ch2s = [], [], []
            
            for line in lines[data_start:]:
                line = line.strip()
                if not line:
                    continue
                # Fjern citattegn
                cleaned = line.replace('"', '')
                parts = [p.strip() for p in cleaned.split(',')]
                # Filtrer tomme parts (pga. efterfølgende kommaer)
                parts = [p for p in parts if p]
                
                if not parts:
                    continue
                    
                try:
                    vals = [float(p) for p in parts]
                except ValueError:
                    continue

                n = len(vals)
                
                # 2 kolonner: Time, CH1
                if n == 2:
                    times.append(vals[0])
                    ch1s.append(vals[1])
                # 3 kolonner: Time, CH1, CH2  
                elif n == 3:
                    times.append(vals[0])
                    ch1s.append(vals[1])
                    ch2s.append(vals[2])
                # 4 kolonner: Time_CH1, V_CH1, Time_CH2, V_CH2
                elif n == 4:
                    times.append(vals[0])  # brug CH1 tid som reference
                    ch1s.append(vals[1])
                    ch2s.append(vals[3])
                # Flere kolonner - prøv at gætte
                elif n >= 5:
                    times.append(vals[0])
                    ch1s.append(vals[1])
                    if len(vals) >= 4:
                        ch2s.append(vals[3])

            if not times:
                return False

            # Konverter til numpy arrays
            self.time = np.array(times, dtype=np.float64)
            if len(self.time) > 1:
                self.dt = float(np.mean(np.diff(self.time)))
                self.sample_rate = 1.0 / self.dt if self.dt > 0 else 1e6

            if ch1s:
                self.ch1_voltage = np.array(ch1s, dtype=np.float64)
                self.ch1_active = True

            if ch2s and len(ch2s) == len(times):
                self.ch2_voltage = np.array(ch2s, dtype=np.float64)
                self.ch2_active = True
            elif ch2s and len(ch2s) != len(times):
                # Hvis CH2 har færre punkter, pad med NaN
                if len(ch2s) < len(times):
                    padded = np.full(len(times), np.nan)
                    padded[:len(ch2s)] = ch2s
                    self.ch2_voltage = padded
                    self.ch2_active = True

            self.filename = os.path.basename(path)
            return True

        except Exception as e:
            print(f"CSV load error: {e}")
            return False

    def load_wfm(self, path: str) -> bool:
        """Parse Rigol DS1052E .wfm binary format (beholdt til fremtidig brug)."""
        try:
            with open(path, 'rb') as f:
                data = f.read()

            HEADER = 511
            MAGIC = b'RIGLWFM\x00'

            if len(data) < HEADER + 8:
                return False
            if data[:8] != MAGIC:
                return False

            n_pts = struct.unpack_from('<I', data, 0x08)[0]
            dt_comb = struct.unpack_from('<f', data, 0x14)[0]

            if n_pts < 8 or dt_comb <= 0:
                return False

            dt_ch = dt_comb * 2.0

            def _extract_channel(block: bytes) -> np.ndarray:
                b = np.frombuffer(block, dtype=np.int8).astype(np.float64)
                return np.concatenate([[b[0]], b[4::2]])

            off1 = HEADER
            if off1 + n_pts > len(data):
                return False
            raw1 = _extract_channel(data[off1:off1 + n_pts])

            off2 = HEADER + n_pts
            raw2 = None
            if off2 + n_pts <= len(data):
                raw2_cand = _extract_channel(data[off2:off2 + n_pts])
                if raw2_cand.max() - raw2_cand.min() > 4:
                    raw2 = raw2_cand

            self.ch1_voltage = raw1 / 25.0
            self.ch1_active = True

            if raw2 is not None:
                n = len(raw1)
                v2 = raw2 / 25.0
                self.ch2_voltage = (np.pad(v2, (0, n - len(v2))) 
                                    if len(v2) < n else v2[:n])
                self.ch2_active = True

            self.dt = float(dt_ch)
            self.sample_rate = 1.0 / dt_ch
            self.time = np.arange(len(self.ch1_voltage)) * dt_ch
            self.filename = os.path.basename(path)
            return True

        except Exception as e:
            print(f"WFM load error: {e}")
            return False


# ── SIGNAL ANALYSIS ENGINE ───────────────────────────────────────────────────
class SignalAnalyzer:
    """Matematisk signalanalyse med 8-bit ADC-kompensation"""

    def __init__(self, voltage: np.ndarray, dt: float):
        self.raw = voltage.copy()
        self.dt = dt
        self.fs = 1.0 / dt
        self._apply_compensation()

    def _apply_compensation(self):
        """Anvender Savitzky-Golay-udjævning."""
        from scipy.signal import savgol_filter

        n = len(self.raw)
        win = min(11, n if n % 2 == 1 else n - 1)

        if win >= 5:
            try:
                self.signal = savgol_filter(self.raw, window_length=win, polyorder=3)
            except Exception:
                self.signal = self.raw.copy()
        else:
            self.signal = self.raw.copy()

        self.dc_offset = float(np.mean(self.signal))
        self.signal_ac = self.signal - self.dc_offset

    def _zero_crossings(self, signal=None):
        s = signal if signal is not None else self.signal_ac
        vpp = float(np.max(s) - np.min(s))
        hyst = vpp * 0.05 if vpp > 0 else 0.01

        crossings = []
        was_negative = bool(s[0] < -hyst) if len(s) > 0 else False

        for i in range(1, len(s)):
            if was_negative and s[i] > hyst:
                frac = ((hyst - s[i-1]) / (s[i] - s[i-1]) 
                        if s[i] != s[i-1] else 0.0)
                crossings.append((i - 1 + frac) * self.dt)
                was_negative = False
            elif s[i] < -hyst:
                was_negative = True

        return crossings

    def frequency(self) -> float | None:
        zc = self._zero_crossings()
        f_zc = None
        if len(zc) >= 2:
            periods = np.diff(zc)
            T_zc = float(np.median(periods))
            if T_zc > 0:
                f_zc = 1.0 / T_zc

        f_fft = self._frequency_fft(hint=f_zc)
        
        if f_fft is not None and f_zc is not None:
            if abs(f_fft - f_zc) / f_zc < 0.05:
                return f_fft
            else:
                return f_zc
        return f_fft or f_zc

    def _frequency_fft(self, hint: float | None = None) -> float | None:
        n = len(self.signal_ac)
        if n < 4:
            return None

        if hint and hint > 0:
            target_df = hint / 100.0
        else:
            target_df = self.fs / 10000.0

        nfft_min = int(np.ceil(self.fs / target_df))
        nfft = max(n, nfft_min, 8192)
        nfft = 2 ** int(np.ceil(np.log2(nfft)))

        window = np.blackman(n)
        padded = np.zeros(nfft)
        padded[:n] = self.signal_ac * window
        spectrum = np.abs(np.fft.rfft(padded))
        freqs = np.fft.rfftfreq(nfft, d=self.dt)
        df = freqs[1]

        if len(spectrum) < 3:
            return None

        k = int(np.argmax(spectrum[1:])) + 1
        if k < 1 or k >= len(spectrum) - 1:
            return float(freqs[k]) if k < len(freqs) else None

        a = spectrum[k - 1]
        b = spectrum[k]
        c = spectrum[k + 1]
        denom = a - 2.0 * b + c
        p = 0.5 * (a - c) / denom if denom != 0 else 0.0
        p = float(np.clip(p, -0.5, 0.5))

        freq = (k + p) * df
        return float(freq) if freq > 0 else None

    def vp(self) -> float:
        return float(np.max(np.abs(self.signal)))

    def vpp(self) -> float:
        return float(np.max(self.signal) - np.min(self.signal))

    def vrms(self) -> float:
        freq = self.frequency()
        if freq and freq > 0:
            T = 1.0 / freq
            n_periods = int(len(self.signal) * self.dt / T)
            if n_periods >= 1:
                n_samples = int(round(n_periods * T / self.dt))
                n_samples = min(n_samples, len(self.signal))
                return float(np.sqrt(np.mean(self.signal[:n_samples]**2)))
        return float(np.sqrt(np.mean(self.signal**2)))

    def risetime(self) -> float | None:
        vmin = np.min(self.signal)
        vmax = np.max(self.signal)
        v10 = vmin + 0.1 * (vmax - vmin)
        v90 = vmin + 0.9 * (vmax - vmin)
        t10, t90 = None, None

        for i in range(1, len(self.signal)):
            if self.signal[i-1] < v10 <= self.signal[i] and t10 is None:
                frac = (v10 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])
                t10 = (i - 1 + frac) * self.dt
            if t10 is not None and self.signal[i-1] < v90 <= self.signal[i] and t90 is None:
                frac = (v90 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])
                t90 = (i - 1 + frac) * self.dt
                break

        if t10 is not None and t90 is not None:
            return t90 - t10
        return None

    def falltime(self) -> float | None:
        vmin = np.min(self.signal)
        vmax = np.max(self.signal)
        v10 = vmin + 0.1 * (vmax - vmin)
        v90 = vmin + 0.9 * (vmax - vmin)
        t90, t10 = None, None

        for i in range(1, len(self.signal)):
            if self.signal[i-1] > v90 >= self.signal[i] and t90 is None:
                frac = (v90 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])
                t90 = (i - 1 + frac) * self.dt
            if t90 is not None and self.signal[i-1] > v10 >= self.signal[i] and t10 is None:
                frac = (v10 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])
                t10 = (i - 1 + frac) * self.dt
                break

        if t90 is not None and t10 is not None:
            return t10 - t90
        return None

    def dutycycle(self) -> float | None:
        vth = (np.max(self.signal) + np.min(self.signal)) / 2.0
        high_samples = np.sum(self.signal > vth)
        return float(high_samples) / len(self.signal) * 100.0

    def crest_factor(self) -> float:
        rms = self.vrms()
        return self.vp() / rms if rms > 1e-12 else float('inf')

    def form_factor(self) -> float:
        rectified = np.abs(self.signal)
        vavg = float(np.mean(rectified))
        return self.vrms() / vavg if vavg > 1e-12 else float('inf')

    def fft_spectrum(self, n_harmonics: int = 40):
        n = len(self.signal_ac)
        nfft = max(n, 4096)
        nfft = 2 ** int(np.ceil(np.log2(nfft)))
        window = np.blackman(n)
        padded = np.zeros(nfft)
        padded[:n] = self.signal_ac * window
        spectrum = np.fft.rfft(padded)
        freqs = np.fft.rfftfreq(nfft, d=self.dt)
        mag = np.abs(spectrum) * 2.0 / (n * 0.42)
        mag_db = 20 * np.log10(np.maximum(mag, 1e-12))
        return freqs, mag_db

    def harmonics(self, n_harmonics: int = 40):
        freq = self.frequency()
        if freq is None or freq <= 0:
            return []
        freqs, mag_db = self.fft_spectrum()
        results = []
        for h in range(1, n_harmonics + 1):
            target = freq * h
            if target > self.fs / 2:
                break
            idx = np.argmin(np.abs(freqs - target))
            results.append((freqs[idx], mag_db[idx]))
        return results

    def _spectral_powers(self):
        freq = self.frequency()
        if freq is None or freq <= 0:
            return None

        n = len(self.signal_ac)
        min_nfft = int(np.ceil(8 * self.fs / freq))
        nfft = max(n, min_nfft, 8192)
        nfft = 2 ** int(np.ceil(np.log2(nfft)))

        window = np.blackman(n)
        padded = np.zeros(nfft)
        padded[:n] = self.signal_ac * window
        spectrum = np.abs(np.fft.rfft(padded)) ** 2
        freqs = np.fft.rfftfreq(nfft, d=self.dt)
        df = self.fs / nfft

        harmonic_spacing_bins = freq / df
        half_width = max(1, min(3, int(harmonic_spacing_bins / 2) - 1))

        harmonic_mask = np.zeros(len(spectrum), dtype=bool)
        fund_bin = None

        for h in range(1, 41):
            f_h = freq * h
            if f_h > self.fs / 2 * 0.98:
                break
            centre = int(round(f_h / df))
            lo = max(1, centre - half_width)
            hi = min(len(spectrum) - 1, centre + half_width)
            harmonic_mask[lo:hi + 1] = True
            if h == 1:
                fund_bin = (lo, hi)

        P_fund = float(np.sum(spectrum[fund_bin[0]:fund_bin[1] + 1])) if fund_bin else 0.0
        P_harm = float(np.sum(spectrum[harmonic_mask])) - P_fund
        noise_mask = ~harmonic_mask
        noise_mask[0] = False
        P_noise = float(np.sum(spectrum[noise_mask]))

        return P_fund, P_harm, P_noise, P_fund + P_harm + P_noise

    def thd(self) -> dict | None:
        res = self._spectral_powers()
        if res is None:
            return None
        P_fund, P_harm, P_noise, _ = res
        if P_fund <= 0:
            return None
        thd_ratio = np.sqrt(max(P_harm, 0.0) / P_fund)
        thd_pct = thd_ratio * 100.0
        thd_db = 20.0 * np.log10(thd_ratio) if thd_ratio > 0 else -120.0
        return {'thd_pct': float(thd_pct), 'thd_db': float(thd_db)}

    def snr(self) -> float | None:
        res = self._spectral_powers()
        if res is None:
            return None
        P_fund, P_harm, P_noise, _ = res
        if P_noise <= 0 or P_fund <= 0:
            return None
        return float(10.0 * np.log10(P_fund / P_noise))

    def sinad(self) -> float | None:
        res = self._spectral_powers()
        if res is None:
            return None
        P_fund, P_harm, P_noise, _ = res
        denom = P_harm + P_noise
        if denom <= 0 or P_fund <= 0:
            return None
        return float(10.0 * np.log10(P_fund / denom))

    def enob(self) -> float | None:
        s = self.sinad()
        if s is None:
            return None
        return float((s - 1.76) / 6.02)


def phase_difference(sig1: SignalAnalyzer, sig2: SignalAnalyzer) -> float | None:
    n = min(len(sig1.signal_ac), len(sig2.signal_ac))
    if n < 4:
        return None

    s1 = sig1.signal_ac[:n]
    s2 = sig2.signal_ac[:n]
    s1n = s1 / (np.std(s1) + 1e-12)
    s2n = s2 / (np.std(s2) + 1e-12)

    corr = np.fft.irfft(np.fft.rfft(s1n) * np.conj(np.fft.rfft(s2n)))
    lag = int(np.argmax(np.abs(corr)))
    if lag > n // 2:
        lag -= n

    freq = sig1.frequency()
    if freq is None or freq <= 0:
        return None
    T = 1.0 / freq
    phase_deg = (lag * sig1.dt / T) * 360.0
    phase_deg = ((phase_deg + 180) % 360) - 180
    return float(phase_deg)


# ── TAB 1: MEASUREMENTS ──────────────────────────────────────────────────────
class MeasurementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        self.ch1_group = self._channel_group("CH1", "#f7cc52")
        self.ch2_group = self._channel_group("CH2", "#5af0e0")

        self.rel_group = QGroupBox("SIGNAL RELATIONS")
        self.rel_group.setMaximumWidth(280)
        rel_layout = QVBoxLayout(self.rel_group)
        self.rel_labels = {}

        for key in ["Frequency match", "Phase", "Av (CH2/CH1)", "AvdB"]:
            row = QHBoxLayout()
            name_lbl = QLabel(key)
            name_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet("color: #f0f6fc; font-size: 13px; font-weight: bold;")
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(name_lbl)
            row.addWidget(val_lbl)
            rel_layout.addLayout(row)
            self.rel_labels[key] = val_lbl

        rel_layout.addStretch()

        layout.addWidget(self.ch1_group)
        layout.addWidget(self.ch2_group)
        layout.addWidget(self.rel_group)

    def _channel_group(self, name: str, color: str) -> QGroupBox:
        group = QGroupBox(name)
        group.setStyleSheet(f"""
            QGroupBox {{ border-color: {color}44; }}
            QGroupBox::title {{ color: {color}; }}
        """)

        grid = QGridLayout(group)
        grid.setSpacing(6)

        metrics = [
            ("Vp", "V"), ("Vpp", "V"), ("Vrms", "V"),
            ("Frequency", "Hz"), ("Rise time", "s"), ("Fall time", "s"),
            ("Duty cycle", "%"), ("Crest factor", ""), ("Form factor", ""),
            (None, None),
            ("THD", "%"), ("THD", "dB"), ("SNR", "dB"),
            ("SINAD", "dB"), ("ENOB", "bit"),
        ]

        labels = {}
        row_idx = 0

        for (m, unit) in metrics:
            if m is None:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet("color: #21262d;")
                grid.addWidget(sep, row_idx, 0, 1, 3)
                row_idx += 1
                continue

            key = f"{m} {unit}" if unit else m

            name_lbl = QLabel(m)
            name_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")

            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            unit_lbl = QLabel(unit)
            unit_lbl.setStyleSheet("color: #484f58; font-size: 10px;")

            grid.addWidget(name_lbl, row_idx, 0)
            grid.addWidget(val_lbl, row_idx, 1)
            grid.addWidget(unit_lbl, row_idx, 2)
            labels[key] = val_lbl
            row_idx += 1

        group.setProperty("labels", labels)
        return group

    def update_measurements(self, data: OscilloscopeData):
        def fmt(v, decimals=4):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return "—"
            if abs(v) >= 1000: return f"{v/1000:.3f}k"
            if abs(v) >= 1: return f"{v:.{decimals}f}"
            if abs(v) >= 1e-3: return f"{v*1e3:.3f}m"
            if abs(v) >= 1e-6: return f"{v*1e6:.3f}µ"
            if abs(v) >= 1e-9: return f"{v*1e9:.3f}n"
            return f"{v:.4e}"

        def fill_channel(group, voltage, dt):
            labels = group.property("labels")
            if voltage is None or len(voltage) == 0:
                for lbl in labels.values():
                    lbl.setText("—")
                return None

            # Fjern NaN-værdier hvis de findes
            clean_voltage = voltage[~np.isnan(voltage)]
            if len(clean_voltage) == 0:
                for lbl in labels.values():
                    lbl.setText("—")
                return None

            ana = SignalAnalyzer(clean_voltage, dt)
            f = ana.frequency()

            labels["Vp V"].setText(fmt(ana.vp()))
            labels["Vpp V"].setText(fmt(ana.vpp()))
            labels["Vrms V"].setText(fmt(ana.vrms()))
            labels["Frequency Hz"].setText(fmt(f))
            labels["Rise time s"].setText(fmt(ana.risetime()))
            labels["Fall time s"].setText(fmt(ana.falltime()))
            dc = ana.dutycycle()
            labels["Duty cycle %"].setText(f"{dc:.1f}" if dc is not None else "—")
            labels["Crest factor"].setText(f"{ana.crest_factor():.3f}")
            labels["Form factor"].setText(f"{ana.form_factor():.3f}")

            thd = ana.thd()
            if thd:
                labels["THD %"].setText(f"{thd['thd_pct']:.3f}")
                labels["THD dB"].setText(f"{thd['thd_db']:.2f}")
            else:
                labels["THD %"].setText("—")
                labels["THD dB"].setText("—")

            snr = ana.snr()
            labels["SNR dB"].setText(f"{snr:.2f}" if snr is not None else "—")
            sinad = ana.sinad()
            labels["SINAD dB"].setText(f"{sinad:.2f}" if sinad is not None else "—")
            enob = ana.enob()
            labels["ENOB bit"].setText(f"{enob:.2f}" if enob is not None else "—")

            return ana

        ana1 = fill_channel(self.ch1_group, data.ch1_voltage if data.ch1_active else None, data.dt)
        ana2 = fill_channel(self.ch2_group, data.ch2_voltage if data.ch2_active else None, data.dt)

        if ana1 and ana2:
            f1 = ana1.frequency()
            f2 = ana2.frequency()
            if f1 and f2:
                match = abs(f1 - f2) / max(f1, f2) <= 0.001
                self.rel_labels["Frequency match"].setText("✓ YES" if match else "✗ NO")

                if match:
                    phase = phase_difference(ana1, ana2)
                    self.rel_labels["Phase"].setText(f"{phase:.2f}°" if phase is not None else "—")
                    av = ana2.vp() / ana1.vp() if ana1.vp() > 1e-9 else None
                    if av is not None:
                        self.rel_labels["Av (CH2/CH1)"].setText(f"{av:.4f}")
                        self.rel_labels["AvdB"].setText(f"{20*np.log10(av):.2f} dB")
                    else:
                        self.rel_labels["Av (CH2/CH1)"].setText("—")
                        self.rel_labels["AvdB"].setText("—")
                else:
                    for key in ["Phase", "Av (CH2/CH1)", "AvdB"]:
                        self.rel_labels[key].setText("N/A")
            else:
                for key in self.rel_labels:
                    self.rel_labels[key].setText("—")
        else:
            for key in self.rel_labels:
                self.rel_labels[key].setText("—")


# ── TAB 2: OSCILLOSCOPE DISPLAY ──────────────────────────────────────────────
class OscilloscopeScreen(QWidget):
    GRID_DIVS_H = 10
    GRID_DIVS_V = 8

    def __init__(self):
        super().__init__()
        self.data: OscilloscopeData | None = None
        self.x_offset = 0.0
        self.x_scale = 1.0
        self.cursor_a: float | None = None
        self.cursor_b: float | None = None
        self.dragging_cursor = None
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self.ch1_color = QColor("#f7cc52")
        self.ch2_color = QColor("#5af0e0")
        self.grid_color = QColor("#1c2128")
        self.grid_major_color = QColor("#21262d")
        self.bg_color = QColor("#0a0e13")

    def set_data(self, data: OscilloscopeData):
        self.data = data
        self.x_offset = 0.0
        self.x_scale = 1.0
        self.cursor_a = None
        self.cursor_b = None
        self.update()

    def set_zoom(self, factor: float):
        self.x_scale = max(0.1, min(100.0, factor))
        self.update()

    def set_pan(self, offset_pct: float):
        if self.data and self.data.time is not None and len(self.data.time) > 0:
            total = float(self.data.time[-1] - self.data.time[0])
            visible = total / self.x_scale
            max_offset = total - visible
            self.x_offset = offset_pct / 100.0 * max(0.0, max_offset)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        w, h = rect.width(), rect.height()
        ml, mr, mt, mb = 60, 20, 20, 40

        sx = ml
        sy = mt
        sw = w - ml - mr
        sh = h - mt - mb

        p.fillRect(rect, self.bg_color)
        p.fillRect(sx, sy, sw, sh, QColor("#070b0f"))

        self._draw_grid(p, sx, sy, sw, sh)

        if self.data is None or self.data.time is None or len(self.data.time) == 0:
            p.setPen(QColor("#30363d"))
            p.setFont(QFont("Consolas", 14))
            p.drawText(QRectF(sx, sy, sw, sh), Qt.AlignCenter,
                       "No data loaded\nFile → Open (Ctrl+O)")
            return

        if self.data.ch1_active and self.data.ch1_voltage is not None:
            self._draw_waveform(p, self.data.time, self.data.ch1_voltage,
                                self.ch1_color, sx, sy, sw, sh, "CH1")

        if self.data.ch2_active and self.data.ch2_voltage is not None:
            self._draw_waveform(p, self.data.time, self.data.ch2_voltage,
                                self.ch2_color, sx, sy, sw, sh, "CH2")

        self._draw_cursors(p, sx, sy, sw, sh)
        self._draw_labels(p, sx, sy, sw, sh)

        p.setPen(QPen(QColor("#30363d"), 1))
        p.drawRect(sx, sy, sw, sh)

    def _draw_grid(self, p: QPainter, sx, sy, sw, sh):
        dh = sh / self.GRID_DIVS_V
        dw = sw / self.GRID_DIVS_H

        pen_major = QPen(self.grid_major_color, 1, Qt.SolidLine)
        pen_minor = QPen(self.grid_color, 1, Qt.DotLine)

        for i in range(self.GRID_DIVS_H + 1):
            x = sx + i * dw
            p.setPen(pen_major if i % 2 == 0 else pen_minor)
            p.drawLine(int(x), sy, int(x), sy + sh)

        for i in range(self.GRID_DIVS_V + 1):
            y = sy + i * dh
            p.setPen(pen_major if i % 2 == 0 else pen_minor)
            p.drawLine(sx, int(y), sx + sw, int(y))

        cx = sx + sw // 2
        cy = sy + sh // 2
        p.setPen(QPen(QColor("#2d3340"), 1))
        p.drawLine(cx - 3, cy, cx + 3, cy)
        p.drawLine(cx, cy - 3, cx, cy + 3)

    def _draw_waveform(self, p: QPainter, time, voltage, color, sx, sy, sw, sh, label):
        if len(time) < 2:
            return

        # Fjern NaN-værdier for visning
        mask = ~np.isnan(voltage)
        if not np.any(mask):
            return
        time_clean = time[mask]
        voltage_clean = voltage[mask]

        t_total = float(time_clean[-1] - time_clean[0])
        t_start = float(time_clean[0]) + self.x_offset
        t_range = t_total / self.x_scale
        t_end = t_start + t_range

        t_start = max(t_start, float(time_clean[0]))
        t_end = min(t_end, float(time_clean[-1]))
        if t_end <= t_start:
            return

        vis_mask = (time_clean >= t_start) & (time_clean <= t_end)
        t_vis = time_clean[vis_mask]
        v_vis = voltage_clean[vis_mask]
        if len(t_vis) < 2:
            return

        v_min = float(np.min(voltage_clean))
        v_max = float(np.max(voltage_clean))
        v_range = v_max - v_min
        if v_range < 1e-12:
            v_range = 1.0
        v_pad = v_range * 0.1
        v_lo = v_min - v_pad
        v_hi = v_max + v_pad
        v_span = v_hi - v_lo

        def to_screen(t_val, v_val):
            px = sx + (t_val - t_start) / (t_end - t_start) * sw
            py = sy + sh - (v_val - v_lo) / v_span * sh
            return px, py

        max_pts = sw * 2
        if len(t_vis) > max_pts:
            idx = np.round(np.linspace(0, len(t_vis) - 1, max_pts)).astype(int)
            t_vis = t_vis[idx]
            v_vis = v_vis[idx]

        pen = QPen(color, 1.5)
        p.setPen(pen)
        path = QPainterPath()
        x0, y0 = to_screen(t_vis[0], v_vis[0])
        path.moveTo(x0, y0)
        for i in range(1, len(t_vis)):
            xi, yi = to_screen(t_vis[i], v_vis[i])
            path.lineTo(xi, yi)
        p.drawPath(path)

        p.setPen(color)
        p.setFont(QFont("Consolas", 9, QFont.Bold))
        lx = sx + 6 + (0 if label == "CH1" else 60)
        scale_str = f"{v_range/8:.3g}V/div"
        p.drawText(int(lx), sy + 14, f"{label}  {scale_str}")

    def _draw_cursors(self, p: QPainter, sx, sy, sw, sh):
        if self.data is None or self.data.time is None:
            return
        t = self.data.time
        t_clean = t[~np.isnan(t)] if np.any(np.isnan(t)) else t
        if len(t_clean) == 0:
            return

        t_start = t_clean[0] + self.x_offset
        t_range = (t_clean[-1] - t_clean[0]) / self.x_scale

        def t_to_x(tc):
            return sx + (tc - t_start) / t_range * sw

        pen_a = QPen(QColor("#ff7b72"), 1, Qt.DashLine)
        pen_b = QPen(QColor("#a5d6ff"), 1, Qt.DashLine)

        if self.cursor_a is not None:
            xa = t_to_x(self.cursor_a)
            p.setPen(pen_a)
            p.drawLine(int(xa), sy, int(xa), sy + sh)
            p.setFont(QFont("Consolas", 9))
            p.setPen(QColor("#ff7b72"))
            p.drawText(int(xa) + 3, sy + 14, f"A:{self._fmt_time(self.cursor_a)}")

        if self.cursor_b is not None:
            xb = t_to_x(self.cursor_b)
            p.setPen(pen_b)
            p.drawLine(int(xb), sy, int(xb), sy + sh)
            p.setFont(QFont("Consolas", 9))
            p.setPen(QColor("#a5d6ff"))
            p.drawText(int(xb) + 3, sy + 28, f"B:{self._fmt_time(self.cursor_b)}")

        if self.cursor_a is not None and self.cursor_b is not None:
            dt = abs(self.cursor_b - self.cursor_a)
            p.setPen(QColor("#c9d1d9"))
            p.setFont(QFont("Consolas", 9))
            info = f"ΔT:{self._fmt_time(dt)}  f:{self._fmt_freq(1/dt if dt > 0 else 0)}"
            p.drawText(sx + sw - 200, sy + 14, info)

    def _draw_labels(self, p: QPainter, sx, sy, sw, sh):
        if self.data is None or self.data.time is None:
            return
        t = self.data.time
        t_clean = t[~np.isnan(t)] if np.any(np.isnan(t)) else t
        if len(t_clean) == 0:
            return

        t_start = t_clean[0] + self.x_offset
        t_range = (t_clean[-1] - t_clean[0]) / self.x_scale

        p.setFont(QFont("Consolas", 9))
        p.setPen(QColor("#484f58"))

        for i in range(self.GRID_DIVS_H + 1):
            tc = t_start + i / self.GRID_DIVS_H * t_range
            x = sx + i * sw / self.GRID_DIVS_H
            p.drawText(int(x) - 20, sy + sh + 18, self._fmt_time(tc))

    def _fmt_time(self, t: float) -> str:
        if np.isnan(t):
            return "—"
        if abs(t) >= 1: return f"{t:.3f}s"
        if abs(t) >= 1e-3: return f"{t*1e3:.2f}ms"
        if abs(t) >= 1e-6: return f"{t*1e6:.2f}µs"
        return f"{t*1e9:.2f}ns"

    def _fmt_freq(self, f: float) -> str:
        if np.isnan(f):
            return "—"
        if f >= 1e6: return f"{f/1e6:.3f}MHz"
        if f >= 1e3: return f"{f/1e3:.3f}kHz"
        return f"{f:.1f}Hz"

    def mousePressEvent(self, event):
        if self.data is None:
            return
        p = self._screen_x_to_time(event.position().x())
        if p is None:
            return
        if event.button() == Qt.LeftButton:
            self.cursor_a = p
        elif event.button() == Qt.RightButton:
            self.cursor_b = p
        self.update()

    def _screen_x_to_time(self, px):
        if self.data is None or self.data.time is None:
            return None
        t = self.data.time
        t_clean = t[~np.isnan(t)] if np.any(np.isnan(t)) else t
        if len(t_clean) == 0:
            return None
        ml, mr = 60, 20
        sw = self.width() - ml - mr
        t_start = t_clean[0] + self.x_offset
        t_range = (t_clean[-1] - t_clean[0]) / self.x_scale
        return t_start + (px - ml) / sw * t_range


class OscilloscopeTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("ZOOM:"))

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(1, 200)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setMaximumWidth(160)

        self.zoom_label = QLabel("1.0×")
        self.zoom_label.setMinimumWidth(40)

        ctrl.addWidget(self.zoom_slider)
        ctrl.addWidget(self.zoom_label)
        ctrl.addWidget(QLabel("  PAN:"))

        self.pan_slider = QSlider(Qt.Horizontal)
        self.pan_slider.setRange(0, 100)
        self.pan_slider.setValue(0)
        self.pan_slider.setMaximumWidth(200)

        ctrl.addWidget(self.pan_slider)
        ctrl.addStretch()
        ctrl.addWidget(QLabel("  LMB=Cursor A   RMB=Cursor B"))

        layout.addLayout(ctrl)

        self.screen = OscilloscopeScreen()
        layout.addWidget(self.screen)

        self.zoom_slider.valueChanged.connect(self._on_zoom)
        self.pan_slider.valueChanged.connect(self._on_pan)

    def _on_zoom(self, val):
        factor = val / 10.0
        self.zoom_label.setText(f"{factor:.1f}×")
        self.screen.set_zoom(factor)

    def _on_pan(self, val):
        self.screen.set_pan(val)

    def set_data(self, data: OscilloscopeData):
        self.screen.set_data(data)


# ── TAB 3: SPECTRUM ANALYZER ─────────────────────────────────────────────────
class SpectrumDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.ch1_harmonics: list = []
        self.ch2_harmonics: list = []
        self.freqs_db: tuple | None = None
        self.ch1_fund: float | None = None
        self.ch2_fund: float | None = None
        self.setMinimumHeight(380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_spectrum(self, ch1_data=None, ch2_data=None):
        self.ch1_harmonics = []
        self.ch2_harmonics = []
        self.freqs_db = None
        self.ch1_fund = None
        self.ch2_fund = None

        freqs1 = db1 = freqs2 = db2 = None

        if ch1_data:
            ana = SignalAnalyzer(ch1_data[0], ch1_data[1])
            f = ana.frequency()
            if f and f < 50000:
                self.ch1_fund = f
                self.ch1_harmonics = ana.harmonics(40)
                freqs1, db1 = ana.fft_spectrum()

        if ch2_data:
            ana = SignalAnalyzer(ch2_data[0], ch2_data[1])
            f = ana.frequency()
            if f and f < 50000:
                self.ch2_fund = f
                self.ch2_harmonics = ana.harmonics(40)
                freqs2, db2 = ana.fft_spectrum()

        if freqs1 is not None or freqs2 is not None:
            if freqs1 is None:
                freqs1, db1 = freqs2, db2
            if freqs2 is None:
                freqs2, db2 = freqs1, db1
            self.freqs_db = (freqs1, db1, freqs2, db2)

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        ml, mr, mt, mb = 70, 20, 20, 50

        p.fillRect(self.rect(), QColor("#070b0f"))

        if self.freqs_db is None:
            p.setPen(QColor("#30363d"))
            p.setFont(QFont("Consolas", 13))
            msg = "No spectrum data"
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, msg)
            return

        freqs1, db1, freqs2, db2 = self.freqs_db
        sw = w - ml - mr
        sh = h - mt - mb

        f_min = max(freqs1[1] if len(freqs1) > 1 else 1, 10)
        f_max_val = float(freqs1[-1])
        db_min = -90.0
        db_max = 10.0

        def to_xy(f, db):
            if f <= 0:
                f = f_min
            xn = np.log10(f/f_min) / np.log10(f_max_val/f_min)
            yn = (db - db_min) / (db_max - db_min)
            return ml + xn * sw, mt + (1 - yn) * sh

        p.setPen(QPen(QColor("#1c2128"), 1))
        for db in range(-90, 20, 10):
            _, y = to_xy(f_min, db)
            p.drawLine(ml, int(y), ml + sw, int(y))
            p.setFont(QFont("Consolas", 8))
            p.setPen(QColor("#484f58"))
            p.drawText(2, int(y) + 4, f"{db}")
            p.setPen(QPen(QColor("#1c2128"), 1))

        for exp in range(1, 6):
            for mult in [1, 2, 5]:
                f = mult * 10**exp
                if f_min <= f <= f_max_val:
                    x, _ = to_xy(f, db_min)
                    p.setPen(QPen(QColor("#1c2128"), 1))
                    p.drawLine(int(x), mt, int(x), mt + sh)
                    p.setPen(QColor("#484f58"))
                    p.setFont(QFont("Consolas", 8))
                    lbl = f"{f/1000:.0f}k" if f >= 1000 else f"{f:.0f}"
                    p.drawText(int(x) - 12, mt + sh + 16, lbl)

        def draw_spectrum(freqs, db, color, alpha=80):
            pen = QPen(color, 1)
            pen.setColor(QColor(color.red(), color.green(), color.blue(), alpha))
            p.setPen(pen)
            if len(freqs) < 2:
                return
            mask = freqs >= f_min
            fr = freqs[mask]
            d = db[mask]
            if len(fr) < 2:
                return
            path = QPainterPath()
            x0, y0 = to_xy(fr[0], d[0])
            path.moveTo(x0, y0)
            for i in range(1, min(len(fr), sw*2)):
                xi, yi = to_xy(fr[i], d[i])
                path.lineTo(xi, yi)
            p.drawPath(path)

        if db1 is not None:
            draw_spectrum(freqs1, db1, QColor("#f7cc52"), 100)
        if db2 is not None:
            draw_spectrum(freqs2, db2, QColor("#5af0e0"), 100)

        def draw_harmonics(harmonics, color, offset_y=0):
            if not harmonics:
                return
            for i, (f, db) in enumerate(harmonics):
                if f < f_min or f > f_max_val:
                    continue
                x, y = to_xy(f, db)
                bar_top = to_xy(f, db)[1]
                bar_bot = to_xy(f, db_min)[1]
                c = QColor(color)
                c.setAlpha(180 if i == 0 else 120)
                p.setPen(QPen(c, 2 if i == 0 else 1))
                p.drawLine(int(x), int(bar_top), int(x), int(bar_bot))
                if i < 10:
                    p.setFont(QFont("Consolas", 7))
                    p.setPen(c)
                    p.drawText(int(x) - 4, int(bar_top) - 3 + offset_y, str(i+1))

        draw_harmonics(self.ch1_harmonics, "#f7cc52", 0)
        draw_harmonics(self.ch2_harmonics, "#5af0e0", 10)

        p.setFont(QFont("Consolas", 9))
        p.setPen(QColor("#8b949e"))
        p.drawText(2, mt + sh // 2, "dBV")
        p.drawText(ml + sw // 2 - 20, h - 4, "Frequency")

        p.setPen(QPen(QColor("#30363d"), 1))
        p.drawRect(ml, mt, sw, sh)


class SpectrumTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.info_bar = QLabel("Load a file to show spectrum. Only signals < 50 kHz are analyzed.")
        self.info_bar.setStyleSheet("color: #8b949e; font-size: 11px; padding: 4px;")
        layout.addWidget(self.info_bar)

        self.display = SpectrumDisplay()
        layout.addWidget(self.display)

        self.harm_frame = QGroupBox("HARMONIC TABLE")
        harm_layout = QHBoxLayout(self.harm_frame)

        self.ch1_harm_label = QLabel("CH1: —")
        self.ch1_harm_label.setStyleSheet("color: #f7cc52; font-size: 11px;")
        self.ch1_harm_label.setAlignment(Qt.AlignTop)

        self.ch2_harm_label = QLabel("CH2: —")
        self.ch2_harm_label.setStyleSheet("color: #5af0e0; font-size: 11px;")
        self.ch2_harm_label.setAlignment(Qt.AlignTop)

        harm_layout.addWidget(self.ch1_harm_label)
        harm_layout.addWidget(self.ch2_harm_label)
        self.harm_frame.setMaximumHeight(120)
        layout.addWidget(self.harm_frame)

    def set_data(self, data: OscilloscopeData):
        ch1 = (data.ch1_voltage, data.dt) if data.ch1_active and data.ch1_voltage is not None else None
        ch2 = (data.ch2_voltage, data.dt) if data.ch2_active and data.ch2_voltage is not None else None
        self.display.set_spectrum(ch1, ch2)

        def harm_text(harmonics, fund, label):
            if not harmonics:
                if fund and fund >= 50000:
                    return f"{label}: {fund/1000:.1f} kHz > 50 kHz limit"
                return f"{label}: —"
            lines = [f"{label}:  f0={fund:.1f} Hz" if fund else f"{label}:"]
            for i, (f, db) in enumerate(harmonics[:10]):
                lines.append(f"  H{i+1}: {f:.1f} Hz  {db:.1f} dBV")
            return "\n".join(lines)

        self.ch1_harm_label.setText(harm_text(
            self.display.ch1_harmonics, self.display.ch1_fund, "CH1"))
        self.ch2_harm_label.setText(harm_text(
            self.display.ch2_harmonics, self.display.ch2_fund, "CH2"))


# ── MAIN WINDOW ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rigol DS1052E Analyzer")
        self.resize(1200, 720)
        self.data: OscilloscopeData | None = None
        self._build_ui()
        self._build_menu()
        self.setStyleSheet(DARK_STYLE)
        QTimer.singleShot(100, self._open_file)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(38)
        header.setStyleSheet("background:#161b22; border-bottom: 1px solid #30363d;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("RIGOL DS1052E  //  OSCILLOSCOPE ANALYZER")
        title.setStyleSheet("color:#58a6ff; font-size: 12px; letter-spacing: 3px; font-weight: bold;")

        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color:#484f58; font-size: 11px;")

        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(self.file_label)

        open_btn = QPushButton("⊕ OPEN FILE")
        open_btn.clicked.connect(self._open_file)
        h_layout.addWidget(open_btn)
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tab_measure = MeasurementWidget()
        self.tab_scope = OscilloscopeTab()
        self.tab_spectrum = SpectrumTab()
        self.tabs.addTab(self.tab_measure, "MEASUREMENTS")
        self.tabs.addTab(self.tab_scope, "OSCILLOSCOPE")
        self.tabs.addTab(self.tab_spectrum, "SPECTRUM")
        layout.addWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — Open a Rigol CSV file")

    def _build_menu(self):
        menu = self.menuBar()
        menu.setStyleSheet("""
            QMenuBar { background:#161b22; color:#c9d1d9; border-bottom: 1px solid #30363d; }
            QMenuBar::item:selected { background:#21262d; }
            QMenu { background:#161b22; color:#c9d1d9; border: 1px solid #30363d; }
            QMenu::item:selected { background:#21262d; }
        """)

        file_menu = menu.addMenu("File")
        open_action = QAction("Open…", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Oscilloscope Data",
            os.path.expanduser("~"),
            "Rigol CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path: str):
        data = OscilloscopeData()
        ok = data.load_csv(path)

        if not ok:
            QMessageBox.warning(self, "Load Error",
                                f"Could not parse file:\n{path}\n\n"
                                "Make sure it is a valid Rigol CSV export.")
            return

        self.data = data

        ch_info = ""
        if data.ch1_active:
            ch_info += "CH1 "
        if data.ch2_active:
            ch_info += "CH2 "
        
        pts_info = f"{len(data.time)} pts" if data.time is not None else "0 pts"
        fs_info = f"fs={data.sample_rate/1000:.1f} kSa/s"
        
        self.file_label.setText(f"  {data.filename}  |  {ch_info}|  {pts_info}  |  {fs_info}")

        self.tab_measure.update_measurements(data)
        self.tab_scope.set_data(data)
        self.tab_spectrum.set_data(data)
        self.status.showMessage(f"Loaded: {path}")


def main():
    missing = []
    try:
        import scipy
    except ImportError:
        missing.append("scipy")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("Rigol DS1052E Analyzer")
    app.setOrganizationName("DSP Tools")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()