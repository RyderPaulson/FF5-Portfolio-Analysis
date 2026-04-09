function hFig = plotHistoricalDrawdown(portfolios, colors)
%PLOTHISTORICALDRAWDOWN  Overlaid historical drawdown series for N portfolios.
%
%   hFig = plotHistoricalDrawdown(portfolios, colors)
%
%   Inputs:
%     portfolios   1×N cell array of PortfolioModel objects (must be analysed)
%     colors       N×3 double RGB matrix (one row per portfolio)
%
%   Each PortfolioModel must have Results.histDates and Results.histDrawdown
%   populated by analyzePortfolio.

    nPort = numel(portfolios);

    % Auto-extend colors if fewer rows than portfolios
    if size(colors, 1) < nPort
        extra = lines(nPort - size(colors, 1));
        colors = [colors; extra];
    end

    hFig = figure;
    hold on;
    for pi = 1:nPort
        r = portfolios{pi}.Results;
        plot(r.histDates, r.histDrawdown * 100, '-', ...
            'Color', colors(pi,:), 'LineWidth', 0.7, ...
            'DisplayName', portfolios{pi}.Title);
    end
    xlabel('Date');
    ylabel('Drawdown (%)');
    title('Historical Drawdown Comparison');
    legend('Location', 'southwest');
    set(gca, 'YDir', 'reverse');
    grid on; box on; hold off;
end
