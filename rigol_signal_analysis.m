% =========================================================================
%  RIGOL DS1052E - PROFESSIONEL SIGNALANALYSE (OPDATERET)
%  Rigol_Signal_Analysis.m
% =========================================================================

clear; close all; clc;

% =========================================================================
%  KONFIGURATION
% =========================================================================
cfg.window_type     = 'hann';
cfg.fft_nfft 	    = 2^16;   % 65536 punkter
cfg.harm_max        = 9;
cfg.spectrogram_win = 256;
cfg.spectrogram_ovl = 0.75;
cfg.report_file     = 'Rigol_Analyserapport.html';
cfg.plot_theme      = 'dark';
cfg.ch1_color       = [0.2 1.0 0.5];
cfg.ch2_color       = [0.3 0.7 1.0];
cfg.accent_color    = [1.0 0.8 0.0];

cfg.peak_hold_enable    = true;
cfg.noise_floor_enable  = true;
cfg.freq_max_khz        = 500;
cfg.mark_harmonics      = true;
cfg.fft_start_freq_hz   = 1;

% =========================================================================
%  INDLÆS DATA
% =========================================================================
fprintf('\n========================================================\n');
fprintf('  RIGOL DS1052E  –  Professionel Signalanalyse\n');
fprintf('========================================================\n\n');

[fname, fpath] = uigetfile( ...
    {'*.mat','MATLAB datafil (*.mat)'; ...
     '*.csv','CSV datafil (*.csv)'; ...
     '*.wfm','Rigol WFM fil (*.wfm)'; ...
     '*.*', 'Alle filer (*.*)'}, ...
    'Vælg Rigol eksportfil');

if isequal(fname, 0)
    error('Ingen fil valgt – analysen afbrydes.');
end
full_path = fullfile(fpath, fname);
fprintf('Indlæser: %s\n', full_path);

[~, ~, ext] = fileparts(fname);

ch1_v = []; ch1_t = []; ch2_v = []; ch2_t = []; Fs = []; ts = [];

if strcmpi(ext, '.mat')
    raw = load(full_path);
    
    has_ch1_voltage = isfield(raw, 'ch1_voltage');
    has_ch2_voltage = isfield(raw, 'ch2_voltage');
    has_ch1_time = isfield(raw, 'ch1_time');
    has_ch2_time = isfield(raw, 'ch2_time');
    has_sample_rate = isfield(raw, 'sample_rate');
    
    if has_ch1_voltage && has_ch1_time
        ch1_v = double(raw.ch1_voltage(:));
        ch1_t = double(raw.ch1_time(:));
    else
        error('Manglende CH1 data');
    end
    
    if has_ch2_voltage
        ch2_v = double(raw.ch2_voltage(:));
        fprintf('CH2 data fundet\n');
    else
        fprintf('ADVARSEL: Ingen CH2 data – sætter til 0V\n');
        ch2_v = zeros(size(ch1_v));
    end
    
    if has_ch2_time
        ch2_t = double(raw.ch2_time(:));
    else
        ch2_t = ch1_t;
    end
    
    if has_sample_rate
        Fs = double(raw.sample_rate);
    else
        if length(ch1_t) > 1
            Fs = 1 / median(diff(ch1_t));  % Rettet: median i stedet for mean
        else
            Fs = 1000000;
        end
    end
    
    if isfield(raw, 'timestamp')
        ts = string(raw.timestamp);
    else
        ts = string(datetime('now','Format','yyyy-MM-dd HH:mm:ss'));
    end

elseif strcmpi(ext, '.wfm')
    fprintf('Format: Rigol WFM binary-fil\n');
    
    fid = fopen(full_path, 'rb', 'ieee-le');
    if fid == -1
        error('Kunne ikke åbne WFM fil');
    end
    
    fseek(fid, 0, 'bof');
    header = fread(fid, 1024, 'uint8');
    header_str = char(header');
    
    fs_match = regexp(header_str, 'SampleRate[=:]\s*(\d+)', 'tokens');
    if ~isempty(fs_match)
        Fs = str2double(fs_match{1}{1});
    else
        Fs = 1000000;
    end
    
    samples_match = regexp(header_str, 'Samples[=:]\s*(\d+)', 'tokens');
    if ~isempty(samples_match)
        num_samples = str2double(samples_match{1}{1});
    else
        num_samples = 10000;
    end
    
    fseek(fid, 1024, 'bof');
    ch1_raw = fread(fid, num_samples, 'int16');
    ch1_v = double(ch1_raw) / 32768 * 10;
    
    dt = 1/Fs;
    ch1_t = (0:length(ch1_v)-1)' * dt;
    
    fseek(fid, 1024 + num_samples*2, 'bof');
    ch2_raw = fread(fid, num_samples, 'int16');
    if ~isempty(ch2_raw)
        ch2_v = double(ch2_raw) / 32768 * 10;
        ch2_t = ch1_t;
    else
        fprintf('ADVARSEL: Ingen CH2 data – sætter til 0V\n');
        ch2_v = zeros(size(ch1_v));
        ch2_t = ch1_t;
    end
    
    ts = string(datetime('now','Format','yyyy-MM-dd HH:mm:ss'));
    fclose(fid);
    
elseif strcmpi(ext, '.csv')
    fprintf('Format: CSV datafil\n');
    
    try
        T = readtable(full_path, 'NumHeaderLines', 1, 'ReadVariableNames', false);
        data = table2array(T);
    catch
        T = readtable(full_path, 'ReadVariableNames', false);
        data = table2array(T);
    end
    
    n_cols = size(data, 2);
    
    if n_cols >= 2
        ch1_t = data(:,1);
        ch1_v = data(:,2);
        fprintf('CH1 data indlæst\n');
    else
        error('CSV filen har ikke tilstrækkelige kolonner');
    end
    
    if n_cols >= 4
        ch2_t = data(:,3);
        ch2_v = data(:,4);
        fprintf('CH2 data indlæst\n');
    elseif n_cols == 3
        ch2_v = data(:,3);
        ch2_t = ch1_t;
        fprintf('CH2 data indlæst fra kolonne 3\n');
    else
        fprintf('ADVARSEL: Kun CH1 data – sætter CH2 til 0V\n');
        ch2_v = zeros(size(ch1_v));
        ch2_t = ch1_t;
    end
    
    valid1 = ~isnan(ch1_t) & ~isnan(ch1_v);
    ch1_t = ch1_t(valid1);
    ch1_v = ch1_v(valid1);
    
    valid2 = ~isnan(ch2_t) & ~isnan(ch2_v);
    if any(valid2)
        ch2_t = ch2_t(valid2);
        ch2_v = ch2_v(valid2);
    else
        ch2_v = zeros(size(ch1_v));
        ch2_t = ch1_t;
    end
    
    if length(ch1_t) > 1
        Fs = 1 / median(diff(ch1_t));  % Rettet: median i stedet for mean
    else
        Fs = 1000000;
    end
    
    ts = string(datetime('now','Format','yyyy-MM-dd HH:mm:ss'));
else
    error('Ukendt filformat: %s', ext);
end

if isempty(ch2_v) || all(ch2_v == 0) || (max(ch2_v) - min(ch2_v)) < 1e-6
    ch2_v = zeros(size(ch1_v));
    ch2_t = ch1_t;
    ch2_has_signal = false;
    fprintf('INFO: CH2 sættes til 0V (intet signal)\n');
else
    ch2_has_signal = true;
    fprintf('CH2 har gyldigt signal\n');
end

min_len = min(length(ch1_v), length(ch2_v));
ch1_v = ch1_v(1:min_len);
ch1_t = ch1_t(1:min_len);
ch2_v = ch2_v(1:min_len);
ch2_t = ch2_t(1:min_len);

has_ch1 = numel(ch1_v) > 4;
has_ch2 = ch2_has_signal && numel(ch2_v) > 4;

fprintf('\n--- Data information ---\n');
fprintf('Sample rate      : %.3f kSa/s\n', Fs/1e3);
fprintf('CH1 samples      : %d\n', numel(ch1_v));
fprintf('CH2 samples      : %d\n', numel(ch2_v));
fprintf('Tidsstempel      : %s\n\n', ts);

% =========================================================================
%  TEMA-OPSÆTNING
% =========================================================================
if strcmp(cfg.plot_theme, 'dark')
    th.fig_bg  = [0.12 0.12 0.14];
    th.ax_bg   = [0.08 0.08 0.10];
    th.fg      = [0.93 0.93 0.93];
    th.grid    = [0.25 0.25 0.28];
    th.title_c = [1.00 1.00 1.00];
else
    th.fig_bg  = [0.96 0.96 0.98];
    th.ax_bg   = [1.00 1.00 1.00];
    th.fg      = [0.10 0.10 0.10];
    th.grid    = [0.80 0.80 0.80];
    th.title_c = [0.05 0.05 0.05];
end

applyTheme = @(ax) set(ax, ...
    'Color', th.ax_bg, 'XColor', th.fg, 'YColor', th.fg, ...
    'GridColor', th.grid, 'MinorGridColor', th.grid, ...
    'GridAlpha', 0.4, 'XGrid','on','YGrid','on');

figStyle = @(f) set(f, 'Color', th.fig_bg, ...
    'Units','normalized', 'Position',[0.02 0.03 0.96 0.94]);

% =========================================================================
%  HJÆLPEFUNKTIONER
% =========================================================================

function [freqs, mag_db, phase_deg, nfft] = compute_fft(signal, Fs, win_type, nfft_in)
    N    = numel(signal);
    if nfft_in == 0
        nfft = 2^nextpow2(N);
    else
        nfft = nfft_in;
    end
    switch lower(win_type)
        case 'hann',     w = hann(N);
        case 'blackman', w = blackman(N);
        case 'flat',     w = flattopwin(N);
        otherwise,       w = ones(N,1);
    end
    w = w(:);
    X     = fft((signal(:) - mean(signal)) .* w, nfft);
    half  = 1:floor(nfft/2)+1;
    mag   = 2*abs(X(half)) / sum(w);
    mag(1)= mag(1)/2;
    freqs = (0:numel(half)-1) * Fs / nfft;
    mag_db    = 20*log10(max(mag, 1e-12));
    phase_deg = angle(X(half)) * 180/pi;
end

function stats = signal_stats(v, Fs)
    stats.N       = numel(v);
    stats.Fs      = Fs;
    stats.vdc     = mean(v);
    v_ac          = v - stats.vdc;
    stats.vrms    = rms(v(:));
    stats.vrms_ac = rms(v_ac(:));
    stats.vp      = max(abs(v));
    stats.vpp     = max(v) - min(v);
    stats.crest   = stats.vp / max(stats.vrms_ac, 1e-12);
    stats.form    = stats.vrms_ac / max(mean(abs(v_ac)), 1e-12);
    
    [freqs, mag, ~, ~] = compute_fft(v, Fs, 'hann', 0);
    search_idx = find(freqs >= 20 & freqs <= 50000);
    if isempty(search_idx)
        search_idx = 2:min(5000, length(mag));
    end
    [~, idx] = max(mag(search_idx));
    
    % ========= FORBEDRET FREKVENSESTIMERING =========
    % Parabolsk interpolation omkring peak for bedre nøjagtighed
    global_idx = search_idx(idx);
    if global_idx > 1 && global_idx < length(mag)
        % Tag tre punkter omkring peak
        y_vals = mag(global_idx-1:global_idx+1);
        x_vals = freqs(global_idx-1:global_idx+1);
        % Fit andengradspolynomium
        p = polyfit(x_vals, y_vals, 2);
        % Toppunktets position
        if p(1) < 0
            f_peak = -p(2) / (2 * p(1));
            % Begræns til rimeligt interval
            f_peak = max(x_vals(1), min(x_vals(3), f_peak));
            stats.freq = f_peak;
        else
            stats.freq = freqs(global_idx);
        end
    else
        stats.freq = freqs(global_idx);
    end
    % ================================================
    
    stats.period = 1 / max(stats.freq, 1e-6);
    
    try
        stats.snr   = snr(v(:), Fs);
        stats.sinad = sinad(v(:), Fs);
        stats.thd   = thd(v(:), Fs) * -1;
        stats.sfdr  = sfdr(v(:), Fs);
        stats.enob  = (stats.sinad - 1.76) / 6.02;
    catch
        stats.snr   = NaN;
        stats.sinad = NaN;
        stats.thd   = NaN;
        stats.sfdr  = NaN;
        stats.enob  = NaN;
    end
end

% =========================================================================
%  BEREGN STATISTIK
% =========================================================================
fprintf('Beregner signalstatistik...\n');
st1 = signal_stats(ch1_v, Fs);
if has_ch2
    st2 = signal_stats(ch2_v, Fs);
else
    st2 = st1;
    st2.vp = 0;
    st2.vpp = 0;
    st2.vrms = 0;
    st2.vrms_ac = 0;
    st2.freq = 0;
    st2.thd = NaN;
end

[f1, mg1, ph1, nfft1] = compute_fft(ch1_v, Fs, cfg.window_type, cfg.fft_nfft);
if has_ch2
    [f2, mg2, ph2, nfft2] = compute_fft(ch2_v, Fs, cfg.window_type, cfg.fft_nfft);
else
    f2 = f1; mg2 = zeros(size(mg1)); ph2 = zeros(size(ph1));
end

% =========================================================================
%  FIGUR 1: TIDSDOMÆNE
% =========================================================================
fprintf('Genererer tidsdomæne-plot...\n');
fig1 = figure('Name','Tidsdomæne','NumberTitle','off');
figStyle(fig1);

ax = subplot(2, 1, 1);
plot(ch1_t*1e3, ch1_v, 'Color', cfg.ch1_color, 'LineWidth', 0.9);
applyTheme(ax);
xlabel('Tid [ms]', 'Color', th.fg);
ylabel('Spænding [V]', 'Color', th.fg);
title(sprintf('CH1 – Tidsdomæne (Vrms = %.4f V, f0 = %.3f Hz)', st1.vrms, st1.freq), ...
    'Color', th.title_c, 'FontSize', 11);
legend('CH1', 'TextColor', th.fg, 'Color', th.ax_bg, 'EdgeColor', th.grid);
grid on;

ax = subplot(2, 1, 2);
if has_ch2
    plot(ch2_t*1e3, ch2_v, 'Color', cfg.ch2_color, 'LineWidth', 0.9);
    title(sprintf('CH2 – Tidsdomæne (Vrms = %.4f V, f0 = %.3f Hz)', st2.vrms, st2.freq), ...
        'Color', th.title_c, 'FontSize', 11);
    legend('CH2', 'TextColor', th.fg, 'Color', th.ax_bg, 'EdgeColor', th.grid);
else
    plot(ch2_t*1e3, ch2_v, 'Color', [0.5 0.5 0.5], 'LineWidth', 0.9);
    title('CH2 – Intet signal (0V)', 'Color', th.title_c, 'FontSize', 11);
    legend('CH2 (0V)', 'TextColor', th.fg, 'Color', th.ax_bg, 'EdgeColor', th.grid);
end
applyTheme(ax);
xlabel('Tid [ms]', 'Color', th.fg);
ylabel('Spænding [V]', 'Color', th.fg);
grid on;

sgtitle('Tidsdomæne – Oscilloskopsignal', 'Color', th.title_c, 'FontSize', 14, 'FontWeight','bold');

% =========================================================================
%  FIGUR 2: FFT-SPEKTRUM
% =========================================================================
fprintf('Genererer FFT-spektrum...\n');
fig2 = figure('Name','FFT Spektrum','NumberTitle','off');
figStyle(fig2);

start_freq_hz = cfg.fft_start_freq_hz;
start_idx = find(f1 >= start_freq_hz, 1, 'first');
if isempty(start_idx), start_idx = 1; end

ax1 = subplot(2, 1, 1);
f_plot = f1(start_idx:end) / 1e3;
mg_plot = mg1(start_idx:end);

semilogx(f_plot, mg_plot, 'Color', cfg.ch1_color, 'LineWidth', 1.2);
hold on;

if cfg.peak_hold_enable && length(mg_plot) > 10
    segment_len = max(floor(length(mg_plot)/10), 1);
    mg1_peakhold = zeros(size(mg_plot));
    for seg = 0:9
        idx_start = seg*segment_len + 1;
        idx_end = min((seg+1)*segment_len, length(mg_plot));
        if idx_start <= idx_end
            mg1_peakhold(idx_start:idx_end) = max(mg1_peakhold(idx_start:idx_end), mg_plot(idx_start:idx_end));
        end
    end
    plot(f_plot, mg1_peakhold, 'Color', cfg.accent_color, 'LineWidth', 1.0, ...
         'LineStyle', '--', 'DisplayName', 'Peak Hold');
end

if cfg.noise_floor_enable && length(mg_plot) > 10
    noise_floor = mean(mg_plot(round(end*0.8):end)) + 3;
    yline(noise_floor, 'Color', [0.7 0.7 0.7], 'LineStyle', ':', ...
          'LineWidth', 1, 'DisplayName', sprintf('Noise Floor (%.1f dBV)', noise_floor));
end

applyTheme(ax1);
xlabel('Frekvens [kHz] (log skala)', 'Color', th.fg);
ylabel('Magnitude [dBV]', 'Color', th.fg);
title(sprintf('CH1 – Spectrum Analyzer (f0 = %.2f Hz)', st1.freq), 'Color', th.title_c, 'FontSize', 10);
xlim([start_freq_hz/1e3 min(cfg.freq_max_khz, Fs/2e3)]);
ylim([-140 max(mg_plot)+10]);
grid on;

f0_idx_start = find(f1 >= st1.freq * 0.9, 1, 'first');
f0_idx_end = find(f1 <= st1.freq * 1.1, 1, 'last');
if isempty(f0_idx_start), f0_idx_start = 2; end
if isempty(f0_idx_end), f0_idx_end = min(length(mg1), f0_idx_start+100); end

[peak_mag1_val, peak_idx1_rel] = max(mg1(f0_idx_start:f0_idx_end));
peak_idx1 = f0_idx_start + peak_idx1_rel - 1;
peak_freq1 = f1(peak_idx1)/1e3;

plot(peak_freq1, mg1(peak_idx1), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r', ...
     'DisplayName', sprintf('Grundfrekvens: %.3f kHz', peak_freq1));

legend('Location', 'northeast', 'TextColor', th.fg, 'Color', th.ax_bg, 'EdgeColor', th.grid, 'FontSize', 8);

ax2 = subplot(2, 1, 2);
if has_ch2 && ~all(mg2 == 0)
    start_idx2 = find(f2 >= start_freq_hz, 1, 'first');
    if isempty(start_idx2), start_idx2 = 1; end
    
    f_plot2 = f2(start_idx2:end) / 1e3;
    mg_plot2 = mg2(start_idx2:end);
    
    semilogx(f_plot2, mg_plot2, 'Color', cfg.ch2_color, 'LineWidth', 1.2);
    hold on;
    
    title(sprintf('CH2 – Spectrum Analyzer (f0 = %.2f Hz)', st2.freq), 'Color', th.title_c, 'FontSize', 10);
    
    f0_idx_start2 = find(f2 >= st2.freq * 0.9, 1, 'first');
    f0_idx_end2 = find(f2 <= st2.freq * 1.1, 1, 'last');
    if isempty(f0_idx_start2), f0_idx_start2 = 2; end
    if isempty(f0_idx_end2), f0_idx_end2 = min(length(mg2), f0_idx_start2+100); end
    
    [peak_mag2_val, peak_idx2_rel] = max(mg2(f0_idx_start2:f0_idx_end2));
    peak_idx2 = f0_idx_start2 + peak_idx2_rel - 1;
    peak_freq2 = f2(peak_idx2)/1e3;
    
    plot(peak_freq2, mg2(peak_idx2), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r', ...
         'DisplayName', sprintf('Grundfrekvens: %.3f kHz', peak_freq2));
    
    legend('Location', 'northeast', 'TextColor', th.fg, 'Color', th.ax_bg, 'EdgeColor', th.grid, 'FontSize', 8);
    xlim([start_freq_hz/1e3 min(cfg.freq_max_khz, Fs/2e3)]);
    ylim([-140 max(mg_plot2)+10]);
else
    text(0.5, 0.5, 'CH2: INTET SIGNAL (0V)', 'Units', 'normalized', ...
        'Color', [1 0.3 0.3], 'FontSize', 14, 'HorizontalAlignment', 'center', 'FontWeight', 'bold');
    title('CH2 – Intet signal (0V)', 'Color', th.title_c, 'FontSize', 10);
end

applyTheme(ax2);
xlabel('Frekvens [kHz] (log skala)', 'Color', th.fg);
ylabel('Magnitude [dBV]', 'Color', th.fg);
grid on;

sgtitle(sprintf('FFT-Spektrum (Fs = %.1f kSa/s)', Fs/1e3), 'Color', th.title_c, 'FontSize', 14, 'FontWeight','bold');

% =========================================================================
%  FIGUR 3: HARMONISK ANALYSE
% =========================================================================
fprintf('Genererer harmonisk analyse...\n');
fig3 = figure('Name','Harmonisk Analyse','NumberTitle','off');
figStyle(fig3);

ax = subplot(2, 1, 1);
f0 = st1.freq;
if f0 < 1 || isnan(f0), f0 = 1000; end
harm_freqs = f0 * (1:cfg.harm_max+1);
harm_mags = zeros(1, cfg.harm_max+1);
for k = 1:cfg.harm_max+1
    [~, idx] = min(abs(f1 - harm_freqs(k)));
    harm_mags(k) = mg1(min(idx, numel(mg1)));
end

bar(1:cfg.harm_max+1, harm_mags, 'FaceColor', cfg.ch1_color, 'EdgeColor', 'none');
applyTheme(ax);
hold on;
plot(1, harm_mags(1), 'o', 'Color', cfg.accent_color, 'MarkerSize', 12, 'MarkerFaceColor', cfg.accent_color);

xlabel('Harmonisk orden', 'Color', th.fg);
ylabel('Magnitude [dBV]', 'Color', th.fg);
x_labels = arrayfun(@(k) sprintf('H%d', k), 1:cfg.harm_max+1, 'UniformOutput', false);
xticks(1:cfg.harm_max+1);
xticklabels(x_labels);
title(sprintf('CH1 – Harmonisk analyse (THD = %.2f dB, f0 = %.3f Hz)', st1.thd, f0), ...
    'Color', th.title_c, 'FontSize', 11);
grid on;

ax = subplot(2, 1, 2);
if has_ch2 && ~all(mg2 == 0)
    f0_2 = st2.freq;
    if f0_2 < 1 || isnan(f0_2), f0_2 = 1000; end
    harm_freqs_2 = f0_2 * (1:cfg.harm_max+1);
    harm_mags_2 = zeros(1, cfg.harm_max+1);
    for k = 1:cfg.harm_max+1
        [~, idx] = min(abs(f2 - harm_freqs_2(k)));
        harm_mags_2(k) = mg2(min(idx, numel(mg2)));
    end
    bar(1:cfg.harm_max+1, harm_mags_2, 'FaceColor', cfg.ch2_color, 'EdgeColor', 'none');
    applyTheme(ax);
    hold on;
    plot(1, harm_mags_2(1), 'o', 'Color', cfg.accent_color, 'MarkerSize', 12, 'MarkerFaceColor', cfg.accent_color);
    title(sprintf('CH2 – Harmonisk analyse (THD = %.2f dB, f0 = %.3f Hz)', st2.thd, f0_2), ...
        'Color', th.title_c, 'FontSize', 11);
else
    text(0.5, 0.5, 'CH2: INTET SIGNAL (0V)', 'Units', 'normalized', ...
        'Color', [1 0.3 0.3], 'FontSize', 14, 'HorizontalAlignment', 'center', 'FontWeight', 'bold');
    title('CH2 – Intet signal (0V)', 'Color', th.title_c, 'FontSize', 11);
end

xlabel('Harmonisk orden', 'Color', th.fg);
ylabel('Magnitude [dBV]', 'Color', th.fg);
xticks(1:cfg.harm_max+1);
xticklabels(x_labels);
grid on;

sgtitle('Harmonisk Analyse', 'Color', th.title_c, 'FontSize', 14, 'FontWeight','bold');

% =========================================================================
%  FIGUR 4: FASEFORSKEL
% =========================================================================
phase_deg = 0;
av_lin = 0;
av_db = 0;

if has_ch1 && has_ch2 && ~all(ch2_v == 0)
    fprintf('Genererer faseforskel og Lissajous...\n');
    fig4 = figure('Name','Fase og Lissajous','NumberTitle','off');
    figStyle(fig4);
    
    if length(ch1_t) ~= length(ch2_t)
        ch2_v_int = interp1(ch2_t, ch2_v, ch1_t, 'linear', 'extrap');
    else
        ch2_v_int = ch2_v;
    end
    
    v1_ac = ch1_v - mean(ch1_v);
    v2_ac = ch2_v_int - mean(ch2_v_int);
    [xc, xc_lags] = xcorr(v1_ac, v2_ac, 'coeff');
    [~, max_idx] = max(xc);
    lag_samples = xc_lags(max_idx);
    f0_est = max(st1.freq, 1);
    phase_deg = mod(lag_samples / (Fs/f0_est) * 360, 360);
    if phase_deg > 180, phase_deg = phase_deg - 360; end
    av_lin = rms(ch2_v_int) / max(rms(ch1_v), 1e-9);
    av_db = 20*log10(av_lin);
    
    ax1 = subplot(1,2,1);
    plot(xc_lags/Fs*1e3, xc, 'Color', cfg.ch1_color, 'LineWidth', 1.2);
    applyTheme(ax1);
    hold on;
    xline(lag_samples/Fs*1e3, '--', sprintf('Δt = %.3f ms', lag_samples/Fs*1e3), ...
        'Color', cfg.accent_color, 'LabelVerticalAlignment','bottom', 'FontSize', 9);
    xlabel('Forsinkelse [ms]', 'Color', th.fg);
    ylabel('Normaliseret krydskorrelation', 'Color', th.fg);
    title(sprintf('Krydskorrelation\nΔφ = %.2f°, Av = %.2f dB', phase_deg, av_db), ...
        'Color', th.title_c, 'FontSize', 11);
    grid on;
    xlim([-5 5]);
    
    ax2 = subplot(1,2,2);
    downsample_factor = max(1, floor(length(ch1_v)/5000));
    scatter(ch1_v(1:downsample_factor:end), ch2_v_int(1:downsample_factor:end), 5, ...
        linspace(0,1,length(ch1_v(1:downsample_factor:end)))', 'filled');
    colormap(ax2, 'hsv');
    cb = colorbar(ax2);
    set(cb, 'Color', th.fg);
    applyTheme(ax2);
    xlabel('CH1 [V]', 'Color', th.fg);
    ylabel('CH2 [V]', 'Color', th.fg);
    title('Lissajous-figur', 'Color', th.title_c, 'FontSize', 11);
    axis equal;
    grid on;
    
    sgtitle(sprintf('Faseforskel og Lissajous (Δφ = %.2f°)', phase_deg), ...
        'Color', th.title_c, 'FontSize', 14, 'FontWeight','bold');
else
    fprintf('Springer faseforskel over – CH2 mangler signal (0V)\n');
end

% =========================================================================
%  GENERER HTML5 RAPPORT
% =========================================================================
fprintf('\nGenererer HTML5 rapport...\n');

% Gem figurer som PNG
fig_files = {};
fig_names = {'tidsdomaene', 'fft_spektrum', 'harmonisk_analyse'};
fig_handles = [fig1, fig2, fig3];

if exist('fig4', 'var')
    fig_handles(4) = fig4;
    fig_names{4} = 'fase_lissajous';
end

for i = 1:length(fig_handles)
    fig_file = fullfile(tempdir, sprintf('rigol_%s.png', fig_names{i}));
    set(fig_handles(i), 'PaperPositionMode', 'auto');
    print(fig_handles(i), fig_file, '-dpng', '-r150');
    fig_files{i} = fig_file;
    fprintf('  Gemt: %s\n', fig_names{i});
end

% Opret HTML fil
html_path = fullfile(fpath, cfg.report_file);
fid = fopen(html_path, 'w', 'n', 'UTF-8');

fprintf(fid, '<!DOCTYPE html>\n');
fprintf(fid, '<html lang="da">\n');
fprintf(fid, '<head>\n');
fprintf(fid, '    <meta charset="UTF-8">\n');
fprintf(fid, '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n');
fprintf(fid, '    <title>RIGOL DS1052E - Signalanalyse Rapport</title>\n');
fprintf(fid, '    <style>\n');
fprintf(fid, '        * { margin:0; padding:0; box-sizing:border-box; }\n');
fprintf(fid, '        body { font-family:"Segoe UI",Tahoma,Geneva,Verdana,sans-serif; background:#1a1a2e; color:#eee; padding:20px; }\n');
fprintf(fid, '        .container { max-width:1400px; margin:0 auto; background:rgba(30,30,40,0.95); border-radius:20px; overflow:hidden; }\n');
fprintf(fid, '        .header { background:#0f3460; padding:30px; text-align:center; border-bottom:3px solid #e94560; }\n');
fprintf(fid, '        .header h1 { font-size:2.5em; color:#e94560; }\n');
fprintf(fid, '        .timestamp { margin-top:15px; padding:8px 15px; background:rgba(255,255,255,0.1); border-radius:8px; display:inline-block; }\n');
fprintf(fid, '        .summary { display:grid; grid-template-columns:repeat(auto-fit,minmax(350px,1fr)); gap:20px; padding:30px; background:#0f0f1a; }\n');
fprintf(fid, '        .card { background:rgba(20,20,30,0.8); border-radius:15px; padding:20px; border-left:4px solid #e94560; }\n');
fprintf(fid, '        .card h3 { color:#e94560; margin-bottom:15px; }\n');
fprintf(fid, '        .stats-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:15px; }\n');
fprintf(fid, '        .stat-item { display:flex; justify-content:space-between; padding:8px; background:rgba(255,255,255,0.05); border-radius:8px; }\n');
fprintf(fid, '        .stat-label { font-weight:bold; color:#aaa; }\n');
fprintf(fid, '        .stat-value { color:#4ecdc4; font-family:monospace; }\n');
fprintf(fid, '        .figure-section { padding:30px; border-top:1px solid #333; }\n');
fprintf(fid, '        .figure-title { font-size:1.5em; margin-bottom:20px; color:#e94560; text-align:center; }\n');
fprintf(fid, '        .figure-container { text-align:center; margin-bottom:40px; background:#0a0a10; border-radius:15px; padding:20px; }\n');
fprintf(fid, '        .figure-container img { max-width:100%%; height:auto; border-radius:10px; }\n');
fprintf(fid, '        .footer { background:#0a0a10; padding:20px; text-align:center; color:#666; }\n');
fprintf(fid, '        .badge { display:inline-block; padding:3px 8px; background:#e94560; border-radius:5px; font-size:0.8em; margin-left:10px; }\n');
fprintf(fid, '        @media (max-width:768px) { .summary { grid-template-columns:1fr; } .stats-grid { grid-template-columns:1fr; } }\n');
fprintf(fid, '    </style>\n');
fprintf(fid, '</head>\n');
fprintf(fid, '<body>\n');
fprintf(fid, '<div class="container">\n');
fprintf(fid, '<div class="header">\n');
fprintf(fid, '<h1>RIGOL DS1052E</h1>\n');
fprintf(fid, '<div class="timestamp">%s</div>\n', char(ts));
fprintf(fid, '</div>\n');

fprintf(fid, '<div class="summary">\n');
fprintf(fid, '<div class="card">\n');
fprintf(fid, '<h3>CH1 - Kanal 1</h3>\n');
fprintf(fid, '<div class="stats-grid">\n');
fprintf(fid, '<div class="stat-item"><span class="stat-label">Grundfrekvens:</span><span class="stat-value">%.3f Hz</span></div>\n', st1.freq);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vrms:</span><span class="stat-value">%.4f V</span></div>\n', st1.vrms);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vp:</span><span class="stat-value">%.4f V</span></div>\n', st1.vp);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vpp:</span><span class="stat-value">%.4f V</span></div>\n', st1.vpp);
fprintf(fid, '<div class="stat-item"><span class="stat-label">THD:</span><span class="stat-value">%.2f dB</span></div>\n', st1.thd);
fprintf(fid, '<div class="stat-item"><span class="stat-label">SNR:</span><span class="stat-value">%.2f dB</span></div>\n', st1.snr);
fprintf(fid, '<div class="stat-item"><span class="stat-label">SINAD:</span><span class="stat-value">%.2f dB</span></div>\n', st1.sinad);
fprintf(fid, '<div class="stat-item"><span class="stat-label">ENOB:</span><span class="stat-value">%.2f bit</span></div>\n', st1.enob);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Samples:</span><span class="stat-value">%d</span></div>\n', st1.N);
fprintf(fid, '</div></div>\n');

ch2_badge = 'INGEN SIGNAL';
if has_ch2 && ~all(ch2_v == 0)
    ch2_badge = 'AKTIV';
end
fprintf(fid, '<div class="card">\n');
fprintf(fid, '<h3>CH2 - Kanal 2 <span class="badge">%s</span></h3>\n', ch2_badge);
fprintf(fid, '<div class="stats-grid">\n');
fprintf(fid, '<div class="stat-item"><span class="stat-label">Grundfrekvens:</span><span class="stat-value">%.3f Hz</span></div>\n', st2.freq);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vrms:</span><span class="stat-value">%.4f V</span></div>\n', st2.vrms);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vp:</span><span class="stat-value">%.4f V</span></div>\n', st2.vp);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vpp:</span><span class="stat-value">%.4f V</span></div>\n', st2.vpp);
fprintf(fid, '<div class="stat-item"><span class="stat-label">THD:</span><span class="stat-value">%.2f dB</span></div>\n', st2.thd);
fprintf(fid, '<div class="stat-item"><span class="stat-label">SNR:</span><span class="stat-value">%.2f dB</span></div>\n', st2.snr);
fprintf(fid, '<div class="stat-item"><span class="stat-label">SINAD:</span><span class="stat-value">%.2f dB</span></div>\n', st2.sinad);
fprintf(fid, '<div class="stat-item"><span class="stat-label">ENOB:</span><span class="stat-value">%.2f bit</span></div>\n', st2.enob);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Samples:</span><span class="stat-value">%d</span></div>\n', st2.N);
fprintf(fid, '</div></div>\n');

fprintf(fid, '<div class="card">\n');
fprintf(fid, '<h3>Kanalrelation</h3>\n');
fprintf(fid, '<div class="stats-grid">\n');
fprintf(fid, '<div class="stat-item"><span class="stat-label">Faseforskel:</span><span class="stat-value">%.2f deg</span></div>\n', phase_deg);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Forstærkning:</span><span class="stat-value">%.2f dB</span></div>\n', av_db);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Sample rate:</span><span class="stat-value">%.2f kSa/s</span></div>\n', Fs/1e3);
fprintf(fid, '<div class="stat-item"><span class="stat-label">FFT vindue:</span><span class="stat-value">%s</span></div>\n', cfg.window_type);
fprintf(fid, '</div></div>\n');
fprintf(fid, '</div>\n');

% Figurer
fprintf(fid, '<div class="figure-section">\n');
fprintf(fid, '<div class="figure-title">Tidsdomene</div>\n');
fprintf(fid, '<div class="figure-container"><img src="file:///%s" alt="Tidsdomene"></div>\n', strrep(fig_files{1}, '\', '/'));
fprintf(fid, '</div>\n');

fprintf(fid, '<div class="figure-section">\n');
fprintf(fid, '<div class="figure-title">FFT Spektrum</div>\n');
fprintf(fid, '<div class="figure-container"><img src="file:///%s" alt="FFT"></div>\n', strrep(fig_files{2}, '\', '/'));
fprintf(fid, '</div>\n');

fprintf(fid, '<div class="figure-section">\n');
fprintf(fid, '<div class="figure-title">Harmonisk Analyse</div>\n');
fprintf(fid, '<div class="figure-container"><img src="file:///%s" alt="Harmonisk"></div>\n', strrep(fig_files{3}, '\', '/'));
fprintf(fid, '</div>\n');

if length(fig_files) >= 4
    fprintf(fid, '<div class="figure-section">\n');
    fprintf(fid, '<div class="figure-title">Faseforskel og Lissajous</div>\n');
    fprintf(fid, '<div class="figure-container"><img src="file:///%s" alt="Lissajous"></div>\n', strrep(fig_files{4}, '\', '/'));
    fprintf(fid, '</div>\n');
end

fprintf(fid, '<div class="footer">\n');
fprintf(fid, '<p>Genereret af RIGOL DS1052E Signalanalyse Tool | MATLAB | %s</p>\n', datestr(now));
fprintf(fid, '</div>\n');
fprintf(fid, '</div>\n');
fprintf(fid, '</body>\n');
fprintf(fid, '</html>\n');

fclose(fid);

fprintf('HTML rapport gemt: %s\n', html_path);

% =========================================================================
%  KONSOL-RAPPORT
% =========================================================================
fprintf('\n');
fprintf('========================================================\n');
fprintf('  SAMMENFATTENDE MÅLERAPPORT\n');
fprintf('========================================================\n');
fprintf('\n');
fprintf('-- CH1 --\n');
fprintf('Grundfrekvens    : %.4f Hz\n', st1.freq);
fprintf('Vrms (total)     : %.4f V\n', st1.vrms);
fprintf('Vp               : %.4f V\n', st1.vp);
fprintf('Vpp              : %.4f V\n', st1.vpp);
fprintf('THD              : %.2f dB\n', st1.thd);
fprintf('SNR              : %.2f dB\n', st1.snr);
fprintf('SINAD            : %.2f dB\n', st1.sinad);
fprintf('ENOB             : %.2f bit\n', st1.enob);
fprintf('\n');

if has_ch2 && ~all(ch2_v == 0)
    fprintf('-- CH2 --\n');
    fprintf('Grundfrekvens    : %.4f Hz\n', st2.freq);
    fprintf('Vrms (total)     : %.4f V\n', st2.vrms);
    fprintf('Vp               : %.4f V\n', st2.vp);
    fprintf('Vpp              : %.4f V\n', st2.vpp);
    fprintf('\n');
    fprintf('-- Relation --\n');
    fprintf('Faseforskel      : %.2f deg\n', phase_deg);
    fprintf('Forstærkning     : %.2f dB\n', av_db);
else
    fprintf('-- CH2 --\n');
    fprintf('*** INTET SIGNAL – KANAL 2 SAT TIL 0V ***\n');
end

fprintf('\n');
fprintf('Analyse afsluttet.\n');
fprintf('HTML rapport: %s\n', html_path);
fprintf('Figurer gemt i: %s\n', tempdir);
fprintf('\n');

% Hjælpefunktion
function out = ternary(condition, true_val, false_val)
    if condition
        out = true_val;
    else
        out = false_val;
    end
end