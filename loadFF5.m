function ff5 = loadFF5(csvPath)
%LOADFF5 Load Fama-French 5-factor daily data from CSV.
%   ff5 = loadFF5(csvPath) returns a timetable with columns:
%   MktRF, SMB, HML, RMW, CMA, RF (all in decimal, not percentage points).

if nargin < 1
    csvPath = "F-F Research Data 5 Factors 2x3 daily.csv";
end

opts = detectImportOptions(csvPath, 'Delimiter', ',');
opts.DataLines = [5 Inf];                      % skip 4 header lines
opts.VariableNames = {'Date','MktRF','SMB','HML','RMW','CMA','RF'};
opts.VariableTypes = {'char','double','double','double','double','double','double'};
opts = setvaropts(opts, 'Date', 'WhitespaceRule', 'trim');

T = readtable(csvPath, opts);

% Remove non-data rows (copyright footer, blanks)
validRows = ~cellfun(@isempty, T.Date) & strlength(T.Date) == 8;
T = T(validRows, :);

% Parse YYYYMMDD dates (with UTC timezone to match Alpaca data)
dates = datetime(T.Date, 'InputFormat', 'yyyyMMdd', 'TimeZone', 'UTC');

% Convert from percentage points to decimals
factorCols = {'MktRF','SMB','HML','RMW','CMA','RF'};
for c = factorCols
    T.(c{1}) = T.(c{1}) / 100;
end

ff5 = timetable(dates, T.MktRF, T.SMB, T.HML, T.RMW, T.CMA, T.RF, ...
    'VariableNames', factorCols);
end
