"""
pyWFM2CSV.py
============
Rigol DS1052E .wfm  →  .csv  converter

Usage:  python pyWFM2CSV.py
  1. File-open dialog  → select .wfm file
  2. File-save dialog  → choose output .csv path
  3. Conversion runs; result is a 4-column CSV identical in structure
     to the Rigol CSV export:

     Time_CH1 (s),Voltage_CH1 (V),Time_CH2 (s),Voltage_CH2 (V)

WFM format (Rigol DS1052E, reverse-engineered):
  0x00   8 B   magic  'RIGLWFM\\0'
  0x08  u32   n_pts       bytes per channel block
  0x0C  f32   fs_comb     combined stream sample rate  (Sa/s)
  0x10  u32   n_channels
  0x14  f32   dt_comb     dt of combined stream  (s)
  0x64  14 B  ASCII timestamp  YYYYMMDDHHMMSS
  0x1FF        data start  (header = 511 bytes)

Data layout – two sequential blocks, each n_pts int8 bytes:
  Block 1 @ 0x1FF  (CH1):
    byte  0        → CH1 sample 0
    bytes 1–3      → filler (0x7F)
    bytes 4,6,8,…  → CH1 samples 1, 2, 3, …
    bytes 5,7,9,…  → filler (0x7F)

  Block 2 @ 0x1FF + n_pts  (CH2):
    bytes 0–3      → filler (0x7F)
    bytes 4,6,8,…  → CH2 samples 0, 1, 2, …
    bytes 5,7,9,…  → filler (0x7F)

Per-channel dt  = dt_comb × 2
Voltage         = raw_int8 / 25.0   (units: scope divisions)

Dependencies:  numpy  (pip install numpy)
"""

import struct
import sys
import os

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
#  WFM PARSER
# ─────────────────────────────────────────────────────────────────────────────

class WFMParseError(Exception):
    pass


def _extract_channel(block: bytes) -> np.ndarray:
    """Extract signal samples from one interleaved block.

    Layout:  [s0, F, F, F, s1, F, s2, F, s3, F, …]
    where F = filler byte (0x7F = 127).
    Returns 1-D float64 array of ADC counts (int8 range −128…127).
    """
    b = np.frombuffer(block, dtype=np.int8).astype(np.float64)
    return np.concatenate([[b[0]], b[4::2]])


def parse_wfm(path: str) -> dict:
    """Parse a Rigol DS1052E .wfm file.

    Returns a dict with keys:
      dt          float   per-channel sample interval (s)
      fs          float   per-channel sample rate (Sa/s)
      timestamp   str     'YYYYMMDDHHMMSS' or '' if absent
      ch1         ndarray voltage array CH1 (scope divisions)
      ch2         ndarray voltage array CH2, or None if inactive
      n_channels  int     1 or 2
    """
    HEADER = 511
    MAGIC  = b'RIGLWFM\x00'

    with open(path, 'rb') as f:
        data = f.read()

    if len(data) < HEADER + 8:
        raise WFMParseError("File too short to be a valid WFM")
    if data[:8] != MAGIC:
        raise WFMParseError(f"Bad magic bytes: {data[:8]!r}  (expected {MAGIC!r})")

    n_pts   = struct.unpack_from('<I', data, 0x08)[0]
    dt_comb = struct.unpack_from('<f', data, 0x14)[0]
    n_ch    = struct.unpack_from('<I', data, 0x10)[0]

    if n_pts < 8:
        raise WFMParseError(f"n_pts={n_pts} is implausibly small")
    if dt_comb <= 0 or dt_comb > 1.0:
        raise WFMParseError(f"dt_comb={dt_comb} is out of range")

    # Timestamp at 0x64 (14 ASCII bytes)
    try:
        ts_raw = data[0x64:0x72]
        timestamp = ts_raw.decode('ascii').rstrip('\x00')
    except Exception:
        timestamp = ''

    dt_ch = dt_comb * 2.0          # per-channel sample interval
    fs_ch = 1.0 / dt_ch            # per-channel sample rate

    # ── CH1 ──────────────────────────────────────────────────────────────────
    off1 = HEADER
    if off1 + n_pts > len(data):
        raise WFMParseError("File truncated before end of CH1 block")
    raw1 = _extract_channel(data[off1:off1 + n_pts])
    v1   = raw1 / 25.0             # scope divisions

    # ── CH2 ──────────────────────────────────────────────────────────────────
    off2  = HEADER + n_pts
    v2    = None
    if off2 + n_pts <= len(data):
        raw2_cand = _extract_channel(data[off2:off2 + n_pts])
        swing = float(raw2_cand.max() - raw2_cand.min())
        if swing > 4:              # more than 4 counts → active signal
            v2 = raw2_cand / 25.0

    return {
        'dt':         dt_ch,
        'fs':         fs_ch,
        'timestamp':  timestamp,
        'ch1':        v1,
        'ch2':        v2,
        'n_channels': 2 if v2 is not None else 1,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  CSV WRITER
# ─────────────────────────────────────────────────────────────────────────────

def write_csv(wfm: dict, out_path: str) -> int:
    """Write parsed WFM data to a Rigol-compatible 4-column CSV.

    Columns:
      Time_CH1 (s), Voltage_CH1 (V), Time_CH2 (s), Voltage_CH2 (V)

    CH2 voltage is filled with 0.0 when only one channel is active.
    Returns number of rows written.
    """
    v1 = wfm['ch1']
    v2 = wfm['ch2'] if wfm['ch2'] is not None else np.zeros(len(v1))

    # Pad/trim to same length
    n = min(len(v1), len(v2))
    v1 = v1[:n];  v2 = v2[:n]

    dt  = wfm['dt']
    t   = np.arange(n) * dt

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('Time_CH1 (s),Voltage_CH1 (V),Time_CH2 (s),Voltage_CH2 (V)\n')
        for i in range(n):
            f.write(f'{t[i]:.10e},{v1[i]:.10f},{t[i]:.10e},{v2[i]:.10f}\n')

    return n


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN — file dialogs
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Use tkinter for lightweight file dialogs (no Qt dependency needed here)
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except ImportError:
        print("ERROR: tkinter not available. "
              "Run with:  python pyWFM2CSV.py <input.wfm> <output.csv>")
        if len(sys.argv) == 3:
            _convert_cli(sys.argv[1], sys.argv[2])
        sys.exit(1)

    root = tk.Tk()
    root.withdraw()          # hide the empty root window
    root.attributes('-topmost', True)

    # ── Pick input WFM ───────────────────────────────────────────────────────
    wfm_path = filedialog.askopenfilename(
        title='Open Rigol WFM file',
        filetypes=[('Rigol WFM', '*.wfm'), ('All files', '*.*')],
    )
    if not wfm_path:
        print("Cancelled.")
        sys.exit(0)

    # ── Parse ────────────────────────────────────────────────────────────────
    try:
        wfm = parse_wfm(wfm_path)
    except WFMParseError as e:
        messagebox.showerror('WFM Parse Error', str(e))
        sys.exit(1)
    except Exception as e:
        messagebox.showerror('Unexpected Error', f'{type(e).__name__}: {e}')
        sys.exit(1)

    # ── Suggest output filename ──────────────────────────────────────────────
    base     = os.path.splitext(os.path.basename(wfm_path))[0]
    init_dir = os.path.dirname(wfm_path)
    init_file = base + '.csv'

    # ── Pick output CSV ──────────────────────────────────────────────────────
    csv_path = filedialog.asksaveasfilename(
        title='Save CSV file',
        initialdir=init_dir,
        initialfile=init_file,
        defaultextension='.csv',
        filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
    )
    if not csv_path:
        print("Cancelled.")
        sys.exit(0)

    # ── Write ────────────────────────────────────────────────────────────────
    try:
        n_rows = write_csv(wfm, csv_path)
    except Exception as e:
        messagebox.showerror('Write Error', f'{type(e).__name__}: {e}')
        sys.exit(1)

    # ── Summary ──────────────────────────────────────────────────────────────
    ch2_info = (f"CH2 active  ({wfm['n_channels']} channels)"
                if wfm['ch2'] is not None else "CH2 inactive (1 channel)")
    ts_info  = f"Timestamp: {wfm['timestamp']}" if wfm['timestamp'] else ""
    summary  = (
        f"Conversion complete.\n\n"
        f"Source:  {os.path.basename(wfm_path)}\n"
        f"Output:  {os.path.basename(csv_path)}\n"
        f"Rows:    {n_rows:,}\n"
        f"dt:      {wfm['dt']:.6e} s  "
        f"({wfm['fs']/1000:.3f} kSa/s per channel)\n"
        f"{ch2_info}\n"
        + (f"{ts_info}\n" if ts_info else "")
    )
    print(summary)
    messagebox.showinfo('Done', summary)


def _convert_cli(wfm_path: str, csv_path: str):
    """Fallback: command-line usage without tkinter."""
    print(f"Parsing  {wfm_path} …")
    wfm = parse_wfm(wfm_path)
    print(f"Writing  {csv_path} …")
    n = write_csv(wfm, csv_path)
    print(f"Done — {n} rows, {wfm['n_channels']} channel(s), "
          f"dt={wfm['dt']:.6e}s")


if __name__ == '__main__':
    # Allow optional CLI usage:  python pyWFM2CSV.py input.wfm output.csv
    if len(sys.argv) == 3:
        _convert_cli(sys.argv[1], sys.argv[2])
    else:
        main()
