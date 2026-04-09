function portRetPaths = garchSimulate(muDaily, omega, alpha, betaG, L, weightsNorm, totalDays, nSim)
%GARCHSIMULATE  GARCH(1,1) multi-asset Monte Carlo — MATLAB Coder compatible.
%
%   portRetPaths = garchSimulate(muDaily, omega, alpha, betaG, L, ...
%                                weightsNorm, totalDays, nSim)
%
%   All inputs are plain double arrays — no toolbox objects, no cell arrays,
%   no structs.  Call rng(seed) before this function in interpreted mode to
%   ensure reproducibility.  In MEX mode the global MATLAB RNG state is used
%   (rng cannot be called inside a MEX); seed externally if needed.
%
%   Inputs:
%     muDaily     nAssets×1    daily expected returns
%     omega       nAssets×1    GARCH constant
%     alpha       nAssets×1    ARCH(1) coefficient
%     betaG       nAssets×1    GARCH(1) coefficient
%     L           nAssets×nAssets  lower-triangular Cholesky of the
%                                   daily correlation matrix
%     weightsNorm 1×nAssets    normalised portfolio weights
%     totalDays   scalar       simulation horizon in days
%     nSim        scalar       number of Monte Carlo paths
%
%   Output:
%     portRetPaths  totalDays×nSim  daily portfolio returns

    nAssets          = numel(muDaily);
    unconditionalVar = omega ./ (1 - alpha - betaG);

    portRetPaths = zeros(totalDays, nSim);
    hPrev        = repmat(unconditionalVar, 1, nSim);   % nAssets×nSim
    ePrev        = zeros(nAssets, nSim);

    for t = 1:totalDays
        % GARCH(1,1) conditional variance update
        hCurr = omega + alpha .* ePrev.^2 + betaG .* hPrev;    % nAssets×nSim

        % Correlated standardised shocks via Cholesky factor
        Zcorr = L * randn(nAssets, nSim);                       % nAssets×nSim

        % Scale by conditional std dev, add drift
        innovations      = sqrt(hCurr) .* Zcorr;               % nAssets×nSim
        assetRet         = muDaily + innovations;               % broadcast nAssets×1 + nAssets×nSim

        % Weighted portfolio return
        portRetPaths(t,:) = weightsNorm * assetRet;             % 1×nSim

        ePrev = innovations;
        hPrev = hCurr;
    end
end
