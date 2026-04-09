function hFig = plotFactorExposures(portfolios)
%PLOTFACTOREXPOSURES  Grouped bar chart of FF5 factor beta loadings.
%
%   hFig = plotFactorExposures(portfolios)
%
%   Inputs:
%     portfolios   1×N cell array of PortfolioModel objects (must be analysed)
%
%   Each PortfolioModel must have Results.portFactorBetas (1×5 row vector)
%   with loadings in the order [Mkt, SMB, HML, RMW, CMA].

    factorNames = {'Mkt', 'SMB', 'HML', 'RMW', 'CMA'};
    nPort       = numel(portfolios);
    factorData  = zeros(nPort, 5);
    labels      = strings(1, nPort);
    for pi = 1:nPort
        factorData(pi,:) = portfolios{pi}.Results.portFactorBetas;
        labels(pi) = portfolios{pi}.Title;
    end

    hFig = figure;
    b = bar(factorData);
    ax = gca;
    for fi = 1:5
        b(fi).FaceColor = 'flat';
    end
    set(ax, 'XTickLabel', labels);
    xtickangle(20);
    ylabel('Factor Beta Loading');
    title('Portfolio Factor Exposures (FF5)');
    legend(factorNames, 'Location', 'northeastoutside');
    box off;
    ax.YAxis.Color = 'none';
    ax.YLabel.Color = [0.15 0.15 0.15];
    ax.YAxis.TickLabelColor = [0.15 0.15 0.15];
    grid on;
    ax.XGrid = 'off';
    ax.YGrid = 'on';
end
