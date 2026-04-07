#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV to MATLAB Converter - Forbedret version
Bruger samme parser-logik som rigol_analyzer.py
"""

import numpy as np
import os
import sys
from datetime import datetime

# Simpel MATLAB fil writer uden scipy
def write_mat_simple(output_path, data_dict):
    """Skriv en simpel MAT-fil (v7.3 format med h5py eller fald tilbage til CSV)"""
    try:
        import h5py
        use_h5py = True
    except ImportError:
        use_h5py = False
        print("ADVARSEL: h5py ikke installeret - gemmer som NPZ fil i stedet")
    
    if use_h5py:
        with h5py.File(output_path, 'w') as f:
            for key, value in data_dict.items():
                if isinstance(value, np.ndarray):
                    f.create_dataset(key, data=value)
                else:
                    f.create_dataset(key, data=np.array([value]))
        return True
    else:
        # Gem som NPZ (kan læses af scipy.io.loadmat eller np.load)
        npz_path = output_path.replace('.mat', '.npz')
        np.savez_compressed(npz_path, **data_dict)
        print(f"Gemte som NPZ fil: {npz_path}")
        return False

def read_csv_robust(csv_path):
    """Læs CSV fil på robust vis - baseret på rigol_analyzer.py's parser"""
    print(f"\nLæser: {csv_path}")
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        # Fald tilbage til default encoding
        with open(csv_path, 'r') as f:
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
        raise ValueError("Ingen data fundet i CSV filen")
    
    print(f"Fundet {len(times)} datapunkter")
    
    # Konverter til numpy arrays
    time = np.array(times, dtype=np.float64)
    dt = 0.0
    sample_rate = 1e6
    
    if len(time) > 1:
        dt = float(np.mean(np.diff(time)))
        if dt > 0:
            sample_rate = 1.0 / dt
    
    print(f"Sample rate: {sample_rate/1000:.2f} kHz")
    print(f"dt: {dt*1e6:.2f} µs")
    
    # Håndter CH1 data
    ch1_voltage = None
    ch1_active = False
    if ch1s:
        ch1_voltage = np.array(ch1s, dtype=np.float64)
        ch1_active = True
        print(f"CH1: {len(ch1_voltage)} samples")
    
    # Håndter CH2 data
    ch2_voltage = None
    ch2_active = False
    if ch2s:
        if len(ch2s) == len(times):
            ch2_voltage = np.array(ch2s, dtype=np.float64)
            ch2_active = True
        else:
            # Hvis CH2 har færre punkter, pad med NaN
            if len(ch2s) < len(times):
                padded = np.full(len(times), np.nan)
                padded[:len(ch2s)] = ch2s
                ch2_voltage = padded
                ch2_active = True
                print(f"CH2: {len(ch2s)} samples (padded to {len(times)})")
            else:
                ch2_voltage = np.array(ch2s[:len(times)], dtype=np.float64)
                ch2_active = True
                print(f"CH2: {len(ch2_voltage)} samples")
    
    return {
        'time': time,
        'ch1_voltage': ch1_voltage,
        'ch2_voltage': ch2_voltage,
        'ch1_active': ch1_active,
        'ch2_active': ch2_active,
        'dt': dt,
        'sample_rate': sample_rate
    }

def main():
    print("\n" + "="*60)
    print("  RIGOL CSV til MATLAB Konverter (forbedret)")
    print("="*60)
    
    # Få input fil
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        print("\nIndtast sti til CSV fil:")
        print("(Du kan også trække filen ind i vinduet)")
        input_file = input("> ").strip().strip('"').strip("'")
    
    if not input_file:
        print("Ingen fil angivet. Afbryder.")
        input("\nTryk Enter for at afslutte...")
        sys.exit(1)
    
    if not os.path.exists(input_file):
        print(f"\nFEJL: Filen '{input_file}' findes ikke!")
        input("\nTryk Enter for at afslutte...")
        sys.exit(1)
    
    try:
        # Læs CSV med robust parser
        data = read_csv_robust(input_file)
        
        time = data['time']
        ch1_v = data['ch1_voltage']
        ch2_v = data['ch2_voltage']
        ch1_active = data['ch1_active']
        ch2_active = data['ch2_active']
        dt = data['dt']
        fs = data['sample_rate']
        
        # Hvis en kanal ikke er aktiv, opret nul-array
        if not ch1_active:
            print("\nADVARSEL: CH1 har ingen data - sætter til 0V")
            ch1_v = np.zeros_like(time)
            ch1_active = True
        
        if not ch2_active:
            print("ADVARSEL: CH2 har ingen data - sætter til 0V")
            ch2_v = np.zeros_like(time)
            ch2_active = True
        
        # Fjern NaN-værdier hvis de findes (kun for analyse, behold tid for struktur)
        ch1_v_clean = ch1_v[~np.isnan(ch1_v)] if np.any(np.isnan(ch1_v)) else ch1_v
        ch2_v_clean = ch2_v[~np.isnan(ch2_v)] if np.any(np.isnan(ch2_v)) else ch2_v
        time_clean = time[~np.isnan(time)] if np.any(np.isnan(time)) else time
        
        # Udskriv info
        print(f"\n--- Data information ---")
        print(f"Tidspunkter: {len(time)}")
        print(f"Sample rate: {fs/1000:.2f} kHz")
        print(f"Tidsinterval: {dt*1e6:.2f} µs")
        
        if ch1_active and len(ch1_v_clean) > 0:
            ch1_range = np.max(ch1_v_clean) - np.min(ch1_v_clean)
            ch1_has_signal = ch1_range > 0.001
            print(f"CH1: {len(ch1_v_clean)} samples, {'HAR SIGNAL' if ch1_has_signal else 'DC/konstant'}")
            if ch1_has_signal:
                print(f"     Spændingsområde: [{np.min(ch1_v_clean):.4f}, {np.max(ch1_v_clean):.4f}] V")
            else:
                print(f"     Værdi: {np.mean(ch1_v_clean):.4f} V")
        
        if ch2_active and len(ch2_v_clean) > 0:
            ch2_range = np.max(ch2_v_clean) - np.min(ch2_v_clean)
            ch2_has_signal = ch2_range > 0.001
            print(f"CH2: {len(ch2_v_clean)} samples, {'HAR SIGNAL' if ch2_has_signal else 'DC/konstant'}")
            if ch2_has_signal:
                print(f"     Spændingsområde: [{np.min(ch2_v_clean):.4f}, {np.max(ch2_v_clean):.4f}] V")
            else:
                print(f"     Værdi: {np.mean(ch2_v_clean):.4f} V")
        
        # Forbered data til gemning
        mat_data = {
            'time': time.reshape(-1, 1),
            'ch1_voltage': ch1_v.reshape(-1, 1),
            'ch2_voltage': ch2_v.reshape(-1, 1),
            'sample_rate': np.array([fs]),
            'dt': np.array([dt]),
            'ch1_active': np.array([ch1_active], dtype=bool),
            'ch2_active': np.array([ch2_active], dtype=bool),
            'timestamp': np.array([datetime.now().strftime('%Y-%m-%d %H:%M:%S')]),
            'filename': np.array([os.path.basename(input_file)])
        }
        
        # Gem fil
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_converted.mat"
        
        # Forsøg at gemme som MAT med scipy
        try:
            from scipy.io import savemat
            savemat(output_file, mat_data, do_compression=True)
            print(f"\n✅ Gemt som MAT-fil: {output_file}")
        except ImportError:
            # Fald tilbage til h5py eller NPZ
            if write_mat_simple(output_file, mat_data):
                print(f"\n✅ Gemt som MAT-fil (h5py): {output_file}")
            else:
                output_file = f"{base_name}_converted.npz"
                print(f"\n⚠️ Gemt som NPZ: {output_file}")
                print("  Installer scipy eller h5py for MAT-format: pip install scipy")
        
        print(f"\n{'='*60}")
        print("  KONVERTERING FULDFØRT!")
        print(f"{'='*60}")
        
        print("\n📁 NÆSTE SKRIDT:")
        print(f"  1. Åbn MATLAB")
        print(f"  2. Indlæs data med: load('{os.path.basename(output_file)}')")
        print(f"  3. Variable: time, ch1_voltage, ch2_voltage, sample_rate, dt")
        
    except Exception as e:
        print(f"\n❌ FEJL: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")
    input("Tryk Enter for at afslutte...")


if __name__ == "__main__":
    main()