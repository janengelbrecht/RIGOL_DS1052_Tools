import numpy as np
import scipy.io as sio
from tkinter import filedialog, Tk
import os

def read_rigol_wfm_enhanced(filepath):
    """
    Læser Rigol WFM fil og ekstraherer data for begge kanaler.
    """
    data_ch1 = None
    data_ch2 = None
    
    with open(filepath, 'rb') as f:
        content = f.read()
        
    print(f"Filstørrelse: {len(content)} bytes")
    
    # Forsøg at finde datasektioner for begge kanaler
    # Rigol DS1052E gemmer ofte CH1 og CH2 data efter hinanden eller interleaved
    
    # Metode 1: Prøv at finde to store datablokke
    sections = []
    in_section = False
    section_start = 0
    
    for i in range(len(content) - 1):
        if content[i] == 0 and content[i+1] != 0 and not in_section:
            in_section = True
            section_start = i + 1
        elif content[i] != 0 and content[i+1] == 0 and in_section:
            in_section = False
            section_length = i - section_start + 1
            if section_length > 500:  # Minimum datasektion længde
                sections.append((section_start, section_length))
    
    if len(sections) >= 2:
        print(f"Fundet {len(sections)} datasektioner - antager 2 kanaler")
        # Tag de to største sektioner som CH1 og CH2
        sections.sort(key=lambda x: x[1], reverse=True)
        
        # CH1
        start1, len1 = sections[0]
        raw_ch1 = content[start1:start1+len1]
        data_ch1 = (np.frombuffer(raw_ch1, dtype=np.uint8).astype(np.float64) / 255.0) * 10.0 - 5.0
        print(f"CH1: {len(data_ch1)} punkter")
        
        # CH2
        start2, len2 = sections[1]
        raw_ch2 = content[start2:start2+len2]
        data_ch2 = (np.frombuffer(raw_ch2, dtype=np.uint8).astype(np.float64) / 255.0) * 10.0 - 5.0
        print(f"CH2: {len(data_ch2)} punkter")
    
    else:
        # Metode 2: Prøv at de-interleave data (CH1, CH2, CH1, CH2...)
        # Spring header over (typisk 512 eller 1024 bytes)
        for header_size in [0, 256, 512, 1024, 2048]:
            if header_size < len(content):
                test_data = content[header_size:header_size+2000]
                even = test_data[0::2]
                odd = test_data[1::2]
                
                even_nonzero = sum(1 for b in even if b != 0)
                odd_nonzero = sum(1 for b in odd if b != 0)
                
                if even_nonzero > len(even) * 0.3 and odd_nonzero > len(odd) * 0.3:
                    print(f"Fundet interleaved data ved header_size={header_size}")
                    all_data = content[header_size:]
                    # Sørg for lige antal bytes
                    if len(all_data) % 2 != 0:
                        all_data = all_data[:-1]
                    
                    raw_ch1 = all_data[0::2]
                    raw_ch2 = all_data[1::2]
                    
                    data_ch1 = (np.frombuffer(raw_ch1, dtype=np.uint8).astype(np.float64) / 255.0) * 10.0 - 5.0
                    data_ch2 = (np.frombuffer(raw_ch2, dtype=np.uint8).astype(np.float64) / 255.0) * 10.0 - 5.0
                    
                    print(f"CH1 (interleaved): {len(data_ch1)} punkter")
                    print(f"CH2 (interleaved): {len(data_ch2)} punkter")
                    break
    
    # Hvis stadig ingen data, prøv at finde én kanal
    if data_ch1 is None:
        # Find længste sekvens af ikke-null bytes
        max_run = 0
        run_start = 0
        current_run = 0
        
        for i, byte in enumerate(content):
            if byte != 0:
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
                    run_start = i - current_run + 1
            else:
                current_run = 0
        
        if max_run > 100:
            raw_data = content[run_start:run_start+max_run]
            data_ch1 = (np.frombuffer(raw_data, dtype=np.uint8).astype(np.float64) / 255.0) * 10.0 - 5.0
            print(f"Fundet én kanal: {len(data_ch1)} punkter")
            data_ch2 = np.zeros(len(data_ch1))  # Tom kanal 2
    
    return data_ch1, data_ch2

def extract_sample_rate(filepath):
    """Ekstraher sample rate fra WFM fil hvis muligt."""
    sample_rate = 1000000  # Default 1 MHz
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read(2000)
            text_content = content.decode('ascii', errors='ignore')
            
            import re
            patterns = [
                r'SampleRate[:\s]*([\d\.]+(?:e[+-]?\d+)?)',
                r'SRA[:\s]*([\d\.]+(?:e[+-]?\d+)?)',
                r'Rate[:\s]*([\d\.]+(?:e[+-]?\d+)?)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    val = float(match.group(1))
                    if val < 1000:
                        val *= 1e6
                    sample_rate = val
                    print(f"Fundet sample rate: {sample_rate:.2f} Hz")
                    break
    except:
        pass
    
    return sample_rate

def save_for_matlab(ch1_data, ch2_data, sample_rate, filepath):
    """
    Gemmer data i præcis det format som MATLAB koden forventer:
    - ch1_voltage
    - ch2_voltage  
    - ch1_time
    - sample_rate
    """
    # Sørg for at data er kolonnevektorer
    ch1_data = np.array(ch1_data).reshape(-1, 1)
    ch2_data = np.array(ch2_data).reshape(-1, 1)
    
    # Opret tidsakse (baseret på længste kanal)
    max_len = max(len(ch1_data), len(ch2_data))
    time_step = 1.0 / sample_rate
    ch1_time = np.arange(0, max_len * time_step, time_step).reshape(-1, 1)
    
    # Hvis kanaler har forskellig længde, pad med NaN
    if len(ch1_data) < max_len:
        ch1_data = np.vstack([ch1_data, np.full((max_len - len(ch1_data), 1), np.nan)])
    if len(ch2_data) < max_len:
        ch2_data = np.vstack([ch2_data, np.full((max_len - len(ch2_data), 1), np.nan)])
    
    # Opret dictionary med præcis de navne MATLAB forventer
    mat_dict = {
        'ch1_voltage': ch1_data,
        'ch2_voltage': ch2_data,
        'ch1_time': ch1_time,
        'sample_rate': np.array([sample_rate])
    }
    
    # Gem som .mat fil
    sio.savemat(filepath, mat_dict, do_compression=True)
    
    print(f"\n=== Gemt til MATLAB format ===")
    print(f"Variable i filen:")
    print(f"  - ch1_voltage: {ch1_data.shape}")
    print(f"  - ch2_voltage: {ch2_data.shape}")
    print(f"  - ch1_time: {ch1_time.shape}")
    print(f"  - sample_rate: {sample_rate} Hz")

def main():
    root = Tk()
    root.withdraw()
    
    print("=== Rigol WFM til MATLAB Konverterer ===")
    print("Optimeret til brug med rigol_signal_analysis2.m\n")
    
    # Vælg WFM fil
    input_file = filedialog.askopenfilename(
        title="Vælg Rigol WFM fil",
        filetypes=[("WFM filer", "*.wfm"), ("Alle filer", "*.*")]
    )
    
    if not input_file:
        print("Ingen fil valgt.")
        root.destroy()
        return
    
    print(f"\nÅbner: {os.path.basename(input_file)}")
    
    # Ekstraher data
    ch1_data, ch2_data = read_rigol_wfm_enhanced(input_file)
    
    if ch1_data is None:
        print("Kunne ikke finde nogen data i filen!")
        root.destroy()
        return
    
    # Ekstraher sample rate
    sample_rate = extract_sample_rate(input_file)
    
    # Spørg om sample rate
    print(f"\nNuværende sample rate: {sample_rate:.2f} Hz")
    response = input("Vil du ændre sample rate? (j/n): ").strip().lower()
    if response == 'j':
        try:
            new_rate = float(input("Indtast ny sample rate (Hz): "))
            sample_rate = new_rate
        except:
            print("Beholder nuværende sample rate")
    
    # Vælg output fil
    output_file = filedialog.asksaveasfilename(
        title="Gem MATLAB fil",
        defaultextension=".mat",
        initialfile=os.path.splitext(input_file)[0] + '.mat',
        filetypes=[("MATLAB MAT filer", "*.mat"), ("Alle filer", "*.*")]
    )
    
    if not output_file:
        print("Ingen gemmeplacering valgt.")
        root.destroy()
        return
    
    # Gem til MATLAB format
    save_for_matlab(ch1_data, ch2_data, sample_rate, output_file)
    
    print("\n=== Konvertering fuldført! ===")
    print(f"Filen er klar til brug i MATLAB med rigol_signal_analysis2.m")
    
    root.destroy()

if __name__ == "__main__":
    main()