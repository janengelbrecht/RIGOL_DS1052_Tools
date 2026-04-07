"""
rigol_analyzer.py
=================
Rigol DS1052E Oscilloscope Data Analyzer
PySide6 Desktop Application — CSV import only.

Faner:
  1. MEASUREMENTS  — elektriske målinger pr. kanal (Vp, Vpp, Vrms, frekvens,
                     risetime, falltime, dutycycle, crest factor, form factor,
                     THD, SNR, SINAD, ENOB) samt kanalrelationer (fase, Av, AvdB)
  2. OSCILLOSCOPE  — grafisk bølgeform med zoom, pan og to markørcursorer
  3. SPECTRUM      — spektrumanalysator med 40 harmoniske og dBV-akse

Afhængigheder:  pip install PySide6 numpy scipy
"""

# ── Standardbiblioteker ──────────────────────────────────────────────────────
import sys                          # sys.argv og sys.exit()
import os                           # os.path til filnavne
import struct                       # binær pakkeoppakning (WFM-format)
import numpy as np                  # numerisk array-behandling og FFT
from pathlib import Path            # objektorienteret filstihaandtering

# ── PySide6 GUI-widgets ──────────────────────────────────────────────────────
from PySide6.QtWidgets import (
    QApplication,    # roden af enhver Qt-applikation
    QMainWindow,     # hoved-vindue med menubar og statusbar
    QTabWidget,      # fane-container til de tre visninger
    QWidget,         # basisklasse for alle visuelle elementer
    QVBoxLayout,     # lodret stapellayout
    QHBoxLayout,     # vandret raekkeled-layout
    QLabel,          # tekst- og statuspvisning
    QFileDialog,     # OS-filvalgs-dialog
    QFrame,          # rammeboks / vandret separator-linie
    QGridLayout,     # gitter-layout til maalevaerditabellen
    QSplitter,       # justerbar opdeler (importeret, ikke brugt aktivt)
    QPushButton,     # klikknap
    QComboBox,       # dropdown-liste (importeret, ikke brugt aktivt)
    QSlider,         # skyderknap til zoom og pan
    QGroupBox,       # rammegruppe med titel
    QScrollArea,     # rullbar beholder (importeret, ikke brugt aktivt)
    QSizePolicy,     # widget-stoerrelsesstrategi
    QStatusBar,      # statuslinje i bunden af vinduet
    QToolBar,        # vaerktoeJslinje (importeret, ikke brugt aktivt)
    QSpinBox,        # heltalsinput-boks (importeret, ikke brugt aktivt)
    QDoubleSpinBox,  # decimal-input-boks (importeret, ikke brugt aktivt)
    QCheckBox,       # afkrydsningsfelt (importeret, ikke brugt aktivt)
    QMessageBox,     # modal fejl-/bekraeftelsesdialog
)
from PySide6.QtCore import (
    Qt,              # namespace med konstanter (alignment, knapper m.v.)
    QTimer,          # enkelt-skuds timer — bruges til forsinket filaabn ved opstart
    Signal,          # Qt-signal til event-kommunikation (importeret, ikke brugt aktivt)
    QPointF,         # flydende-komma 2D-punkt (importeret, ikke brugt aktivt)
    QRectF,          # flydende-komma rektangel — bruges i paintEvent
    QSize,           # heltal stoerrelse (importeret, ikke brugt aktivt)
)
from PySide6.QtGui import (
    QPainter,        # 2D-tegne-engine til bølgeform og spektrum
    QPen,            # linjefarve og -tykkelse til QPainter
    QColor,          # RGBA-farvevaerdi
    QBrush,          # fyldfarve (importeret, ikke brugt aktivt)
    QFont,           # skrifttype og -stoerrelse
    QPainterPath,    # sammenkaedet vektorsti til bølgeformstegning
    QLinearGradient, # liniear farveovergang (importeret, ikke brugt aktivt)
    QRadialGradient, # radial farveovergang (importeret, ikke brugt aktivt)
    QFontMetrics,    # tekstbredde-maaling (importeret, ikke brugt aktivt)
    QAction,         # menuhandling med genvejstast
    QKeySequence,    # standard-genvejstast (Ctrl+O, Ctrl+Q m.v.)
    QPixmap,         # rasterbillede (importeret, ikke brugt aktivt)
    QPalette,        # farvepalette for widgets (importeret, ikke brugt aktivt)
)


# ─────────────────────────────────────────────────────────────────────────────
#  DARK THEME STYLESHEET
#  Qt CSS-stylesheet der saetter hele programmets moerke farvetema.
#  Alle farver er hentet fra GitHubs Dark-tema paleta.
# ─────────────────────────────────────────────────────────────────────────────

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0d1117;      /* Baggrundsfarve: naesten sort */
    color: #e6edf3;                 /* Standard tekstfarve: lys graa */
    font-family: 'Consolas', 'Courier New', monospace;  /* Monospace skrift — velegnet til tal */
    font-size: 12px;                /* Standard skriftstoerrelse */
}
QTabWidget::pane {
    border: 1px solid #30363d;      /* Kant rundt om fane-indholdet */
    background-color: #0d1117;      /* Faneindholdets baggrundsfarve */
}
QTabBar::tab {
    background-color: #161b22;      /* Ikke-valgt fanes baggrundsfarve */
    color: #8b949e;                 /* Ikke-valgt fanes tekstfarve: graa */
    padding: 8px 20px;              /* Indvendig afstand i fane-label */
    border: 1px solid #30363d;      /* Kant rundt om fane */
    border-bottom: none;            /* Ingen bundkant — smelter sammen med indhold */
    min-width: 140px;               /* Minimumsbredde saa alle faner er jaevnbrede */
    font-size: 11px;                /* Lidt mindre skrift end standard */
    letter-spacing: 1px;            /* Lidt ekstra afstand mellem bogstaver */
    text-transform: uppercase;      /* Fanenavn altid med store bogstaver */
}
QTabBar::tab:selected {
    background-color: #0d1117;      /* Valgt fane smelter visuelt sammen med indhold */
    color: #58a6ff;                 /* Valgt fanes tekstfarve: blaa */
    border-top: 2px solid #58a6ff; /* Blaa linie oeverst paa aktiv fane */
}
QTabBar::tab:hover {
    background-color: #1c2128;      /* Lysere baggrund naar musen holdes over fane */
    color: #c9d1d9;                 /* Lidt lysere tekst ved hover */
}
QGroupBox {
    border: 1px solid #30363d;      /* Kant rundt om grupperammen */
    border-radius: 4px;             /* Afrundede hjoerner */
    margin-top: 16px;               /* Plads til titlen over rammen */
    padding: 8px;                   /* Indvendig afstand */
    font-size: 11px;                /* Skriftstoerrelse for gruppeoverskrift */
    color: #8b949e;                 /* Daemp gruppetitlen */
    letter-spacing: 1px;            /* Lettere spaerret gruppeoverskrift */
    text-transform: uppercase;      /* Gruppeoverskrift altid med store bogstaver */
}
QGroupBox::title {
    subcontrol-origin: margin;      /* Titlen placeres i marginen oeverst */
    left: 10px;                     /* Indryk fra venstre kant */
    padding: 0 4px;                 /* Vandret polstring saa kanten ikke skaerer igennem */
}
QPushButton {
    background-color: #21262d;      /* Knapbaggrund: moerk graa */
    border: 1px solid #30363d;      /* Kant rundt om knap */
    border-radius: 4px;             /* Afrundede hjoerner */
    color: #c9d1d9;                 /* Knaptekst: lys graa */
    padding: 6px 14px;              /* Indvendig afstand */
    font-size: 11px;                /* Skriftstoerrelse */
}
QPushButton:hover {
    background-color: #30363d;      /* Lysere baggrund ved hover */
    border-color: #58a6ff;          /* Blaa kant ved hover */
    color: #58a6ff;                 /* Blaa tekst ved hover */
}
QPushButton:pressed {
    background-color: #388bfd26;    /* Gennemsigtig blaa baggrund ved tryk */
}
QComboBox {
    background-color: #21262d;      /* Dropdown-boks baggrund */
    border: 1px solid #30363d;      /* Dropdown-boks kant */
    border-radius: 4px;             /* Afrundede hjoerner */
    color: #c9d1d9;                 /* Dropdown-tekst: lys graa */
    padding: 4px 8px;               /* Indvendig afstand */
}
QComboBox::drop-down { border: none; }  /* Skjul standard dropdown-pil */
QComboBox QAbstractItemView {
    background-color: #21262d;      /* Listeboks baggrund */
    border: 1px solid #30363d;      /* Listeboks kant */
    color: #c9d1d9;                 /* Listeboks tekst */
    selection-background-color: #388bfd26;  /* Markeringsfarve i listen */
}
QLabel { color: #c9d1d9; }          /* Alle etiket-widgets: lys graa tekst */
QSlider::groove:horizontal {
    background: #21262d;            /* Sporbaggrund for skyderknap */
    height: 4px;                    /* Sporhojde */
    border-radius: 2px;             /* Afrundede sporende */
}
QSlider::handle:horizontal {
    background: #58a6ff;            /* Skydeknappens farve: blaa */
    width: 14px;                    /* Bredde af skydeknap */
    height: 14px;                   /* Hoejde af skydeknap */
    margin: -5px 0;                 /* Centrerer knappen lodret i sporet */
    border-radius: 7px;             /* Rund knap */
}
QSlider::sub-page:horizontal { background: #388bfd; border-radius: 2px; }  /* Fyldfarve til venstre for skyder */
QCheckBox::indicator {
    width: 14px; height: 14px;      /* Stoerrelse af afkrydsningsboks */
    border: 1px solid #30363d;      /* Kant */
    border-radius: 3px;             /* Let afrundet */
    background: #21262d;            /* Tomt afkrydsningsfelt: moerk graa */
}
QCheckBox::indicator:checked { background: #388bfd; }  /* Markeret afkrydsningsfelt: blaa */
QStatusBar {
    background-color: #161b22;      /* Statusbarens baggrundsfarve */
    border-top: 1px solid #30363d; /* Adskillelseslinie over statusbaren */
    color: #8b949e;                 /* Statusbarens tekstfarve: daemp graa */
    font-size: 11px;                /* Lidt mindre skrift i statusbaren */
}
QScrollBar:vertical {
    background: #0d1117;            /* Rullebarens baggrund */
    width: 8px;                     /* Rullebarens bredde */
    border-radius: 4px;             /* Afrundede kanter */
}
QScrollBar::handle:vertical {
    background: #30363d;            /* Rulleknappens farve */
    border-radius: 4px;             /* Afrundet rulleknap */
    min-height: 20px;               /* Minimumshoejde saa rulleknappen er klikbar */
}
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #30363d; }  /* Vandrette/lodrette separatorlinjer: moerk graa */
"""


# ─────────────────────────────────────────────────────────────────────────────
#  DATA PARSING
#  OscilloscopeData er en simpel datacontainer der holder den indlaesd CSV-data
#  og stiller den til raadighed for analyse og visning.
# ─────────────────────────────────────────────────────────────────────────────

# Klasse der indeholder alle data fra en enkelt CSV-fil (begge kanaler)
class OscilloscopeData:
    """Container for oscilloscope channel data"""

    # Konstruktoer: initialiserer alle felter til tomme/standard vaerdier
    def __init__(self):
        self.ch1_raw: np.ndarray | None = None      # Raa ADC-vaerdier kanal 1 (ubrugt i CSV-flow)
        self.ch2_raw: np.ndarray | None = None      # Raa ADC-vaerdier kanal 2 (ubrugt i CSV-flow)
        self.ch1_voltage: np.ndarray | None = None  # Spændingssamples kanal 1 i volt
        self.ch2_voltage: np.ndarray | None = None  # Spændingssamples kanal 2 i volt
        self.time: np.ndarray | None = None         # Tidsvektor i sekunder (delt for begge kanaler)
        self.sample_rate: float = 1e6               # Samplehastighed i Sa/s, standard 1 MSa/s
        self.dt: float = 1e-6                       # Tidstrin mellem samples i sekunder
        self.ch1_scale: float = 1.0                 # Scopets V/div-indstilling kanal 1 (fra header)
        self.ch2_scale: float = 1.0                 # Scopets V/div-indstilling kanal 2 (fra header)
        self.ch1_offset: float = 0.0                # DC-offset indstilling kanal 1 (fra header)
        self.ch2_offset: float = 0.0                # DC-offset indstilling kanal 2 (fra header)
        self.time_scale: float = 1e-3               # Scopets tid/div-indstilling i s/div
        self.filename: str = ""                     # Filnavn uden sti — vises i header-bar
        self.ch1_active: bool = False               # Sand naar kanal 1 har gyldige data
        self.ch2_active: bool = False               # Sand naar kanal 2 har gyldige data

    # Indlaeser en Rigol CSV-eksportfil og fylder objektets felter
    def load_csv(self, path: str) -> bool:
        """Parse Rigol CSV export.
        Understøtter tre kolonneformater:
          2-kol:  Time, CH1
          3-kol:  Time, CH1, CH2
          4-kol:  Time_CH1, V_CH1, Time_CH2, V_CH2   (Rigol standard-eksport)
        Returnerer True ved succes, False ved fejl.
        """
        try:
            # Åbn filen med UTF-8 BOM-understøttelse (Rigol tilfojer BOM)
            with open(path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()                           # Indlaes alle linjer som tekst

            # Find den foerste datalinje ved at lede efter den foerste
            # linje der starter med et tal (dvs. ikke en header-linje)
            data_start = 0                                      # Indeks for foerste datalinje
            header_line = ""                                    # Gemmer header-linjen til kolonnedetektering
            for i, line in enumerate(lines):                    # Gennemgaa linje for linje
                stripped = line.strip()                         # Fjern whitespace for og bagved
                if not stripped:                                # Spring tomme linjer over
                    continue
                parts = [p.strip() for p in stripped.split(',')]  # Opdel paa komma
                try:
                    float(parts[0])                             # Forsøg at konvertere foerste felt til tal
                    data_start = i                              # Lykkedes: denne linje er foerste datalinje
                    break                                       # Stop søgningen
                except ValueError:
                    header_line = stripped                      # Mislykkedes: gem som header-linje
                    data_start = i + 1                          # Naeste linje er kandidat til foerste datalinje

            # Analyser header-linjen for at bestemme kolonneformat
            # (bruges kun til diagnoser — selve kolonneantallet detekteres nedenfor)
            header_parts = [p.strip().lower() for p in header_line.split(',')]  # Split og lowercase
            ncols_header = len(header_parts)                    # Antal kolonner ifoelge header

            # Forbered tomme lister til de tre mulige datakolonner
            times, ch1s, ch2s = [], [], []                     # Tidspunkter, CH1-volt, CH2-volt

            # Gennemgaa alle datalinjer fra foerste datalinje til slut
            for line in lines[data_start:]:
                line = line.strip()                             # Fjern whitespace
                if not line:                                    # Spring tomme linjer over
                    continue
                parts = line.split(',')                         # Opdel paa komma
                try:
                    vals = [float(p) for p in parts]            # Konverter alle felter til float
                except ValueError:
                    continue                                     # Ugyldig linje (fx header-rest) — spring over

                n = len(vals)                                   # Antal kolonner i denne linje
                if n == 4:
                    # Rigol 4-kolonneformat: Time_CH1, V_CH1, Time_CH2, V_CH2
                    times.append(vals[0])                       # Tidspunkt fra CH1-tidskolonne
                    ch1s.append(vals[1])                        # CH1-spænding
                    ch2s.append(vals[3])                        # CH2-spænding (kolonne 3, ikke 2!)
                elif n == 3:
                    # 3-kolonneformat: faelles tid, CH1, CH2
                    times.append(vals[0])                       # Faelles tidspunkt
                    ch1s.append(vals[1])                        # CH1-spænding
                    ch2s.append(vals[2])                        # CH2-spænding
                elif n == 2:
                    # 2-kolonneformat: kun tid og CH1
                    times.append(vals[0])                       # Tidspunkt
                    ch1s.append(vals[1])                        # CH1-spænding (ingen CH2)
                elif n >= 5:
                    # Ukendt bredt format — antag kolonner 0,1,3 som Time,CH1,CH2
                    times.append(vals[0])                       # Tidspunkt
                    ch1s.append(vals[1])                        # CH1-spænding
                    ch2s.append(vals[3])                        # CH2-spænding (springer kolonne 2 over)

            if not times:                                       # Ingen gyldige datalinjer fundet
                return False                                    # Returner fejl

            # Konverter tidslisten til numpy-array og udregn dt og samplehastighed
            self.time = np.array(times)                        # Tidsvektor som numpy-array
            if len(self.time) > 1:                             # Behøver mindst 2 punkter for at beregne dt
                self.dt = float(np.mean(np.diff(self.time)))              # Gennemsnitlig tidsforskel = dt
                self.sample_rate = 1.0 / self.dt if self.dt > 0 else 1e6  # fs = 1/dt

            # Gem CH1-data hvis der er nogen
            if ch1s:
                self.ch1_voltage = np.array(ch1s, dtype=np.float64)  # CH1-spændingsarray
                self.ch1_active = True                                 # Markér kanal 1 som aktiv

            # Gem CH2-data kun hvis antallet matcher antallet af tidspunkter
            if ch2s and len(ch2s) == len(times):
                self.ch2_voltage = np.array(ch2s, dtype=np.float64)  # CH2-spændingsarray
                self.ch2_active = True                                 # Markér kanal 2 som aktiv

            self.filename = os.path.basename(path)             # Gem filnavn uden mappestr
            return True                                         # Indlaesning lykkedes

        except Exception as e:
            print(f"CSV load error: {e}")                      # Log fejlbeskeden til konsol
            return False                                        # Returner fejl til kald

    # Indlaeser en Rigol DS1052E WFM-binærfil (beholdt til eventuel fremtidig brug)
    def load_wfm(self, path: str) -> bool:
        """Parse Rigol DS1052E .wfm binary format.

        Bekraeftet header-layout (RIGLWFM magic, reverse-engineered):
          0x00   8 B   magic 'RIGLWFM\\0'
          0x08  u32   n_pts      – bytes per kanalblok
          0x0C  f32   fs_comb    – kombineret stream samplehastighed (Sa/s)
          0x10  u32   n_channels
          0x14  f32   dt_comb    – dt for kombineret stream (s)
          0x64  14 B  ASCII-tidsstempel  YYYYMMDDHHMMSS
          0x1FF        datastart (header = 511 bytes)

        Datalayout — to sekventielle blokke, hver n_pts int8-bytes:
          Blok 1 @ 0x1FF (CH1):
            Byte 0         → CH1 sample 0
            Bytes 1–3      → filler (0x7F)
            Bytes 4,6,8,…  → CH1 samples 1, 2, 3, …
            Bytes 5,7,9,…  → filler (0x7F)

          Blok 2 @ 0x1FF + n_pts (CH2):
            Bytes 0–3      → filler (0x7F)
            Bytes 4,6,8,…  → CH2 samples 0, 1, 2, …
            Bytes 5,7,9,…  → filler (0x7F)

        Per-kanal dt  = dt_comb × 2
        Spænding      = raw_int8 / 25.0  (enheder: scope-divisioner)
        """
        try:
            with open(path, 'rb') as f:                        # Åbn fil i binær tilstand
                data = f.read()                                 # Indlaes hele filen som bytes

            HEADER = 511                                        # Header-størrelse i bytes (altid 511)
            MAGIC  = b'RIGLWFM\x00'                            # De 8 forventede magic bytes i filstart

            if len(data) < HEADER + 8:                         # Filen er for kort til at vaere gyldig
                return False
            if data[:8] != MAGIC:                              # Foerste 8 bytes matcher ikke RIGLWFM
                return False

            n_pts   = struct.unpack_from('<I', data, 0x08)[0]  # Antal bytes per kanalblok (little-endian uint32)
            dt_comb = struct.unpack_from('<f', data, 0x14)[0]  # Tidstrin for kombineret stream (little-endian float32)

            if n_pts < 8 or dt_comb <= 0:                     # Sanity-tjek: ugyldig header
                return False

            dt_ch = dt_comb * 2.0                              # Per-kanal dt er dobbelt af kombineret dt (interleaved)

            # Indre hjælpefunktion: udtrækker signalsamples fra én interleaved blok.
            # Blok-layout: [s0, F, F, F, s1, F, s2, F, ...] hvor F=filler (0x7F=127)
            def _extract_channel(block: bytes) -> np.ndarray:
                """Udtrækker signalsamples fra en interleaved datablok."""
                b = np.frombuffer(block, dtype=np.int8).astype(np.float64)  # Tolkes som signed bytes
                return np.concatenate([[b[0]], b[4::2]])        # Sample 0 + hver 2. byte fra byte 4

            # Indlaes CH1-blok (starter ved byte 511 = 0x1FF)
            off1 = HEADER                                       # Start-offset for CH1-blok
            if off1 + n_pts > len(data):                       # Kontrollér at blokken er inden for filen
                return False
            raw1 = _extract_channel(data[off1:off1 + n_pts])  # Udtræk CH1 ADC-vaerdier

            # Indlaes CH2-blok (starter umiddelbart efter CH1-blokken)
            off2 = HEADER + n_pts                              # Start-offset for CH2-blok
            raw2 = None                                         # Standardvaerdi: ingen CH2
            if off2 + n_pts <= len(data):                      # Kontrollér at CH2-blok er til stede
                raw2_cand = _extract_channel(data[off2:off2 + n_pts])  # Udtræk kandidat-CH2
                if raw2_cand.max() - raw2_cand.min() > 4:      # Mere end 4 counts swing = reelt signal
                    raw2 = raw2_cand                            # Acceptér CH2

            # Konverter ADC-counts til scope-divisioner (25 counts = 1 V/div)
            self.ch1_voltage = raw1 / 25.0                     # CH1-spænding i scope-divisioner
            self.ch1_active  = True                            # CH1 er altid aktiv i en WFM-fil

            if raw2 is not None:                               # Kun hvis CH2 var aktiv
                n = len(raw1)                                  # Referencelangde = CH1-laengde
                v2 = raw2 / 25.0                               # CH2-spænding i scope-divisioner
                # Sikr at CH2 har samme laengde som CH1 ved padding eller trimning
                self.ch2_voltage = (np.pad(v2, (0, n - len(v2)))  # Pad med nuller hvis CH2 er kortere
                                    if len(v2) < n else v2[:n])    # Trim hvis CH2 er laengere
                self.ch2_active  = True                        # Markér CH2 som aktiv

            self.dt          = float(dt_ch)                    # Gem per-kanal tidstrin
            self.sample_rate = 1.0 / dt_ch                     # Beregn samplehastighed fra dt
            self.time        = np.arange(len(self.ch1_voltage)) * dt_ch  # Konstruér tidsvektor
            self.filename    = os.path.basename(path)          # Gem filnavn uden sti
            return True                                         # WFM indlaest korrekt

        except Exception as e:
            print(f"WFM load error: {e}")                      # Log fejl til konsol
            return False                                        # Returner fejl


# ─────────────────────────────────────────────────────────────────────────────
#  SIGNAL ANALYSIS ENGINE
#  SignalAnalyzer modtager et spændingsarray og dt, og beregner alle elektriske
#  maaleparametre. 8-bit ADC-kompensation udføres automatisk ved oprettelse.
# ─────────────────────────────────────────────────────────────────────────────

# Klasse der udfører alle signalanalyser for ét kanalarray
class SignalAnalyzer:
    """Matematisk signalanalyse med 8-bit ADC-kompensation"""

    # Konstruktoer: modtager rå spændingsarray og tidstrin, anvender kompensation
    def __init__(self, voltage: np.ndarray, dt: float):
        self.raw = voltage.copy()    # Gem kopi af rådata uforandret
        self.dt = dt                 # Tidstrin i sekunder mellem samples
        self.fs = 1.0 / dt           # Samplehastighed i Hz (fs = 1/dt)
        self._apply_compensation()   # Udfør Savitzky-Golay-udjævning med det samme

    # Anvender Savitzky-Golay-filter for at reducere kvantiseringsstøj fra 8-bit ADC
    def _apply_compensation(self):
        """Anvender Savitzky-Golay-udjævning for at reducere 8-bit kvantiseringsstøj.
        Savitzky-Golay bevarer signalets form (Vp, Vpp) bedre end et simpelt glidende
        gennemsnit, fordi det tilpasser et polynomium lokalt i stedet for at middele.
        """
        from scipy.signal import savgol_filter, butter, filtfilt  # Importér filterbibliotek

        n = len(self.raw)                                          # Antal samples i signalet
        # Beregn vindueslængde: brug 11 samples hvis muligt, men aldrig mere end signallaengden.
        # Vinduet skal vaere ulige for Savitzky-Golay.
        win = min(11, n if n % 2 == 1 else n - 1)                 # Ulige vinduslængde ≤ 11

        if win >= 5:                                               # Minimum 5 samples for at filter giver mening
            try:
                # Savitzky-Golay med polynomiegrad 3: god form-bevarelse for sinusbølger
                self.signal = savgol_filter(self.raw, window_length=win, polyorder=3)
            except Exception:
                self.signal = self.raw.copy()                      # Fallback: brug rådata ved fejl
        else:
            self.signal = self.raw.copy()                          # For korte signaler: ingen udjævning

        # Beregn og fjern DC-offset saa AC-analyser arbejder om nul
        self.dc_offset = float(np.mean(self.signal))               # DC-niveau = gennemsnit af signalet
        self.signal_ac = self.signal - self.dc_offset              # AC-signal = signal minus DC

    # Finder tidspunkter for stigende nulgennemgange med hysteresebaand
    def _zero_crossings(self, signal=None):
        """Finder stigende nul-gennemgange med ±5% Vpp hysteresebaand.

        Hysteresen undgår at støjspidser nær nul tælles som falske gennemgange.
        Kun stigende gennemgange tælles (negativt → positivt), fordi ét sæt er
        nok til at bestemme perioden, og to sæt (stigning + fald) kan give 2×
        for-høj frekvens for asymmetriske bølgeformer.

        Returnerer liste af tidspunkter (sekunder) med sub-sample-præcision
        via lineær interpolation til nøjagtighed bedre end ét sample.
        """
        s    = signal if signal is not None else self.signal_ac   # Brug AC-signal som standard
        vpp  = float(np.max(s) - np.min(s))                       # Peak-to-peak af signalet
        hyst = vpp * 0.05                                          # Hysteresebaand = 5% af Vpp

        crossings    = []                                          # Liste til gennemgangstidspunkter
        was_negative = bool(s[0] < -hyst)                         # Startstate: er signal under -hyst?

        for i in range(1, len(s)):
            if was_negative and s[i] > hyst:
                # Signal krydser opad fra under -hyst til over +hyst → stigende gennemgang
                # Interpolér præcist tidspunkt for gennemgang ved threshold=+hyst
                frac = ((hyst - s[i-1]) / (s[i] - s[i-1])        # Brøkdel af sample-interval
                        if s[i] != s[i-1] else 0.0)               # Undgå division med nul
                crossings.append((i - 1 + frac) * self.dt)        # Præcist tidspunkt i sekunder
                was_negative = False                               # Nu er signal positivt
            elif s[i] < -hyst:
                was_negative = True                                # Signal er igen tydeligt negativt

        return crossings                                           # Returner liste af gennemgangstider

    # Beregner frekvens med høj præcision ved at kombinere FFT og nulgennemgange
    def frequency(self) -> float | None:
        """Beregner frekvens med høj præcision.

        Primær metode: zero-paddet Blackman FFT med parabolsk interpolation.
          Zero-padding øger FFT-opløsningen saa binbredden er f0/100, dvs.
          ~10 mHz opløsning for et 1 kHz signal fra en 10 ms optagelse.
          Parabolsk interpolation paa de 3 bins rundt om toppen giver
          sub-bin nøjagtighed uden ekstra beregning.

        Verifikation: hysteresenulgennemgang giver et uafhængiigt skøn.
          Hvis de to metoder er enige inden for 5%: brug FFT (mere præcis).
          Hvis de er uenige: brug nulgennemgang (mere robust mod harmoniske).
        """
        # ── Trin 1: nulgennemgangs-estimat ───────────────────────────────────
        zc = self._zero_crossings()                                # Find alle stigende nulgennemgange
        f_zc: float | None = None                                  # Standard: ingen ZC-frekvens endnu
        if len(zc) >= 2:                                           # Behøver mindst 2 gennemgange for periode
            periods = np.diff(zc)                                  # Tidsforskelle = perioder
            T_zc = float(np.median(periods))                       # Median-periode (robust mod outliers)
            if T_zc > 0:                                           # Undgå division med nul
                f_zc = 1.0 / T_zc                                  # Frekvens = 1 / periode

        # ── Trin 2: FFT-estimat ───────────────────────────────────────────────
        f_fft = self._frequency_fft(hint=f_zc)                    # Beregn FFT-frekvens, brug ZC som hint

        # ── Trin 3: Afgør hvilken der er bedst ───────────────────────────────
        if f_fft is not None and f_zc is not None:                 # Begge estimater tilgaengelige
            if abs(f_fft - f_zc) / f_zc < 0.05:                   # Enige inden for 5%?
                return f_fft                                        # Ja: brug FFT (mere præcis)
            else:
                return f_zc                                         # Uenige: brug ZC (mere robust)
        return f_fft or f_zc                                       # Returner hvad der er tilgængeligt

    # Beregner frekvens via zero-paddet FFT med parabolsk interpolation
    def _frequency_fft(self, hint: float | None = None) -> float | None:
        """Zero-paddet Blackman FFT med parabolsk interpolation.

        Zero-padding: signalets laengde øges til nfft saa binbredden df = fs/nfft
        er mindst f_hint/100. For f_hint=1000 Hz og fs=1 MSa/s giver det
        nfft = 100 * 1e6/1000 = 100 000 → nfft = 131072 (næste 2^n).
        Binbredde df = 1e6/131072 ≈ 7.6 Hz → ved 1 kHz: ~130 bins per periode.
        Parabolsk interpolation giver yderligere ~10× præcisionsforøgelse.
        """
        n = len(self.signal_ac)                                    # Antal AC-signal-samples
        if n < 4:                                                  # For kortе signaler giver FFT ingen mening
            return None

        # Beregn nødvendig FFT-størrelse for ønsket frekvensopløsning
        if hint and hint > 0:                                      # Brug ZC-estimat som hint hvis tilgængeligt
            target_df = hint / 100.0                               # Ønsket binbredde = f/100
        else:
            target_df = self.fs / 10000.0                          # Fallback: mindst 10000 bins i alt

        nfft_min = int(np.ceil(self.fs / target_df))              # Mindste nfft for ønsket opløsning
        nfft = max(n, nfft_min, 8192)                             # Brug minimum 8192 bins
        nfft = 2 ** int(np.ceil(np.log2(nfft)))                   # Rund op til nærmeste 2^n (FFT er hurtigst)

        window = np.blackman(n)                                    # Blackman-vindue: god dynamikrange, lav leakage
        padded = np.zeros(nfft)                                    # Allokér nul-paddet buffer
        padded[:n] = self.signal_ac * window                      # Kopier vinduet signal ind i bufferen
        spectrum = np.abs(np.fft.rfft(padded))                    # Halvsidet amplitudespektrum (kun positive frekvenser)
        freqs    = np.fft.rfftfreq(nfft, d=self.dt)               # Frekvensvektor tilhørende spektret
        df       = freqs[1]                                        # Binbredde = fs/nfft

        if len(spectrum) < 3:                                      # For kort til interpolation
            return None

        # Find spektraltoppen (spring DC-bin 0 over da den er offset-relateret)
        k = int(np.argmax(spectrum[1:])) + 1                      # Indeks for maksimum-bin (ekskl. DC)
        if k < 1 or k >= len(spectrum) - 1:                       # Randtilfaelde: kan ikke interpolere
            return float(freqs[k]) if k < len(freqs) else None    # Returner blot bin-frekvensen

        # Parabolsk interpolation på amplituden rundt om toppen
        # Formlen er: korrekt_bin = k + 0.5*(a-c)/(a-2b+c)
        # hvor a=spektrum[k-1], b=spektrum[k], c=spektrum[k+1]
        a = spectrum[k - 1]                                        # Amplitudebiin til venstre for top
        b = spectrum[k]                                            # Amplitudebin ved top
        c = spectrum[k + 1]                                        # Amplitudebin til hojre for top
        denom = a - 2.0 * b + c                                    # Nævner i interpolationsformlen
        p = 0.5 * (a - c) / denom if denom != 0 else 0.0          # Korrektion i bin-enheder
        p = float(np.clip(p, -0.5, 0.5))                          # Begræns korrektionen til ±0.5 bin

        freq = (k + p) * df                                        # Interpoleret frekvens i Hz
        return float(freq) if freq > 0 else None                   # Returner positiv frekvens

    # Beregner peak-spænding (maksimalt absolut vaerdi)
    def vp(self) -> float:
        """Peak-spænding = største absolutte øjebliksvaerdi i signalet."""
        return float(np.max(np.abs(self.signal)))                  # Max af |signal|

    # Beregner peak-to-peak spænding
    def vpp(self) -> float:
        """Peak-to-peak spænding = forskel mellem maksimum og minimum."""
        return float(np.max(self.signal) - np.min(self.signal))    # Max minus min

    # Beregner sand RMS-spænding over et helt antal perioder
    def vrms(self) -> float:
        """Sand RMS integreret over et præcist antal perioder.

        At integrere over et helt antal perioder (i stedet for hele bufferen)
        undgår fejl ved ufuldstændige perioder i bufferenden, som kan give
        op til ±3% fejl paa Vrms for lave frekvenser.
        """
        freq = self.frequency()                                    # Bestem signalets frekvens
        if freq and freq > 0:                                      # Kun hvis frekvens er gyldig
            T = 1.0 / freq                                         # Periodetid i sekunder
            n_periods = int(len(self.signal) * self.dt / T)        # Heltalsdel af antal perioder i bufferen
            if n_periods >= 1:                                     # Mindst én hel periode
                n_samples = int(round(n_periods * T / self.dt))    # Nøjagtigt antal samples for hele perioder
                n_samples = min(n_samples, len(self.signal))       # Overskrid ikke bufferlængden
                return float(np.sqrt(np.mean(self.signal[:n_samples]**2)))  # RMS = sqrt(mean(x²))
        # Fallback: brug hele bufferen
        return float(np.sqrt(np.mean(self.signal**2)))             # RMS over alle samples

    # Beregner 10%→90% stigetid
    def risetime(self) -> float | None:
        """10%→90% stigetid: tid fra 10% til 90% af signalets svingning.

        Niveauerne er 10% og 90% af svingningen (max-min), ikke absolutte vaerdier,
        saa metoden er uafhaengig af DC-offset og skalering.
        Returnerer None hvis der ikke kan findes baade t10 og t90.
        """
        vmin = np.min(self.signal)                                 # Minimum af signalet
        vmax = np.max(self.signal)                                 # Maksimum af signalet
        v10 = vmin + 0.1 * (vmax - vmin)                          # 10%-niveauet
        v90 = vmin + 0.9 * (vmax - vmin)                          # 90%-niveauet
        t10, t90 = None, None                                      # Initialisér tidspunkter til None

        for i in range(1, len(self.signal)):
            # Find foerste tidspunkt signal stiger forbi 10%-niveauet
            if self.signal[i-1] < v10 <= self.signal[i] and t10 is None:
                frac = (v10 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])  # Interpolationsbrøk
                t10 = (i - 1 + frac) * self.dt                    # Præcist tidspunkt for 10%-krydsning
            # Find foerste tidspunkt signal stiger forbi 90%-niveauet (efter t10)
            if t10 is not None and self.signal[i-1] < v90 <= self.signal[i] and t90 is None:
                frac = (v90 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])  # Interpolationsbrøk
                t90 = (i - 1 + frac) * self.dt                    # Præcist tidspunkt for 90%-krydsning
                break                                               # Stop søgning efter første komplette stigetid

        if t10 is not None and t90 is not None:                    # Begge tidspunkter fundet?
            return t90 - t10                                        # Stigetid = t90 minus t10
        return None                                                 # Ufuldstændig: returner None

    # Beregner 90%→10% faldtid
    def falltime(self) -> float | None:
        """90%→10% faldtid: tid fra 90% til 10% af signalets svingning under fald.

        Samme princip som risetime() men for det faldende flanke.
        Returnerer None hvis der ikke kan findes baade t90 og t10.
        """
        vmin = np.min(self.signal)                                 # Minimum
        vmax = np.max(self.signal)                                 # Maksimum
        v10 = vmin + 0.1 * (vmax - vmin)                          # 10%-niveau
        v90 = vmin + 0.9 * (vmax - vmin)                          # 90%-niveau
        t90, t10 = None, None                                      # Initialisér tidspunkter

        for i in range(1, len(self.signal)):
            # Find foerste faldende krydsning af 90%-niveauet
            if self.signal[i-1] > v90 >= self.signal[i] and t90 is None:
                frac = (v90 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])
                t90 = (i - 1 + frac) * self.dt                    # Tidspunkt for 90%-krydsning
            # Find foerste faldende krydsning af 10%-niveauet (efter t90)
            if t90 is not None and self.signal[i-1] > v10 >= self.signal[i] and t10 is None:
                frac = (v10 - self.signal[i-1]) / (self.signal[i] - self.signal[i-1])
                t10 = (i - 1 + frac) * self.dt                    # Tidspunkt for 10%-krydsning
                break

        if t90 is not None and t10 is not None:
            return t10 - t90                                        # Faldtid = t10 minus t90 (positiv vaerdi)
        return None

    # Beregner duty cycle som procentdel over 50%-threshold
    def dutycycle(self) -> float | None:
        """Duty cycle = procentdel af tid signalet er over midtniveauet.

        Midtniveauet er midtpunktet i svingningen (max+min)/2, ikke nødvendigvis 0V.
        """
        vth = (np.max(self.signal) + np.min(self.signal)) / 2.0   # Threshold = midtpunkt af svingning
        high_samples = np.sum(self.signal > vth)                   # Antal samples over threshold
        return float(high_samples) / len(self.signal) * 100.0     # Procentdel af tid over threshold

    # Beregner crest factor
    def crest_factor(self) -> float:
        """Crest factor = Vpeak / Vrms.

        Crest factor er 1.414 for en sinusbølge, 1.0 for et fuldent DC-signal
        og højere for pulsede signaler med korte kraftige toppe.
        """
        rms = self.vrms()                                          # Beregn RMS-vaerdien
        return self.vp() / rms if rms > 1e-12 else float('inf')   # Vp/Vrms (undgaa division med nul)

    # Beregner form factor
    def form_factor(self) -> float:
        """Form factor = Vrms / |Vgns_ligerettet|.

        Form factor er π/(2√2) ≈ 1.111 for en sinusbølge,
        1.0 for et DC-signal, og lavere for firkantbølger.
        """
        rectified = np.abs(self.signal)                            # Ligerettet signal = |signal|
        vavg = float(np.mean(rectified))                           # Gennemsnit af det ligerettede signal
        return self.vrms() / vavg if vavg > 1e-12 else float('inf')  # Vrms / Vavg_rect

    # Beregner FFT-spektrum i dBV med Blackman-vindue og zero-padding
    def fft_spectrum(self, n_harmonics: int = 40):
        """Beregner FFT-amplitudespektrum i dBV.

        Blackman-vinduet anvendes for at reducere spectral leakage.
        Zero-padding til næste 2^n giver glattere spektrum-visning.
        Amplitudekorrigering for Blackman-vinduet: faktor 1/(n*0.42).

        Returnerer tuple (frekvenser, magnituder_i_dBV) begge som numpy-arrays.
        """
        n = len(self.signal_ac)                                    # Antal AC-signal-samples
        nfft = max(n, 4096)                                        # Minimum 4096 bins
        nfft = 2 ** int(np.ceil(np.log2(nfft)))                   # Rund op til 2^n for FFT-effektivitet
        window = np.blackman(n)                                    # Blackman-vindue-koefficienter
        padded = np.zeros(nfft)                                    # Zero-paddet buffer
        padded[:n] = self.signal_ac * window                      # Anvend vindue og kopier signal
        spectrum = np.fft.rfft(padded)                             # Halvsidet kompleks FFT
        freqs = np.fft.rfftfreq(nfft, d=self.dt)                  # Tilsvarende frekvensvektor
        mag = np.abs(spectrum) * 2.0 / (n * 0.42)                 # Amplitudekorrektion for Blackman-vindue
        mag_db = 20 * np.log10(np.maximum(mag, 1e-12))            # Konverter til dBV (undgaa log(0))
        return freqs, mag_db                                       # Returner frekvens- og dBV-arrays

    # Returnerer liste af (frekvens, dBV) for fundamental og de foerste n_harmonics harmoniske
    def harmonics(self, n_harmonics: int = 40):
        """Finder frekvens og amplitude for fundamental og de foerste n harmoniske.

        For hver harmonisk h = 1, 2, ..., n_harmonics beregnes:
          - forventet frekvens: h × f0
          - naermeste FFT-bin hertil
          - amplituden af denne bin i dBV

        Stopper hvis harmonisk frekvens overstiger Nyquist-grænsen (fs/2).
        Returnerer liste af (frekvens_Hz, amplitude_dBV) tupler.
        """
        freq = self.frequency()                                    # Grundtone-frekvens
        if freq is None or freq <= 0:                              # Ingen gyldig frekvens → ingen harmoniske
            return []
        freqs, mag_db = self.fft_spectrum()                        # Beregn fuldt spektrum
        results = []                                               # Tom resultatliste
        for h in range(1, n_harmonics + 1):                        # Gennemgaa harmoniske 1..n
            target = freq * h                                      # Forventet frekvens for h'te harmoniske
            if target > self.fs / 2:                               # Over Nyquist-grænsen?
                break                                               # Stop — ingen mening over Nyquist
            idx = np.argmin(np.abs(freqs - target))                # Find naermeste FFT-bin
            results.append((freqs[idx], mag_db[idx]))              # Tilføj (frekvens, amplitude) til resultat
        return results                                             # Returner liste af harmoniske

    # Beregner spektrale effekter for fundamental, harmoniske og støj
    def _spectral_powers(self):
        """Beregner lineaer effekt for fundamental, harmoniske og støj separat.

        Bruger Blackman-vindue FFT med adaptiv zero-padding saa harmonic
        bin-vinduer aldrig overlapper (mindst 5× bin-afstand kræves).

        Returnerer tuple: (P_fundamental, P_harmonics, P_noise, P_total_ac)
        alle i lineaere effektenheder (amplitude²).
        Returnerer None hvis frekvens ikke kan bestemmes.
        """
        freq = self.frequency()                                    # Grundtone-frekvens
        if freq is None or freq <= 0:                              # Ingen gyldig frekvens
            return None

        n = len(self.signal_ac)                                    # Antal samples

        # Beregn nødvendig FFT-størrelse saa bin-vinduer ikke overlapper.
        # Ønsket: afstand mellem harmoniske-bins (= freq/df bins) er > 2*half_width+3.
        # Med half_width=3 kræver vi spacing > 7 bins → df < freq/7 → nfft > 7*fs/freq.
        # Brug faktor 8 for lidt ekstra margin.
        min_nfft = int(np.ceil(8 * self.fs / freq))               # Mindste nfft for ikke-overlappende vinduer
        nfft = max(n, min_nfft, 8192)                             # Brug mindst 8192
        nfft = 2 ** int(np.ceil(np.log2(nfft)))                   # Rund op til 2^n

        window = np.blackman(n)                                    # Blackman-vindue
        padded = np.zeros(nfft)                                    # Zero-paddet buffer
        padded[:n] = self.signal_ac * window                      # Anvend vindue
        spectrum = np.abs(np.fft.rfft(padded)) ** 2               # Effektspektrum = |FFT|²
        freqs    = np.fft.rfftfreq(nfft, d=self.dt)               # Frekvensvektor
        df       = self.fs / nfft                                  # Binbredde

        # Adaptiv bin-halv-bredde: brug max 3, men aldrig saa bred at vinduer overlapper
        harmonic_spacing_bins = freq / df                          # Afstand mellem harmoniske i bin-enheder
        half_width = max(1, min(3, int(harmonic_spacing_bins / 2) - 1))  # Halvbredde: 1..3 bins

        # Opbyg boolsk maske over alle bins der tilhører harmoniske
        harmonic_mask = np.zeros(len(spectrum), dtype=bool)        # Startvaerdi: ingen bins markeret
        fund_bin = None                                            # Fundamental-bin-interval kendes endnu ikke

        for h in range(1, 41):                                     # Gennemgaa harmoniske 1..40
            f_h = freq * h                                         # Forventet frekvens for h'te harmoniske
            if f_h > self.fs / 2 * 0.98:                          # Stop nær Nyquist (2% margin)
                break
            centre = int(round(f_h / df))                          # Central bin for denne harmoniske
            lo = max(1, centre - half_width)                       # Nedre bin-grænse (min 1 for at undgaa DC)
            hi = min(len(spectrum) - 1, centre + half_width)      # Øvre bin-grænse
            harmonic_mask[lo:hi + 1] = True                        # Markér disse bins som harmoniske
            if h == 1:                                             # Gem fundamental-bin-interval
                fund_bin = (lo, hi)                                # Bruges til P_fund beregning

        # Summér effekt i de relevante bins
        P_fund = float(np.sum(spectrum[fund_bin[0]:fund_bin[1] + 1])) if fund_bin else 0.0  # Fundamental-effekt
        P_harm = float(np.sum(spectrum[harmonic_mask])) - P_fund   # Harmonisk-effekt = alle harm. minus fund.
        noise_mask    = ~harmonic_mask                             # Støj-bins = alt der IKKE er harmonisk
        noise_mask[0] = False                                       # Ekskludér DC-bin (bin 0) fra støj
        P_noise = float(np.sum(spectrum[noise_mask]))              # Total støjeffekt

        return P_fund, P_harm, P_noise, P_fund + P_harm + P_noise  # Returner fire effektvaerdier

    # Beregner Total Harmonic Distortion i procent og dB
    def thd(self) -> dict | None:
        """THD (Total Harmonic Distortion).

        THD = sqrt(P_H2 + P_H3 + ... + P_H40) / sqrt(P_H1)

        Udtrykkes som procent og dB.
        THD < 1% er lavt, > 10% er kraftig forvrengning.
        Kan overstige 100% for meget forvrengede signaler (fx firkantbølger).
        Returnerer dict med 'thd_pct' og 'thd_db', eller None ved fejl.
        """
        res = self._spectral_powers()                              # Hent effektfordelingen
        if res is None:                                            # Ingen gyldig spektralanalyse
            return None
        P_fund, P_harm, P_noise, _ = res                          # Udpak de fire effektvaerdier
        if P_fund <= 0:                                            # Ingen fundamental-effekt → kan ikke beregne
            return None
        thd_ratio = np.sqrt(max(P_harm, 0.0) / P_fund)           # THD-ratio = sqrt(P_harm/P_fund)
        thd_pct = thd_ratio * 100.0                               # Konverter til procent
        thd_db  = 20.0 * np.log10(thd_ratio) if thd_ratio > 0 else -120.0  # Konverter til dB
        return {'thd_pct': float(thd_pct), 'thd_db': float(thd_db)}  # Returner som dict

    # Beregner Signal-to-Noise Ratio i dB
    def snr(self) -> float | None:
        """SNR (Signal-to-Noise Ratio) i dB.

        SNR = 10 × log10(P_fundamental / P_noise)

        Kun fundamental tælles som signal; alle ikke-harmoniske bins er støj.
        For Rigol DS1052E (8-bit): typisk 38-42 dB.
        Returnerer None ved fejl.
        """
        res = self._spectral_powers()                              # Hent effektfordelingen
        if res is None:                                            # Ingen gyldig spektralanalyse
            return None
        P_fund, P_harm, P_noise, _ = res                          # Udpak effektvaerdier
        if P_noise <= 0 or P_fund <= 0:                           # Ugyldige vaerdier
            return None
        return float(10.0 * np.log10(P_fund / P_noise))           # SNR = 10*log10(signal/støj)

    # Beregner SINAD i dB
    def sinad(self) -> float | None:
        """SINAD (Signal-to-Noise-And-Distortion) i dB.

        SINAD = 10 × log10(P_fundamental / (P_noise + P_harmonics))

        Anderledes end SNR: harmonisk forvrengning tæller med som uønsket.
        SINAD er den vigtigste enkelttal-parameter for ADC-kvalitet.
        Returnerer None ved fejl.
        """
        res = self._spectral_powers()                              # Hent effektfordelingen
        if res is None:                                            # Ingen gyldig spektralanalyse
            return None
        P_fund, P_harm, P_noise, _ = res                          # Udpak effektvaerdier
        denom = P_harm + P_noise                                   # Naevner = støj + forvrengning
        if denom <= 0 or P_fund <= 0:                             # Undgaa division med nul
            return None
        return float(10.0 * np.log10(P_fund / denom))             # SINAD = 10*log10(fund/(harm+noise))

    # Beregner Effective Number of Bits
    def enob(self) -> float | None:
        """ENOB (Effective Number of Bits).

        ENOB = (SINAD_dB - 1.76) / 6.02

        Fortolkning: en ideel n-bit ADC har SINAD = 6.02n + 1.76 dB.
        Rigol DS1052E (8-bit nominal) giver typisk ENOB ≈ 6-7 bits
        pga. analog støj og ADC-ikke-linearitet.
        Returnerer None ved fejl.
        """
        s = self.sinad()                                           # Hent SINAD-vaerdien
        if s is None:                                              # Ingen gyldig SINAD
            return None
        return float((s - 1.76) / 6.02)                           # ENOB-formel fra IEEE 1241


# Beregner fasedrejning i grader mellem to kanaler via krydskorrelation
def phase_difference(sig1: SignalAnalyzer, sig2: SignalAnalyzer) -> float | None:
    """Fasedrejning fra CH1 til CH2 i grader via FFT-krydskorrelation.

    Krydskorrelation i frekvensdomænet (via FFT) er hurtigere end i tidsdomænet
    og giver den samme resultat. Lagget konverteres til grader via:
      fase = (lag × dt / T) × 360°

    Normalisering til [-180°, 180°] sikrer at resultatet er intuitivt:
    positiv vaerdi = CH2 efterslæber CH1, negativ = CH2 forudlober CH1.
    Returnerer None hvis signalet er for kort eller frekvens ikke kan bestemmes.
    """
    n = min(len(sig1.signal_ac), len(sig2.signal_ac))             # Brug den korteste laengde
    if n < 4:                                                      # For kort til krydskorrelation
        return None

    # Normaliser begge signaler til enhedsvariance for at fjerne amplitudeforskelle
    s1 = sig1.signal_ac[:n]                                        # CH1 AC-signal, trimmet til n
    s2 = sig2.signal_ac[:n]                                        # CH2 AC-signal, trimmet til n
    s1n = s1 / (np.std(s1) + 1e-12)                               # Normalisér CH1 (undgaa /0)
    s2n = s2 / (np.std(s2) + 1e-12)                               # Normalisér CH2 (undgaa /0)

    # Beregn krydskorrelation i frekvensdomænet: XCorr(s1,s2) = IFFT(FFT(s1) × conj(FFT(s2)))
    corr = np.fft.irfft(np.fft.rfft(s1n) * np.conj(np.fft.rfft(s2n)))  # Cirkulær krydskorrelation
    lag = int(np.argmax(np.abs(corr)))                             # Sample-lag ved maksimal korrelation
    if lag > n // 2:                                               # Wrap-around korrektion:
        lag -= n                                                   # Negative lags er kodet som store positive tal

    # Konverter sample-lag til fasedrejning i grader
    freq = sig1.frequency()                                        # Grundtonefrekvens fra CH1
    if freq is None or freq <= 0:                                  # Ingen gyldig frekvens
        return None
    T = 1.0 / freq                                                 # Periodetid
    phase_deg = (lag * sig1.dt / T) * 360.0                       # Fase = (lag/periode) × 360°

    # Normaliser til [-180°, 180°] saa resultatet altid er i standardintervallet
    phase_deg = ((phase_deg + 180) % 360) - 180                   # Normaliseringsformel
    return float(phase_deg)                                        # Returner fasedrejning i grader


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1: MEASUREMENTS
#  Viser en tabel med alle elektriske maaleparametre for begge kanaler
#  samt signalrelationer (fase, foerstaerkning) naar frekvenserne matcher.
# ─────────────────────────────────────────────────────────────────────────────

# Widget der udgør "MEASUREMENTS"-fanen med to kanalgrupper og en relationsgruppe
class MeasurementWidget(QWidget):

    # Konstruktoer: bygger UI-strukturen
    def __init__(self):
        super().__init__()                                         # Initialiser basisklassen QWidget
        self._build_ui()                                           # Byg alle widgets

    # Opbygger hele maalevisningens layout
    def _build_ui(self):
        layout = QHBoxLayout(self)                                 # Vandret layout: CH1 | CH2 | Relationer
        layout.setSpacing(12)                                      # 12 pixels mellemrum mellem grupper
        layout.setContentsMargins(12, 12, 12, 12)                  # 12 pixels margen paa alle sider

        # Opret en maalegruppebeoks for kanal 1 (gul farve)
        self.ch1_group = self._channel_group("CH1", "#f7cc52")    # Gul farve for CH1
        # Opret en maalegruppebeoks for kanal 2 (cyan farve)
        self.ch2_group = self._channel_group("CH2", "#5af0e0")    # Cyan farve for CH2

        # Opret signalrelations-gruppebeoks (maks 280 pixels bred)
        self.rel_group = QGroupBox("SIGNAL RELATIONS")             # Ramme med titel
        self.rel_group.setMaximumWidth(280)                        # Begraens bredde
        rel_layout = QVBoxLayout(self.rel_group)                   # Lodret layout inden i relationsgruppen
        self.rel_labels = {}                                       # Dict til at gemme vaerdi-labels

        # Opret en vaerdi-raekke for hvert relationsparameter
        for key in ["Frequency match", "Phase", "Av (CH2/CH1)", "AvdB"]:
            row = QHBoxLayout()                                    # Vandret layout: navn | vaerdi
            name_lbl = QLabel(key)                                 # Parameternavn til venstre
            name_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")  # Daemp parameternavnet
            val_lbl = QLabel("—")                                  # Vaerdi til hojre, startvaerdi "—"
            val_lbl.setStyleSheet("color: #f0f6fc; font-size: 13px; font-weight: bold;")  # Hvid fed vaerdi
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Hojrejuster vaerdien
            row.addWidget(name_lbl)                                # Tilføj navn til raekke
            row.addWidget(val_lbl)                                 # Tilføj vaerdi til raekke
            rel_layout.addLayout(row)                              # Tilføj raekken til relationslayout
            self.rel_labels[key] = val_lbl                         # Gem label-reference i dict

        rel_layout.addStretch()                                    # Fyldplads under relationsparametrene

        # Tilføj alle tre grupper til hovedlayoutet
        layout.addWidget(self.ch1_group)                           # CH1-gruppe yderst til venstre
        layout.addWidget(self.ch2_group)                           # CH2-gruppe i midten
        layout.addWidget(self.rel_group)                           # Relationsgruppe yderst til hojre

    # Opretter en maalegruppebeoks for én kanal med alle parametre
    def _channel_group(self, name: str, color: str) -> QGroupBox:
        """Opretter en QGroupBox med et gitter af alle maaleparametre for én kanal.

        Hvert parameter vises som tre widgets i et gitter:
          kolonne 0: parameternavn (daemp graa)
          kolonne 1: maalte vaerdi (kanalfarve, fed)
          kolonne 2: enhed (meget daemp)

        color-strengen bruges baade til border og til vaerdi-tekst.
        """
        group = QGroupBox(name)                                    # Gruppebeoks med kanalnavnet som titel
        # Tilpas border-farve og titelfarve til kanalens farve
        group.setStyleSheet(f"""
            QGroupBox {{ border-color: {color}44; }}
            QGroupBox::title {{ color: {color}; }}
        """)                                                       # 44 = 27% alpha for daemp border

        grid = QGridLayout(group)                                  # Gitter-layout til parameterraekkerne
        grid.setSpacing(6)                                         # 6 pixels mellem raekker

        # Liste af (parameternavn, enhed) — None,None indsaetter en separator-linie
        metrics = [
            ("Vp",          "V"),        # Peak-spænding
            ("Vpp",         "V"),        # Peak-to-peak-spænding
            ("Vrms",        "V"),        # Sand RMS-spænding
            ("Frequency",   "Hz"),       # Fundamental-frekvens
            ("Rise time",   "s"),        # 10%→90% stigetid
            ("Fall time",   "s"),        # 90%→10% faldtid
            ("Duty cycle",  "%"),        # Procentdel over midtniveau
            ("Crest factor",""),         # Vp/Vrms (dimensionslos)
            ("Form factor", ""),         # Vrms/Vavg_rect (dimensionslos)
            (None, None),                # Visuel separator-linie
            ("THD",         "%"),        # Total Harmonic Distortion i procent
            ("THD",         "dB"),       # Total Harmonic Distortion i dB
            ("SNR",         "dB"),       # Signal-to-Noise Ratio
            ("SINAD",       "dB"),       # Signal-to-Noise-and-Distortion
            ("ENOB",        "bit"),      # Effective Number of Bits
        ]

        labels = {}                                                # Dict til label-referencer
        row_idx = 0                                                # Aktuel raekke i gitteret

        for (m, unit) in metrics:
            if m is None:
                # Indsaet en vandret separator-linie for at adskille maalegrupper visuelt
                sep = QFrame()                                     # Tom ramme
                sep.setFrameShape(QFrame.HLine)                   # Vandret linie
                sep.setStyleSheet("color: #21262d;")              # Moerk graa farve
                grid.addWidget(sep, row_idx, 0, 1, 3)             # Straekning over alle 3 kolonner
                row_idx += 1                                       # Naeste raekke
                continue                                           # Spring resten over for denne iteration

            # Unik noegel: "THD %" vs "THD dB" for at skelne de to THD-raekker
            key = f"{m} {unit}" if unit else m                    # F.eks. "THD %" eller "Crest factor"

            name_lbl = QLabel(m)                                   # Parameternavn-label
            name_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")  # Daemp parameternavn

            val_lbl = QLabel("—")                                  # Vaerdi-label, startvaerdi = ingen data
            val_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")  # Kanalfarve, fed
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Hojrejuster vaerdier

            unit_lbl = QLabel(unit)                                # Enheds-label
            unit_lbl.setStyleSheet("color: #484f58; font-size: 10px;")  # Meget daemp enhed

            # Tilføj alle tre labels til gitteret
            grid.addWidget(name_lbl, row_idx, 0)                   # Navn i kolonne 0
            grid.addWidget(val_lbl,  row_idx, 1)                   # Vaerdi i kolonne 1
            grid.addWidget(unit_lbl, row_idx, 2)                   # Enhed i kolonne 2
            labels[key] = val_lbl                                  # Gem vaerdi-label-reference
            row_idx += 1                                           # Naeste raekke

        group.setProperty("labels", labels)                        # Gem labels-dict som Qt-property paa gruppen
        return group                                               # Returner faerdig gruppebeoks

    # Opdaterer alle maalte vaerdier med data fra et OscilloscopeData-objekt
    def update_measurements(self, data: OscilloscopeData):
        """Analyserer begge aktive kanaler og opdaterer alle visningslabels.

        Indre funktion fmt() formaterer en float til eng-prefix-notation
        (k, m, µ, n) saa vaerdier altid passer i labels uanset stoerrelse.
        """

        # Indre hjælpefunktion: formaterer en float med passende SI-prefix
        def fmt(v, decimals=4):
            if v is None: return "—"                              # Ingen data → em-dash
            if abs(v) >= 1000: return f"{v/1000:.3f}k"           # Kilo (fx 1.234kHz)
            if abs(v) >= 1:    return f"{v:.{decimals}f}"        # Enheder (fx 3.1416V)
            if abs(v) >= 1e-3: return f"{v*1e3:.3f}m"            # Milli (fx 1.000ms)
            if abs(v) >= 1e-6: return f"{v*1e6:.3f}µ"            # Mikro (fx 1.000µs)
            if abs(v) >= 1e-9: return f"{v*1e9:.3f}n"            # Nano (fx 1.000ns)
            return f"{v:.4e}"                                      # Videnskabelig notation for meget sma vaerdier

        # Indre hjælpefunktion: analyserer én kanal og udfylder dens labels
        def fill_channel(group, voltage, dt):
            """Analyserer voltage-array og skriver resultater til labels i group."""
            labels = group.property("labels")                     # Hent labels-dict gemt paa gruppen
            if voltage is None:                                    # Kanalen har ingen data?
                for lbl in labels.values(): lbl.setText("—")      # Nulstil alle labels
                return None                                        # Ingen analysator at returnere

            ana = SignalAnalyzer(voltage, dt)                     # Opret analysator for denne kanal
            f = ana.frequency()                                    # Beregn fundamental-frekvens

            # Skriv maalte vaerdier til de tilsvarende labels
            labels["Vp V"].setText(fmt(ana.vp()))                 # Peak-spænding
            labels["Vpp V"].setText(fmt(ana.vpp()))               # Peak-to-peak
            labels["Vrms V"].setText(fmt(ana.vrms()))             # Sand RMS
            labels["Frequency Hz"].setText(fmt(f))                 # Frekvens
            labels["Rise time s"].setText(fmt(ana.risetime()))    # Stigetid
            labels["Fall time s"].setText(fmt(ana.falltime()))    # Faldtid
            dc = ana.dutycycle()                                   # Duty cycle
            labels["Duty cycle %"].setText(f"{dc:.1f}" if dc is not None else "—")  # 1 decimal
            labels["Crest factor"].setText(f"{ana.crest_factor():.3f}")  # 3 decimaler
            labels["Form factor"].setText(f"{ana.form_factor():.3f}")    # 3 decimaler

            # THD kræver speciel haandtering da den returnerer et dict (eller None)
            thd = ana.thd()
            if thd:                                                # Gyldig THD?
                labels["THD %"].setText(f"{thd['thd_pct']:.3f}")  # THD i procent
                labels["THD dB"].setText(f"{thd['thd_db']:.2f}")  # THD i dB
            else:
                labels["THD %"].setText("—")                       # Ingen data
                labels["THD dB"].setText("—")

            snr = ana.snr()                                        # Signal-to-Noise Ratio
            labels["SNR dB"].setText(f"{snr:.2f}" if snr is not None else "—")

            sinad = ana.sinad()                                    # Signal-to-Noise-and-Distortion
            labels["SINAD dB"].setText(f"{sinad:.2f}" if sinad is not None else "—")

            enob = ana.enob()                                      # Effective Number of Bits
            labels["ENOB bit"].setText(f"{enob:.2f}" if enob is not None else "—")

            return ana                                             # Returner analysatorobjektet til relationsberegning

        # Analysér begge kanaler (None voltage → kanal ikke aktiv)
        ana1 = fill_channel(
            self.ch1_group,
            data.ch1_voltage if data.ch1_active else None,        # CH1-data eller None
            data.dt                                                # Faelles tidstrin
        )
        ana2 = fill_channel(
            self.ch2_group,
            data.ch2_voltage if data.ch2_active else None,        # CH2-data eller None
            data.dt
        )

        # Beregn signalrelationer kun hvis begge kanaler er aktive
        if ana1 and ana2:
            f1 = ana1.frequency()                                  # CH1-frekvens
            f2 = ana2.frequency()                                  # CH2-frekvens
            if f1 and f2:                                          # Begge frekvenser gyldige?
                # Tjek frekvens-match: indenfor 0.1% = samme generator
                match = abs(f1 - f2) / max(f1, f2) <= 0.001       # Sand hvis frekvenserne matcher
                self.rel_labels["Frequency match"].setText("✓ YES" if match else "✗ NO")

                if match:                                          # Kun beregn fase/Av hvis samme frekvens
                    phase = phase_difference(ana1, ana2)           # Fasedrejning CH1→CH2 i grader
                    self.rel_labels["Phase"].setText(f"{phase:.2f}°" if phase is not None else "—")

                    av = ana2.vp() / ana1.vp() if ana1.vp() > 1e-9 else None  # Spændingsfoerstaerkning
                    if av is not None:
                        self.rel_labels["Av (CH2/CH1)"].setText(f"{av:.4f}")          # Linear foerstaerkning
                        self.rel_labels["AvdB"].setText(f"{20*np.log10(av):.2f} dB")  # Foerstaerkning i dB
                    else:
                        self.rel_labels["Av (CH2/CH1)"].setText("—")  # CH1 for lille til division
                        self.rel_labels["AvdB"].setText("—")
                else:
                    # Frekvenserne matcher ikke → fase og Av er meningslose
                    for key in ["Phase", "Av (CH2/CH1)", "AvdB"]:
                        self.rel_labels[key].setText("N/A")        # N/A = ikke applicable
            else:
                # Frekvens ikke tilgaengelig for mindst én kanal
                for key in self.rel_labels: self.rel_labels[key].setText("—")
        else:
            # Mindre end to aktive kanaler → ingen relationer at vise
            for key in self.rel_labels: self.rel_labels[key].setText("—")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2: OSCILLOSCOPE DISPLAY
#  Tegner bølgeformerne paa en sort skærm med gitter, zoom, pan og to cursorer.
# ─────────────────────────────────────────────────────────────────────────────

# Widget der tegner oscilloskopets bølgeform med 10×8 gitter og cursorer
class OscilloscopeScreen(QWidget):
    """Professionel oscilloskopbølgeform-visning med zoom og cursorer"""

    GRID_DIVS_H = 10   # Antal vandrette gitter-divisioner (standard = 10)
    GRID_DIVS_V = 8    # Antal lodrette gitter-divisioner (standard = 8)

    # Konstruktoer: initialiserer tilstand og farver
    def __init__(self):
        super().__init__()                                         # Initialiser QWidget basisklassen
        self.data: OscilloscopeData | None = None                  # Ingen data indlæst endnu
        self.x_offset = 0.0                                        # Panforskydning i sekunder (0 = start)
        self.x_scale = 1.0                                         # Zoomfaktor (1.0 = hel buffer vist)
        self.cursor_a: float | None = None                         # Cursor A tidspunkt i sekunder (None = ikke sat)
        self.cursor_b: float | None = None                         # Cursor B tidspunkt i sekunder (None = ikke sat)
        self.dragging_cursor = None                                # Holder styr paa hvilken cursor der traekkes
        self.setMinimumHeight(400)                                 # Mindst 400 pixels hojde
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Udvid for at fylde pladsen
        self.setMouseTracking(True)                                # Modtag mus-events ogsaa uden klik

        # Farvedefinitioner for alle grafikelementer
        self.ch1_color = QColor("#f7cc52")                         # Gul farve for CH1-bølgeform
        self.ch2_color = QColor("#5af0e0")                         # Cyan farve for CH2-bølgeform
        self.grid_color = QColor("#1c2128")                        # Meget moerk graa for sekundaere gitterlinjer
        self.grid_major_color = QColor("#21262d")                  # Lidt lysere for primaere gitterlinjer
        self.bg_color = QColor("#0a0e13")                          # Naesten sort baggrund

    # Indlaesser nye data og nulstiller zoom/pan/cursorer
    def set_data(self, data: OscilloscopeData):
        """Gemmer nyt OscilloscopeData-objekt og nulstiller visningsstate."""
        self.data = data                                           # Gem datareference
        self.x_offset = 0.0                                        # Nulstil pan til start af buffer
        self.x_scale = 1.0                                         # Nulstil zoom til hel buffer
        self.cursor_a = None                                       # Fjern cursor A
        self.cursor_b = None                                       # Fjern cursor B
        self.update()                                              # Tvang gentegning

    # Saetter zoomfaktor og begrænser til gyldigt interval
    def set_zoom(self, factor: float):
        """Saetter X-axis zoomfaktor. 1.0 = hel buffer. 10.0 = 1/10 af bufferen vist."""
        self.x_scale = max(0.1, min(100.0, factor))               # Begræns zoom til [0.1, 100]
        self.update()                                              # Gentegn

    # Saetter panforskydning ud fra procent (0..100)
    def set_pan(self, offset_pct: float):
        """Saetter panforskydning som procent (0=start, 100=slut).

        Maksimal panforskydning begrænses saa den synlige del aldrig gaar
        ud over bufferens ende.
        """
        if self.data and self.data.time is not None:
            total = float(self.data.time[-1] - self.data.time[0])  # Total bufferlaengde i sekunder
            visible = total / self.x_scale                          # Synlig tidslaengde ved nuvaerende zoom
            max_offset = total - visible                            # Maksimal forskydning inden for bufferen
            self.x_offset = offset_pct / 100.0 * max(0.0, max_offset)  # Sæt aktuel offset
        self.update()                                              # Gentegn

    # Hoved-tegningsmetode — kaldes af Qt ved behov for gentegning
    def paintEvent(self, event):
        """Tegner hele oscilloskopvisningen: baggrund, gitter, bølgeformer, cursorer og akselabler."""
        p = QPainter(self)                                         # Opret tegnerobjekt for denne widget
        p.setRenderHint(QPainter.Antialiasing, True)               # Glat anti-aliasing for skarpe linjer
        rect = self.rect()                                         # Hent widget-dimensioner
        w, h = rect.width(), rect.height()                         # Bredde og hojde i pixels

        # Definér marginer for at give plads til akselabler
        ml, mr, mt, mb = 60, 20, 20, 40                           # Venstre, hojre, top, bund margen i pixels

        # Beregn scopeskærmens aktive tegneeomraade inden for marginerne
        sx = ml                                                    # Skærm-X start (venstre kant)
        sy = mt                                                    # Skærm-Y start (top)
        sw = w - ml - mr                                           # Skærmbredde i pixels
        sh = h - mt - mb                                           # Skærmhojde i pixels

        # Tegn baggrund: hele widget hav sort, scopeskærmen lidt moerkere
        p.fillRect(rect, self.bg_color)                            # Hel widget: naesten sort
        p.fillRect(sx, sy, sw, sh, QColor("#070b0f"))              # Scopeskærm: endnu moerkere sort

        # Tegn gitter over skærmen
        self._draw_grid(p, sx, sy, sw, sh)

        # Hvis ingen data er indlæst: vis hjælpetekst og stop
        if self.data is None:
            p.setPen(QColor("#30363d"))                            # Moerk graa tekst
            p.setFont(QFont("Consolas", 14))                       # Stor skrift
            p.drawText(QRectF(sx, sy, sw, sh), Qt.AlignCenter,    # Centrér tekst
                       "No data loaded\nFile → Open (Ctrl+O)")
            return                                                  # Stop tegning her

        # Tegn bølgeform for kanal 1 hvis den er aktiv
        if self.data.ch1_active and self.data.ch1_voltage is not None:
            self._draw_waveform(p, self.data.time, self.data.ch1_voltage,
                                self.ch1_color, sx, sy, sw, sh, "CH1")

        # Tegn bølgeform for kanal 2 hvis den er aktiv
        if self.data.ch2_active and self.data.ch2_voltage is not None:
            self._draw_waveform(p, self.data.time, self.data.ch2_voltage,
                                self.ch2_color, sx, sy, sw, sh, "CH2")

        # Tegn de to tidscursorer (A og B) med maalingsaflæsninger
        self._draw_cursors(p, sx, sy, sw, sh)

        # Tegn tidsaksens labler langs bundkanten
        self._draw_labels(p, sx, sy, sw, sh)

        # Tegn scopeskærmens kant-rektangel
        p.setPen(QPen(QColor("#30363d"), 1))                       # Moerk graa kant
        p.drawRect(sx, sy, sw, sh)                                 # Rektangulær kant

    # Tegner gitterlinjer og krydshaar i midten af skærmen
    def _draw_grid(self, p: QPainter, sx, sy, sw, sh):
        """Tegner 10×8 gitter med primaere (solide) og sekundaere (prikket) linjer,
        plus et lille krydshaar i skærmens midte som reference."""
        dh = sh / self.GRID_DIVS_V                                 # Pixels pr. lodret division
        dw = sw / self.GRID_DIVS_H                                 # Pixels pr. vandret division

        pen_major = QPen(self.grid_major_color, 1, Qt.SolidLine)   # Solid linie for primaere gridlinjer
        pen_minor = QPen(self.grid_color, 1, Qt.DotLine)           # Prikket linie for sekundaere gridlinjer

        # Tegn lodrette gitterlinjer (vaekker fra venstre mod hojre)
        for i in range(self.GRID_DIVS_H + 1):                     # 11 lodrette linjer for 10 divisioner
            x = sx + i * dw                                        # X-position for denne linje
            p.setPen(pen_major if i % 2 == 0 else pen_minor)       # Major linje for hvert 2. trin
            p.drawLine(int(x), sy, int(x), sy + sh)                # Lodret linje fra top til bund

        # Tegn vandrette gitterlinjer (fra top mod bund)
        for i in range(self.GRID_DIVS_V + 1):                     # 9 vandrette linjer for 8 divisioner
            y = sy + i * dh                                        # Y-position for denne linje
            p.setPen(pen_major if i % 2 == 0 else pen_minor)       # Major linje for hvert 2. trin
            p.drawLine(sx, int(y), sx + sw, int(y))                # Vandret linje fra venstre til hojre

        # Tegn et lille krydshaar præcist i skærmens midte som reference-nul
        cx = sx + sw // 2                                          # Centrum X-koordinat
        cy = sy + sh // 2                                          # Centrum Y-koordinat
        p.setPen(QPen(QColor("#2d3340"), 1))                       # Lidt lysere end gitteret
        p.drawLine(cx - 3, cy, cx + 3, cy)                        # Vandret del af krydshaar
        p.drawLine(cx, cy - 3, cx, cy + 3)                        # Lodret del af krydshaar

    # Tegner én kanal-bølgeform med korrekt tids- og spændingsskalering
    def _draw_waveform(self, p: QPainter, time, voltage, color, sx, sy, sw, sh, label):
        """Tegner en bølgeform paa scopeskærmen med zoom og pan.

        Kun samples inden for det synlige tidsvindue tegnes.
        For mange samples nedsamplez til 2×pixelbredde for ydeevne.
        Spændingsakseen skaleres automatisk til signalets fulde udsvingning +10% polstring.
        """
        if len(time) < 2:                                          # Behøver mindst 2 punkter for at tegne
            return

        t_total = float(time[-1] - time[0])                        # Total bufferlaengde i sekunder
        t_start = float(time[0]) + self.x_offset                   # Visning start: buffer-start + pan-offset
        t_range = t_total / self.x_scale                           # Synlig tidslaengde: total/zoom
        t_end = t_start + t_range                                  # Visning slut

        # Begræns visningsvinduet til bufferens grænser
        t_start = max(t_start, float(time[0]))                     # Aldrig foer buffer-start
        t_end = min(t_end, float(time[-1]))                        # Aldrig efter buffer-slut
        if t_end <= t_start:                                       # Tomt interval?
            return                                                  # Intet at tegne

        # Udvælg kun de samples der falder inden for det synlige tidsvindue
        mask = (time >= t_start) & (time <= t_end)                 # Boolsk maske for synlige samples
        t_vis = time[mask]                                         # Synlige tidspunkter
        v_vis = voltage[mask]                                      # Tilsvarende spændingsvaerdier
        if len(t_vis) < 2:                                         # For faa synlige punkter
            return                                                  # Intet at tegne

        # Beregn spændingsskalering ud fra HELE signalets udsvingning (ikke kun synlig del)
        v_min = float(np.min(voltage))                             # Global minimum-spænding
        v_max = float(np.max(voltage))                             # Global maksimum-spænding
        v_range = v_max - v_min                                    # Total spændingssvingning
        if v_range < 1e-12:                                        # DC-signal eller nul — undgaa division med 0
            v_range = 1.0                                          # Fallback: 1V range
        v_pad = v_range * 0.1                                      # 10% polstring over og under
        v_lo = v_min - v_pad                                       # Nedre grænse for spændingsaksen
        v_hi = v_max + v_pad                                       # Øvre grænse for spændingsaksen
        v_span = v_hi - v_lo                                       # Total spændingsafstand for skalering

        # Indre hjælpefunktion: konverterer (tid, spænding) til (screen_x, screen_y)
        def to_screen(t_val, v_val):
            px = sx + (t_val - t_start) / (t_end - t_start) * sw  # Lineaer tidskortlægning til pixels
            py = sy + sh - (v_val - v_lo) / v_span * sh            # Spænding kortlægning (Y er inverteret!)
            return px, py

        # Nedsampel hvis der er flere datapunkter end der er pixels at tegne i
        max_pts = sw * 2                                           # Maksimalt 2 punkter pr. skærmpixel
        if len(t_vis) > max_pts:                                   # For mange punkter?
            idx = np.round(np.linspace(0, len(t_vis) - 1, max_pts)).astype(int)  # Jaevnt fordelte indekser
            t_vis = t_vis[idx]                                     # Reducer til max_pts tidspunkter
            v_vis = v_vis[idx]                                     # Tilsvarende spændingsvaerdier

        # Byg en QPainterPath (forbundet polylinje) for effektiv tegning
        pen = QPen(color, 1.5)                                     # 1.5 pixels tyk linje i kanalfarven
        p.setPen(pen)
        path = QPainterPath()                                      # Tom vektorsti
        x0, y0 = to_screen(t_vis[0], v_vis[0])                    # Startpunkt
        path.moveTo(x0, y0)                                        # Flyt pen til startpunkt uden at tegne
        for i in range(1, len(t_vis)):                             # Forbind alle punkter med rette linjer
            xi, yi = to_screen(t_vis[i], v_vis[i])
            path.lineTo(xi, yi)                                    # Tilføj linjestykke til stien
        p.drawPath(path)                                           # Tegn hele stien i ét kald (hurtigt)

        # Tegn kanal-label og V/div-vaerdi øverst til venstre paa scopeskærmen
        p.setPen(color)                                            # Brug kanalfarven
        p.setFont(QFont("Consolas", 9, QFont.Bold))               # Fed monospace-skrift
        lx = sx + 6 + (0 if label == "CH1" else 60)              # CH1 yderst venstre, CH2 lidt til hojre
        scale_str = f"{v_range/8:.3g}V/div"                        # V/div = total svingning / 8 divisioner
        p.drawText(int(lx), sy + 14, f"{label}  {scale_str}")     # Tegn "CH1  1.23V/div"

    # Tegner de to tidscursorer med tidsmaalinger og delta-T
    def _draw_cursors(self, p: QPainter, sx, sy, sw, sh):
        """Tegner cursor A (rød) og cursor B (blaa) som stiplede lodrette linjer.

        Hvis begge cursorer er sat vises ΔT og den tilsvarende frekvens 1/ΔT
        øverst til hojre paa scopeskærmen.
        """
        if self.data is None: return                               # Ingen data → ingen cursorer
        t = self.data.time
        if t is None: return                                       # Ingen tidsvektor

        t_start = t[0] + self.x_offset                            # Synlig tidsstart
        t_range = (t[-1] - t[0]) / self.x_scale                   # Synlig tidslaengde

        # Indre hjælpefunktion: konverterer tidspunkt til skærm-X-koordinat
        def t_to_x(tc):
            return sx + (tc - t_start) / t_range * sw             # Lineaer kortlægning tid → pixels

        pen_a = QPen(QColor("#ff7b72"), 1, Qt.DashLine)            # Rød stiplet linje for cursor A
        pen_b = QPen(QColor("#a5d6ff"), 1, Qt.DashLine)            # Lysblaa stiplet linje for cursor B

        # Tegn cursor A hvis den er sat
        if self.cursor_a is not None:
            xa = t_to_x(self.cursor_a)                             # X-position for cursor A
            p.setPen(pen_a)                                        # Rød stiplet linje
            p.drawLine(int(xa), sy, int(xa), sy + sh)              # Lodret linje fra top til bund
            p.setFont(QFont("Consolas", 9))
            p.setPen(QColor("#ff7b72"))                             # Rød tekstfarve
            p.drawText(int(xa) + 3, sy + 14, f"A:{self._fmt_time(self.cursor_a)}")  # Tidsmaalingsaflæsning

        # Tegn cursor B hvis den er sat
        if self.cursor_b is not None:
            xb = t_to_x(self.cursor_b)                             # X-position for cursor B
            p.setPen(pen_b)                                        # Blaa stiplet linje
            p.drawLine(int(xb), sy, int(xb), sy + sh)              # Lodret linje
            p.setFont(QFont("Consolas", 9))
            p.setPen(QColor("#a5d6ff"))                             # Blaa tekstfarve
            p.drawText(int(xb) + 3, sy + 28, f"B:{self._fmt_time(self.cursor_b)}")  # Tidsmaalingsaflæsning

        # Vis ΔT og tilsvarende frekvens naar begge cursorer er aktive
        if self.cursor_a is not None and self.cursor_b is not None:
            dt = abs(self.cursor_b - self.cursor_a)               # Tidsafstand mellem cursorer
            p.setPen(QColor("#c9d1d9"))                            # Lys graa tekst
            p.setFont(QFont("Consolas", 9))
            info = f"ΔT:{self._fmt_time(dt)}  f:{self._fmt_freq(1/dt if dt > 0 else 0)}"  # Formel-streng
            p.drawText(sx + sw - 200, sy + 14, info)              # Placér øverst til hojre

    # Tegner tidsaksens labler langs bundkanten af scopeskærmen
    def _draw_labels(self, p: QPainter, sx, sy, sw, sh):
        """Tegner tidsvaerdier langs X-aksen ved hvert gitter-kryds."""
        if self.data is None: return                               # Ingen data
        t = self.data.time
        if t is None: return

        t_start = t[0] + self.x_offset                            # Synlig tidsstart
        t_range = (t[-1] - t[0]) / self.x_scale                   # Synlig tidslaengde

        p.setFont(QFont("Consolas", 9))                            # Lille monospace-skrift
        p.setPen(QColor("#484f58"))                                # Daemp graa farve

        # Tegn tidslabel ved hvert af de 11 lodrette gitter-kryds
        for i in range(self.GRID_DIVS_H + 1):
            tc = t_start + i / self.GRID_DIVS_H * t_range         # Tidspunkt for dette kryds
            x = sx + i * sw / self.GRID_DIVS_H                    # X-koordinat for dette kryds
            p.drawText(int(x) - 20, sy + sh + 18, self._fmt_time(tc))  # Tegn formateret tidslabel

    # Hjælpefunktion: formaterer et tidspunkt til læsbar streng med SI-prefix
    def _fmt_time(self, t: float) -> str:
        """Returnerer tid formateret med passende enhed: s, ms, µs eller ns."""
        if abs(t) >= 1: return f"{t:.3f}s"                        # Sekunder (3 decimaler)
        if abs(t) >= 1e-3: return f"{t*1e3:.2f}ms"                # Millisekunder
        if abs(t) >= 1e-6: return f"{t*1e6:.2f}µs"                # Mikrosekunder
        return f"{t*1e9:.2f}ns"                                    # Nanosekunder

    # Hjælpefunktion: formaterer en frekvens til læsbar streng med SI-prefix
    def _fmt_freq(self, f: float) -> str:
        """Returnerer frekvens formateret med passende enhed: MHz, kHz eller Hz."""
        if f >= 1e6: return f"{f/1e6:.3f}MHz"                     # Megahertz
        if f >= 1e3: return f"{f/1e3:.3f}kHz"                     # Kilohertz
        return f"{f:.1f}Hz"                                        # Hertz

    # Haandterer muse-klik: venstre knap saetter cursor A, hojre saetter cursor B
    def mousePressEvent(self, event):
        """Venstre muse-klik = cursor A (rød), hojre muse-klik = cursor B (blaa)."""
        if self.data is None: return                               # Ingen data → ingen cursorer
        p = self._screen_x_to_time(event.position().x())          # Konverter klik-X til tidspunkt
        if p is None: return                                       # Klik udenfor scopeskærmen
        if event.button() == Qt.LeftButton:                        # Venstre knap?
            self.cursor_a = p                                      # Saet cursor A
        elif event.button() == Qt.RightButton:                     # Hojre knap?
            self.cursor_b = p                                      # Saet cursor B
        self.update()                                              # Gentegn for at vise ny cursor

    # Konverterer en skærm-X-koordinat til det tilsvarende tidspunkt i signalet
    def _screen_x_to_time(self, px):
        """Konverterer pixel-X-position til tidspunkt i sekunder via lineaer interpolation."""
        if self.data is None or self.data.time is None: return None  # Ingen data
        ml = 60; mr = 20                                           # Venstre og hojre margen (skal matche paintEvent)
        sw = self.width() - ml - mr                               # Skærmbredde i pixels
        t = self.data.time
        t_start = t[0] + self.x_offset                            # Synlig tidsstart
        t_range = (t[-1] - t[0]) / self.x_scale                   # Synlig tidslaengde
        return t_start + (px - ml) / sw * t_range                 # Lineaer kortlægning pixels → sekunder


# Widget der udgør "OSCILLOSCOPE"-fanen med kontrolbjaelke og scopeskærm
class OscilloscopeTab(QWidget):

    # Konstruktoer: opbygger UI
    def __init__(self):
        super().__init__()                                         # Initialiser basisklassen
        self._build_ui()                                           # Byg kontrolbjaelke og scopeskærm

    # Opbygger fane-layoutet med kontroller øverst og scopeskærm nedenunder
    def _build_ui(self):
        layout = QVBoxLayout(self)                                 # Lodret layout: kontroller + skærm
        layout.setSpacing(8)                                       # 8 pixels mellemrum
        layout.setContentsMargins(8, 8, 8, 8)                      # 8 pixels margen

        # Kontrolbjaelke med zoom-slider, zoom-label, pan-slider og brugsanvisning
        ctrl = QHBoxLayout()                                       # Vandret layout for kontrolbjaelken
        ctrl.addWidget(QLabel("ZOOM:"))                            # Label for zoom-slider

        self.zoom_slider = QSlider(Qt.Horizontal)                  # Vandret zoom-slider
        self.zoom_slider.setRange(1, 200)                          # Vaerdiinterval: 1..200 (svarer til 0.1x..20x)
        self.zoom_slider.setValue(10)                              # Startvaerdi: 10 = 1.0× zoom
        self.zoom_slider.setMaximumWidth(160)                      # Begraens bredde for at holde layoutet kompakt

        self.zoom_label = QLabel("1.0×")                           # Viser aktuel zoomfaktor som tekst
        self.zoom_label.setMinimumWidth(40)                        # Minimum bredde saa labelen ikke springer

        ctrl.addWidget(self.zoom_slider)                           # Tilføj zoom-slider
        ctrl.addWidget(self.zoom_label)                            # Tilføj zoom-label
        ctrl.addWidget(QLabel("  PAN:"))                           # Label for pan-slider

        self.pan_slider = QSlider(Qt.Horizontal)                   # Vandret pan-slider
        self.pan_slider.setRange(0, 100)                           # 0% = start af buffer, 100% = slut
        self.pan_slider.setValue(0)                                # Start ved bufferens begyndelse
        self.pan_slider.setMaximumWidth(200)                       # Begraens bredde

        ctrl.addWidget(self.pan_slider)                            # Tilføj pan-slider
        ctrl.addStretch()                                          # Fyldplads der skubber brugsanvisningen mod hojre
        ctrl.addWidget(QLabel("  LMB=Cursor A   RMB=Cursor B"))   # Brugsanvisning for cursorer

        layout.addLayout(ctrl)                                     # Tilføj kontrolbjaelken til fane-layoutet

        self.screen = OscilloscopeScreen()                         # Opret scopeskærm-widgetten
        layout.addWidget(self.screen)                              # Tilføj scopeskærmen under kontrolbjaelken

        # Forbind slider-signaler til handler-metoderne
        self.zoom_slider.valueChanged.connect(self._on_zoom)       # Zoom-slider → _on_zoom
        self.pan_slider.valueChanged.connect(self._on_pan)         # Pan-slider → _on_pan

    # Haandterer zoom-slider-aendringer
    def _on_zoom(self, val):
        """Konverterer slider-vaerdi (1..200) til zoomfaktor (0.1..20.0)."""
        factor = val / 10.0                                        # 10 → 1.0×, 20 → 2.0× osv.
        self.zoom_label.setText(f"{factor:.1f}×")                  # Opdatér zoom-label
        self.screen.set_zoom(factor)                               # Videresend til scopeskærmen

    # Haandterer pan-slider-aendringer
    def _on_pan(self, val):
        """Videresender pan-vaerdi (0..100) til scopeskærmen."""
        self.screen.set_pan(val)                                   # val=0: start, val=100: slut af buffer

    # Modtager nyt OscilloscopeData-objekt og videresender til scopeskærmen
    def set_data(self, data: OscilloscopeData):
        """Videresender data til den underliggende scopeskærm-widget."""
        self.screen.set_data(data)                                 # Scopeskærmen haandterer resten


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3: SPECTRUM ANALYZER
#  Viser FFT-spektrum i dBV paa logaritmisk frekvensakse med harmoniske markers.
# ─────────────────────────────────────────────────────────────────────────────

# Widget der tegner spektrumanalysatoren med log-frekvensakse og dBV-akse
class SpectrumDisplay(QWidget):
    """Professionel spektrumanalyse-visning"""

    # Konstruktoer: initialiserer tomme spektrum-data
    def __init__(self):
        super().__init__()
        self.ch1_harmonics: list = []                              # Liste af (frekvens, dBV) tupler for CH1
        self.ch2_harmonics: list = []                              # Liste af (frekvens, dBV) tupler for CH2
        self.freqs_db: tuple | None = None                         # (freqs1, db1, freqs2, db2) — hele spektret
        self.ch1_fund: float | None = None                         # CH1 fundamental-frekvens i Hz
        self.ch2_fund: float | None = None                         # CH2 fundamental-frekvens i Hz
        self.setMinimumHeight(380)                                 # Mindst 380 pixels hojde for god laesbarhed
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Udvid for at fylde pladsen

    # Beregner og gemmer spektrum for begge kanaler
    def set_spectrum(self, ch1_data=None, ch2_data=None):
        """Analyserer kanaldata og gemmer spektrum-resultater til tegning.

        ch1_data og ch2_data er tupler: (voltage_array, dt) eller None.
        Signaler med fundamental over 50 kHz analyseres ikke (THD ville vaere usikker).
        """
        # Nulstil alle spektrum-data inden ny beregning
        self.ch1_harmonics = []                                    # Tom harmonisk-liste for CH1
        self.ch2_harmonics = []                                    # Tom harmonisk-liste for CH2
        self.freqs_db = None                                       # Intet spektrum endnu
        self.ch1_fund = None                                       # Ingen fundamental endnu
        self.ch2_fund = None

        freqs1 = db1 = freqs2 = db2 = None                        # Spektrumdata for begge kanaler

        # Analyser CH1 hvis data er tilgængeligt
        if ch1_data:
            ana = SignalAnalyzer(ch1_data[0], ch1_data[1])        # Opret analysator for CH1
            f = ana.frequency()                                    # Bestem fundamental-frekvens
            if f and f < 50000:                                    # Kun under 50 kHz analyseres
                self.ch1_fund = f                                  # Gem CH1 fundamental
                self.ch1_harmonics = ana.harmonics(40)             # Beregn op til 40 harmoniske
                freqs1, db1 = ana.fft_spectrum()                   # Beregn hele spektret til visning
            elif f and f >= 50000:
                self.ch1_fund = f                                  # Gem frekvens men analyser ikke (for hoj)

        # Analyser CH2 hvis data er tilgængeligt
        if ch2_data:
            ana = SignalAnalyzer(ch2_data[0], ch2_data[1])        # Opret analysator for CH2
            f = ana.frequency()
            if f and f < 50000:
                self.ch2_fund = f
                self.ch2_harmonics = ana.harmonics(40)
                freqs2, db2 = ana.fft_spectrum()
            elif f and f >= 50000:
                self.ch2_fund = f

        # Gem spektrumdata til tegning; brug det ene spektrum hvis kun ét er tilgængeligt
        if freqs1 is not None or freqs2 is not None:
            if freqs1 is None: freqs1, db1 = freqs2, db2          # Brug CH2 hvis CH1 mangler
            if freqs2 is None: freqs2, db2 = freqs1, db1          # Brug CH1 hvis CH2 mangler
            self.freqs_db = (freqs1, db1, freqs2, db2)             # Gem alle fire arrays til paintEvent

        self.update()                                              # Tvang gentegning

    # Tegner spektrumanalysatoren med grid, spektrumkurver og harmoniske markers
    def paintEvent(self, event):
        """Tegner hele spektrumvisningen: baggrund, grid, kurver og harmoniske."""
        p = QPainter(self)                                         # Opret tegnerobjekt
        p.setRenderHint(QPainter.Antialiasing)                     # Aktiver anti-aliasing
        w, h = self.width(), self.height()                         # Dimensioner i pixels
        ml, mr, mt, mb = 70, 20, 20, 50                           # Marginer: venstre, hojre, top, bund

        p.fillRect(self.rect(), QColor("#070b0f"))                 # Mørk baggrund for hele widgetten

        # Vis besked hvis ingen spektrumdata er tilgængeligt
        if self.freqs_db is None:
            p.setPen(QColor("#30363d"))
            p.setFont(QFont("Consolas", 13))
            msg = "No spectrum data"                               # Standardbesked
            if self.ch1_fund and self.ch1_fund >= 50000:           # Særlig besked hvis frekvensen er for hoj
                msg = f"CH1: {self.ch1_fund/1000:.1f} kHz — exceeds 50 kHz limit"
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, msg)   # Centrér besked
            return                                                  # Stop tegning

        freqs1, db1, freqs2, db2 = self.freqs_db                  # Udpak spektrumdata
        sw = w - ml - mr                                           # Spektrumvisningsbredde
        sh = h - mt - mb                                           # Spektrumvisningshojde

        # Frekvensakse: logaritmisk skala fra ~10 Hz til Nyquist
        f_min = max(freqs1[1] if len(freqs1) > 1 else 1, 10)      # Startfrekvens (undgaa DC og 0)
        f_max_val = float(freqs1[-1])                              # Slutfrekvens = Nyquist

        # dBV-akse: fast skala fra -90 til +10 dBV
        db_min = -90.0                                             # Nedre dBV-grænse
        db_max = 10.0                                              # Øvre dBV-grænse

        # Indre hjælpefunktion: konverterer (frekvens, dBV) til (screen_x, screen_y)
        def to_xy(f, db):
            if f <= 0: f = f_min                                   # Undgaa log(0)
            xn = np.log10(f/f_min) / np.log10(f_max_val/f_min)   # Normaliseret log-frekvensposition [0..1]
            yn = (db - db_min) / (db_max - db_min)                 # Normaliseret dBV-position [0..1]
            return ml + xn * sw, mt + (1 - yn) * sh               # Pixels (Y inverteret: hojt dBV = lav Y)

        # Tegn vandrette dBV-gitterlinjer fra -90 til +10 med 10 dBV mellemrum
        p.setPen(QPen(QColor("#1c2128"), 1))                       # Moerk gitterlinje
        for db in range(-90, 20, 10):                              # -90, -80, ..., +10
            _, y = to_xy(f_min, db)                                # Y-koordinat for dette dB-niveau
            p.drawLine(ml, int(y), ml + sw, int(y))               # Vandret gitterlinje
            p.setFont(QFont("Consolas", 8))
            p.setPen(QColor("#484f58"))                            # Daemp dBV-label
            p.drawText(2, int(y) + 4, f"{db}")                    # dBV-label til venstre
            p.setPen(QPen(QColor("#1c2128"), 1))                   # Skift tilbage til gitter-pen

        # Tegn lodrette frekvens-gitterlinjer ved 1,2,5,10,20,50,...Hz
        for exp in range(1, 6):                                    # Potenser: 10¹=10 til 10⁵=100000
            for mult in [1, 2, 5]:                                 # Multiplum: 1×, 2×, 5× af potensen
                f = mult * 10**exp                                 # Frekvens for denne gridlinje (fx 20 Hz)
                if f_min <= f <= f_max_val:                        # Kun inden for synligt frekvensomraade
                    x, _ = to_xy(f, db_min)                        # X-koordinat for denne frekvens
                    p.setPen(QPen(QColor("#1c2128"), 1))
                    p.drawLine(int(x), mt, int(x), mt + sh)        # Lodret gitterlinje
                    p.setPen(QColor("#484f58"))
                    p.setFont(QFont("Consolas", 8))
                    lbl = f"{f/1000:.0f}k" if f >= 1000 else f"{f:.0f}"  # "1k" for 1000 Hz, "100" for 100 Hz
                    p.drawText(int(x) - 12, mt + sh + 16, lbl)    # Frekvens-label under plottet

        # Indre hjælpefunktion: tegner en kontinuert spektrumkurve
        def draw_spectrum(freqs, db, color, alpha=80):
            """Tegner den kontinuerte FFT-spektrumkurve for én kanal."""
            pen = QPen(color, 1)
            pen.setColor(QColor(color.red(), color.green(), color.blue(), alpha))  # Gennemsigtig farve
            p.setPen(pen)
            if len(freqs) < 2: return                              # For faa punkter → skip
            mask = freqs >= f_min                                  # Kun frekvenser over f_min
            fr = freqs[mask]; d = db[mask]                         # Filtrer arrays
            if len(fr) < 2: return
            path = QPainterPath()                                  # Start ny vektorsti
            x0, y0 = to_xy(fr[0], d[0])
            path.moveTo(x0, y0)                                    # Startpunkt
            for i in range(1, min(len(fr), sw*2)):                 # Begræns til 2×skærmbredde
                xi, yi = to_xy(fr[i], d[i])
                path.lineTo(xi, yi)                                # Forbind med linjestykke
            p.drawPath(path)                                       # Tegn hele stien

        # Tegn spektrumkurver for begge kanaler
        if db1 is not None:
            draw_spectrum(freqs1, db1, QColor("#f7cc52"), 100)     # CH1: gul
        if db2 is not None:
            draw_spectrum(freqs2, db2, QColor("#5af0e0"), 100)     # CH2: cyan

        # Indre hjælpefunktion: tegner lodrette søjler og numre for harmoniske
        def draw_harmonics(harmonics, color, offset_y=0):
            """Tegner én lodret søjle per harmonisk fra dBV-niveauet ned til x-aksen."""
            if not harmonics: return                               # Ingen harmoniske → skip
            max_db = max(h[1] for h in harmonics)                  # Hoejeste harmonisk (bruges ikke pt.)
            for i, (f, db) in enumerate(harmonics):                # Gennemgaa alle harmoniske
                if f < f_min or f > f_max_val: continue            # Kun inden for frekvensomraade
                x, y = to_xy(f, db)                                # Toppen af søjlen (ved dBV-niveau)
                bar_top = to_xy(f, db)[1]                          # Y-koordinat for søjlens top
                bar_bot = to_xy(f, db_min)[1]                      # Y-koordinat for søjlens bund (x-akse)
                c = QColor(color)
                c.setAlpha(180 if i == 0 else 120)                 # Fundamental (i=0) lidt mere synlig
                p.setPen(QPen(c, 2 if i == 0 else 1))              # Fundamental: tykkere søjle
                p.drawLine(int(x), int(bar_top), int(x), int(bar_bot))  # Tegn søjlen
                if i < 10:                                         # Vis harmonisk-nummer for de foerste 10
                    p.setFont(QFont("Consolas", 7))                # Meget lille skrift
                    p.setPen(c)
                    p.drawText(int(x) - 4, int(bar_top) - 3 + offset_y, str(i+1))  # "1", "2", ..., "10"

        # Tegn harmoniske markers for begge kanaler
        draw_harmonics(self.ch1_harmonics, "#f7cc52", 0)           # CH1: gule markers
        draw_harmonics(self.ch2_harmonics, "#5af0e0", 10)          # CH2: cyan markers (10px lavere for laesbarhed)

        # Tegn akselabels
        p.setFont(QFont("Consolas", 9))
        p.setPen(QColor("#8b949e"))
        p.drawText(2, mt + sh // 2, "dBV")                        # Y-akse label: dBV
        p.drawText(ml + sw // 2 - 20, h - 4, "Frequency")         # X-akse label: Frequency

        # Tegn spektrumplotets kant
        p.setPen(QPen(QColor("#30363d"), 1))
        p.drawRect(ml, mt, sw, sh)                                 # Rektangulær kant


# Widget der udgør "SPECTRUM"-fanen med infobjaelke, spektrumplot og harmonisk tabel
class SpectrumTab(QWidget):

    # Konstruktoer: opbygger fane-layoutet
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)                                 # Lodret layout
        layout.setContentsMargins(8, 8, 8, 8)

        # Infobjaelke øverst i fanen med brugsanvisning
        self.info_bar = QLabel("Load a file to show spectrum. Only signals < 50 kHz are analyzed.")
        self.info_bar.setStyleSheet("color: #8b949e; font-size: 11px; padding: 4px;")
        layout.addWidget(self.info_bar)                            # Tilføj infobjaelke øverst

        self.display = SpectrumDisplay()                           # Opret spektrumvisnings-widget
        layout.addWidget(self.display)                             # Tilføj spektrumplot i midten

        # Harmonisk tabel nedenunder spektrumplottet
        self.harm_frame = QGroupBox("HARMONIC TABLE")              # Ramme med titel
        harm_layout = QHBoxLayout(self.harm_frame)

        # Label til CH1's harmoniske liste (gul farve)
        self.ch1_harm_label = QLabel("CH1: —")
        self.ch1_harm_label.setStyleSheet("color: #f7cc52; font-size: 11px;")
        self.ch1_harm_label.setAlignment(Qt.AlignTop)              # Top-justér tekst

        # Label til CH2's harmoniske liste (cyan farve)
        self.ch2_harm_label = QLabel("CH2: —")
        self.ch2_harm_label.setStyleSheet("color: #5af0e0; font-size: 11px;")
        self.ch2_harm_label.setAlignment(Qt.AlignTop)

        harm_layout.addWidget(self.ch1_harm_label)                 # CH1 til venstre
        harm_layout.addWidget(self.ch2_harm_label)                 # CH2 til hojre
        self.harm_frame.setMaximumHeight(120)                      # Begraens tabellens hojde
        layout.addWidget(self.harm_frame)                          # Tilføj tabel nedenunder spektrum

    # Modtager nye data og opdaterer spektrumplot og harmonisk tabel
    def set_data(self, data: OscilloscopeData):
        """Videresender kanaldata til SpectrumDisplay og opdaterer harmonisk-tabellen."""
        # Pak data om til tupler (voltage, dt) som SpectrumDisplay forventer
        ch1 = (data.ch1_voltage, data.dt) if data.ch1_active and data.ch1_voltage is not None else None
        ch2 = (data.ch2_voltage, data.dt) if data.ch2_active and data.ch2_voltage is not None else None
        self.display.set_spectrum(ch1, ch2)                        # Beregn og tegn spektrum

        # Indre hjælpefunktion: genererer tekst til harmonisk-labelen for én kanal
        def harm_text(harmonics, fund, label):
            """Formaterer en tekstliste over de foerste 10 harmoniske."""
            if not harmonics:                                      # Ingen harmoniske data?
                if fund and fund >= 50000:                         # Fundamental over 50 kHz?
                    return f"{label}: {fund/1000:.1f} kHz > 50 kHz limit"  # Vis grænse-besked
                return f"{label}: —"                               # Ingen data
            lines = [f"{label}:  f0={fund:.1f} Hz" if fund else f"{label}:"]  # Overskrift med fundamental
            for i, (f, db) in enumerate(harmonics[:10]):           # Vis maks 10 harmoniske
                lines.append(f"  H{i+1}: {f:.1f} Hz  {db:.1f} dBV")  # "H1: 1000.0 Hz  -3.5 dBV"
            return "\n".join(lines)                                # Saml til flerlinjet tekst

        # Opdatér begge harmoniske labels
        self.ch1_harm_label.setText(harm_text(
            self.display.ch1_harmonics, self.display.ch1_fund, "CH1"))
        self.ch2_harm_label.setText(harm_text(
            self.display.ch2_harmonics, self.display.ch2_fund, "CH2"))


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
#  Hoved-vinduet samler de tre faner, menulinjen, header-bjaelken og statusbaren.
# ─────────────────────────────────────────────────────────────────────────────

# Hoved-vinduesklasse der indeholder hele applikationens UI
class MainWindow(QMainWindow):

    # Konstruktoer: saetter vinduets grundlaeggende egenskaber op
    def __init__(self):
        super().__init__()                                         # Initialiser QMainWindow
        self.setWindowTitle("Rigol DS1052E Analyzer")              # Titel i vinduesbjælken
        self.resize(1200, 720)                                     # Startdimension: 1200×720 pixels
        self.data: OscilloscopeData | None = None                  # Ingen data indlæst endnu
        self._build_ui()                                           # Byg alle widgets og layouts
        self._build_menu()                                         # Byg menulinjen
        self.setStyleSheet(DARK_STYLE)                             # Anvend det moerke tema
        # Forsink åbning af fildialog med 100 ms saa vinduet naår at blive vist foerst
        QTimer.singleShot(100, self._open_file)                    # 100 ms enkelt-skuds timer

    # Opbygger hele UI-strukturen: header-bjaelke, faner og statusbar
    def _build_ui(self):
        """Opbygger hoved-vinduets layout: header | faner | statusbar."""
        central = QWidget()                                        # Central widget som container
        self.setCentralWidget(central)                             # Saet som hoved-indhold i vinduet
        layout = QVBoxLayout(central)                              # Lodret layout: header + faner
        layout.setContentsMargins(0, 0, 0, 0)                      # Ingen marginer rundt om hoved-layout
        layout.setSpacing(0)                                       # Ingen mellemrum mellem elementer

        # ── Header-bjaelke ─────────────────────────────────────────────────
        header = QFrame()                                          # Ramme som header-container
        header.setFixedHeight(38)                                  # Fast hojde: 38 pixels
        header.setStyleSheet("background:#161b22; border-bottom: 1px solid #30363d;")
        h_layout = QHBoxLayout(header)                             # Vandret layout inden i headeren
        h_layout.setContentsMargins(12, 0, 12, 0)                  # Vandret margen, ingen lodret

        title = QLabel("RIGOL DS1052E  //  OSCILLOSCOPE ANALYZER")  # Programtitel
        title.setStyleSheet("color:#58a6ff; font-size: 12px; letter-spacing: 3px; font-weight: bold;")

        self.file_label = QLabel("No file loaded")                 # Viser aktuel fils navn og info
        self.file_label.setStyleSheet("color:#484f58; font-size: 11px;")

        h_layout.addWidget(title)                                  # Titel yderst til venstre
        h_layout.addStretch()                                      # Fyldplads skubber resten mod hojre
        h_layout.addWidget(self.file_label)                        # Filinfo til hojre for titel

        open_btn = QPushButton("⊕ OPEN FILE")                      # Knap til aabning af fil
        open_btn.clicked.connect(self._open_file)                  # Forbind klik til _open_file-metoden
        h_layout.addWidget(open_btn)                               # Knap yderst til hojre
        layout.addWidget(header)                                   # Tilføj header øverst i hoved-layout

        # ── Fane-widget med de tre analysatorfaner ─────────────────────────
        self.tabs = QTabWidget()                                   # Container til de tre faner
        self.tab_measure  = MeasurementWidget()                    # Fane 1: elektriske maalinger
        self.tab_scope    = OscilloscopeTab()                      # Fane 2: oscilloskopvisning
        self.tab_spectrum = SpectrumTab()                          # Fane 3: spektrumanalyse
        self.tabs.addTab(self.tab_measure,  "MEASUREMENTS")        # Tilføj maale-fane
        self.tabs.addTab(self.tab_scope,    "OSCILLOSCOPE")        # Tilføj scope-fane
        self.tabs.addTab(self.tab_spectrum, "SPECTRUM")            # Tilføj spektrum-fane
        layout.addWidget(self.tabs)                                # Tilføj faner under headeren

        # ── Statusbar i vinduets bund ───────────────────────────────────────
        self.status = QStatusBar()                                 # Qt's innebygde statusbar
        self.setStatusBar(self.status)                             # Saet som vinduets statusbar
        self.status.showMessage("Ready — Open a Rigol CSV file")   # Startbesked

    # Opbygger applikationens menubar med Fil-menu
    def _build_menu(self):
        """Opbygger menulinjen med File → Open og File → Quit."""
        menu = self.menuBar()                                      # Hent menubar-objektet
        menu.setStyleSheet("""
            QMenuBar { background:#161b22; color:#c9d1d9; border-bottom: 1px solid #30363d; }
            QMenuBar::item:selected { background:#21262d; }
            QMenu { background:#161b22; color:#c9d1d9; border: 1px solid #30363d; }
            QMenu::item:selected { background:#21262d; }
        """)                                                       # Moerkt tema paa menubar og dropdown

        file_menu = menu.addMenu("File")                           # Opret "File"-menugruppe

        open_action = QAction("Open…", self)                       # "Open..."-menuvalg
        open_action.setShortcut(QKeySequence.Open)                 # Genvejstast: Ctrl+O
        open_action.triggered.connect(self._open_file)             # Forbind til _open_file
        file_menu.addAction(open_action)                           # Tilføj til File-menuen

        file_menu.addSeparator()                                   # Vandret separator-linie i menuen

        quit_action = QAction("Quit", self)                        # "Quit"-menuvalg
        quit_action.setShortcut(QKeySequence.Quit)                 # Genvejstast: Ctrl+Q
        quit_action.triggered.connect(self.close)                  # Forbind til vinduets close()
        file_menu.addAction(quit_action)                           # Tilføj til File-menuen

    # Viser OS-fildialog og indlæser den valgte CSV-fil
    def _open_file(self):
        """Åbner OS-fildialog og videresender den valgte CSV-sti til _load_file."""
        path, _ = QFileDialog.getOpenFileName(
            self,                                                  # Foraelder-widget
            "Open Oscilloscope Data",                             # Dialogtitel
            os.path.expanduser("~"),                              # Startmappe: brugerens hjemmemappe
            "Rigol CSV Files (*.csv);;All Files (*)"              # Filtype-filter
        )
        if not path:                                               # Bruger trykkede Annuller?
            return                                                  # Gør ingenting
        self._load_file(path)                                      # Indlæs den valgte fil

    # Indlæser og analyserer en CSV-fil og opdaterer alle tre faner
    def _load_file(self, path: str):
        """Indlæser CSV-filen, validerer den og opdaterer alle tre analysatorfaner."""
        data = OscilloscopeData()                                  # Opret tomt datacontainer-objekt
        ok = data.load_csv(path)                                   # Forsøg at indlæse og parse filen

        if not ok:                                                 # Parsing mislykkedes?
            QMessageBox.warning(self, "Load Error",                # Vis fejldialog
                                f"Could not parse file:\n{path}\n\n"
                                "Make sure it is a valid Rigol CSV export.")
            return                                                  # Afbryd — behold evt. tidligere data

        self.data = data                                           # Gem de nye data

        # Opdatér header-barens filinfo med navn, aktive kanaler, antal punkter og fs
        self.file_label.setText(f"  {data.filename}  |  "
                                f"{'CH1 ' if data.ch1_active else ''}"       # Viser "CH1 " hvis aktiv
                                f"{'CH2 ' if data.ch2_active else ''}|  "    # Viser "CH2 " hvis aktiv
                                f"{len(data.time) if data.time is not None else 0} pts  |  "  # Antal samples
                                f"fs={data.sample_rate/1000:.1f} kSa/s")     # Samplehastighed i kSa/s

        # Videresend data til alle tre faner saa de opdaterer sig
        self.tab_measure.update_measurements(data)                 # Opdatér maalefanen
        self.tab_scope.set_data(data)                              # Opdatér scopefanen
        self.tab_spectrum.set_data(data)                           # Opdatér spektrumfanen
        self.status.showMessage(f"Loaded: {path}")                 # Vis filsti i statusbaren


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
#  main() er programmets indgangspunkt. Den tjekker afhæengigheder, opretter
#  Qt-applikationen og starter hændelsesloekken.
# ─────────────────────────────────────────────────────────────────────────────

# Programmets hoved-funktion der starter Qt-applikationen
def main():
    """Starter Rigol DS1052E Analyzer.

    Tjekker at scipy er installeret, opretter QApplication, viser MainWindow
    og starter Qt's hændelsesloekke. Hændelsesloekken korer indtil vinduet lukkes.
    """
    # Tjek at alle nødvendige biblioteker er installeret
    missing = []                                                   # Tom liste til manglende pakker
    try: import scipy                                              # scipy bruges til Savitzky-Golay filter
    except ImportError: missing.append("scipy")                   # Mangler scipy

    if missing:                                                    # Nogen pakker mangler?
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)                                                # Afbryd med fejlkode 1

    app = QApplication(sys.argv)                                   # Opret Qt-applikation (ét eksemplar pr. process)
    app.setApplicationName("Rigol DS1052E Analyzer")               # Applikationsnavn (bruges i OS-titelbjaelker)
    app.setOrganizationName("DSP Tools")                           # Organisationsnavn (bruges til konfigurationsfiler)

    # Aktiver support for hojoplosningsskærme (HiDPI / Retina)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)                # Brug hojoplosnings-pixmaps

    win = MainWindow()                                             # Opret hoved-vinduet
    win.show()                                                     # Vis vinduet paa skærmen
    sys.exit(app.exec())                                           # Start hændelsesloekken; sys.exit ved lukning


# Python-standardkonstruktion: kør main() kun naar filen eksekveres direkte,
# ikke naar den importeres som et modul i et andet program
if __name__ == "__main__":
    main()                                                         # Start programmet
