function prices = loadOrFetchBars(symbols, alpacaClient, startDate)
%LOADORFETCHBARS  Alpaca daily close prices with a per-symbol date-keyed cache.
%
%   prices = loadOrFetchBars(symbols, alpacaClient)
%   prices = loadOrFetchBars(symbols, alpacaClient, startDate)
%
%   Returns a synchronised timetable of closing prices, one variable per
%   symbol (named by ticker).
%
%   Each symbol is cached individually in cache/bars_<symbol>_<yyyymmdd>.mat
%   so symbols shared across different portfolio calls are only downloaded
%   once per day.  Only symbols missing from today's cache are fetched, in
%   a single batch API call.  Stale files from previous days are removed
%   automatically per symbol.
%
%   Inputs:
%     symbols        1×N string array of ticker symbols
%     alpacaClient   Alpaca object (already constructed by the caller)
%     startDate      history start date string (default: '2000-01-01')

    arguments
        symbols      (1,:) string
        alpacaClient Alpaca
        startDate    string = "2000-01-01"
    end

    cacheDir = 'cache';
    [~, ~]   = mkdir(cacheDir);
    dateStr  = datestr(now, 'yyyymmdd');

    % ---------------------------------------------------------------
    % Identify which symbols are missing from today's cache
    % ---------------------------------------------------------------
    missing = string.empty(1, 0);
    for i = 1:numel(symbols)
        if ~isfile(symbolCacheFile(cacheDir, symbols(i), dateStr))
            missing(end+1) = symbols(i); %#ok<AGROW>
        end
    end

    % ---------------------------------------------------------------
    % Fetch missing symbols in one batch API call
    % ---------------------------------------------------------------
    if ~isempty(missing)
        fprintf('  [fetch] Downloading bars: %s\n', strjoin(missing, ', '));
        rawData = alpacaClient.getBars(missing, "1Day", startDate, datetime('today'));

        if numel(missing) == 1
            % Single-symbol: getBars unwraps to a timetable directly
            saveSingleSymbol(cacheDir, missing(1), dateStr, rawData);
        else
            % Multi-symbol: getBars returns a struct keyed by safeFieldName
            for i = 1:numel(missing)
                fn = strrep(char(missing(i)), '.', '_');
                saveSingleSymbol(cacheDir, missing(i), dateStr, rawData.(fn));
            end
        end
        fprintf('  [fetch] Cached %d symbol(s).\n', numel(missing));
    else
        fprintf('  [cache] All bars loaded from cache.\n');
    end

    % ---------------------------------------------------------------
    % Load every requested symbol from cache and synchronise
    % ---------------------------------------------------------------
    priceTables = cell(1, numel(symbols));
    for i = 1:numel(symbols)
        c               = load(symbolCacheFile(cacheDir, symbols(i), dateStr), 'closeData');
        priceTables{i}  = c.closeData;
    end

    if numel(symbols) == 1
        prices = priceTables{1};
    else
        prices = synchronize(priceTables{:});
    end
    prices.Properties.VariableNames = symbols;
end

% =========================================================================
%  Local helpers
% =========================================================================

function f = symbolCacheFile(cacheDir, sym, dateStr)
%SYMBOLCACHEFILE  Full path to the per-symbol cache file for a given date.
    safeSym = lower(strrep(char(sym), '.', '_'));
    f = fullfile(cacheDir, sprintf('bars_%s_%s.mat', safeSym, dateStr));
end

function saveSingleSymbol(cacheDir, sym, dateStr, tt)
%SAVESINGLESYMBOL  Persist a symbol's Close column; remove stale files first.
    safeSym  = lower(strrep(char(sym), '.', '_'));
    stale    = dir(fullfile(cacheDir, sprintf('bars_%s_*.mat', safeSym)));
    for k = 1:numel(stale)
        delete(fullfile(cacheDir, stale(k).name));
    end
    closeData = tt(:, "Close"); %#ok<NASGU>
    save(symbolCacheFile(cacheDir, sym, dateStr), 'closeData', '-v7.3');
end
