classdef PortfolioModel
% PortfolioModel  Lightweight container for a portfolio of assets.
%
%   pm = PortfolioModel(assets, weights)
%   pm = PortfolioModel(assets, weights, 'Title', t, 'RebalanceCost', c)
%
%   Properties
%     Assets        – 1×N string array of ticker symbols
%     Weights       – 1×N double, auto-normalised so sum == 1
%     Title         – descriptive label  (default "")
%     RebalanceCost – percentage of total portfolio value  (default 0)
%
%   Example
%     pm = PortfolioModel(["AAPL" "MSFT" "GOOG"], [0.4 0.3 0.3], ...
%                         'Title', "Tech 3", 'RebalanceCost', 0.001);
%     disp(pm);

    % ------------------------------------------------------------------ %
    properties
        Assets        (1,:) string
        Weights       (1,:) double
        Title         (1,1) string  = ""
        RebalanceCost (1,1) double  = 0      % fraction, e.g. 0.001 = 0.1 %
        Results       struct = struct()      % populated by analyzePortfolio
    end

    % ------------------------------------------------------------------ %
    methods

        % ============================================================== %
        %  Constructor
        % ============================================================== %
        function obj = PortfolioModel(assets, weights, nvargs)
            arguments
                assets  (1,:) string
                weights (1,:) double
                nvargs.Title         (1,1) string  = ""
                nvargs.RebalanceCost (1,1) double  = 0
            end

            if numel(assets) ~= numel(weights)
                error('PortfolioModel:dimMismatch', ...
                      'Assets (%d) and Weights (%d) must have the same length.', ...
                      numel(assets), numel(weights));
            end

            obj.Assets        = assets;
            obj.Weights       = weights / sum(weights);   % auto-normalise
            obj.Title         = nvargs.Title;
            obj.RebalanceCost = nvargs.RebalanceCost;
        end

        % ============================================================== %
        %  Convenience helpers
        % ============================================================== %
        function n = nAssets(obj)
        %NASSETS  Number of assets in the portfolio.
            n = numel(obj.Assets);
        end

        function tf = isValid(obj)
        %ISVALID  True when the portfolio is well-formed.
        %   Checks: no NaN weights, lengths match, weights sum ≈ 1.
            tf = numel(obj.Assets) == numel(obj.Weights) && ...
                 ~any(isnan(obj.Weights)) && ...
                 abs(sum(obj.Weights) - 1) < 1e-8;
        end

        function tf = isAnalyzed(obj)
        %ISANALYZED  True when Results has been populated by analyzePortfolio.
        %   Checks for the key fields that printSummary requires.
            tf = ~isempty(fieldnames(obj.Results)) && ...
                 isfield(obj.Results, 'portMuAnnual') && ...
                 isfield(obj.Results, 'sharpe') && ...
                 isfield(obj.Results, 'milestones');
        end

        % ============================================================== %
        %  Analytics (data passed in, not stored)
        % ============================================================== %
        function er = expectedReturn(obj, muAnnual)
        %EXPECTEDRETURN  Portfolio expected annual return.
        %   er = pm.expectedReturn(muAnnual)  where muAnnual is N×1.
            er = obj.Weights * muAnnual(:);
        end

        function sr = expectedRisk(obj, SigmaAnnual)
        %EXPECTEDRISK  Portfolio annualised volatility (std dev).
        %   sr = pm.expectedRisk(SigmaAnnual)  where SigmaAnnual is N×N.
            sr = sqrt(obj.Weights * SigmaAnnual * obj.Weights');
        end

        function s = sharpeRatio(obj, muAnnual, SigmaAnnual, Rf)
        %SHARPERATIO  (E[r] – Rf) / sigma.
            s = (obj.expectedReturn(muAnnual) - Rf) / ...
                 obj.expectedRisk(SigmaAnnual);
        end

        function fb = factorExposure(obj, factorBetas)
        %FACTOREXPOSURE  Portfolio-level factor betas (1×5).
        %   fb = pm.factorExposure(factorBetas)  where factorBetas is N×5.
            fb = obj.Weights * factorBetas;
        end

        % ============================================================== %
        %  Conversion
        % ============================================================== %
        function s = toStruct(obj)
        %TOSTRUCT  Convert to a plain struct for pipeline compatibility.
            s.symbols  = obj.Assets;
            s.weights  = obj.Weights;
            s.title    = obj.Title;
            s.rebalanceCost = obj.RebalanceCost;
        end

        % ============================================================== %
        %  Display
        % ============================================================== %
        function disp(obj)
        %DISP  Pretty-print the portfolio.
            if obj.Title ~= ""
                fprintf('  PortfolioModel: "%s"\n', obj.Title);
            else
                fprintf('  PortfolioModel\n');
            end
            fprintf('  %-8s  %8s\n', 'Asset', 'Weight');
            fprintf('  %-8s  %8s\n', '--------', '--------');
            for k = 1:numel(obj.Assets)
                fprintf('  %-8s  %7.2f%%\n', obj.Assets(k), obj.Weights(k)*100);
            end
            fprintf('  %-8s  %7.2f%%\n', 'Total', sum(obj.Weights)*100);
            if obj.RebalanceCost > 0
                fprintf('  Rebalance cost: %.3f%%\n', obj.RebalanceCost*100);
            end
        end

    end  % methods
end  % classdef
