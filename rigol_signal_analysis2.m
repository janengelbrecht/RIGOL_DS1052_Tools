function RigolAnalyse()
    % Hovedfunktion til analyse af Rigol .mat data
    
    %% 1. INDLÆS DATA FRA FIL
    [fileName, filePath] = uigetfile('*.mat', 'Vælg Rigol MAT-fil');
    if isequal(fileName,0)
        disp('Filvalg annulleret.');
        return;
    end
    
    fullFilePath = fullfile(filePath, fileName);
    raw = load(fullFilePath);
    
    % Indlæs med de præcise navne fra Rigol SCPI Suite
    try
        ch1 = double(raw.ch1_voltage(:));
        ch2 = double(raw.ch2_voltage(:));
        t   = double(raw.ch1_time(:));
        fs  = double(raw.sample_rate);
    catch ME
        error('Kunne ikke finde de korrekte variabler (ch1_voltage, ch2_voltage, ch1_time, sample_rate). Tjek om det er den rigtige fil.');
    end
    
    % Tjek om CH2 har noget signal (ikke konstant 0)
    ch2_has_signal = (max(ch2) - min(ch2)) > 0.001;  % Tærskel på 1mV
    
    if ~ch2_has_signal
        warning('CH2 har konstant signal (ingen måling). Faseforskel kan ikke beregnes korrekt.');
    end

    %% 2. UDFØR BEREGNINGER
    disp('Beregner signalparametre...');
    resCH1 = beregnParametre(ch1, fs);
    
    if ch2_has_signal
        resCH2 = beregnParametre(ch2, fs);
    else
        % CH2 er konstant - returner tomme værdier
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
    
    % Krydskanal beregninger (kun hvis CH2 har signal)
    if ch2_has_signal && resCH1.Vp > 0
        Av = resCH2.Vp / resCH1.Vp;
        AvdB = 20 * log10(Av);
        
        % Faseforskel
        [c, lags] = xcorr(ch1 - mean(ch1), ch2 - mean(ch2));
        [~, I] = max(abs(c));
        timeDelay = lags(I) / fs;
        faseforskel = mod(timeDelay * resCH1.Frekvens * 360, 360);
        if faseforskel > 180, faseforskel = faseforskel - 360; end
    else
        Av = NaN;
        AvdB = NaN;
        faseforskel = NaN;
        warning('Kunne ikke beregne krydskanal parametre - CH2 signal mangler');
    end

    %% 3. GENERER OSCILLOSKOP BILLED
    disp('Genererer tidsdomæne graf...');
    figScope = figure('Visible', 'off', 'Position', [100, 100, 800, 400]);
    plot(t*1000, ch1, 'Color', '#4DBEEE', 'LineWidth', 1.5); % Lyseblå
    hold on;
    
    if ch2_has_signal
        plot(t*1000, ch2, 'Color', '#77AC30', 'LineWidth', 1.5); % Grøn
        legend('CH1', 'CH2', 'TextColor', 'w', 'Color', 'none', 'EdgeColor', 'none');
    else
        legend('CH1', 'TextColor', 'w', 'Color', 'none', 'EdgeColor', 'none');
        text(0.5, 0.5, 'CH2: INTET SIGNAL', 'Units', 'normalized', ...
            'Color', 'r', 'FontSize', 14, 'HorizontalAlignment', 'center');
    end
    
    set(gca, 'Color', '#1E1E1E', 'XColor', '#CCCCCC', 'YColor', '#CCCCCC');
    set(gcf, 'Color', '#1E1E1E');
    grid on;
    ax = gca;
    ax.GridColor = [0.7 0.7 0.7];
    ax.GridAlpha = 0.5;
    title('Oscilloskop Måling', 'Color', 'w');
    xlabel('Tid (ms)', 'Color', 'w');
    ylabel('Amplitude (V)', 'Color', 'w');
    
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
        plotKlippetFFT(ch1, resCH1.SNR, '#4DBEEE', fs);
        grid on;
        title('Spektrumanalyse - Kanal 1 (CH1)', 'Color', 'k');
        ylabel('Amplitude (dB)', 'Color', 'k');
        xlim([1, fs/2]); 
        
        % Nederste graf (CH2) - kun hvis der er signal
        subplot(2, 1, 2);
        if ch2_has_signal && ~isnan(resCH2.SNR)
            plotKlippetFFT(ch2, resCH2.SNR, '#77AC30', fs);
            title('Spektrumanalyse - Kanal 2 (CH2)', 'Color', 'k');
        else
            % Vis tom graf med besked
            plot([0 1], [0 0], 'Color', '#77AC30', 'LineWidth', 1.2);
            title('Spektrumanalyse - Kanal 2 (CH2) - INTET SIGNAL', 'Color', 'k');
            text(0.5, 0.5, 'CH2: INTET SIGNAL', 'Units', 'normalized', ...
                'Color', 'r', 'FontSize', 12, 'HorizontalAlignment', 'center');
        end
        grid on;
        xlabel('Frekvens (Hz) - Logaritmisk', 'Color', 'k');
        ylabel('Amplitude (dB)', 'Color', 'k');
        xlim([1, fs/2]); 
        
        exportgraphics(figFFT, fftImgPath, 'Resolution', 150);
        close(figFFT);
        fftSection = sprintf('<img src="fft_plot.png" alt="FFT Spectrum" class="responsive-img">');
    else
        fftSection = '<p style="color: #d9534f;">Grundfrekvensen er over 50 kHz eller kunne ikke beregnes. Spektrumanalyse blev ikke genereret.</p>';
    end

    %% 5. GENERER HTML5 RAPPORT
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
    
    % CH2 SNR string
    ch2_snr_str = sprintf('%.1f', -resCH2.SNR);
    if isnan(resCH2.SNR), ch2_snr_str = 'N/A'; end
    
    html = sprintf([
        '<!DOCTYPE html>\n', ...
        '<html lang="da">\n', ...
        '<head>\n', ...
        '    <meta charset="UTF-8">\n', ...
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n', ...
        '    <title>Rigol signalanalyse rapport</title>\n', ...
        '    <style>\n', ...
        '        body { font-family: "Segoe UI", Arial, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }\n', ...
        '        .container { max-width: 1000px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }\n', ...
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
        '                <table>\n', ...
        '                    <tr><th>Frekvens</th><td>%s</td></tr>\n', ...
        '                    <tr><th>THD</th><td>%s</td></tr>\n', ...
        '                    <tr><th>SNR (Støjgulv)</th><td>%s dB</td></tr>\n', ...
        '                    <tr><th>SINAD</th><td>%s</td></td>\n', ...
        '                    <tr><th>SFDR</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Vp (Spids)</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Vpp (Spids-Spids)</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Vrms</th><td>%.3f V</td></tr>\n', ...
        '                    <tr><th>Rise Time</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Fall Time</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Duty Cycle</th><td>%s</td></tr>\n', ...
        '                    <tr><th>Crest Faktor</th><td>%.3f</td></tr>\n', ...
        '                    <tr><th>Form Faktor</th><td>%.3f</td></tr>\n', ...
        '                </table>\n', ...
        '                <p class="warning">OBS: CH2 har intet signal! Kontroller tilslutning af kanal 2.</p>\n', ...
        '            </div>\n', ...
        '        </div>\n', ...
        '        \n', ...
        '        <h2>Spektrumanalyse (FFT)</h2>\n', ...
        '        <p><em>Frekvenskomposanter under de respektive SNR-støjgulve (%s dB for CH1 / %s dB for CH2) er filtreret væk.</em></p>\n', ...
        '        %s\n', ...
        '        \n', ...
        '        <h2>Tidsdomæne (Oscilloskop)</h2>\n', ...
        '        <img src="scope_plot.png" alt="Oscilloskop" class="responsive-img">\n', ...
        '    </div>\n', ...
        '</body>\n', ...
        '</html>'
    ], fileName, faseforskel_str, Av_str, AvdB_str, ...
       resCH1.Frekvens, resCH1.THD_pct, resCH1.THD_dB, resCH1.SNR, resCH1.SINAD, resCH1.SFDR, ...
       resCH1.Vp, resCH1.Vpp, resCH1.Vrms, resCH1.RiseTime, resCH1.FallTime, resCH1.DutyCycle, ...
       resCH1.CrestFaktor, resCH1.FormFaktor, ...
       'Kunne ikke beregnes', 'Kunne ikke beregnes', ch2_snr_str, 'Kunne ikke beregnes', 'Kunne ikke beregnes', ...
       resCH2.Vp, resCH2.Vpp, resCH2.Vrms, 'Kunne ikke beregnes', 'Kunne ikke beregnes', 'Kunne ikke beregnes', ...
       resCH2.CrestFaktor, resCH2.FormFaktor, ...
       num2str(-resCH1.SNR, '%.1f'), ch2_snr_str, fftSection);
    
    fwrite(fid, html);
    fclose(fid);
    
    disp('Analyse færdig! HTML-rapporten åbnes nu.');
    web(['file://' htmlPath], '-browser');
end

%% ========================================================================
%  HJÆLPEFUNKTIONER (Placeret udenfor hovedfunktionen for stabilitet)
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
    
    res.CrestFaktor = res.Vp / res.Vrms;
    res.FormFaktor = res.Vrms / res.Vavg;
    
    try 
        res.Frekvens = medfreq(signal, fs_val); 
    catch
        res.Frekvens = NaN;
    end
    
    try 
        res.RiseTime = mean(risetime(signal, fs_val)); 
    catch, 
        res.RiseTime = NaN; 
    end
    
    try 
        res.FallTime = mean(falltime(signal, fs_val)); 
    catch, 
        res.FallTime = NaN; 
    end
    
    try 
        res.DutyCycle = mean(dutycycle(signal, fs_val)) * 100; 
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

function plotKlippetFFT(signal, stoejgulv_dB, farve, fs_val)
    L = length(signal);
    Y = fft(signal);
    P2 = abs(Y/L);
    P1 = P2(1:floor(L/2)+1);
    P1(2:end-1) = 2*P1(2:end-1);
    f = fs_val*(0:(L/2))/L;
    
    % Normaliser så grundtonen er 0 dB
    max_val = max(P1);
    if max_val > 0
        P1_dB = 20*log10(P1 / max_val);
    else
        P1_dB = zeros(size(P1));
    end
    
    % Sikkerhed: Hvis støjgulvet (SNR) ikke kunne beregnes, sæt en standard
    if isnan(stoejgulv_dB) || stoejgulv_dB <= 0
        stoejgulv_dB = 80; 
    end
    
    % Sæt alt under støjgulvet TIL støjgulvets værdi for en kontinuerlig flad linje
    P1_dB(P1_dB < -stoejgulv_dB) = -stoejgulv_dB; 
    
    semilogx(f, P1_dB, 'Color', farve, 'LineWidth', 1.2);
    
    % Lås Y-aksen fast, så man altid ser fra støjgulvet op til lidt over 0 dB
    ylim([-stoejgulv_dB - 10, 5]);
end