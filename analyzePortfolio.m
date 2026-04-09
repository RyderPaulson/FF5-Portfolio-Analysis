function results = analyzePortfolio(pm, options)
% ANALYZEPORTFOLIO  FF5 factor analysis, GARCH Monte Carlo, and risk metrics.
%
%   results = analyzePortfolio(pm)
%   results = analyzePortfolio(pm, Name, Value)
%
%   Inputs:
%       pm  - PortfolioModel object (Assets, Weights, Title, RebalanceCost)
%
%   Name-Value Arguments:
%       Rf               - Risk-free rate (default: 0.045)
%       nSimulations     - Number of Monte Carlo paths (default: 10000)
%       HorizonYears     - Total simulation horizon in years (default: 44)
%       Milestones       - Struct array with 'name' and 'year' fields
%       MilestoneTargets - Target multiples for milestone probability (default: [3 10])
%       Title            - Title override (default: pm.Title)
%       FF5Path          - Path to Fama-French 5-factor CSV
%       UseCache         - Load/save portfolio results cache (default: true)
%       Verbose          - Print intermediate output (default: false)

    arguments
        pm (1,1) PortfolioModel
        options.Rf (1,1) double = 0.045
        options.nSimulations (1,1) double = 10000
        options.HorizonYears (1,1) double = 44
        options.Milestones struct = [struct('name','House','year',10); struct('name','Retire','year',44)]
        options.MilestoneTargets (1,:) double = [3 10]
        options.Title string = ""
        options.FF5Path string = "F-F Research Data 5 Factors 2x3 daily.csv"
        options.UseCache (1,1) logical = true
        options.Verbose (1,1) logical = false
    end

    % Use portfolio title if no override provided
    if options.Title == ""
        options.Title = pm.Title;
    end

    symbols     = pm.Assets;
    weightsNorm = pm.Weights;          % already normalised by PortfolioModel
    nAssets     = pm.nAssets();
    tradingDaysPerYear = 252;

    %% Level-2 Cache Check (portfolio results)
    cacheFile = '';
    if options.UseCache
        [hit, cacheFile] = portfolioCacheKey(symbols, weightsNorm);
        if hit
            c = load(cacheFile);
            % Validate cache has required fields (new fields added over time)
            if isfield(c.results, 'forecastedReturns') && isfield(c.results, 'factorPremiaAnnual')
                fprintf('  [cache] Portfolio results loaded from cache.\n');
                results = c.results;
                return;
            else
                fprintf('  [cache] Stale cache detected — recomputing.\n');
            end
        end
    end

    %% Data Download (Level-1 Cache via loadOrFetchBars)
    load('alpaca_keys.mat', 'alpaca_key_id', 'alpaca_secret');
    alpacaClient = Alpaca(alpaca_key_id, alpaca_secret);
    prices       = loadOrFetchBars(symbols, alpacaClient);

    % Compute returns
    returns      = tick2ret(prices);
    assetReturns = returns{:, symbols};
    returnDates  = returns.Time;

    % Drop rows with any NaN
    validRows    = all(~isnan(assetReturns), 2);
    assetReturns = assetReturns(validRows, :);
    returnDates  = returnDates(validRows);

    if options.Verbose
        fprintf('  Usable observations: %d (%.1f years)\n', ...
            size(assetReturns, 1), size(assetReturns, 1)/tradingDaysPerYear);
    end

    %% Fama-French 5-Factor Expected Returns
    Rf  = options.Rf;
    ff5 = loadFF5(options.FF5Path);

    % Strip time-of-day from Alpaca timestamps before synchronising
    returnDatesDay = dateshift(returnDates, 'start', 'day');
    assetTT        = array2timetable(assetReturns, 'RowTimes', returnDatesDay, ...
                                     'VariableNames', "Asset" + (1:nAssets));
    syncTT         = synchronize(assetTT, ff5, 'intersection');
    assetRetSync   = double(syncTT{:, "Asset" + (1:nAssets)});
    factorMatrix   = double([syncTT.MktRF, syncTT.SMB, syncTT.HML, syncTT.RMW, syncTT.CMA]);
    rfDaily        = double(syncTT.RF);
    syncDates      = syncTT.Properties.RowTimes;
    nObs           = size(assetRetSync, 1);

    % OLS regression per asset: (r_i - RF) = alpha + betas * factors + epsilon
    factorBetas = zeros(nAssets, 5);
    alphas      = zeros(nAssets, 1);
    X           = [ones(nObs, 1), factorMatrix];
    for i = 1:nAssets
        excessRet        = assetRetSync(:,i) - rfDaily;
        coeffs           = X \ excessRet;
        alphas(i)        = coeffs(1);
        factorBetas(i,:) = coeffs(2:6)';
    end

    % Expected returns using long-run factor premia (full FF5 history, not just overlap)
    fullFactors        = double([ff5.MktRF, ff5.SMB, ff5.HML, ff5.RMW, ff5.CMA]);
    factorPremiaDaily  = mean(fullFactors);
    factorPremiaAnnual = factorPremiaDaily * tradingDaysPerYear;
    muAnnual           = Rf + (factorBetas * factorPremiaAnnual')';
    muDaily            = muAnnual(:) / tradingDaysPerYear;

    % Portfolio factor exposures
    portFactorBetas = weightsNorm * factorBetas;

    if options.Verbose
        factorNames = ["Mkt" "SMB" "HML" "RMW" "CMA"];
        fprintf('\n  FF5 Factor Betas:\n');
        fprintf('  %-6s %8s %8s %8s %8s %8s  E[r]\n', '', factorNames);
        for i = 1:nAssets
            fprintf('  %-6s %8.3f %8.3f %8.3f %8.3f %8.3f  %.2f%%\n', ...
                symbols(i), factorBetas(i,:), muAnnual(i)*100);
        end
        fprintf('  Portfolio factor exposures:\n');
        fprintf('  %-6s %8.3f %8.3f %8.3f %8.3f %8.3f\n', 'Port', portFactorBetas);
    end

    %% Ledoit-Wolf Shrinkage Covariance
    [SigmaDaily, shrinkageIntensity] = ledoitWolfShrink(assetRetSync);

    if options.Verbose
        fprintf('  Ledoit-Wolf shrinkage intensity: %.4f\n', shrinkageIntensity);
    end

    % Portfolio-level moments
    portMuAnnual    = weightsNorm * muAnnual(:);
    SigmaAnnual     = SigmaDaily * tradingDaysPerYear;
    portSigmaAnnual = sqrt(weightsNorm * SigmaAnnual * weightsNorm');

    %% GARCH(1,1) Parameter Fitting
    totalDays = options.HorizonYears * tradingDaysPerYear;
    nSim      = options.nSimulations;

    omega = zeros(nAssets, 1);
    alpha = zeros(nAssets, 1);
    betaG = zeros(nAssets, 1);
    for i = 1:nAssets
        mdl      = garch(1,1);
        est      = estimate(mdl, assetRetSync(:,i), 'Display', 'off');
        omega(i) = est.Constant;
        alpha(i) = est.ARCH{1};
        betaG(i) = est.GARCH{1};
    end

    if options.Verbose
        fprintf('\n  GARCH(1,1) Parameters:\n');
        fprintf('  %-6s %12s %12s %12s\n', '', 'omega', 'alpha', 'beta');
        for i = 1:nAssets
            fprintf('  %-6s %12.6f %12.6f %12.6f\n', symbols(i), omega(i), alpha(i), betaG(i));
        end
    end

    % Correlation matrix for correlated shocks
    D          = sqrt(diag(SigmaDaily));
    corrMatrix = SigmaDaily ./ (D * D');
    L          = chol(corrMatrix, 'lower');

    %% Monte Carlo Simulation via garchSimulate
    % rng is called here so that interpreted-mode runs are reproducible.
    % In MEX mode, seed the RNG externally before calling analyzePortfolio.
    rng(42);
    portRetPaths = garchSimulate(muDaily, omega, alpha, betaG, L, weightsNorm, totalDays, nSim);

    % Cumulative wealth paths
    initialValue = 1 - pm.RebalanceCost;
    paths        = initialValue * cumprod(1 + portRetPaths, 1);
    tYears       = (1:totalDays)' / tradingDaysPerYear;

    % Fan-chart percentiles
    pct5  = prctile(paths, 5,  2);
    pct25 = prctile(paths, 25, 2);
    pct50 = prctile(paths, 50, 2);
    pct75 = prctile(paths, 75, 2);
    pct95 = prctile(paths, 95, 2);

    %% Historical Risk Metrics
    portHistReturns = assetRetSync * weightsNorm';
    nHist           = numel(portHistReturns);
    portVolAnnual   = portSigmaAnnual;

    rfDailyScalar = Rf / tradingDaysPerYear;
    downsideRet   = min(portHistReturns - rfDailyScalar, 0);
    downsideDev   = sqrt(mean(downsideRet.^2)) * sqrt(tradingDaysPerYear);

    cumWealth      = cumprod(1 + portHistReturns);
    runningMax     = cummax(cumWealth);
    drawdownSeries = 1 - cumWealth ./ runningMax;
    maxDrawdown    = max(drawdownSeries);

    arithReturn = mean(portHistReturns) * tradingDaysPerYear;
    geomReturn  = exp(sum(log(1 + portHistReturns)) / nHist)^tradingDaysPerYear - 1;

    sharpe     = (portMuAnnual - Rf) / portVolAnnual;
    histSharpe = (arithReturn  - Rf) / portVolAnnual;   % realized; comparable to Morningstar
    sortino    = (portMuAnnual - Rf) / downsideDev;
    calmar     = geomReturn / maxDrawdown;

    %% Build Results Struct
    milestones = options.Milestones;

    results.symbols            = symbols;
    results.weights            = weightsNorm;
    results.factorBetas        = factorBetas;
    results.alphas             = alphas;
    results.portFactorBetas    = portFactorBetas;
    results.muAnnual           = muAnnual;
    results.factorPremiaAnnual = factorPremiaAnnual;
    results.portMuAnnual       = portMuAnnual;
    results.portSigmaAnnual    = portSigmaAnnual;
    results.portRisk           = portSigmaAnnual;
    results.portReturn         = portMuAnnual;
    results.assetReturns       = assetRetSync;
    results.SigmaAnnual        = SigmaAnnual;
    results.shrinkageIntensity = shrinkageIntensity;
    results.garchParams        = struct('omega', omega, 'alpha', alpha, 'beta', betaG);
    results.arithReturn        = arithReturn;
    results.geomReturn         = geomReturn;
    results.portVolAnnual      = portVolAnnual;
    results.downsideDev        = downsideDev;
    results.maxDrawdown        = maxDrawdown;
    results.sharpe             = sharpe;
    results.histSharpe         = histSharpe;
    results.sortino            = sortino;
    results.calmar             = calmar;
    results.histDrawdown       = drawdownSeries;
    results.histDates          = syncDates(1:nHist);   % FF5-sync aligned dates
    results.tradingDaysPerYear = tradingDaysPerYear;

    % Forecasted returns data (used by plotForecastedReturns)
    results.forecastedReturns.tYears = tYears;
    results.forecastedReturns.pct5   = pct5;
    results.forecastedReturns.pct25  = pct25;
    results.forecastedReturns.pct50  = pct50;
    results.forecastedReturns.pct75  = pct75;
    results.forecastedReturns.pct95  = pct95;

    % Milestone cross-sections — stored in place of full paths to keep
    % cache files compact.  milestoneVals{m} is 1×nSim for milestone m.
    results.milestoneVals = cell(1, numel(milestones));
    for m = 1:numel(milestones)
        mIdx = milestones(m).year * tradingDaysPerYear;
        if mIdx <= totalDays
            results.milestoneVals{m} = paths(mIdx, :);
        else
            results.milestoneVals{m} = [];
        end
    end

    % Milestone statistics
    for m = 1:numel(milestones)
        mIdx = milestones(m).year * tradingDaysPerYear;
        if mIdx <= totalDays
            vals = results.milestoneVals{m};
            ms.name         = milestones(m).name;
            ms.year         = milestones(m).year;
            ms.medianGrowth = median(vals);
            ms.pct5         = prctile(vals, 5);
            ms.pct95        = prctile(vals, 95);
            ms.probLoss     = mean(vals < 1) * 100;
            ms.VaR5         = 1 - prctile(vals, 5);
            ms.CVaR5        = 1 - mean(vals(vals <= prctile(vals, 5)));
            ms.CAGR         = median(vals)^(1/milestones(m).year) - 1;

            targetProbs = zeros(size(options.MilestoneTargets));
            for ti = 1:numel(options.MilestoneTargets)
                targetProbs(ti) = mean(vals >= options.MilestoneTargets(ti)) * 100;
            end
            ms.targetMultiples = options.MilestoneTargets;
            ms.targetProbs     = targetProbs;
            results.milestones(m) = ms;
        end
    end

    %% Save to Level-2 Cache
    if options.UseCache && ~isempty(cacheFile)
        save(cacheFile, 'results');
    end
end

% =========================================================================
%  Local Functions
% =========================================================================

function [hit, cacheFile] = portfolioCacheKey(symbols, weightsNorm)
%PORTFOLIOCACHEKEY  Compute cache filename and check if a same-day file exists.
%   Returns hit=true and the cacheFile path if the file exists;
%   hit=false and the target cacheFile path if it does not.
    cacheDir = 'cache';
    [~, ~]   = mkdir(cacheDir);

    % djb2-style hash over symbols+weights string
    keyStr = [strjoin(symbols, '+'), '|', ...
              strjoin(arrayfun(@(w) sprintf('%.6f', w), weightsNorm, ...
                              'UniformOutput', false), ',')];
    h = 5381;
    for c = double(uint8(char(keyStr)))
        h = mod(h * 33 + c, 2^32);
    end
    cacheFile = fullfile(cacheDir, sprintf('port_%08x_%s.mat', uint32(h), datestr(now,'yyyymmdd')));
    hit = isfile(cacheFile);
end
