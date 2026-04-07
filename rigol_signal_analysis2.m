function RigolAnalyse()
    % Hovedfunktion til analyse af Rigol data (CSV eller MAT)
    
    %% 1. INDLÆS DATA FRA FIL (CSV eller MAT)
    [fileName, filePath] = uigetfile({'*.csv;*.mat', 'CSV- eller MAT-fil (*.csv, *.mat)'; ...
                                      '*.csv', 'CSV-datafil (*.csv)'; ...
                                      '*.mat', 'MATLAB datafil (*.mat)'}, ...
                                     'Vælg Rigol eksportfil');
    if isequal(fileName,0)
        disp('Filvalg annulleret.');
        return;
    end
    
    fullFilePath = fullfile(filePath, fileName);
    [~, ~, ext] = fileparts(fileName);
    
    % Initialiser variable
    ch1 = [];
    ch2 = [];
    t   = [];
    fs  = [];
    
    fprintf('\n========================================================\n');
    fprintf('  RIGOL DS1052E – Professionel Signalanalyse\n');
    fprintf('========================================================\n\n');
    fprintf('Indlæser: %s\n', fileName);
    
    % =====================================================================
    % INDLAES CSV FIL (som i rigol_signal_analysis.m)
    % =====================================================================
    if strcmpi(ext, '.csv')
        fprintf('Format: CSV datafil – CH1 analyseres\n');
        
        fid = fopen(fullFilePath, 'r');
        if fid == -1
            error('Kunne ikke åbne CSV-fil');
        end
        
        % Spring headerlinjer over (Rigol CSV har typisk 2 headerlinjer)
        fgetl(fid);  % "X,CH1,"
        fgetl(fid);  % "Second,Volt,"
        
        % Læs data
        data = textscan(fid, '%f%f', 'Delimiter', ',', 'CollectOutput', 1);
        fclose(fid);
        
        if isempty(data{1}) || size(data{1},1) < 10
            error('CSV-filen har ikke tilstrækkelige data');
        end
        
        t   = data{1}(:,1);
        ch1 = data{1}(:,2);
        
        % Beregn sample rate
        dt = median(diff(t));
        fs = 1 / dt;
        
        fprintf('  CH1 data indlæst: %d samples\n', length(ch1));
        fprintf('  Sample rate : %.1f Hz (dt = %.2f µs)\n', fs, dt*1e6);
        fprintf('  Tidsinterval: %.3f ms til %.3f ms\n', min(t)*1000, max(t)*1000);
        
        % Målt Vpp fra CSV data
        Vpp_measured = max(ch1) - min(ch1);
        Vp_measured = max(abs(ch1));
        fprintf('  CH1 Vpp (målt): %.4f V\n', Vpp_measured);
        fprintf('  CH1 Vp (målt): %.4f V\n', Vp_measured);
        
        % CH2 findes ikke i enkeltkanals CSV – opret tom kanal
        ch2 = zeros(size(ch1));
        
    % =====================================================================
    % INDLAES MAT FIL
    % =====================================================================
    elseif strcmpi(ext, '.mat')
        fprintf('Format: MAT datafil\n');
        raw = load(fullFilePath);
        
        % Find de korrekte variable
        try
            if isfield(raw, 'ch1_voltage')
                ch1 = double(raw.ch1_voltage(:));
            elseif isfield(raw, 'CH1')
                ch1 = double(raw.CH1(:));
            elseif isfield(raw, 'ch1')
                ch1 = double(raw.ch1(:));
            else
                error('Kunne ikke finde CH1 data');
            end
            
            if isfield(raw, 'ch2_voltage')
                ch2 = double(raw.ch2_voltage(:));
            elseif isfield(raw, 'CH2')
                ch2 = double(raw.CH2(:));
            else
                ch2 = zeros(size(ch1));
                warning('CH2 data ikke fundet – opretter nul-vektor');
            end
            
            if isfield(raw, 'ch1_time')
                t = double(raw.ch1_time(:));
            elseif isfield(raw, 'X')
                t = double(raw.X(:));
            elseif isfield(raw, 'time')
                t = double(raw.time(:));
            else
                error('Kunne ikke finde tidsakse');
            end
            
            if isfield(raw, 'sample_rate')
                fs = double(raw.sample_rate);
            else
                dt = median(diff(t));
                fs = 1 / dt;
                fprintf('  Sample rate beregnet: %.1f Hz\n', fs);
            end
            
        catch ME
            error('MAT-fil format ikke genkendt: %s', ME.message);
        end
        
        % Validér data
        valid = ~isnan(t) & ~isnan(ch1);
        t = t(valid);
        ch1 = ch1(valid);
        if length(ch2) == length(valid)
            ch2 = ch2(valid);
        else
            ch2 = zeros(size(ch1));
        end
        
        fprintf('  CH1 samples : %d\n', length(ch1));
        fprintf('  Sample rate : %.1f Hz\n', fs);
        
    else
        error('Ukendt filformat: %s', ext);
    end
    
    % Tjek om CH2 har noget signal
    ch2_has_signal = (max(ch2) - min(ch2)) > 0.001;  % Tærskel 1mV
    
    if ~ch2_has_signal
        fprintf('  CH2: Intet signal (konstant).\n');
    else
        fprintf('  CH2: Signal detekteret.\n');
    end
    
    %% 2. UDFØR BEREGNINGER
    fprintf('\nBeregner signalparametre...\n');
    resCH1 = beregnParametre(ch1, fs);
    
    if ch2_has_signal
        resCH2 = beregnParametre(ch2, fs);
    else
        % CH2 er konstant – returner tomme værdier
        resCH2 = struct();
        resCH2.Vp = 0;
        resCH2.Vmin = 0;
        resCH2.Vpp = 0;
        resCH2.Vrms = 0;
        resCH2.Vavg = 0;
        resCH2.CrestFaktor = 0;
        resCH2.FormFaktor = 0;
        resCH2.Frekvens = NaN;
        resCH2.RiseTime = NaN;
        resCH2.FallTime = NaN;
        resCH2.DutyCycle = NaN;
        resCH2.THD_dB = NaN;
        resCH2.THD_pct = NaN;
        resCH2.SNR = NaN;
        resCH2.SINAD = NaN;
        resCH2.SFDR = NaN;
    end
    
    % Udskriv CH1 resultater
    fprintf('\n--- MÅLTE VÆRDIER (CH1) ---\n');
    fprintf('  Vpp             : %.4f V\n', resCH1.Vpp);
    fprintf('  Vp              : %.4f V\n', resCH1.Vp);
    fprintf('  Vrms            : %.4f V\n', resCH1.Vrms);
    fprintf('  Grundfrekvens   : %.2f Hz\n', resCH1.Frekvens);
    fprintf('  THD             : %.2f dB (%.4f %%)\n', resCH1.THD_dB, resCH1.THD_pct);
    fprintf('  SNR             : %.2f dB\n', resCH1.SNR);
    fprintf('  SINAD           : %.2f dB\n', resCH1.SINAD);
    fprintf('  SFDR            : %.2f dB\n', resCH1.SFDR);
    
    % Krydskanal beregninger (kun hvis CH2 har signal)
    if ch2_has_signal && resCH1.Vp > 0
        Av = resCH2.Vp / resCH1.Vp;
        AvdB = 20 * log10(Av);
        
        % Faseforskel via cross-correlation
        [c, lags] = xcorr(ch1 - mean(ch1), ch2 - mean(ch2));
        [~, I] = max(abs(c));
        timeDelay = lags(I) / fs;
        faseforskel = mod(timeDelay * resCH1.Frekvens * 360, 360);
        if faseforskel > 180, faseforskel = faseforskel - 360; end
        
        fprintf('\n--- KRYDSKANAL MÅLINGER ---\n');
        fprintf('  Spændingsforstærkning Av : %.4f (%.2f dB)\n', Av, AvdB);
        fprintf('  Faseforskel             : %.2f grader\n', faseforskel);
    else
        Av = NaN;
        AvdB = NaN;
        faseforskel = NaN;
    end
    
    %% 3. GENERER OSCILLOSKOP BILLED
    disp('Genererer tidsdomæne graf...');
    figScope = figure('Visible', 'off', 'Position', [100, 100, 800, 400]);
    plot(t*1000, ch1, 'Color', '#4DBEEE', 'LineWidth', 1.5);
    hold on;
    
    if ch2_has_signal
        plot(t*1000, ch2, 'Color', '#77AC30', 'LineWidth', 1.5);
        legend('CH1', 'CH2', 'TextColor', 'w', 'Color', 'none', 'EdgeColor', 'none');
    else
        legend('CH1', 'TextColor', 'w', 'Color', 'none', 'EdgeColor', 'none');
    end
    
    set(gca, 'Color', '#1E1E1E', 'XColor', '#CCCCCC', 'YColor', '#CCCCCC');
    set(gcf, 'Color', '#1E1E1E');
    grid on;
    ax = gca;
    ax.GridColor = [0.7 0.7 0.7];
    ax.GridAlpha = 0.5;
    title(sprintf('Oscilloskop Måling (CH1: Vpp = %.3f V, f = %.1f Hz)', ...
        resCH1.Vpp, resCH1.Frekvens), 'Color', 'w');
    xlabel('Tid (ms)', 'Color', 'w');
    ylabel('Amplitude (V)', 'Color', 'w');
    xlim([min(t*1000) max(t*1000)]);
    
    scopeImgPath = fullfile(filePath, 'scope_plot.png');
    exportgraphics(figScope, scopeImgPath, 'Resolution', 150);
    close(figScope);
    
    %% 4. GENERER SPECTRUM ANALYSE (FFT) MED TO GRAFER (SUBPLOTS)
    disp('Genererer spektrumanalyse graf...');
    fftImgPath = fullfile(filePath, 'fft_plot.png');
    
    if ~isnan(resCH1.Frekvens) && resCH1.Frekvens < 50000
        figFFT = figure('Visible', 'off', 'Position', [100, 100, 800, 600]);
        
        % Øverste graf (CH1)
        subplot(2, 1, 1);
        plotKlippetFFT(ch1, abs(resCH1.SNR), '#4DBEEE', fs, resCH1.Frekvens);
        grid on;
        title(sprintf('Spektrumanalyse - Kanal 1 (CH1) - f0 = %.1f Hz, SNR = %.1f dB', ...
            resCH1.Frekvens, resCH1.SNR), 'Color', 'k');
        ylabel('Amplitude (dB)', 'Color', 'k');
        xlim([1, min(fs/2, 50000)]);
        
        % Nederste graf (CH2)
        subplot(2, 1, 2);
        if ch2_has_signal && ~isnan(resCH2.SNR)
            plotKlippetFFT(ch2, abs(resCH2.SNR), '#77AC30', fs, resCH2.Frekvens);
            title(sprintf('Spektrumanalyse - Kanal 2 (CH2) - f0 = %.1f Hz, SNR = %.1f dB', ...
                resCH2.Frekvens, resCH2.SNR), 'Color', 'k');
        else
            plot([0 1], [0 0], 'Color', '#77AC30', 'LineWidth', 1.2);
            title('Spektrumanalyse - Kanal 2 (CH2) - INTET SIGNAL', 'Color', 'k');
            text(0.5, 0.5, 'CH2: INTET SIGNAL', 'Units', 'normalized', ...
                'Color', 'r', 'FontSize', 12, 'HorizontalAlignment', 'center');
        end
        grid on;
        xlabel('Frekvens (Hz) - Logaritmisk', 'Color', 'k');
        ylabel('Amplitude (dB)', 'Color', 'k');
        xlim([1, min(fs/2, 50000)]);
        
        exportgraphics(figFFT, fftImgPath, 'Resolution', 150);
        close(figFFT);
        fftSection = sprintf('<img src="fft_plot.png" alt="FFT Spectrum" class="responsive-img">');
    else
        fftSection = sprintf('<p style="color: #d9534f;">Grundfrekvensen er over 50 kHz (%.1f Hz) eller kunne ikke beregnes. Spektrumanalyse blev ikke genereret.</p>', resCH1.Frekvens);
    end
    
    %% 5. GENERER HTML5 RAPPORT (BEHOLDER STIL FRA VERSION 2)
    disp('Opretter HTML-rapport...');
    htmlPath = fullfile(filePath, 'Rapport.html');
    fid = fopen(htmlPath, 'w', 'n', 'UTF-8');
    
    % Håndter NaN værdier i rapporten
    faseforskel_str = sprintf('%.2f', faseforskel);
    if isnan(faseforskel), faseforskel_str = 'Kunne ikke beregnes (CH2 mangler)'; end
    
    Av_str = sprintf('%.4f', Av);
    if isnan(Av), Av_str = 'Kunne ikke beregnes'; end
    
    AvdB_str = sprintf('%.2f', AvdB);
    if isnan(AvdB), AvdB_str = 'Kunne ikke beregnes'; end
    
    % CH2 værdier formateret
    if ch2_has_signal && ~isnan(resCH2.Frekvens)
        ch2_freq_str = sprintf('%.2f Hz', resCH2.Frekvens);
        ch2_thd_str = sprintf('%.4f %% (%.2f dB)', resCH2.THD_pct, resCH2.THD_dB);
        ch2_snr_str = sprintf('%.1f dB', resCH2.SNR);
        ch2_sinad_str = sprintf('%.2f dB', resCH2.SINAD);
        ch2_sfdr_str = sprintf('%.2f dB', resCH2.SFDR);
        ch2_rise_str = sprintf('%.2e s', resCH2.RiseTime);
        ch2_fall_str = sprintf('%.2e s', resCH2.FallTime);
        ch2_duty_str = sprintf('%.2f %%', resCH2.DutyCycle);
        ch2_crest_str = sprintf('%.3f', resCH2.CrestFaktor);
        ch2_form_str = sprintf('%.3f', resCH2.FormFaktor);
        ch2_warning = '';
    else
        ch2_freq_str = 'Kunne ikke beregnes';
        ch2_thd_str = 'Kunne ikke beregnes';
        ch2_snr_str = 'N/A';
        ch2_sinad_str = 'Kunne ikke beregnes';
        ch2_sfdr_str = 'Kunne ikke beregnes';
        ch2_rise_str = 'Kunne ikke beregnes';
        ch2_fall_str = 'Kunne ikke beregnes';
        ch2_duty_str = 'Kunne ikke beregnes';
        ch2_crest_str = '0';
        ch2_form_str = '0';
        ch2_warning = '<p class="warning">OBS: CH2 har intet signal! Kontroller tilslutning af kanal 2.</p>';
    end
    
    html = sprintf([...
        '<!DOCTYPE html>\n', ...
        '<html lang="da">\n', ...
        '<head>\n', ...
        '    <meta charset="UTF-8">\n', ...
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n', ...
        '    <title>Rigol signalanalyse rapport</title>\n', ...
        '    <style>\n', ...
        '        body { font-family: "Segoe UI", Arial, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }\n', ...
        '        .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }\n', ...
        '        h1, h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }\n', ...
        '        .flex-container { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 30px; }\n', ...
        '        .card { flex: 1; min-width: 300px; background: #fafafa; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }\n', ...
        '        .card h3 { margin-top: 0; color: #e67e22; }\n', ...
        '        table { width: 100%%; border-collapse: collapse; }\n', ...
        '        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }\n', ...
        '        th { color: #555; }\n', ...
        '        .responsive-img { max-width: 100%%; height: auto; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 15px; }\n', ...
        '        .highlight { font-weight: bold; color: #2980b9; }\n', ...
        '        .warning { color: #d9534f; font-weight: bold; }\n', ...
        '    </style>\n', ...
        '</head>\n', ...
        '<body>\n', ...
        '    <div class="container">\n', ...
        '        <h1>Målerapport: Rigol signalanalyse</h1>\n', ...
        '        <p>Fil: <strong>%s</strong></p>\n', ...
        '        \n', ...
        '        <h2>Krydskanal Parametre</h2>\n', ...
        '        <p>Faseforskel: <span class="highlight">%s</span></p>\n', ...
        '        <p>Spændingsforstærkning (Av): <span class="highlight">%s</span></p>\n', ...
        '        <p>Spændingsforstærkning (Av dB): <span class="highlight">%s dB</span></p>\n', ...
        '        \n', ...
        '        <h2>Kanalspecifikke Data</h2>\n', ...
        '        <div class="flex-container">\n', ...
        '            \n', ...
        '            <div class="card">\n', ...
        '                <h3 style="color: #2980b9;">Kanal 1 (CH1)</h3>\n', ...
        '                <table>\n', ...
        '                    <tr><th>Frekvens</th><td>%.2f Hz</td></tr>\n', ...
        '                    <tr><th>THD</th><td>%.4f %% (%.2f dB)</td></tr>\n', ...
        '                    <tr><th>SNR (Støjgulv)</th><td>%.2f dB</td></tr>\n', ...
        '                    <tr><th>SINAD</th><td>%.2f dB</td></tr>\n', ...
        '                    <tr><th>SFDR</th><td>%.2f dB</td></tr>\n', ...
        '                    <tr><th>Vp (Spids)</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Vpp (Spids-Spids)</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Vrms</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Rise Time</th><td>%.2e s</td></tr>\n', ...
        '                    <tr><th>Fall Time</th><td>%.2e s</td></tr>\n', ...
        '                    <tr><th>Duty Cycle</th><td>%.2f %%</td></tr>\n', ...
        '                    <tr><th>Crest Faktor</th><td>%.3f</td></tr>\n', ...
        '                    <tr><th>Form Faktor</th><td>%.3f</td></tr>\n', ...
        '                </table>\n', ...
        '            </div>\n', ...
        '            \n', ...
        '            <div class="card">\n', ...
        '                <h3 style="color: #27ae60;">Kanal 2 (CH2)</h3>\n', ...
        '                20\n', ...
        '                    <tr><th>Frekvens</th><td>%s</td></tr>\n', ...
        '                    <tr><th>THD</th><td>%s</td></tr>\n', ...
        '                    <tr><th>SNR (Støjgulv)</th><td>%s dB</td></tr>\n', ...
        '                    <tr><th>SINAD</th><td>%s</td></tr>\n', ...
        '                    <tr><th>SFDR</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Vp (Spids)</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Vpp (Spids-Spids)</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Vrms</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Rise Time</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Fall Time</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Duty Cycle</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Crest Faktor</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Form Faktor</th><td>%s</td></tr>\n', ...
        '                </table>\n', ...
        '                %s\n', ...
        '            </div>\n', ...
        '        </div>\n', ...
        '        \n', ...
        '        <h2>Spektrumanalyse (FFT)</h2>\n', ...
        '        <p><em>Frekvenskomposanter under de respektive SNR-støjgulve (%.1f dB for CH1 / %s for CH2) er filtreret væk.</em></p>\n', ...
        '        %s\n', ...
        '        \n', ...
        '        <h2>Tidsdomæne (Oscilloskop)</h2>\n', ...
        '        <img src="scope_plot.png" alt="Oscilloskop" class="responsive-img">\n', ...
        '    </div>\n', ...
        '</body>\n', ...
        '</html>'...
    ], fileName, faseforskel_str, Av_str, AvdB_str, ...
       resCH1.Frekvens, resCH1.THD_pct, resCH1.THD_dB, resCH1.SNR, resCH1.SINAD, resCH1.SFDR, ...
       resCH1.Vp, resCH1.Vpp, resCH1.Vrms, resCH1.RiseTime, resCH1.FallTime, resCH1.DutyCycle, ...
       resCH1.CrestFaktor, resCH1.FormFaktor, ...
       ch2_freq_str, ch2_thd_str, ch2_snr_str, ch2_sinad_str, ch2_sfdr_str, ...
       resCH2.Vp, resCH2.Vpp, resCH2.Vrms, ...
       ch2_rise_str, ch2_fall_str, ch2_duty_str, ch2_crest_str, ch2_form_str, ...
       ch2_warning, ...
       resCH1.SNR, ch2_snr_str, fftSection);
    
    fprintf(fid, '%s', html);
    fclose(fid);
    
    fprintf('\n========================================================\n');
    fprintf('  SAMMENFATTENDE MÅLERAPPORT\n');
    fprintf('========================================================\n');
    fprintf('\n-- CH1 --\n');
    fprintf('  Grundfrekvens    : %.2f Hz\n', resCH1.Frekvens);
    fprintf('  Vrms (total)     : %.4f V\n', resCH1.Vrms);
    fprintf('  Vp (peak)        : %.4f V\n', resCH1.Vp);
    fprintf('  Vpp              : %.4f V\n', resCH1.Vpp);
    fprintf('  THD              : %.2f dB (%.4f %%)\n', resCH1.THD_dB, resCH1.THD_pct);
    fprintf('  SNR              : %.2f dB\n', resCH1.SNR);
    fprintf('  SINAD            : %.2f dB\n', resCH1.SINAD);
    fprintf('  SFDR             : %.2f dB\n', resCH1.SFDR);
    fprintf('\n');
    fprintf('Analyse afsluttet.\n');
    fprintf('HTML rapport: %s\n', htmlPath);
    fprintf('\n');
    
    disp('Åbner HTML-rapport...');
    web(['file://' htmlPath], '-browser');
end

%% ========================================================================
%  HJÆLPEFUNKTIONER
%  ========================================================================

function res = beregnParametre(signal, fs_val)
    % Tjek om signalet er konstant (ingen variation)
    if max(signal) - min(signal) < 1e-6
        % Konstant signal - returner standard værdier
        res.Vp = max(signal);
        res.Vmin = min(signal);
        res.Vpp = res.Vp - res.Vmin;
        res.Vrms = rms(signal);
        res.Vavg = mean(abs(signal)); 
        res.CrestFaktor = 0;
        res.FormFaktor = 0;
        res.Frekvens = NaN;
        res.RiseTime = NaN;
        res.FallTime = NaN;
        res.DutyCycle = NaN;
        res.THD_dB = NaN;
        res.THD_pct = NaN;
        res.SNR = NaN;
        res.SINAD = NaN;
        res.SFDR = NaN;
        return;
    end
    
    res.Vp = max(signal);
    res.Vmin = min(signal);
    res.Vpp = res.Vp - res.Vmin;
    res.Vrms = rms(signal);
    res.Vavg = mean(abs(signal)); 
    
    res.CrestFaktor = res.Vp / max(res.Vrms, 1e-12);
    res.FormFaktor = res.Vrms / max(res.Vavg, 1e-12);
    
    try 
        res.Frekvens = medfreq(signal, fs_val); 
    catch
        % Backup: brug FFT til at finde frekvens
        [f, mag] = compute_fft_simple(signal, fs_val);
        [~, idx] = max(mag(2:end));
        res.Frekvens = f(idx+1);
    end
    
    try 
        rt = risetime(signal, fs_val);
        if ~isempty(rt)
            res.RiseTime = mean(rt);
        else
            res.RiseTime = NaN;
        end
    catch, 
        res.RiseTime = NaN; 
    end
    
    try 
        ft = falltime(signal, fs_val);
        if ~isempty(ft)
            res.FallTime = mean(ft);
        else
            res.FallTime = NaN;
        end
    catch, 
        res.FallTime = NaN; 
    end
    
    try 
        dc = dutycycle(signal, fs_val);
        if ~isempty(dc)
            res.DutyCycle = mean(dc) * 100;
        else
            res.DutyCycle = NaN;
        end
    catch, 
        res.DutyCycle = NaN; 
    end
    
    try 
        res.THD_dB = thd(signal, fs_val); 
    catch, 
        res.THD_dB = NaN; 
    end
    
    if ~isnan(res.THD_dB)
        res.THD_pct = 100 * (10^(res.THD_dB / 20));
    else
        res.THD_pct = NaN;
    end
    
    try 
        res.SNR = snr(signal, fs_val); 
    catch, 
        res.SNR = NaN; 
    end
    
    try 
        res.SINAD = sinad(signal, fs_val); 
    catch, 
        res.SINAD = NaN; 
    end
    
    try 
        res.SFDR = sfdr(signal, fs_val); 
    catch, 
        res.SFDR = NaN; 
    end
end

function plotKlippetFFT(signal, stoejgulv_dB, farve, fs_val, fundamental_freq)
    L = length(signal);
    Y = fft(signal - mean(signal));
    P2 = abs(Y/L);
    P1 = P2(1:floor(L/2)+1);
    P1(2:end-1) = 2*P1(2:end-1);
    f = fs_val*(0:(L/2))/L;
    
    % Normaliser så grundtonen er 0 dB
    % Find index for fundamental frekvens
    [~, fund_idx] = min(abs(f - fundamental_freq));
    max_val = P1(fund_idx);
    
    if max_val > 0
        P1_dB = 20*log10(P1 / max_val);
    else
        P1_dB = zeros(size(P1));
    end
    
    % Sikkerhed: Hvis støjgulvet (SNR) ikke kunne beregnes, sæt en standard
    if isnan(stoejgulv_dB) || stoejgulv_dB <= 0
        stoejgulv_dB = 80; 
    end
    
    % Sæt alt under støjgulvet TIL støjgulvets værdi
    P1_dB(P1_dB < -stoejgulv_dB) = -stoejgulv_dB; 
    
    semilogx(f, P1_dB, 'Color', farve, 'LineWidth', 1.2);
    hold on;
    
    % Marker fundamental
    plot(fundamental_freq, 0, 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'r');
    
    % Marker harmoniske op til 5. orden
    for h = 2:5
        harm_freq = fundamental_freq * h;
        if harm_freq < fs_val/2
            [~, harm_idx] = min(abs(f - harm_freq));
            if harm_idx <= length(P1_dB)
                plot(harm_freq, P1_dB(harm_idx), 'mo', 'MarkerSize', 6);
            end
        end
    end
    
    % Lås Y-aksen fast
    ylim([-stoejgulv_dB - 10, 5]);
    xlim([1, min(fs_val/2, 50000)]);
end

function [f, mag_db] = compute_fft_simple(signal, Fs)
    N = length(signal);
    Y = fft(signal - mean(signal));
    P2 = abs(Y/N);
    P1 = P2(1:floor(N/2)+1);
    P1(2:end-1) = 2*P1(2:end-1);
    f = Fs * (0:floor(N/2)) / N;
    mag_db = 20*log10(P1 + eps);
end