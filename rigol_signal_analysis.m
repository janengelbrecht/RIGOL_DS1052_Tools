% =========================================================================
%  RIGOL DS1052E - PROFESSIONEL SIGNALANALYSE (KORRIGERET FOR CSV)
%  Rigol_Signal_Analysis.m
% =========================================================================

clear; close all; clc;

% =========================================================================
%  KONFIGURATION
% =========================================================================
cfg.window_type     = 'hann';
cfg.fft_nfft 	    = 2^16;
cfg.harm_max        = 9;
cfg.report_file     = 'Rigol_Analyserapport.html';
cfg.plot_theme      = 'dark';
cfg.ch1_color       = [0.2 1.0 0.5];
cfg.accent_color    = [1.0 0.8 0.0];

cfg.fft_start_freq_hz   = 1;

% =========================================================================
%  INDLÆS DATA
% =========================================================================
fprintf('\n========================================================\n');
fprintf('  RIGOL DS1052E  –  Professionel Signalanalyse\n');
fprintf('========================================================\n\n');

[fname, fpath] = uigetfile( ...
    {'*.csv','CSV datafil (*.csv)'; ...
     '*.mat','MATLAB datafil (*.mat)'; ...
     '*.wfm','Rigol WFM fil (*.wf m)'; ...
     '*.*', 'Alle filer (*.*)'}, ...
    'Vælg Rigol eksportfil');

if isequal(fname, 0)
    error('Ingen fil valgt – analysen afbrydes.');
end
full_path = fullfile(fpath, fname);
fprintf('Indlæser: %s\n', full_path);

[~, ~, ext] = fileparts(fname);

ch1_v = []; ch1_t = []; Fs = [];

if strcmpi(ext, '.csv')
    fprintf('Format: CSV datafil – CH1 analyseres\n');
    
    % Læs hele CSV filen
    fid = fopen(full_path, 'r');
    if fid == -1
        error('Kunne ikke åbne CSV fil');
    end
    
    % Spring de 2 header linjer over
    fgetl(fid);  % "X,CH1,"
    fgetl(fid);  % "Second,Volt,"
    
    % Læs alle data
    data = textscan(fid, '%f%f', 'Delimiter', ',', 'CollectOutput', 1);
    fclose(fid);
    
    if ~isempty(data{1}) && size(data{1}, 1) > 10
        ch1_t = data{1}(:,1);
        ch1_v = data{1}(:,2);
        fprintf('CH1 data indlæst: %d samples\n', length(ch1_t));
        
        % Beregn sample rate fra tidsaksen
        dt = median(diff(ch1_t));
        Fs = 1 / dt;
        fprintf('Sample rate: %.1f Hz (dt = %.2f µs)\n', Fs, dt*1e6);
        fprintf('Tidsinterval: %.3f ms til %.3f ms\n', min(ch1_t)*1000, max(ch1_t)*1000);
        fprintf('Total tid: %.3f ms\n', (max(ch1_t)-min(ch1_t))*1000);
        
        % Målt Vpp fra CSV data
        Vpp_measured = max(ch1_v) - min(ch1_v);
        Vp_measured = max(abs(ch1_v));
        fprintf('CH1 Vpp (målt): %.4f V\n', Vpp_measured);
        fprintf('CH1 Vp (målt): %.4f V\n', Vp_measured);
    else
        error('CSV filen har ikke tilstrækkelige data');
    end
    
    ts = string(datetime('now','Format','yyyy-MM-dd HH:mm:ss'));
    
elseif strcmpi(ext, '.mat')
    raw = load(full_path);
    
    if isfield(raw, 'X') && isfield(raw, 'CH1')
        ch1_t = double(raw.X(:));
        ch1_v = double(raw.CH1(:));
    elseif isfield(raw, 'ch1_time') && isfield(raw, 'ch1_voltage')
        ch1_t = double(raw.ch1_time(:));
        ch1_v = double(raw.ch1_voltage(:));
    else
        var_names = fieldnames(raw);
        for i = 1:length(var_names)
            if isnumeric(raw.(var_names{i}))
                data = raw.(var_names{i});
                if size(data, 2) >= 2
                    ch1_t = double(data(:,1));
                    ch1_v = double(data(:,2));
                    fprintf('CH1 data fundet i %s\n', var_names{i});
                    break;
                end
            end
        end
    end
    
    if isempty(ch1_v)
        error('Manglende CH1 data');
    end
    
    valid = ~isnan(ch1_t) & ~isnan(ch1_v);
    ch1_t = ch1_t(valid);
    ch1_v = ch1_v(valid);
    
    if length(ch1_t) > 1
        Fs = 1 / median(diff(ch1_t));
    else
        Fs = 100000;
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
    
    ts = string(datetime('now','Format','yyyy-MM-dd HH:mm:ss'));
    fclose(fid);
else
    error('Ukendt filformat: %s', ext);
end

fprintf('\n--- Data information ---\n');
fprintf('Sample rate      : %.1f Hz\n', Fs);
fprintf('CH1 samples      : %d\n', numel(ch1_v));
fprintf('Tidsstempel      : %s\n', ts);

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
%  BEREGN STATISTIK
% =========================================================================
fprintf('\nBeregner signalstatistik...\n');

% Beregn FFT
[f1, mg1, ~, nfft1] = compute_fft(ch1_v, Fs, cfg.window_type, cfg.fft_nfft);

% Find grundfrekvensen (forventer 1000 Hz, søg 800-1200 Hz)
search_f_min = 800;
search_f_max = 1200;
search_idx = find(f1 >= search_f_min & f1 <= search_f_max);

if isempty(search_idx)
    % Backup: søg 500-2000 Hz
    search_idx = find(f1 >= 500 & f1 <= 2000);
end

[peak_mag, peak_pos] = max(mg1(search_idx));
global_peak_idx = search_idx(peak_pos);
fundamental_freq = f1(global_peak_idx);

% Parabolsk interpolation
if global_peak_idx > 1 && global_peak_idx < length(mg1)
    y_vals = mg1(global_peak_idx-1:global_peak_idx+1);
    x_vals = f1(global_peak_idx-1:global_peak_idx+1);
    p = polyfit(x_vals, y_vals, 2);
    if p(1) < 0
        f_peak = -p(2) / (2 * p(1));
        if f_peak > 800 && f_peak < 1200
            fundamental_freq = f_peak;
        end
    end
end

fprintf('Fundamental frekvens: %.2f Hz\n', fundamental_freq);

% Beregn signalstatistikker
st1 = signal_stats_calc(ch1_v, Fs, fundamental_freq);

% Udskriv resultater
fprintf('\n--- MÅLTE VÆRDIER ---\n');
fprintf('CH1 Vpp             : %.4f V\n', max(ch1_v) - min(ch1_v));
fprintf('CH1 Vp              : %.4f V\n', max(abs(ch1_v)));
fprintf('CH1 Vrms            : %.4f V\n', st1.vrms);
fprintf('CH1 Grundfrekvens   : %.2f Hz\n', st1.freq);
fprintf('CH1 THD             : %.2f dB\n', st1.thd);
fprintf('CH1 SNR             : %.2f dB\n', st1.snr);

% =========================================================================
%  FIGUR 1: TIDSDOMÆNE
% =========================================================================
fprintf('\nGenererer tidsdomæne-plot...\n');
fig1 = figure('Name','Tidsdomæne','NumberTitle','off');
figStyle(fig1);

ax = subplot(1, 1, 1);
plot(ch1_t*1000, ch1_v, 'Color', cfg.ch1_color, 'LineWidth', 1.0);
applyTheme(ax);
xlabel('Tid [ms]', 'Color', th.fg);
ylabel('Spænding [V]', 'Color', th.fg);
title(sprintf('CH1 – Tidsdomæne (Vp = %.3f V, Vrms = %.3f V, f = %.1f Hz)', ...
    st1.vp, st1.vrms, st1.freq), 'Color', th.title_c, 'FontSize', 11);
legend('CH1', 'TextColor', th.fg, 'Color', th.ax_bg, 'EdgeColor', th.grid);
grid on;
xlim([min(ch1_t*1000) max(ch1_t*1000)]);

% =========================================================================
%  FIGUR 2: FFT-SPEKTRUM
% =========================================================================
fprintf('Genererer FFT-spektrum...\n');
fig2 = figure('Name','FFT Spektrum','NumberTitle','off');
figStyle(fig2);

ax = subplot(1, 1, 1);
f_plot = f1 / 1000;
semilogx(f_plot, mg1, 'Color', cfg.ch1_color, 'LineWidth', 1.2);
hold on;

applyTheme(ax);
xlabel('Frekvens [kHz] (log skala)', 'Color', th.fg);
ylabel('Magnitude [dBV]', 'Color', th.fg);
title(sprintf('CH1 – Spectrum Analyzer (f0 = %.1f Hz)', st1.freq), 'Color', th.title_c, 'FontSize', 11);
xlim([0.05 50]);
ylim([-140 max(mg1)+10]);
grid on;

% Marker grundfrekvens
fund_idx = round(st1.freq / Fs * nfft1) + 1;
if fund_idx <= length(mg1)
    plot(st1.freq/1000, mg1(fund_idx), 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r', ...
         'DisplayName', sprintf('Grundfrekvens: %.1f Hz', st1.freq));
end

% Marker harmoniske
for h = 2:cfg.harm_max
    harm_freq = st1.freq * h;
    if harm_freq < Fs/2 && harm_freq < 50000
        harm_idx = round(harm_freq / Fs * nfft1) + 1;
        if harm_idx <= length(mg1)
            plot(harm_freq/1000, mg1(harm_idx), 'mo', 'MarkerSize', 6, ...
                 'DisplayName', sprintf('H%d: %.1f Hz', h, harm_freq));
        end
    end
end

legend('Location', 'northeast', 'TextColor', th.fg, 'Color', th.ax_bg, 'EdgeColor', th.grid, 'FontSize', 8);

% =========================================================================
%  FIGUR 3: HARMONISK ANALYSE
% =========================================================================
fprintf('Genererer harmonisk analyse...\n');
fig3 = figure('Name','Harmonisk Analyse','NumberTitle','off');
figStyle(fig3);

ax = subplot(1, 1, 1);
harm_mags = zeros(1, cfg.harm_max+1);
harm_mags(1) = mg1(fund_idx);

for k = 2:cfg.harm_max+1
    harm_freq = st1.freq * k;
    if harm_freq < Fs/2 && harm_freq < 50000
        harm_idx = round(harm_freq / Fs * nfft1) + 1;
        if harm_idx <= length(mg1)
            harm_mags(k) = mg1(harm_idx);
        end
    end
end

% Normaliser til dBc
harm_mags_dBc = harm_mags - harm_mags(1);

bar(1:cfg.harm_max+1, harm_mags_dBc, 'FaceColor', cfg.ch1_color, 'EdgeColor', 'none');
applyTheme(ax);
hold on;
plot(1, harm_mags_dBc(1), 'o', 'Color', cfg.accent_color, 'MarkerSize', 12, 'MarkerFaceColor', cfg.accent_color);

xlabel('Harmonisk orden', 'Color', th.fg);
ylabel('Relativ magnitude [dBc]', 'Color', th.fg);
x_labels = arrayfun(@(k) sprintf('H%d', k), 1:cfg.harm_max+1, 'UniformOutput', false);
xticks(1:cfg.harm_max+1);
xticklabels(x_labels);
title(sprintf('CH1 – Harmonisk analyse (THD = %.1f dB, f0 = %.1f Hz)', st1.thd, st1.freq), ...
    'Color', th.title_c, 'FontSize', 12);
grid on;
ylim([-80 5]);

% =========================================================================
%  GENERER HTML RAPPORT
% =========================================================================
fprintf('\nGenererer HTML rapport...\n');

fig_files = {};
fig_names = {'tidsdomaene', 'fft_spektrum', 'harmonisk_analyse'};
fig_handles = [fig1, fig2, fig3];

for i = 1:length(fig_handles)
    fig_file = fullfile(tempdir, sprintf('rigol_%s.png', fig_names{i}));
    set(fig_handles(i), 'PaperPositionMode', 'auto');
    print(fig_handles(i), fig_file, '-dpng', '-r150');
    fig_files{i} = fig_file;
    fprintf('  Gemt: %s\n', fig_names{i});
end

html_path = fullfile(fpath, cfg.report_file);
fid = fopen(html_path, 'w', 'n', 'UTF-8');

fprintf(fid, '<!DOCTYPE html>\n');
fprintf(fid, '<html lang="da">\n');
fprintf(fid, '<head>\n');
fprintf(fid, '    <meta charset="UTF-8">\n');
fprintf(fid, '    <title>RIGOL DS1052E - Signalanalyse Rapport</title>\n');
fprintf(fid, '    <style>\n');
fprintf(fid, '        body { font-family: "Segoe UI", Arial, sans-serif; background: #1a1a2e; color: #eee; margin: 0; padding: 20px; }\n');
fprintf(fid, '        .container { max-width: 1200px; margin: 0 auto; background: #16213e; border-radius: 15px; overflow: hidden; }\n');
fprintf(fid, '        .header { background: #0f3460; padding: 20px; text-align: center; border-bottom: 3px solid #e94560; }\n');
fprintf(fid, '        .header h1 { color: #e94560; margin: 0; }\n');
fprintf(fid, '        .timestamp { margin-top: 10px; color: #aaa; }\n');
fprintf(fid, '        .summary { padding: 20px; background: #0f0f1a; }\n');
fprintf(fid, '        .card { background: #1a1a2e; border-radius: 10px; padding: 20px; max-width: 500px; margin: 0 auto; border-left: 4px solid #e94560; }\n');
fprintf(fid, '        .card h3 { color: #e94560; text-align: center; margin-top: 0; }\n');
fprintf(fid, '        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }\n');
fprintf(fid, '        .stat-item { display: flex; justify-content: space-between; padding: 8px; background: #0f0f1a; border-radius: 5px; }\n');
fprintf(fid, '        .stat-label { color: #aaa; }\n');
fprintf(fid, '        .stat-value { color: #4ecdc4; font-family: monospace; }\n');
fprintf(fid, '        .figure-section { padding: 20px; border-top: 1px solid #333; }\n');
fprintf(fid, '        .figure-title { text-align: center; color: #e94560; font-size: 1.4em; margin-bottom: 15px; }\n');
fprintf(fid, '        .figure-container { text-align: center; background: #0a0a10; border-radius: 10px; padding: 20px; }\n');
fprintf(fid, '        .figure-container img { max-width: 100%%; border-radius: 8px; }\n');
fprintf(fid, '        .footer { text-align: center; padding: 15px; color: #666; background: #0a0a10; }\n');
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
fprintf(fid, '<h3>CH1 - Måleresultater</h3>\n');
fprintf(fid, '<div class="stats-grid">\n');
fprintf(fid, '<div class="stat-item"><span class="stat-label">Grundfrekvens:</span><span class="stat-value">%.2f Hz</span></div>\n', st1.freq);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vrms:</span><span class="stat-value">%.4f V</span></div>\n', st1.vrms);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vp (peak):</span><span class="stat-value">%.4f V</span></div>\n', st1.vp);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Vpp:</span><span class="stat-value">%.4f V</span></div>\n', st1.vpp);
fprintf(fid, '<div class="stat-item"><span class="stat-label">THD:</span><span class="stat-value">%.2f dB</span></div>\n', st1.thd);
fprintf(fid, '<div class="stat-item"><span class="stat-label">SNR:</span><span class="stat-value">%.2f dB</span></div>\n', st1.snr);
fprintf(fid, '<div class="stat-item"><span class="stat-label">SINAD:</span><span class="stat-value">%.2f dB</span></div>\n', st1.sinad);
fprintf(fid, '<div class="stat-item"><span class="stat-label">ENOB:</span><span class="stat-value">%.2f bit</span></div>\n', st1.enob);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Sample rate:</span><span class="stat-value">%.0f Hz</span></div>\n', Fs);
fprintf(fid, '<div class="stat-item"><span class="stat-label">Samples:</span><span class="stat-value">%d</span></div>\n', st1.N);
fprintf(fid, '</div></div>\n');
fprintf(fid, '</div>\n');

for i = 1:length(fig_names)
    fprintf(fid, '<div class="figure-section">\n');
    fprintf(fid, '<div class="figure-title">%s</div>\n', upper(fig_names{i}));
    fprintf(fid, '<div class="figure-container"><img src="file:///%s" alt="%s"></div>\n', ...
        strrep(fig_files{i}, '\', '/'), fig_names{i});
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
%  KONSOL RAPPORT
% =========================================================================
fprintf('\n');
fprintf('========================================================\n');
fprintf('  SAMMENFATTENDE MÅLERAPPORT\n');
fprintf('========================================================\n');
fprintf('\n');
fprintf('-- CH1 --\n');
fprintf('Grundfrekvens    : %.2f Hz\n', st1.freq);
fprintf('Vrms (total)     : %.4f V\n', st1.vrms);
fprintf('Vp (peak)        : %.4f V\n', st1.vp);
fprintf('Vpp              : %.4f V\n', st1.vpp);
fprintf('DC offset        : %.4f V\n', st1.vdc);
fprintf('THD              : %.2f dB\n', st1.thd);
fprintf('SNR              : %.2f dB\n', st1.snr);
fprintf('SINAD            : %.2f dB\n', st1.sinad);
fprintf('ENOB             : %.2f bit\n', st1.enob);
fprintf('\n');
fprintf('Analyse afsluttet.\n');
fprintf('HTML rapport: %s\n', html_path);
fprintf('\n');

% =========================================================================
%  FUNKTIONER
% =========================================================================

function [freqs, mag_db, phase_deg, nfft] = compute_fft(signal, Fs, win_type, nfft_in)
    N = numel(signal);
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
    X = fft((signal(:) - mean(signal)) .* w, nfft);
    half = 1:floor(nfft/2)+1;
    mag = 2*abs(X(half)) / sum(w);
    mag(1) = mag(1)/2;
    freqs = (0:numel(half)-1) * Fs / nfft;
    mag_db = 20*log10(max(mag, 1e-12));
    phase_deg = angle(X(half)) * 180/pi;
end

function stats = signal_stats_calc(v, Fs, fundamental_freq)
    stats.N = numel(v);
    stats.Fs = Fs;
    stats.vdc = mean(v);
    v_ac = v - stats.vdc;
    stats.vrms = rms(v(:));
    stats.vrms_ac = rms(v_ac(:));
    stats.vp = max(abs(v));
    stats.vpp = max(v) - min(v);
    stats.crest = stats.vp / max(stats.vrms_ac, 1e-12);
    stats.form = stats.vrms_ac / max(mean(abs(v_ac)), 1e-12);
    stats.freq = fundamental_freq;
    stats.period = 1 / max(stats.freq, 1e-6);
    
    try
        stats.snr = snr(v(:), Fs);
        stats.sinad = sinad(v(:), Fs);
        stats.thd = thd(v(:), Fs);
        stats.sfdr = sfdr(v(:), Fs);
        stats.enob = (stats.sinad - 1.76) / 6.02;
    catch
        stats.snr = NaN;
        stats.sinad = NaN;
        stats.thd = NaN;
        stats.sfdr = NaN;
        stats.enob = NaN;
    end
end