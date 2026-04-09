function hFig = plotReturnDistributions(portfolios, colors, milestones)
%PLOTRETURNDISTRIBUTIONS  KDE comparison of simulated terminal wealth at each milestone.
%
%   hFig = plotReturnDistributions(portfolios, colors, milestones)
%
%   Inputs:
%     portfolios   1×N cell array of PortfolioModel objects (must be analysed)
%     colors       N×3 double RGB matrix (one row per portfolio)
%     milestones   struct array with 'name' and 'year' fields
%
%   Each PortfolioModel must have Results.milestoneVals populated by
%   analyzePortfolio.

    nPort = numel(portfolios);
    nMile = numel(milestones);

    % Auto-extend colors if fewer rows than portfolios
    if size(colors, 1) < nPort
        extra = lines(nPort - size(colors, 1));
        colors = [colors; extra];
    end

    % Extract labels from PortfolioModel titles
    labels = strings(1, nPort);
    for pi = 1:nPort
        labels(pi) = portfolios{pi}.Title;
    end

    hFig = figure;
    for mi = 1:nMile
        subplot(nMile, 1, mi);
        hold on;

        mYear  = milestones(mi).year;
        useLog = mYear >= 30;   % switch to log10 scale for long horizons

        % Pool values across all portfolios to set a shared axis range
        allVals = [];
        for pi = 1:nPort
            r = portfolios{pi}.Results;
            v = r.milestoneVals{mi};
            if isempty(v); continue; end
            if useLog; v = v(v > 0); end        % discard ruined paths before log
            if isempty(v); continue; end
            if useLog; v = log10(v); end
            allVals = [allVals, v]; %#ok<AGROW>
        end

        if isempty(allVals); continue; end

        xCenter   = median(allVals);
        halfWidth = min(xCenter - prctile(allVals, 0.5), ...
                        prctile(allVals, 99.5) - xCenter);
        xiGrid    = linspace(xCenter - halfWidth, xCenter + halfWidth, 1000);

        for pi = 1:nPort
            vals = portfolios{pi}.Results.milestoneVals{mi};
            if isempty(vals); continue; end
            if useLog; vals = vals(vals > 0); end   % same filter for per-portfolio KDE
            if isempty(vals); continue; end
            if useLog; vals = log10(vals); end
            [f, xi] = ksdensity(vals, xiGrid);
            plot(xi, f, '-', 'Color', colors(pi,:), 'LineWidth', 2, ...
                'DisplayName', labels(pi));
        end

        % Breakeven: 1× in linear scale, log10(1)=0 in log scale
        xline(double(~useLog), 'k--', 'LineWidth', 1, 'DisplayName', 'Breakeven');
        xlim([xCenter - halfWidth, xCenter + halfWidth]);

        if useLog
            xlabel(sprintf('Portfolio Value at %s (%d yr) — log_{10}(×Initial)', ...
                milestones(mi).name, mYear));
        else
            xlabel(sprintf('Portfolio Value at %s (%d yr) — Multiple of Initial', ...
                milestones(mi).name, mYear));
        end
        ylabel('Probability Density');
        title(sprintf('Return Distribution — %s (%d-Year Horizon)', ...
            milestones(mi).name, mYear));
        legend('Location', 'northeast');
        grid on; box off; hold off;
    end
    sgtitle('Return Distribution Comparison');
end
