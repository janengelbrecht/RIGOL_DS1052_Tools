# RIGOL_DS1052_Tools
Python and MATLAB tools for Rigol DS1052E

Dette repository indeholder filer der kan udvide funktionaliteten af RIgol DS1052E oscilloscopet.
Du overfører først WFM eller CSV filer via USB stik til computeren fra DS1052E.
Disse kan du så konvertere med python filerne.
Med MATLAB filerne kan du så lave avanceret analyse på oscilloscop data.
Matlab er valgt da de fleste ingeniørstuderende og professionelle ingeniører anvender Matlab.

<b>pyCSV2MAT.py:</b>

Dette program konverterer CSV-filer fra RIGOL oscilloskoper til MATLAB-format (.mat eller .npz). 
Programmet kan håndtere op til 2 kanaler (CH1 og CH2).

Krav
Påkrævet til MAT-filer:

pip install numpy scipy
Alternativ (kun NPZ-format):

pip install numpy

Sådan bruger du programmet
Metode 1: Kør med fil som argument

python pyCSV2MAT.py "sti/til/din_fil.csv"
Metode 2: Kør og indtast filsti

python pyCSV2MAT.py
Programmet spørger derefter efter filens sti. Du kan også trække filen ind i terminalvinduet.

Understøttede CSV-formater
Programmet genkender automatisk følgende kolonne-formater:
Format
Kolonner
Beskrivelse
4 kolonner
CH1 tid, CH1 spænding, CH2 tid, CH2 spænding
Fuld data for begge kanaler
3 kolonner
Fælles tid, CH1 spænding, CH2 spænding
Samme tidsakse for begge
2 kolonner
Tid, CH1 spænding
Kun CH1 (CH2 sættes til 0V)
Understøttede separatorer:
Komma ,
Semikolon ;
Tabulator \t
Mellemrum

Output
Programmet gemmer følgende variable:
Variabel
Beskrivelse
ch1_time
Tidsakse for kanal 1
ch1_voltage
Spændingsdata for kanal 1
ch2_time
Tidsakse for kanal 2
ch2_voltage
Spændingsdata for kanal 2
sample_rate
Beregnet sample rate (Hz)
timestamp
Konverteringstidspunkt
Outputfil: [originalt_navn]_converted.mat (eller .npz hvis scipy mangler)

Eksempel
Input CSV (maaling.csv):

0.000,0.00,0.000,0.00
0.001,0.52,0.001,0.51
0.002,1.04,0.002,1.03
0.003,1.56,0.003,1.55
Output i MATLAB:

load('maaling_converted.mat')
plot(ch1_time, ch1_voltage)
hold on
plot(ch2_time, ch2_voltage)
legend('CH1', 'CH2')
xlabel('Time (s)')
ylabel('Voltage (V)')

Fejlhåndtering
Problem
Løsning
File not found
Tjek filens sti og navn
Ingen data fundet
Tjek at CSV indeholder tal (ikke kun kommentarer)
ImportError: scipy
Installer scipy, eller brug den genererede .npz fil
Forventer 2,3 eller 4 kolonner
Tjek at CSV har korrekt antal kolonner

Noter
Kommentarlinjer startende med # ignoreres
Tomme linjer ignoreres
Hvis en kanal har konstant spænding (< 1 mV variation), sættes den til 0V
Sample rate beregnes automatisk ud fra tidsforskelle

<b>pyWFM2MAT.py:</b>

Dette Python-script konverterer Rigol oscilloskops WFM-filer (binære datafiler) til MATLAB .mat-filer, 
der er kompatible med MATLAB-scriptet rigol_signal_analysis2.m.
Scriptet ekstraherer spændingsdata fra kanal 1 og 2, beregner en tidsakse baseret på sample rate, 
og gemmer alt i et format MATLAB let kan indlæse.

Krav
Software
Python 3.x
Biblioteker:
numpy
scipy (modulet scipy.io)
tkinter (normalt inkluderet i Python-installationer)
Installation af afhængigheder

pip install numpy scipy
Hardware
Rigol oscilloskop (testet med DS1052E, men burde fungere med andre modeller)
WFM-fil gemt fra oscilloskopet

Sådan bruger du scriptet
Trin 1: Kør scriptet

python pyWFM2MAT.py

Trin 2: Vælg WFM-fil

Et vindue åbnes (filedialog).
Naviger til din .wfm-fil og vælg den.
Scriptet analyserer filen og viser information i terminalen:

Filstørrelse: 123456 bytes
Fundet 2 datasektioner - antager 2 kanaler
CH1: 12000 punkter
CH2: 12000 punkter

Trin 3: Kontroller sample rate
Scriptet forsøger automatisk at finde sample rate i filens header.
Eksempel på output:

Nuværende sample rate: 1000000.00 Hz
Vil du ændre sample rate? (j/n):
Indtast n for at beholde den fundne værdi.
Indtast j for selv at indtaste en ny sample rate (i Hz), f.eks. 500000 for 500 kHz.
Trin 4: Vælg output-fil
Et nyt vindue åbnes.
Vælg hvor den konverterede .mat-fil skal gemmes.
Standardnavnet er det samme som WFM-filen, men med .mat-endelse.
Trin 5: Afslutning
Scriptet gemmer filen og viser:
text
=== Gemt til MATLAB format ===
Variable i filen:
  - ch1_voltage: (12000, 1)
  - ch2_voltage: (12000, 1)
  - ch1_time: (12000, 1)
  - sample_rate: 1000000.0 Hz

=== Konvertering fuldført! ===

Output-filens indhold (MATLAB-format)
Variabelnavn          Beskrivelse                           Dimension
ch1_voltage           Spændingsdata fra kanal 1 (volt)      N×1 kolonnevektor
ch2_voltage           Spændingsdata fra kanal 2 (volt)      N×1 kolonnevektor
ch1_time              Tidsakse (sekunder)                   N×1 kolonnevektor
sample_rate           Sample rate (Hz)                      1×1 skalar

Note: Hvis kanalerne har forskellig længde, udfyldes den korte med NaN (Not-a-Number).

Sådan indlæser du filen i MATLAB
Når du har genereret .mat-filen, kan du indlæse den i MATLAB med:

load('din_fil.mat');
Derefter kan du f.eks. plotte data:

plot(ch1_time, ch1_voltage);
xlabel('Tid (s)');
ylabel('Spænding (V)');

Fejlfinding
Problem                                   Mulig årsag                           Løsning
"Kunne ikke finde nogen data i filen!"    WFM-formatet er ukendt                Tjek at filen er fra et Rigol oscilloskop. Prøv at gemme filen igen fra oscilloskopet.
Kun én kanal fundet                       Kun kanal 1 var aktiv ved optagelse   Scriptet gemmer kanal 2 som nulvektor. Det er normalt.
Forkert tidsakse                          Sample rate er forkert                Brug muligheden for at ændre sample rate manuelt. Tjek oscilloskopets indstillinger.
ImportError: No module named 'scipy'      SciPy ikke installeret                Kør pip install scipy

Sådan virker scriptet (teknisk baggrund)

Scriptet bruger tre metoder til at finde data:
Sektionsdetektion – Finder store sammenhængende datablokke (ikke-nul bytes).
Interleaving – Hvis data er lagret som CH1, CH2, CH1, CH2… deinterleaver scriptet.
Enkelt kanal – Finder den længste sekvens af ikke-nul bytes.

Spændingsskalering:   Værdi = (byte / 255) × 10 - 5 → giver området -5V til +5V (typisk for Rigol).

Bemærkninger
Scriptet er optimeret til Rigol DS1052E, men burde fungere med de fleste Rigol-modeller.
Tidsaksen ch1_time er baseret på længste kanal – begge kanaler får samme tidsakse.
Hvis du kun har brug for én kanal, ignoreres den anden automatisk.

Eksempel på komplet kørsel

=== Rigol WFM til MATLAB Konverterer ===
Optimeret til brug med rigol_signal_analysis2.m

Åbner: trace001.wfm
Filstørrelse: 24576 bytes
Fundet 2 datasektioner - antager 2 kanaler
CH1: 10240 punkter
CH2: 10240 punkter
Fundet sample rate: 500000.00 Hz

Nuværende sample rate: 500000.00 Hz
Vil du ændre sample rate? (j/n): n

=== Gemt til MATLAB format ===
Variable i filen:
  - ch1_voltage: (10240, 1)
  - ch2_voltage: (10240, 1)
  - ch1_time: (10240, 1)
  - sample_rate: 500000.0 Hz

=== Konvertering fuldført! ===
Filen er klar til brug i MATLAB med rigol_signal_analysis2.m

<b>rigol_signal_analasys.m:</b>

Dette MATLAB-script analyserer signaler fra RIGOL DS1052E oscilloskopet. Det understøtter import af data i tre formater:
Format    Beskrivelse
.mat      MATLAB datafil (anbefales)
.csv      Kommasepareret tekstfil
.wfm      RIGOL binary waveform fil

Scriptet genererer automatisk en HTML5-rapport med grafer og måleresultater.

2. Systemkrav
MATLAB R2019a eller nyere
Toolboxes:
Signal Processing Toolbox (til snr, sinad, thd, sfdr)
Statistics and Machine Learning Toolbox (valgfri, til median)

3. Konfiguration
Rediger cfg strukturen i starten af scriptet:

cfg.window_type     = 'hann';      % Vindue: 'hann', 'blackman', 'flat'
cfg.fft_nfft 	    = 2^16;        % FFT punkter (0 = auto)
cfg.harm_max        = 9;           % Antal harmoniske komponenter
cfg.spectrogram_win = 256;         % Spectrogram vindueslængde
cfg.spectrogram_ovl = 0.75;        % Overlap (0-1)
cfg.report_file     = 'Rigol_Analyserapport.html';
cfg.plot_theme      = 'dark';      % 'dark' eller 'light'
cfg.peak_hold_enable    = true;    % Peak-hold i FFT
cfg.noise_floor_enable  = true;    % Vis støjgulv
cfg.freq_max_khz        = 500;     % Maks frekvens i plot
cfg.mark_harmonics      = true;    % Markér harmoniske
cfg.fft_start_freq_hz   = 1;       % Startfrekvens i FFT plot

4. Sådan bruges scriptet

Trin 1: Forbered dine data
Fra oscilloskopet til .mat fil:

% Eksempel på hvordan data gemmes fra oscilloskopet
ch1_voltage = data_from_scope_ch1;
ch1_time    = time_vector;
ch2_voltage = data_from_scope_ch2;
ch2_time    = time_vector;  % Samme tidsbase som CH1
sample_rate = 1e6;          % 1 MSa/s
timestamp   = datestr(now);

save('mit_signal.mat', 'ch1_voltage', 'ch1_time', ...
     'ch2_voltage', 'ch2_time', 'sample_rate', 'timestamp');
Påkrævede felter i .mat fil:
ch1_voltage og ch1_time (obligatorisk)
ch2_voltage og ch2_time (valgfri)
sample_rate (valgfri - beregnes automatisk)
timestamp (valgfri)

Trin 2: Kør scriptet

Åbn MATLAB
Naviger til mappen med scriptet
Skriv i kommandovinduet:
rigol_signal_analysis
Vælg din datafil når dialogboksen åbnes

Trin 3: Afkod resultaterne

Scriptet åbner automatisk 4 figurer:
Figur    Indhold
1        Tidsdomæne for CH1 og CH2
2        FFT-spektrum med peak-hold og støjgulv
3        Harmonisk analyse (THD)
4        Krydskorrelation og Lissajous-figur

En HTML rapport gemmes i samme mappe som datafilen.

5. Forstå outputtet
Målte parametre
Parameter              Beskrivelse
Grundfrekvens          Dominerende frekvens (forbedret med parabolsk interpolation)
Vrms                   Effektivværdi (RMS)
Vp / Vpp               Topspænding / peak-to-peak
THD                    Total harmonisk distortion (dB)
SNR                    Signal-to-noise ratio (dB)
SINAD                  Signal-to-noise and distortion (dB)
ENOB                   Effektivt antal bits = (SINAD - 1.76)/6.02
Crest-faktor           Vp / Vrms
Formfaktor             Vrms / gennemsnit af absolut værdi

Faseforskel mellem CH1 og CH2
Faseforskel beregnes via krydskorrelation og vises som:
Positiv værdi: CH2 forsinker CH1
Negativ værdi: CH2 fører CH1

6. Fejlfinding
Problem
Løsning
"Ingen fil valgt"
Vælg en gyldig fil i dialogboksen
"Manglende CH1 data"
.mat fil skal indeholde ch1_voltage og ch1_time
CH2 viser 0V
CH2 data mangler eller er konstant - scriptet håndterer dette
FFT ser mærkelig ud
Tjek cfg.fft_start_freq_hz - sæt den til 1 eller højere
Lange beregningstider
Reducer cfg.fft_nfft (f.eks. til 2^14)
Faseplot vises ikke
CH2 har intet gyldigt signal

7. Filformater i detaljer
.mat format (anbefales)

% Påkrævet:
ch1_voltage  % Søjlevektor
ch1_time     % Søjlevektor

% Valgfrit:
ch2_voltage, ch2_time
sample_rate  % Hvis ikke angivet, beregnes fra ch1_time
timestamp    % Tekststreng med dato/tid
.csv format
Kolonne 1: CH1 tid (sekunder)
Kolonne 2: CH1 spænding (volt)
Kolonne 3: CH2 tid (sekunder) - valgfri
Kolonne 4: CH2 spænding (volt) - valgfri
.wfm format
RIGOL binært format med 1024 byte header
Automatisk detektering af sample rate og antal samples

8. Eksempel på konsoloutput

========================================================
  RIGOL DS1052E  –  Professionel Signalanalyse
========================================================

Indlæser: C:\Data\oscilloscope_2024.mat
CH2 data fundet

--- Data information ---
Sample rate      : 1000.000 kSa/s
CH1 samples      : 1000000
CH2 samples      : 1000000
Tidsstempel      : 2024-01-15 14:30:22

-- CH1 --
Grundfrekvens    : 1000.1234 Hz
Vrms (total)     : 3.5355 V
THD              : -45.23 dB
ENOB             : 7.82 bit

HTML rapport: C:\Data\Rigol_Analyserapport.html

9. Tip til bedre målinger
Brug tilstrækkelig sampling - Mindst 10× grundfrekvensen
Undgå clipping - Signalet bør være inden for oscilloskopets dynamikområde
Brug DC kobling for præcis DC-offset måling
Synkroniser kanalerne for præcis faseforskelsmåling
Vælg passende FFT vindue:
hann: Generelt formål
blackman: Bedre undertrykkelse af sidelober
flat: Mest præcis amplitudemåling

10. Kendte begrænsninger
Filer større end ~100 MB kan medføre hukommelsesproblemer
WFM format understøtter kun 16-bit int data
Faseforskelsmåling kræver synkroniserede kanaler

<b>rigol_signal_analasys2.m:</b>

Programmet indlæser en .mat-fil fra et Rigol oscilloskop, beregner en lang række signalparametre for CH1 og CH2, og genererer en HTML-rapport med:
Tidsdomæne (oscilloskopbillede)
Spektrumanalyse (FFT) for begge kanaler
Nøgletal: frekvens, THD, SNR, SINAD, SFDR, Vp, Vpp, Vrms, rise/fall time, duty cycle, crest- og formfaktor
Krydskanal-parametre: faseforskel og spændingsforstærkning 
Av

2. Krav til inputdata (Rigol .mat-fil)
Programmet forventer følgende variable i .mat-filen:
Variabelnavn                Beskrivelse
ch1_voltage                  Vektor med spændingsværdier for kanal 1
ch2_voltage                 Vektor med spændingsværdier for kanal 2
ch1_time                       Tidsvektor (sekunder)
sample_rate                 Samplerate i Hz

⚠️ Advarsel: Hvis variabelnavnene afviger, stopper programmet med en fejlmeddelelse.

3. Sådan kører du programmet
Åbn MATLAB.
Naviger til mappen, hvor rigol_signal_analysis2.m ligger.
Kør funktionen ved at skrive i Command Window:
matlab
RigolAnalyse
Vælg en .mat-fil når filvælgeren åbnes.
Programmet udfører analysen og åbner automatisk HTML-rapporten i din browser.

4. Output – Hvad får du?
4.1 Genererede filer (samme mappe som inputfilen)
Filnavn
Indhold
Rapport.html
Komplet målerapport (åbnes i browser)
scope_plot.png
Oscilloskopvisning (CH1 + CH2)
fft_plot.png
Spektrumanalyse (CH1 ovenfor, CH2 nedenfor)
4.2 Eksempler på beregnede parametre i rapporten
Kanal 1 (CH1)
Frekvens, THD (i % og dB), SNR, SINAD, SFDR
Vp, Vpp, Vrms, Rise time, Fall time, Duty cycle, Crest factor, Form factor
Kanal 2 (CH2)
Samme parametre som CH1 – hvis signalet ikke er konstant.
Krydskanal
Faseforskel (i grader, ±360°)
Spændingsforstærkning 
Av=Vp_CH2/Vp_CH1
AvdB=20 * log(Vp_CH2/Vp,CH1)

5. Håndtering af fejl og manglende signal
Situation
Programmet gør:
CH2 er konstant (ingen måling)
Spring over CH2-beregninger. Viser i rapporten: CH2 har intet signal
Grundfrekvens > 50 kHz
FFT-sektionen udelades (for at undgå uoverskuelige plots)
SNR / THD / SINAD kan ikke beregnes
Sætter værdien til NaN og viser "Kunne ikke beregnes" i rapporten
Filen indeholder ikke de rigtige variable
Stopper med en klar fejlmeddelelse

6. Tekniske detaljer (for viderekomne)
6.1 Beregningsmetoder (MATLAB-funktioner)
Parameter              Funktion brugt
Frekvens                 medfreq()
THD                         thd()
SNR                         snr()
SINAD                     sinad()
SFDR                       sfdr()
Rise/fall time          risetime(), falltime()
Duty cycle              dutycycle()
Faseforskel            xcorr() (cross-correlation)
6.2 FFT-visning
Grundtonen normaliseres til 0 dB.
Komponenter under SNR-støjgulvet sættes til støjgulvets niveau for et rent plot.
Frekvensaksen er logaritmisk (semilogx).
6.3 Rapportsprog
Rapporten er på dansk – både labels i grafer og tekst i HTML.

7. Fejlfinding
Problem
Løsningsforslag
Kunne ikke finde de korrekte variabler
Kontroller at .mat-filen indeholder ch1_voltage, ch2_voltage, ch1_time, sample_rate.
CH2 har konstant signal
Tilslut et signal til kanal 2 på oscilloskopet, eller ignorer advarslen.
FFT-sektionen mangler i rapporten
Grundfrekvensen overstiger 50 kHz. Accepter eller modificér grænsen i koden.
HTML-rapporten vises forkert
Sørg for at scope_plot.png og fft_plot.png ligger i samme mappe som HTML-filen.

8. Eksempel på brug (hurtig start)
Gem data fra Rigol oscilloskop som .mat via Rigol SCPI Suite.
Start MATLAB, kør RigolAnalyse.
Vælg filen Eksperiment1.mat.
Browser åbner med rapport – du ser f.eks.:
Faseforskel: 45,2°
Forstærkning: 2,34 (7,38 dB)
THD CH1: 0,05%
Brug tallene i din laboratorierapport.

9. Ændring af opsætning (avanceret)
Hvis du vil ændre f.eks.:
Maksimum frekvens for FFT (linje ca. 85 i koden):

if ~isnan(resCH1.Frekvens) && resCH1.Frekvens < 50000
Skift 50000 til din grænse.
Tærskel for "CH2 har signal" (linje ca. 25):

ch2_has_signal = (max(ch2) - min(ch2)) > 0.001;
Skift 0.001 til f.eks. 0.0005 for mere følsom detektion.
Standard støjgulv i FFT (linje i plotKlippetFFT):

if isnan(stoejgulv_dB) || stoejgulv_dB <= 0
    stoejgulv_dB = 80;
end
Skift 80 til en dB-værdi efter eget valg.

10. Bemærkninger
Programmet overskriver eksisterende .png-filer i samme mappe uden advarsel.

Det egentlige program:

# 📘 RIGOL DS1052E OSCILLOSCOPE DATA ANALYZER — BRUGERVEJLEDNING

**Version:** 1.0
**Platform:** Windows / Linux / macOS (Python 3.8+ og PySide6)
**Formål:** Professionel analyse af Rigol DS1052E oscilloskop-data (CSV-eksport)

---

## 📌 INDHOLD

1. Introduktion
2. Installation og afhængigheder
3. Opstart
4. Overordnet layout
5. Fane 1: Measurements
6. Fane 2: Oscilloscope
7. Fane 3: Spectrum
8. Fejlfinding
9. Tastaturgenveje

---

## 1. INTRODUKTION

**Rigol DS1052E Analyzer** er et desktopværktøj til avanceret signalanalyse baseret på CSV-data.

### Funktioner

* 15+ elektriske parametre (Vp, Vpp, Vrms, frekvens, THD, SNR, ENOB m.fl.)
* Interaktiv bølgeformvisning med zoom og cursorer
* FFT-baseret spektrumanalyse (op til 40 harmoniske)
* Kanalrelationer: fase og forstærkning

**Signalbehandling:**
Automatisk kompensation for 8-bit ADC via Savitzky-Golay filtrering

---

## 2. INSTALLATION OG AFHÆNGIGHEDER

| Pakke       | Installation        | Funktion         |
| ----------- | ------------------- | ---------------- |
| Python 3.8+ | python.org          | Runtime          |
| PySide6     | pip install PySide6 | GUI              |
| numpy       | pip install numpy   | Numerik          |
| scipy       | pip install scipy   | Signalbehandling |

### Verifikation

```bash
python -c "import PySide6, numpy, scipy; print('OK')"
```

---

## 3. OPSTART

```bash
python rigol_analyzer.py
```

### Understøttede formater

* CSV (2–4 kolonner)
* WFM (begrænset support)

Efter indlæsning opdateres alle analysefaner automatisk.

---

## 4. OVERORDNET LAYOUT

```
+---------------------------------------------------------------+
| HEADER: RIGOL DS1052E ANALYZER                                |
+---------------------------------------------------------------+
| [MEASUREMENTS] [OSCILLOSCOPE] [SPECTRUM]                      |
|                                                               |
|                   Aktivt analysevindue                        |
|                                                               |
+---------------------------------------------------------------+
| STATUS BAR                                                    |
+---------------------------------------------------------------+
```

**Header:** Filinfo, kanaler, sample rate
**Faner:** Navigerer mellem analysemoduler
**Statuslinje:** Systemstatus og fejlmeddelelser

---

## 5. FANE 1: MEASUREMENTS

### Struktur

* CH1 (gul)
* CH2 (cyan)
* Signal Relations

### Parametre

| Parameter    | Beskrivelse                   | Enhed |
| ------------ | ----------------------------- | ----- |
| Vp           | Peak spænding                 | V     |
| Vpp          | Peak-to-peak                  | V     |
| Vrms         | RMS over hele perioder        | V     |
| Frequency    | FFT-baseret med interpolation | Hz    |
| Rise/Fall    | 10–90 % transitions           | s     |
| Duty cycle   | Aktiv tidsandel               | %     |
| Crest factor | Vp / Vrms                     | –     |
| Form factor  | Vrms / rectified              | –     |
| THD          | Total harmonisk forvrængning  | %/dB  |
| SNR          | Signal/støj                   | dB    |
| SINAD        | Signal + støj + forvrængning  | dB    |
| ENOB         | Effektive bits                | bit   |

### Kanalrelationer

| Parameter       | Beskrivelse          |
| --------------- | -------------------- |
| Frequency match | ≤0,1 % afvigelse     |
| Phase           | Forskydning (grader) |
| Av              | Lineær gain          |
| AvdB            | Gain i dB            |

---

## 6. FANE 2: OSCILLOSCOPE

### Kontroller

| Kontrol | Funktion                       |
| ------- | ------------------------------ |
| Zoom    | 0,1× – 20×                     |
| Pan     | 0–100 %                        |
| Mus     | LMB = Cursor A, RMB = Cursor B |

### Cursorer

* Cursor A (rød)
* Cursor B (blå)

**Viser:**

* ΔT (tidsforskel)
* f = 1/ΔT

### Visning

* 10×8 divisionsgitter
* CH1 (gul), CH2 (cyan)
* Automatisk V/div skalering

---

## 7. FANE 3: SPECTRUM

### Karakteristika

* dBV-skala: –90 til +10 dBV
* Log frekvensakse
* FFT op til Nyquist

### Harmoniske

* Op til 40 harmoniske
* H1 fremhævet
* Markører med indeks

### Begrænsning

* Analyse kun < 50 kHz

### Eksempel

```
CH1: f0 = 1000 Hz
H1: 1000 Hz  -3.5 dBV
H2: 2000 Hz -45.2 dBV
H3: 3000 Hz -52.1 dBV
```

---

## 8. FEJLFINDING

### Problem: Manglende pakker

```bash
pip install PySide6 numpy scipy
```

### Problem: CSV kan ikke læses

Mulige årsager:

* Forkert format
* Korrupt fil
* Encoding mismatch

### Problem: Ingen harmonisk analyse

* Signal > 50 kHz

### Problem: Fase = N/A

* Frekvenser matcher ikke

### Problem: Forkert RMS

* Beregning kræver detekterbar frekvens

---

## 9. TASTATURGENVEJE

| Genvej | Funktion |
| ------ | -------- |
| Ctrl+O | Åbn fil  |
| Ctrl+Q | Afslut   |

---

## 📌 AFSLUTTENDE BEMÆRKNINGER

Dette værktøj udvider oscilloskopets analysekapacitet markant ved at kombinere:

* Tidsdomæne
* Frekvensdomæne
* Statistisk analyse

**Resultat:** Hurtigere, mere præcise målinger og dybere indsigt.

---

📢 Rapportér fejl via projektets issue-tracker.

HTML-rapporten åbnes automatisk med MATLABs web-kommando.
Alle grafer har mørk baggrund i MATLAB-figuren, men rapportens baggrund er lys for læsevenlighed.
