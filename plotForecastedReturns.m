function hFig = plotForecastedReturns(portfolios, options)
%PLOTFORECASTEDRETURNS  Forecasted return chart for one or more portfolios.
%
%   hFig = plotForecastedReturns(pm)
%   hFig = plotForecastedReturns({pm1, pm2, ...})
%   hFig = plotForecastedReturns(..., 'Subplot', true)
%
%   Plots the 5th / 25th / 50th / 75th / 95th percentile wealth paths
%   from Monte Carlo simulation.  Each PortfolioModel must have been
%   analysed (Results.forecastedReturns populated by analyzePortfolio).
%
%   Inputs:
%     portfolios – single PortfolioModel, or cell array of PortfolioModels
%
%   Name-Value Arguments:
%     Subplot        – logical (false)  create a subplot grid for each portfolio
%     ColorPrimary   – 1×3 RGB         main line colour  (default: [0 148 94]/255)
%     ColorSecondary – 1×3 RGB         milestone markers  (default: [20 45 105]/255)
%     Milestones     – struct array     with 'name' and 'year' fields

    arguments
        portfolios
        options.Subplot        (1,1) logical = false
        options.ColorPrimary   (1,3) double  = [0 148 94]./255
        options.ColorSecondary (1,3) double  = [20 45 105]./255
        options.Milestones     struct = [struct('name','House','year',10); ...
                                         struct('name','Retire','year',44)]
    end

    % Normalise input to cell array
    if isa(portfolios, 'PortfolioModel')
        portfolios = {portfolios};
    end
    nPort = numel(portfolios);

    % Validate
    for k = 1:nPort
        assert(isa(portfolios{k}, 'PortfolioModel'), ...
            'plotForecastedReturns:badType', 'Input %d is not a PortfolioModel.', k);
        assert(isfield(portfolios{k}.Results, 'forecastedReturns'), ...
            'plotForecastedReturns:noData', ...
            '"%s" has no forecasted returns data. Run analyzePortfolio first.', ...
            portfolios{k}.Title);
    end

    % Size the figure so it fills the live-script output pane
    if options.Subplot && nPort > 1
        nCols = 1;
        nRows = nPort;
        figW  = 2000;
        figH  = 500 * nRows;
    else
        nCols = 1; nRows = 1;
        figW  = 1200;
        figH  = 500;
    end
    hFig = figure('Position', [50 50 figW figH]);

    if nPort == 1 && ~options.Subplot
        % Single portfolio — full figure
        renderForecastedReturns(gca, portfolios{1}, options);
    elseif options.Subplot
        % Subplot grid
        for k = 1:nPort
            subplot(nRows, nCols, k);
            renderForecastedReturns(gca, portfolios{k}, options);
        end
        sgtitle('Forecasted Returns');
    else
        % Multiple portfolios overlaid on one axes (median lines only)
        ax = gca;
        hold(ax, 'on');
        cmap = lines(nPort);
        legendEntries = cell(1, nPort);
        for k = 1:nPort
            fc = portfolios{k}.Results.forecastedReturns;
            semilogy(ax, fc.tYears, fc.pct50, '-', ...
                'Color', cmap(k,:), 'LineWidth', 2);
            legendEntries{k} = char(portfolios{k}.Title);
        end
        yline(1, 'k--', 'LineWidth', 0.5);
        for m = 1:numel(options.Milestones)
            xline(options.Milestones(m).year, '--', ...
                'Color', options.ColorSecondary, 'LineWidth', 1.5);
        end
        xlabel('Years');
        ylabel('Portfolio Value (multiple of initial)');
        title('Forecasted Returns — Median Comparison');
        legend(legendEntries{:}, 'Location', 'northwest');
        set(ax, 'YGrid', 'on', 'XGrid', 'off');
        ax.YAxis.Color          = 'none';
        ax.YLabel.Color         = [0.15 0.15 0.15];
        ax.YAxis.TickLabelColor = [0.15 0.15 0.15];
        box off; hold off;
    end
end

% =========================================================================
function renderForecastedReturns(ax, pm, options)
%RENDERFORECASTEDRETURNS  Draw a single forecasted returns chart on the given axes.
    fc = pm.Results.forecastedReturns;
    tradingDaysPerYear = 252;

    % --- percentile bands ----------------------------------------------- %
    % Fill shaded bands, then overlay median
    fill(ax, [fc.tYears; flipud(fc.tYears)], ...
             [fc.pct5;   flipud(fc.pct95)], ...
         options.ColorPrimary, 'FaceAlpha', 0.10, 'EdgeColor', 'none', ...
         'HandleVisibility', 'off');
    hold(ax, 'on');
    fill(ax, [fc.tYears; flipud(fc.tYears)], ...
             [fc.pct25;  flipud(fc.pct75)], ...
         options.ColorPrimary, 'FaceAlpha', 0.20, 'EdgeColor', 'none', ...
         'HandleVisibility', 'off');

    % Invisible dummy patches for the legend (band colours)
    p1 = patch(ax, NaN, NaN, options.ColorPrimary, ...
        'FaceAlpha', 0.10, 'EdgeColor', 'none', 'DisplayName', '5th–95th');
    p2 = patch(ax, NaN, NaN, options.ColorPrimary, ...
        'FaceAlpha', 0.30, 'EdgeColor', 'none', 'DisplayName', '25th–75th');

    semilogy(ax, fc.tYears, fc.pct50, '-', 'Color', options.ColorPrimary, ...
        'LineWidth', 2.5, 'DisplayName', 'Median');
    yline(ax, 1, 'k--', 'LineWidth', 0.5, 'HandleVisibility', 'off');

    % --- milestone vertical lines with inline labels -------------------- %
    milestones = options.Milestones;
    for m = 1:numel(milestones)
        mIdx = milestones(m).year * tradingDaysPerYear;
        if mIdx <= numel(fc.pct50)
            medVal = fc.pct50(mIdx);
            lbl = sprintf('%s: %.1f×', milestones(m).name, medVal);
        else
            lbl = milestones(m).name;
        end
        xline(ax, milestones(m).year, '--', lbl, ...
            'Color', options.ColorSecondary, 'LineWidth', 1.5, ...
            'LabelOrientation', 'horizontal', ...
            'LabelVerticalAlignment', 'bottom', ...
            'FontSize', 8, 'FontWeight', 'bold', ...
            'HandleVisibility', 'off');
    end

    % --- labels --------------------------------------------------------- %
    xlabel(ax, 'Years');
    ylabel(ax, 'Portfolio Value (multiple of initial)');
    if pm.Title ~= ""
        title(ax, sprintf('Forecasted Returns — %s', pm.Title));
    else
        title(ax, 'Forecasted Returns');
    end
    legend(ax, 'Location', 'northwest', 'FontSize', 7, 'Box', 'off');

    set(ax, 'YScale', 'log', 'YGrid', 'on', 'XGrid', 'off');
    ax.YAxis.Color          = 'none';
    ax.YLabel.Color         = [0.15 0.15 0.15];
    ax.YAxis.TickLabelColor = [0.15 0.15 0.15];
    box(ax, 'off'); hold(ax, 'off');
end
