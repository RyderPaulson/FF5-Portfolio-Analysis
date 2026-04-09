function [SigmaShrunk, delta] = ledoitWolfShrink(X)
%LEDOITWOLFSHRINK Ledoit-Wolf shrinkage toward constant-correlation target.
%   [SigmaShrunk, delta] = ledoitWolfShrink(X)
%   X: T-by-N matrix of asset returns (raw, not demeaned).
%   Returns the shrunk covariance matrix and the optimal shrinkage intensity.

[T, N] = size(X);
X = X - mean(X);                       % demean
S = (X' * X) / T;                      % sample covariance

% --- Constant-correlation target ---
sVec  = sqrt(diag(S));                  % asset std devs
R     = S ./ (sVec * sVec');            % sample correlation matrix
rBar  = (sum(R(:)) - N) / (N*(N-1));   % mean off-diagonal correlation
F     = rBar * (sVec * sVec');          % target covariance
F(logical(eye(N))) = diag(S);           % keep sample variances on diagonal

% --- Optimal shrinkage intensity (Ledoit & Wolf 2004) ---
X2 = X.^2;
piMat = (X2' * X2) / T - S.^2;         % element-wise pi
piSum = sum(piMat(:));                  % total pi

% rho: asymptotic covariance with the target
thetaMat = ((X.^3)' * X) / T - diag(diag(S)) * R;
rhoOffDiag = sum(sum(rBar * (sVec ./ sVec') .* thetaMat));
rhoSum = sum(diag(piMat)) + rhoOffDiag;

% gamma: squared Frobenius distance between S and F
gammaSum = norm(S - F, 'fro')^2;

% Optimal intensity
kappa = (piSum - rhoSum) / gammaSum;
delta = max(0, min(1, kappa / T));

SigmaShrunk = delta * F + (1 - delta) * S;
end
