%BUILDMEX  Compile garchSimulate and ledoitWolfShrink to MEX via MATLAB Coder.
%
%   Run once from the project directory after installing MATLAB Coder:
%       >> buildMex
%
%   Prerequisites:
%       MATLAB Coder toolbox
%       A C compiler configured — run:  mex -setup C
%
%   After compilation, MATLAB automatically prefers the .mex* binaries over
%   the .m fallbacks whenever garchSimulate() or ledoitWolfShrink() are
%   called.  Delete the .mex* files to revert to interpreted mode.
%
%   Reproducibility note:
%       In interpreted mode, rng(42) is called inside analyzePortfolio just
%       before garchSimulate to seed the simulation.  MEX code cannot call
%       rng — it uses the current MATLAB global RNG state.  To get the same
%       numbers in MEX mode, call rng(42) in your workspace before running
%       analyzePortfolio.
%
%   Re-run buildMex if you change garchSimulate.m or if you need to support
%   portfolios with more than maxAssets assets.

fprintf('=== MATLAB Coder MEX Build ===\n\n');

% Check prerequisites
if isempty(mex.getCompilerConfigurations('C'))
    error('No C compiler configured.  Run:  mex -setup C');
end

cfg                        = coder.config('mex');
cfg.GenerateReport         = false;
cfg.IntegrityChecks        = false;   % remove bounds/NaN checks for speed
cfg.ResponsivenessChecks   = false;

% -------------------------------------------------------------------
% garchSimulate  (the Monte Carlo hot loop)
% -------------------------------------------------------------------
% Declare variable-size inputs bounded by maxAssets.
% Re-run buildMex if your largest portfolio exceeds this.
maxAssets = 20;

muDailyT     = coder.typeof(0, [maxAssets 1],         [true false]);
omegaT       = coder.typeof(0, [maxAssets 1],         [true false]);
alphaT       = coder.typeof(0, [maxAssets 1],         [true false]);
betaGT       = coder.typeof(0, [maxAssets 1],         [true false]);
LT           = coder.typeof(0, [maxAssets maxAssets], [true true]);
weightsNormT = coder.typeof(0, [1 maxAssets],         [false true]);
totalDaysT   = coder.typeof(0);   % scalar double
nSimT        = coder.typeof(0);   % scalar double

fprintf('Compiling garchSimulate ...\n');
codegen garchSimulate -config cfg ...
    -args {muDailyT, omegaT, alphaT, betaGT, LT, weightsNormT, totalDaysT, nSimT} ...
    -o garchSimulate
fprintf('  garchSimulate.%s written.\n\n', mexext);

% -------------------------------------------------------------------
% ledoitWolfShrink
% -------------------------------------------------------------------
% Input is a T-by-N returns matrix (not a covariance matrix).
% maxObs covers ~60 years of daily data with headroom.
maxObs = 20000;
lwT    = coder.typeof(0, [maxObs maxAssets], [true true]);

fprintf('Compiling ledoitWolfShrink ...\n');
codegen ledoitWolfShrink -config cfg -args {lwT} -o ledoitWolfShrink
fprintf('  ledoitWolfShrink.%s written.\n\n', mexext);

% -------------------------------------------------------------------
% Smoke test
% -------------------------------------------------------------------
fprintf('Running smoke test ...\n');
nA = 3; nSTest = 200; nDTest = 252;
mu_t   = 0.0001 * ones(nA, 1);
omg_t  = 1e-6   * ones(nA, 1);
alp_t  = 0.05   * ones(nA, 1);
bet_t  = 0.90   * ones(nA, 1);
L_t    = eye(nA);
wts_t  = ones(1, nA) / nA;

rng(1);
outM = garchSimulate(mu_t, omg_t, alp_t, bet_t, L_t, wts_t, nDTest, nSTest);
assert(isequal(size(outM), [nDTest, nSTest]), 'Output size mismatch.');
assert(~any(isnan(outM(:))), 'NaN values in output.');
fprintf('  Smoke test passed.  Output size: %dx%d\n\n', size(outM, 1), size(outM, 2));

fprintf('Build complete.\n');
fprintf('Delete the .mex* files at any time to revert to interpreted mode.\n');
