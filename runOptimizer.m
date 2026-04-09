function portOut = runOptimizer(method, portIn, opts)
%RUNOPTIMIZER  Dispatcher — run any optimiser by name.
%
%   portOut = runOptimizer(method, portIn, opts)
%
%   Inputs
%     method – string: "meanvariance", "cvar", "blacklitterman",
%                      "riskparity", "factorbased"
%     portIn – PortfolioModel (must be analysed — Results populated)
%     opts   – struct from defaultOptimOptions (optional; defaults
%              are created automatically if omitted)
%
%   Returns
%     portOut – PortfolioModel with optimised weights
%
%   Example
%     opts = defaultOptimOptions(pm, 'Rf', 0.045);
%     mvPort = runOptimizer("meanvariance", pm, opts);

    arguments
        method      (1,1) string
        portIn      (1,1) PortfolioModel
        opts        struct = defaultOptimOptions(portIn)
    end

    switch lower(method)
        case "meanvariance"
            portOut = optimMeanVariance(portIn, opts);

        case "cvar"
            portOut = optimCVaR(portIn, opts);

        case "blacklitterman"
            portOut = optimBlackLitterman(portIn, opts);

        case "riskparity"
            portOut = optimRiskParity(portIn, opts);

        case "factorbased"
            portOut = optimFactorBased(portIn, opts);

        otherwise
            error('runOptimizer:unknownMethod', ...
                  'Unknown optimiser "%s". Valid options: meanvariance, cvar, blacklitterman, riskparity, factorbased.', ...
                  method);
    end
end
