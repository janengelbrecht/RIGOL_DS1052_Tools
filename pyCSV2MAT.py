#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV to MATLAB Converter - Enkel version
"""

import numpy as np
import os
import sys

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

def read_csv_simple(csv_path):
    """Læs CSV fil på enkel vis"""
    print(f"\nLæser: {csv_path}")
    
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    
    # Fjern kommentarer og tomme linjer
    data_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            data_lines.append(line)
    
    if not data_lines:
        raise ValueError("Ingen data fundet i CSV filen")
    
    # Find separator
    first_line = data_lines[0]
    if ',' in first_line:
        sep = ','
    elif ';' in first_line:
        sep = ';'
    elif '\t' in first_line:
        sep = '\t'
    else:
        sep = ' '
    
    print(f"Brugt separator: '{sep}'")
    
    # Parse data
    data = []
    for line in data_lines:
        parts = line.split(sep)
        # Fjern tomme strenge
        parts = [p.strip() for p in parts if p.strip()]
        if parts:
            try:
                row = [float(p) for p in parts]
                data.append(row)
            except:
                continue
    
    if not data:
        raise ValueError("Kunne ikke parse data fra CSV filen")
    
    # Konverter til numpy array
    data = np.array(data)
    print(f"Data shape: {data.shape}")
    
    return data

def main():
    print("\n" + "="*60)
    print("  RIGOL CSV til MATLAB Konverter")
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
        # Læs CSV
        data = read_csv_simple(input_file)
        n_rows, n_cols = data.shape
        
        print(f"\nFundet {n_cols} kolonner og {n_rows} rækker")
        
        # Ekstraher kanaler
        if n_cols >= 4:
            print("Format: CH1 tid, CH1 spænding, CH2 tid, CH2 spænding")
            ch1_t = data[:, 0]
            ch1_v = data[:, 1]
            ch2_t = data[:, 2]
            ch2_v = data[:, 3]
        elif n_cols == 3:
            print("Format: Fælles tid, CH1 spænding, CH2 spænding")
            ch1_t = data[:, 0]
            ch1_v = data[:, 1]
            ch2_t = data[:, 0].copy()
            ch2_v = data[:, 2]
        elif n_cols == 2:
            print("Format: Kun CH1 (tid, spænding)")
            ch1_t = data[:, 0]
            ch1_v = data[:, 1]
            ch2_t = ch1_t.copy()
            ch2_v = np.zeros_like(ch1_v)
            print("  CH2 sættes til 0V")
        else:
            raise ValueError(f"Forventer 2, 3 eller 4 kolonner, fik {n_cols}")
        
        # Tjek for reelt signal
        ch1_range = np.max(ch1_v) - np.min(ch1_v)
        ch2_range = np.max(ch2_v) - np.min(ch2_v)
        
        ch1_has_signal = ch1_range > 0.001
        ch2_has_signal = ch2_range > 0.001
        
        # Hvis CH1 er konstant, lav dummy
        if not ch1_has_signal:
            print("\nADVARSEL: CH1 har konstant/ingen signal - sætter til 0V")
            ch1_v = np.zeros_like(ch1_v)
        
        # Hvis CH2 er konstant, lav dummy
        if not ch2_has_signal:
            print("ADVARSEL: CH2 har konstant/ingen signal - sætter til 0V")
            ch2_v = np.zeros_like(ch2_v)
        
        # Beregn sample rate
        if len(ch1_t) > 1:
            dt = np.mean(np.diff(ch1_t))
            fs = 1.0 / dt if dt > 0 else 1000000
        else:
            fs = 1000000
        
        # Udskriv info
        print(f"\n--- Resultater ---")
        print(f"Sample rate: {fs/1000:.2f} kHz")
        print(f"CH1: {len(ch1_v)} samples, {'HAR SIGNAL' if ch1_has_signal else 'DC 0V'}")
        if ch1_has_signal:
            print(f"     Spændingsområde: [{np.min(ch1_v):.4f}, {np.max(ch1_v):.4f}] V")
        print(f"CH2: {len(ch2_v)} samples, {'HAR SIGNAL' if ch2_has_signal else 'DC 0V'}")
        if ch2_has_signal:
            print(f"     Spændingsområde: [{np.min(ch2_v):.4f}, {np.max(ch2_v):.4f}] V")
        
        # Forbered data til gemning
        from datetime import datetime
        mat_data = {
            'ch1_time': ch1_t.reshape(-1, 1),
            'ch1_voltage': ch1_v.reshape(-1, 1),
            'ch2_time': ch2_t.reshape(-1, 1),
            'ch2_voltage': ch2_v.reshape(-1, 1),
            'sample_rate': np.array([fs]),
            'timestamp': np.array([datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        }
        
        # Gem fil
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_converted.mat"
        
        # Forsøg at gemme som MAT
        try:
            from scipy.io import savemat
            savemat(output_file, mat_data, do_compression=True)
            print(f"\n✅ Gemt som MAT-fil: {output_file}")
        except ImportError:
            # Fald tilbage til NPZ
            output_file = f"{base_name}_converted.npz"
            np.savez_compressed(output_file, **mat_data)
            print(f"\n⚠️ Scipy ikke installeret - gemt som NPZ: {output_file}")
            print("  Installer scipy med: pip install scipy")
        
        print(f"\n{'='*60}")
        print("  KONVERTERING FULDFØRT!")
        print(f"{'='*60}")
        
        print("\n📁 NÆSTE SKRIDT:")
        print(f"  1. Åbn MATLAB")
        print(f"  2. Kør: rigol_signal_analysis")
        print(f"  3. Vælg filen: {output_file}")
        
    except Exception as e:
        print(f"\n❌ FEJL: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")
    input("Tryk Enter for at afslutte...")

if __name__ == "__main__":
    main()