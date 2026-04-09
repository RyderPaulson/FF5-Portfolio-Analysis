classdef Alpaca < handle
    % ALPACA MATLAB SDK for Alpaca Markets historical stock data API.
    %
    %   a = Alpaca('YOUR_KEY_ID', 'YOUR_SECRET_KEY')
    %
    %   bars   = a.getBars("AAPL", "1Day", "2025-01-01", "2025-01-31")
    %   trades = a.getTrades("AAPL", "2025-01-02", "2025-01-02")
    %   quotes = a.getQuotes("AAPL", "2025-01-02", "2025-01-02")
    %   snap   = a.getSnapshots(["AAPL", "TSLA"])

    properties (Access = private)
        ApiKeyId     string
        ApiSecretKey string
        BaseUrl      string = "https://data.alpaca.markets/v2"
        RequestTimestamps double = []  % posixtime values for throttling
    end

    properties (Access = public)
        RateLimit double = 200  % requests per minute (adjust for higher-tier plans)
    end

    methods (Access = public)

        function obj = Alpaca(apiKeyId, apiSecretKey)
            % ALPACA Construct an Alpaca API client.
            %   a = Alpaca('KEY_ID', 'SECRET_KEY')
            arguments
                apiKeyId string {mustBeNonempty}
                apiSecretKey string {mustBeNonempty}
            end
            obj.ApiKeyId = apiKeyId;
            obj.ApiSecretKey = apiSecretKey;
        end

        function result = getBars(obj, symbols, timeframe, startDate, endDate, opts)
            % GETBARS Fetch historical OHLCV bar data.
            %
            %   tt = a.getBars("AAPL", "1Day", "2025-01-01", "2025-03-01")
            %   tt = a.getBars("AAPL", "1Hour", datetime(2025,1,1), datetime(2025,1,31), Adjustment="all")
            %   s  = a.getBars(["AAPL","TSLA"], "1Day", "2025-01-01", "2025-03-01")
            %
            %   Single symbol  -> timetable with Open, High, Low, Close, Volume, TradeCount, VWAP
            %   Multi  symbols -> struct of timetables keyed by symbol
            arguments
                obj
                symbols
                timeframe    string {mustBeNonempty}
                startDate
                endDate
                opts.Adjustment string {mustBeMember(opts.Adjustment, ["split","dividend","all",""])} = "split"
                opts.Feed       string {mustBeMember(opts.Feed, ["sip","iex","otc",""])} = ""
                opts.Sort       string {mustBeMember(opts.Sort, ["asc","desc",""])} = ""
            end

            symbols = string(symbols);
            params = struct();
            params.symbols   = strjoin(symbols, ",");
            params.timeframe = timeframe;
            params.start     = obj.formatDateParam(startDate);
            params.end_      = obj.formatDateParam(endDate);
            params.limit     = 10000;
            if opts.Adjustment ~= ""
                params.adjustment = opts.Adjustment;
            end
            if opts.Feed ~= ""
                params.feed = opts.Feed;
            end
            if opts.Sort ~= ""
                params.sort = opts.Sort;
            end

            raw = obj.paginatedRequest("/stocks/bars", params, "bars");
            result = obj.buildResult(symbols, raw, @obj.parseBars);
        end

        function result = getTrades(obj, symbols, startDate, endDate, opts)
            % GETTRADES Fetch historical tick-level trade data.
            %
            %   tt = a.getTrades("AAPL", "2025-01-02", "2025-01-02")
            %
            %   Returns timetable with Price, Size, Exchange, Conditions columns.
            arguments
                obj
                symbols
                startDate
                endDate
                opts.Feed string {mustBeMember(opts.Feed, ["sip","iex","otc",""])} = ""
                opts.Sort string {mustBeMember(opts.Sort, ["asc","desc",""])} = ""
            end

            symbols = string(symbols);
            params = struct();
            params.symbols = strjoin(symbols, ",");
            params.start   = obj.formatDateParam(startDate);
            params.end_    = obj.formatDateParam(endDate);
            params.limit   = 10000;
            if opts.Feed ~= ""
                params.feed = opts.Feed;
            end
            if opts.Sort ~= ""
                params.sort = opts.Sort;
            end

            raw = obj.paginatedRequest("/stocks/trades", params, "trades");
            result = obj.buildResult(symbols, raw, @obj.parseTrades);
        end

        function result = getQuotes(obj, symbols, startDate, endDate, opts)
            % GETQUOTES Fetch historical bid/ask quote data.
            %
            %   tt = a.getQuotes("AAPL", "2025-01-02", "2025-01-02")
            %
            %   Returns timetable with BidPrice, BidSize, BidExchange, AskPrice,
            %   AskSize, AskExchange, Conditions columns.
            arguments
                obj
                symbols
                startDate
                endDate
                opts.Feed string {mustBeMember(opts.Feed, ["sip","iex","otc",""])} = ""
                opts.Sort string {mustBeMember(opts.Sort, ["asc","desc",""])} = ""
            end

            symbols = string(symbols);
            params = struct();
            params.symbols = strjoin(symbols, ",");
            params.start   = obj.formatDateParam(startDate);
            params.end_    = obj.formatDateParam(endDate);
            params.limit   = 10000;
            if opts.Feed ~= ""
                params.feed = opts.Feed;
            end
            if opts.Sort ~= ""
                params.sort = opts.Sort;
            end

            raw = obj.paginatedRequest("/stocks/quotes", params, "quotes");
            result = obj.buildResult(symbols, raw, @obj.parseQuotes);
        end

        function result = getSnapshots(obj, symbols)
            % GETSNAPSHOTS Fetch latest market snapshot for symbols.
            %
            %   snap = a.getSnapshots("AAPL")
            %   snap = a.getSnapshots(["AAPL","TSLA"])
            %
            %   Returns struct with fields per symbol. Each contains:
            %     LatestTrade, LatestQuote, MinuteBar, DailyBar, PrevDailyBar
            arguments
                obj
                symbols
            end

            symbols = string(symbols);
            params = struct();
            params.symbols = strjoin(symbols, ",");

            data = obj.request("/stocks/snapshots", params);

            result = struct();
            for i = 1:numel(symbols)
                sym = symbols(i);
                fieldName = obj.safeFieldName(sym);
                if isfield(data, fieldName)
                    snapData = data.(fieldName);
                    entry = struct();

                    if isfield(snapData, 'latestTrade')
                        lt = snapData.latestTrade;
                        entry.LatestTrade = struct( ...
                            'Time', datetime(lt.t, 'InputFormat', "yyyy-MM-dd'T'HH:mm:ssZ", 'TimeZone', 'UTC'), ...
                            'Price', lt.p, ...
                            'Size', lt.s, ...
                            'Exchange', string(lt.x));
                    end

                    if isfield(snapData, 'latestQuote')
                        lq = snapData.latestQuote;
                        entry.LatestQuote = struct( ...
                            'Time', datetime(lq.t, 'InputFormat', "yyyy-MM-dd'T'HH:mm:ssZ", 'TimeZone', 'UTC'), ...
                            'BidPrice', lq.bp, ...
                            'BidSize', lq.bs, ...
                            'AskPrice', lq.ap, ...
                            'AskSize', lq.as_);
                    end

                    barFields = {'minuteBar', 'dailyBar', 'prevDailyBar'};
                    outFields = {'MinuteBar', 'DailyBar', 'PrevDailyBar'};
                    for k = 1:numel(barFields)
                        if isfield(snapData, barFields{k})
                            b = snapData.(barFields{k});
                            entry.(outFields{k}) = struct( ...
                                'Time', datetime(b.t, 'InputFormat', "yyyy-MM-dd'T'HH:mm:ssZ", 'TimeZone', 'UTC'), ...
                                'Open', b.o, ...
                                'High', b.h, ...
                                'Low', b.l, ...
                                'Close', b.c, ...
                                'Volume', b.v, ...
                                'VWAP', b.vw);
                        end
                    end

                    result.(fieldName) = entry;
                end
            end

            % Unwrap if single symbol
            if numel(symbols) == 1
                fnames = fieldnames(result);
                if ~isempty(fnames)
                    result = result.(fnames{1});
                end
            end
        end

    end % public methods

    methods (Access = private)

        function data = request(obj, endpoint, queryParams)
            % REQUEST Execute a single authenticated GET request.
            obj.throttle();

            url = obj.BaseUrl + endpoint;
            queryStr = obj.buildQueryString(queryParams);
            if queryStr ~= ""
                url = url + "?" + queryStr;
            end

            options = weboptions( ...
                'HeaderFields', { ...
                    'APCA-API-KEY-ID',     char(obj.ApiKeyId); ...
                    'APCA-API-SECRET-KEY', char(obj.ApiSecretKey) ...
                }, ...
                'ContentType', 'json', ...
                'Timeout', 30 ...
            );

            maxRetries = 3;
            for attempt = 1:maxRetries
                try
                    data = webread(char(url), options);
                    obj.RequestTimestamps(end+1) = posixtime(datetime('now'));
                    return;
                catch ME
                    if contains(ME.message, '429') && attempt < maxRetries
                        fprintf('Rate limited. Waiting 5 seconds (attempt %d/%d)...\n', attempt, maxRetries);
                        pause(5);
                    else
                        error('Alpaca:RequestFailed', ...
                            'API request failed: %s\nURL: %s', ME.message, url);
                    end
                end
            end
        end

        function allData = paginatedRequest(obj, endpoint, params, dataField)
            % PAGINATEDREQUEST Fetch all pages of data automatically.
            allData = struct();
            pageToken = "";

            while true
                if pageToken ~= ""
                    params.page_token = pageToken;
                end

                data = obj.request(endpoint, params);

                % Merge symbol data from this page into allData
                if isfield(data, char(dataField))
                    pageData = data.(char(dataField));
                    symbols = fieldnames(pageData);
                    for i = 1:numel(symbols)
                        sym = symbols{i};
                        newRows = pageData.(sym);
                        if isfield(allData, sym)
                            allData.(sym) = [allData.(sym); newRows];
                        else
                            allData.(sym) = newRows;
                        end
                    end
                end

                % Check for next page
                if isfield(data, 'next_page_token') && ~isempty(data.next_page_token)
                    pageToken = string(data.next_page_token);
                else
                    break;
                end
            end
        end

        function result = buildResult(obj, symbols, rawData, parseFn)
            % BUILDRESULT Convert raw paginated data into timetables.
            result = struct();
            for i = 1:numel(symbols)
                sym = symbols(i);
                fieldName = obj.safeFieldName(sym);
                if isfield(rawData, fieldName) && ~isempty(rawData.(fieldName))
                    result.(fieldName) = parseFn(rawData.(fieldName));
                end
            end

            % Unwrap single symbol
            if numel(symbols) == 1
                fnames = fieldnames(result);
                if ~isempty(fnames)
                    result = result.(fnames{1});
                else
                    result = timetable();
                end
            end
        end

        function tt = parseBars(~, bars)
            % PARSEBARS Convert bar struct array to timetable.
            if isempty(bars)
                tt = timetable();
                return;
            end
            n = numel(bars);
            Time       = NaT(n, 1, 'TimeZone', 'UTC');
            Open       = zeros(n, 1);
            High       = zeros(n, 1);
            Low        = zeros(n, 1);
            Close      = zeros(n, 1);
            Volume     = zeros(n, 1);
            TradeCount = zeros(n, 1);
            VWAP       = zeros(n, 1);

            for i = 1:n
                Time(i)       = datetime(bars(i).t, 'InputFormat', "yyyy-MM-dd'T'HH:mm:ssZ", 'TimeZone', 'UTC');
                Open(i)       = bars(i).o;
                High(i)       = bars(i).h;
                Low(i)        = bars(i).l;
                Close(i)      = bars(i).c;
                Volume(i)     = bars(i).v;
                TradeCount(i) = bars(i).n;
                VWAP(i)       = bars(i).vw;
            end

            tt = timetable(Time, Open, High, Low, Close, Volume, TradeCount, VWAP);
        end

        function tt = parseTrades(~, trades)
            % PARSETRADES Convert trade struct array to timetable.
            if isempty(trades)
                tt = timetable();
                return;
            end
            n = numel(trades);
            Time     = NaT(n, 1, 'TimeZone', 'UTC');
            Price    = zeros(n, 1);
            Size     = zeros(n, 1);
            Exchange = strings(n, 1);
            Conditions = cell(n, 1);

            for i = 1:n
                Time(i)     = datetime(trades(i).t, 'InputFormat', "yyyy-MM-dd'T'HH:mm:ssZ", 'TimeZone', 'UTC');
                Price(i)    = trades(i).p;
                Size(i)     = trades(i).s;
                Exchange(i) = string(trades(i).x);
                if isfield(trades(i), 'c') && ~isempty(trades(i).c)
                    Conditions{i} = trades(i).c;
                else
                    Conditions{i} = {};
                end
            end

            tt = timetable(Time, Price, Size, Exchange, Conditions);
        end

        function tt = parseQuotes(~, quotes)
            % PARSEQUOTES Convert quote struct array to timetable.
            if isempty(quotes)
                tt = timetable();
                return;
            end
            n = numel(quotes);
            Time        = NaT(n, 1, 'TimeZone', 'UTC');
            BidPrice    = zeros(n, 1);
            BidSize     = zeros(n, 1);
            BidExchange = strings(n, 1);
            AskPrice    = zeros(n, 1);
            AskSize     = zeros(n, 1);
            AskExchange = strings(n, 1);
            Conditions  = cell(n, 1);

            for i = 1:n
                Time(i)        = datetime(quotes(i).t, 'InputFormat', "yyyy-MM-dd'T'HH:mm:ssZ", 'TimeZone', 'UTC');
                BidPrice(i)    = quotes(i).bp;
                BidSize(i)     = quotes(i).bs;
                BidExchange(i) = string(quotes(i).bx);
                AskPrice(i)    = quotes(i).ap;
                AskSize(i)     = quotes(i).as_;
                AskExchange(i) = string(quotes(i).ax);
                if isfield(quotes(i), 'c') && ~isempty(quotes(i).c)
                    Conditions{i} = quotes(i).c;
                else
                    Conditions{i} = {};
                end
            end

            tt = timetable(Time, BidPrice, BidSize, BidExchange, AskPrice, AskSize, AskExchange, Conditions);
        end

        function dtStr = formatDateParam(~, dt)
            % FORMATDATEPARAM Convert datetime or string to RFC-3339 date string.
            if isdatetime(dt)
                dtStr = string(datestr(dt, 'yyyy-mm-ddTHH:MM:SS') + "Z");
            else
                dtStr = string(dt);
            end
        end

        function throttle(obj)
            % THROTTLE Enforce rate limiting.
            now_ = posixtime(datetime('now'));

            % Prune timestamps older than 60 seconds
            obj.RequestTimestamps = obj.RequestTimestamps(obj.RequestTimestamps > now_ - 60);

            buffer = 10;
            if numel(obj.RequestTimestamps) >= (obj.RateLimit - buffer)
                % Wait until the oldest request in the window expires
                oldest = min(obj.RequestTimestamps);
                waitTime = 60 - (now_ - oldest) + 0.1;
                if waitTime > 0
                    fprintf('Rate limit approaching. Pausing %.1f seconds...\n', waitTime);
                    pause(waitTime);
                    % Prune again after waiting
                    obj.RequestTimestamps = obj.RequestTimestamps( ...
                        obj.RequestTimestamps > posixtime(datetime('now')) - 60);
                end
            end
        end

        function qs = buildQueryString(~, params)
            % BUILDQUERYSTRING Convert struct to URL query string.
            fnames = fieldnames(params);
            parts = strings(1, numel(fnames));
            for i = 1:numel(fnames)
                key = fnames{i};
                val = params.(key);
                % Handle the 'end_' -> 'end' rename (end is reserved in MATLAB)
                apiKey = key;
                if strcmp(key, 'end_')
                    apiKey = 'end';
                end
                % Handle 'as_' -> 'as' rename
                if strcmp(key, 'as_')
                    apiKey = 'as';
                end
                parts(i) = string(apiKey) + "=" + urlencode(string(val));
            end
            qs = strjoin(parts, "&");
        end

        function name = safeFieldName(~, symbol)
            % SAFEFIELDNAME Convert symbol to valid MATLAB struct field name.
            name = char(symbol);
            name = regexprep(name, '[^a-zA-Z0-9]', '_');
            if ~isempty(name) && (name(1) >= '0' && name(1) <= '9')
                name = ['x' name];
            end
        end

    end % private methods

    methods (Static, Access = private)

        function encoded = urlencode(str)
            % URLENCODE Percent-encode a string for URL query parameters.
            str = char(str);
            encoded = '';
            for i = 1:length(str)
                c = str(i);
                if (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || ...
                   (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.' || c == '~'
                    encoded = [encoded c]; %#ok<AGROW>
                elseif c == ','
                    encoded = [encoded '%2C']; %#ok<AGROW>
                else
                    encoded = [encoded sprintf('%%%02X', double(c))]; %#ok<AGROW>
                end
            end
        end

    end % static private methods

end
