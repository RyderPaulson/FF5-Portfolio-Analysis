function opts = defaultOptimOptions(portIn, nvargs)
%DEFAULTOPTIMOPTIONS  Shared constraint / parameter defaults for all optimisers.
%
%   opts = defaultOptimOptions(pm)
%   opts = defaultOptimOptions(pm, 'Rf', 0.04, 'LongOnly', false, ...)
%
%   Accepts a PortfolioModel and returns a struct accepted by every
%   optimXxx function.  When the portfolio has been analysed (Results
%   populated), factorBetas, factorPremiaAnnual, and scenarioReturns
%   are auto-populated from Results unless explicitly overridden.
%   Method-specific fields that are unused by a particular optimiser
%   are simply ignored.
%
%   COMMON FIELDS
%     LongOnly       – logical  (true)   false allows short positions
%     MinWeight      – 1×N      ([])     per-asset lower bounds (default 0 if LongOnly)
%     MaxWeight      – 1×N      ([])     per-asset upper bounds (default 1)
%     FullyInvested  – logical  (true)   weights must sum to 1
%     Rf             – scalar   (0.045)  annualised risk-free rate
%
%   MEAN-VARIANCE
%     TargetReturn   – scalar   (NaN)    target annual return (NaN → use MaxSharpe)
%     MaxSharpe      – logical  (true)   maximise Sharpe ratio instead of targeting return
%
%   CVaR
%     Alpha          – scalar   (0.05)   tail probability (5 % → 95 % CVaR)
%     scenarioReturns – T×N     ([])     scenario return matrix (auto from Results)
%
%   BLACK-LITTERMAN
%     Tau                – scalar   (0.05)   uncertainty scaling on prior
%     ViewConfidence     – 1×K     ([])     per-view confidence (0–1), K = # views
%     factorBetas        – N×5     ([])     asset FF5 factor betas (auto from Results)
%     factorPremiaAnnual – 1×5     ([])     annualised FF5 factor premia (auto from Results)
%     equilibriumWeights – 1×N     ([])     market-cap or reference weights (default: equal)
%
%   FACTOR-BASED
%     FactorTargets  – 1×5      (NaN×5)  desired factor exposures (NaN = unconstrained)
%     FactorPenalty  – 1×5      (ones)   penalty weights for deviation from targets
%     RiskAversion   – scalar   (0.5)    trade-off between factor targeting and risk

    arguments
        portIn (1,1) PortfolioModel

        % — common —
        nvargs.LongOnly       (1,1) logical = true
        nvargs.MinWeight      (1,:) double  = []
        nvargs.MaxWeight      (1,:) double  = []
        nvargs.FullyInvested  (1,1) logical = true
        nvargs.Rf             (1,1) double  = 0.045

        % — mean-variance —
        nvargs.TargetReturn   (1,1) double  = NaN
        nvargs.MaxSharpe      (1,1) logical = true

        % — CVaR —
        nvargs.Alpha          (1,1) double  = 0.05
        nvargs.scenarioReturns       double = []

        % — Black-Litterman —
        nvargs.Tau             (1,1) double  = 0.05
        nvargs.ViewConfidence  (1,:) double  = []
        nvargs.factorBetas            double = []
        nvargs.factorPremiaAnnual (1,:) double = []
        nvargs.equilibriumWeights (1,:) double = []

        % — factor-based —
        nvargs.FactorTargets  (1,5) double  = nan(1,5)
        nvargs.FactorPenalty  (1,5) double  = ones(1,5)
        nvargs.RiskAversion   (1,1) double  = 0.5
    end

    nAssets = portIn.nAssets();

    % --- auto-populate from Results when available ------------------- %
    hasResults = ~isempty(fieldnames(portIn.Results));

    if isempty(nvargs.factorBetas) && hasResults && isfield(portIn.Results, 'factorBetas')
        nvargs.factorBetas = portIn.Results.factorBetas;
    end
    if isempty(nvargs.factorPremiaAnnual) && hasResults && isfield(portIn.Results, 'factorPremiaAnnual')
        nvargs.factorPremiaAnnual = portIn.Results.factorPremiaAnnual;
    end
    if isempty(nvargs.scenarioReturns) && hasResults && isfield(portIn.Results, 'assetReturns')
        nvargs.scenarioReturns = portIn.Results.assetReturns;
    end

    % --- expand / default bounds ------------------------------------ %
    if isempty(nvargs.MinWeight)
        if nvargs.LongOnly
            nvargs.MinWeight = zeros(1, nAssets);
        else
            nvargs.MinWeight = -ones(1, nAssets);    % allow up to -100 % short
        end
    end
    if isempty(nvargs.MaxWeight)
        nvargs.MaxWeight = ones(1, nAssets);
    end

    % Validate dimensions
    assert(numel(nvargs.MinWeight) == nAssets, ...
        'MinWeight length (%d) must equal nAssets (%d).', ...
        numel(nvargs.MinWeight), nAssets);
    assert(numel(nvargs.MaxWeight) == nAssets, ...
        'MaxWeight length (%d) must equal nAssets (%d).', ...
        numel(nvargs.MaxWeight), nAssets);

    opts = nvargs;
end
