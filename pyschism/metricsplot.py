# -*- coding: utf-8 -*-
""" Metrics plot
"""

from plot_default_formats import set_color_cycle_dark2, set_scatter_color, make_plot_isometric, set_dual_axes, set_xaxis_dateformat, rotate_xticks,brewer_colors
from vtools.functions.api import cosine_lanczos, interpolate_ts, interpolate_ts_nan, LINEAR, shift
from vtools.functions.skill_metrics import rmse, median_error, skill_score, corr_coefficient
from vtools.data.vtime import days, hours, minutes, time_interval, time_sequence
from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
from datetime import timedelta

__all__ = ['plot_metrics', 'plot_comparison']

def calculate_lag(a, b, max_shift, period=None,
                  resolution=time_interval(minutes=1), interpolate_method=None):
    """ Calculate lag of the second time series b, that maximizes the cross-correlation with a.

        Parameters
        ----------
        a,b: vtools.data.timeseries.Timeseries
            Two time series to compare. The time extent of b must be the same or a superset of that of a.

        max_shift: interval
            Maximum pos/negative time shift to consider in cross-correlation (ie, from -max_shift to +max_shift)

        period: interval, optional
            Period that will be used to further clip the time_window of analysis to fit a periodicity.

        interpolate_method: str, optional
            Interpolate method to generate a time series with a lag-calculation interpolation

        Returns
        -------
        lag : datetime.timedelta
            lag
    """
    # Get the available range from the first time series
    a_windowed_by_b = a.window(b.start, b.end)
    time_window = (a_windowed_by_b.start, a_windowed_by_b.end)
    if (time_window[1] - time_window[0]).total_seconds() <= 0.:
        raise ValueError('No available time series in the given time_window')

    # Calculate actual time range to use
    start = time_window[0] + max_shift
    if period is not None:
        n_periods = np.floor(((time_window[1] - max_shift) - start).total_seconds() / period.total_seconds())
        if n_periods <= 0.:
            raise ValueError("The time series is too short to cover one period.")
        end = start + time_interval(seconds=n_periods * period.total_seconds())
    else:
        end = time_window[1] - max_shift
    if (end - start).total_seconds() < 0.:
        raise ValueError("The time series is too short.")

    # This is actual time series to calculate lag
    a_part = a.window(start, end)
    start = a_part.start
    end = a_part.end
    a_part_masked = np.ma.masked_invalid(a_part.data, np.nan)

    # Interpolate the second vector
    factor = a.interval.total_seconds() / resolution.total_seconds()
    if not factor - np.floor(factor) < 1.e-6:
        raise ValueError('The interval of the time series is not integer multiple of the resolution.')
    else:
        factor = int(np.floor(factor))

    new_n = np.ceil((end - start + 2 * max_shift).total_seconds() / resolution.total_seconds()) + 1
    max_shift_tick = int(max_shift.total_seconds() / resolution.total_seconds())
    length = 2 * max_shift_tick + 1
    n = len(a_part)
    if interpolate_method is None:
        interpolate_method = LINEAR
    b_interpolated = interpolate_ts(b,
                                    time_sequence(a_part.start - max_shift,
                                                  resolution, new_n),
                                    method=interpolate_method)
    def unnorm_xcor(lag):
        lag_int = int(lag)
        b_part = b_interpolated.data[lag_int:lag_int+factor*n-1:factor]
        return -np.ma.inner(a_part_masked, b_part)


    index = np.arange(-max_shift_tick, max_shift_tick + 1)
    brent = True
    if brent is True:
        from scipy.optimize import minimize_scalar
        res = minimize_scalar(unnorm_xcor, method='bounded',
                              bounds=(0, length), options={'xatol': 0.5})
        v0 = index[int(np.floor(res.x))] * resolution.total_seconds()
    else:
        re = np.empty(length)
        for i in range(length):
            re[i] = unnorm_xcor(i)
        v0 = index[np.argmax(-re)] * resolution.total_seconds()
    return time_interval(seconds=v0)


def safe_window(ts, window):
    """
    window function with safety.

    Returns
    -------
    vtools.data.timeseries.TimeSeries
    """
    if window[0] > window[1]:
        raise ValueError("The left value of the window is larger than the right.")
    if ts is not None:
        if ts.end < window[0] or ts.start > window[1]:
            return None
        else:
            return ts.window(*window)
    else:
        return None


def get_common_window(tss, window=None):
    """ Get a least common time window of time series that fits tightly
        on the first time series
    """
    lower_bound = None
    upper_bound = None
    for ts in tss:
        if not ts is None:
            if lower_bound is None:
                lower_bound = ts.start
            else:
                if lower_bound < ts.start:
                    lower_bound = ts.start
            if upper_bound is None:
                upper_bound = ts.end
            else:
                if upper_bound > ts.end:
                    upper_bound = ts.end
    if (lower_bound is None or upper_bound is None) \
        or (lower_bound > upper_bound):
        return None
    else:
        if window is not None:
            if lower_bound < window[0]:
                lower_bound = window[0]
            if upper_bound > window[1]:
                upper_bound = window[1]
            return (lower_bound, upper_bound)
        else:
            return (lower_bound, upper_bound)


def get_union_window(tss, window=None):
    """ Get a union time window of time series
    """
    lower_bound = None
    upper_bound = None
    for ts in tss:
        if not ts is None:
            if lower_bound is None:
                lower_bound = ts.start
            else:
                if lower_bound > ts.start:
                    lower_bound = ts.start
            if upper_bound is None:
                upper_bound = ts.end
            else:
                if upper_bound < ts.end:
                    upper_bound = ts.end
    else:
        if window is not None:
            if lower_bound > window[0]:
                lower_bound = window[0]
            if upper_bound < window[1]:
                upper_bound = window[1]
            return (lower_bound, upper_bound)
        else:
            return (lower_bound, upper_bound)


def filter_timeseries(tss, cutoff_period="40hr"):
    """ Filter time series

        Parameters
        ----------

        Returns
        -------
        list of vtools.data.timeseries.TimeSeries
            filtered time series
    """
    filtered = []
    for ts in tss:
        if ts is None:
            filtered.append(None)
        else:
            ts_filtered = cosine_lanczos(ts, cutoff_period=cutoff_period)
            ts_filtered.props['filtered'] = 'cosine_lanczos'
            filtered.append(ts_filtered)
    return filtered


def fill_gaps(tss, max_gap_to_fill=time_interval(hours=1)):
    tss_filled = []
    for ts in tss:
        if ts is not None:
            max_gap = int(max_gap_to_fill.total_seconds() / ts.interval.total_seconds())
            if max_gap > 0:
                tss_filled.append(interpolate_ts_nan(ts, max_gap=max_gap))
            else:
                tss_filled.append(ts)
        else:
            tss_filled.append(None)
    return tss_filled


def plot_metrics_to_figure(fig, tss,
                           title=None, window_inst=None, window_avg=None,
                           labels=None,
                           max_shift=hours(2),
                           period=minutes(int(12.24 * 60)),
                           label_loc=1,
                           legend_size=12):
    """ Plot a metrics plot

        Returns
        -------
        matplotlib.figure.Figure
    """
    grids = gen_metrics_grid()
    axes = dict(list(zip(list(grids.keys()), list(map(fig.add_subplot,
                                      list(grids.values()))))))
    if labels is None:
        labels = [ts.props.get('label') for ts in tss]
    plot_inst_and_avg(axes, tss, window_inst, window_avg, labels, label_loc, legend_size)
    if title is not None:
        axes['inst'].set_title(title)
    if window_avg is not None:
        tss_clipped = [safe_window(ts, window_avg) for ts in tss]
    else:
        tss_clipped = tss
    lags = calculate_lag_of_tss(tss_clipped, max_shift, period)
    metrics, tss_scatter = calculate_metrics(tss_clipped, lags)
    if tss_scatter is not None:
        ax_scatter = axes['scatter']
        plot_scatter(ax_scatter, tss_scatter)
    unit = tss[0].props.get('unit') if tss[0] is not None else None
    str_metrics = gen_metrics_string(metrics, labels[1:], unit)
    write_metrics_string(axes['inst'], str_metrics)
    return fig


def plot_inst_and_avg(axes, tss, window_inst, window_avg, labels, label_loc, legend_size):
    """ Plot instantaneous and filtered time series plot
    """
    if window_inst is None:
        window_inst = get_union_window(tss)
    lines = plot_tss(axes['inst'], tss, window_inst)
    if labels is not None:
        axes['inst'].legend(lines, labels, prop={'size': legend_size}, loc=label_loc)

    if window_avg is None:
        window_avg = get_union_window(tss)
    pad = days(4)
    window_to_filter = (window_avg[0] - pad, window_avg[1] + pad)
    tss_clipped = [safe_window(ts, window_to_filter) for ts in tss]
    tss_filtered = filter_timeseries(tss_clipped)
    plot_tss(axes['avg'], tss_filtered, window_avg)


def plot_comparsion_to_figure(fig, tss, title=None,
                              window_inst=None, window_avg=None, labels=None,
                              label_loc=1, legend_size=12):
    """ Plot a metrics plot

        Returns
        -------
        matplotlib.figure.Figure
    """
    grids = gen_simple_grid()
    axes = dict(list(zip(list(grids.keys()), list(map(fig.add_subplot,
                                      list(grids.values()))))))
    plot_inst_and_avg(axes, tss, window_inst, window_avg, labels,
                      label_loc, legend_size)
    if title is not None:
        axes['inst'].set_title(title)
    return fig


def gen_simple_grid():
    """ Set a simple grid that only has instantaneous and filtered plots
        without metrics calculation
    """
    grids = {}
    g = GridSpec(2, 1, height_ratios=[1, 1])
    grids['inst'] = g[0, 0]
    grids['avg'] = g[1, 0]
    g.update(top=0.93, bottom=0.13, right=0.88, hspace=0.4, wspace=0.8)
    return grids


def gen_metrics_grid():
    grids = {}
    g = GridSpec(2, 2, width_ratios=[1.8, 1], height_ratios=[1, 1])
    grids['inst'] = g[0, 0:2]
    grids['avg'] = g[1, 0]
    grids['scatter'] = g[1, 1]
    #g.update(top=0.93, bottom=0.2, right=0.88, hspace=0.4, wspace=0.8)
    g.update(top=0.90, bottom=0.2, right=0.88, hspace=0.4, wspace=0.8)
    return grids


def plot_tss(ax, tss, window=None):
    """ Simply plot lines from a list of time series
    """
    if window is not None:
        tss_plot = [safe_window(ts, window) for ts in tss]
    else:
        tss_plot = tss
    lines = []
    if check_if_all_tss_are_bad(tss_plot):
        for ts in tss:
            l, = ax.plot([], [])
            lines.append(l)
    else:
        ts_plotted = None
        for ts in tss_plot:
            if ts is not None:
                ax.grid(True, linestyle='-', linewidth=0.1, color='0.5')
                l, = ax.plot(ts.times, ts.data)
                if ts_plotted is None:
                    ts_plotted = ts
            else:
                l, = ax.plot([], [])
            lines.append(l)
        if ts_plotted is not None:
            set_dual_axes(ax, ts_plotted)
            set_xaxis_dateformat(ax, date_format="%m/%d/%Y", rotate=25)
    return lines


def gen_metrics_string(metrics, names, unit=None):
    """ Create a metrics string.
    """
    str_metrics = []
    # Metrics
    for i, metric in enumerate(metrics):
        if metric is None:
            str_metrics.append(None)
            continue
        line_metrics = str()
        if names[i] is not None:
            line_metrics = "%s: " % names[i]
        if unit is not None:
            line_metrics += "RMSE=%.3f %s   " % (metric['rmse'], unit)
        else:
            line_metrics += "RMSE=%.3f      " % (metric['rmse'])
        lag = metric['lag']
        if lag is not None:
            seconds_ = lag.total_seconds()
            line_metrics += "Lag=%d min   " % (seconds_ / 60.)
            line_metrics += r"Bias$_\phi$=%.3f   " % metric['bias']
            line_metrics += r"NSE$_\phi$=%.3f   " % metric['nse']
            line_metrics += r"R$_\phi$=%.3f   " % metric['corr']
        else:
            line_metrics += "Lag=N/A  "
            line_metrics += r"Bias$_\phi$=N/A  "
            line_metrics += r"NSE$_\phi$=N/A  "
            line_metrics += r"R$_\phi$=N/A"
        str_metrics.append(line_metrics)
    return str_metrics


def write_metrics_string(ax, str_metrics, metrics_loc=None):
    """ Put a metrics string in the figure
    """
    if metrics_loc is None:
        metrics_loc = (0.5, -1.75)
    dy = 0.1
    if len(str_metrics) > 0:
        for i, txt in enumerate(str_metrics):
            if txt is not None:
                top = metrics_loc[1] - dy * i
                ax.text(metrics_loc[0],
                        top, txt,
                        horizontalalignment='center',
                        verticalalignment='top',
                        transform=ax.transAxes)


def add_regression_line(axes, d1, d2):
    """ Add a regression line to a scatter plot
    """
    model, resid = np.linalg.lstsq(
        np.vstack([d1, np.ones(len(d1))]).T, d2)[:2]
    x = np.array([min(d1), max(d1)])
    y = model[0] * x + model[1]
    bc1 = brewer_colors[1]
    l, = axes.plot(x, y, color=bc1)
    # Text info
    if model[1] >= 0.:
        eqn = "Y=%.3f*X+%.3f" % (model[0], model[1])
    # Calculate the linear regression
    else:
        eqn = "Y=%.3f*X-%.3f" % (model[0], -model[1])
    axes.legend([l,], [eqn,], loc='upper left', prop={'size': 10})


def plot_scatter(ax, tss):
    """ Plat a scatter plot
    """
    # Get common time window. Use the first two time series
    if tss is None or len(tss) < 2:
        ax.set_visible(False)
        return
    # if metrics['lag'] is None:
    #     ax.set_visible(False)
    #     return
    if any([ts is None for ts in tss[:2]]):
        ax.set_visible(False)
        return

    ts_base = tss[0]
    ts_target = tss[1]
    nonnan_flag = np.logical_not(np.logical_or(np.isnan(ts_base.data),
                                               np.isnan(ts_target.data)))
    ts_target = ts_target.data[nonnan_flag]
    ts_base = ts_base.data[nonnan_flag]
    ax.grid(True, linestyle='-', linewidth=0.1, color='0.5')
    artist = ax.scatter(ts_base, ts_target)

    # if self._have_regression is True:
    #     self.add_regression_line(ts_base, ts_target)
    add_regression_line(ax, ts_base, ts_target)

    set_scatter_color(artist)
    make_plot_isometric(ax)

    labels = ['Obs', 'Sim']
    unit = tss[0].props.get('unit')
    labels = [l + " (%s)" % unit for l in labels]
    ax.set_xlabel(labels[0])
    ax.set_ylabel(labels[1])
    rotate_xticks(ax, 25)


def calculate_lag_of_tss(tss, max_shift, period):
    """ Calculate lags between the first time series, which is observation
        most of time and the following time series one by one.
        The results will be stored at self._lags.
    """
    lags = []
    if len(tss) < 2:
        raise ValueError("Number of time series is less than two.")
    for i in range(len(tss) - 1):
        if tss[0] is not None:
            if tss[i+1] is None or np.all(np.isnan(tss[i+1].data)):
                lags.append(None)
                continue
            try:
                lag = calculate_lag(tss[0], tss[i+1],
                                    max_shift, period)
                if lag == -max_shift or lag == max_shift:
                    lags.append(None)
                else:
                    lags.append(lag)
            except ValueError:
                lags.append(None)
        else:
            lags.append(None)
    return lags

def calculate_metrics(tss, lags, interpolate_method='linear'):
    """
    Calculate metrics.

    The first time series is the base, and other are controls.
    The root mean square error is calculated without a lag correction.
    and the shift with the maximum autocorrelation is a lag.
    The other metrics, Bias, NSE, and R are calculated after lag correction
    on controls, which are the second and latter time series.
    """
    assert len(tss) > 1
    ts_base = tss[0]
    metrics = []
    tss_for_scatter = None
    for i in range(len(tss) - 1):
        ts_target = tss[i + 1]
        if ts_base is None or ts_target is None:
            metrics.append(None)
            continue
        window_common = get_common_window((ts_base, ts_target))
        if window_common is None:
            metrics.append(None)
            continue
        ts1 = ts_base.window(*window_common)
        ts2 = ts_target.window(*window_common)
        if np.all(np.isnan(ts1.data)) or np.all(np.isnan(ts2.data)):
            metrics.append(None)
            continue
        if ts1.start != ts2.start or ts1.interval != ts2.interval:
            ts2_interpolated = interpolate_ts(ts_target, ts1,
                                              method=interpolate_method)
            rmse_ = rmse(ts1, ts2_interpolated)
        else:
            ts2_interpolated = ts2
            rmse_ = rmse(ts1, ts2)
        # Items with the lag correction
        if lags[i] is None:
            bias = None
            nse = None
            corr = None
        else:
            if lags[i] != timedelta():
                ts_target_shifted = shift(ts_target,-lags[i])
                window_common = get_common_window((ts_base, ts_target_shifted))
                ts1 = ts_base.window(*window_common)
                ts2 = ts_target_shifted.window(*window_common)
                if ts1.start != ts2.start or ts1.interval != ts2.interval:
                    ts2_interpolated = interpolate_ts(ts_target_shifted, ts1,
                                                      method=interpolate_method)
                else:
                    ts2_interpolated = ts2
            bias = median_error(ts2_interpolated, ts1)
            nse = skill_score(ts2_interpolated, ts1)
            corr = corr_coefficient(ts2_interpolated, ts1)
        metrics.append({'rmse': rmse_, 'bias': bias,
                        'nse': nse, 'corr': corr, 'lag': lags[i]})
        if i == 0 and lags[0] is not None:
            tss_for_scatter = (ts1, ts2_interpolated)
    return metrics, tss_for_scatter


def set_figure():
    """ Set a Matplotlib figure and return it
    """
    fig = plt.gcf()
    fig.clear()
    fig.set_size_inches(12, 7.5)
    set_color_cycle_dark2()
    return fig


def check_if_all_tss_are_bad(tss):
    """ Check if all time series in a list are not good.
        'Not good' means that a time series is None or all np.nan
    """
    return all([ts is None or np.all(np.isnan(ts.data)) for ts in tss])


def plot_metrics(*args, **kwargs):
    """
    Create a metrics plot

    Parameters
    ----------
    *args: variable number of TimeSeries

    Returns
    -------
    matplotlib.pyplot.figure.Figure
    """
    fig = set_figure()
    fig = plot_metrics_to_figure(fig, args, **kwargs)
    return fig


def plot_comparison(*args, **kwargs):
    """
    Create a simple comparison plot without metrics calculation

    Parameters
    ----------
    *args: variable number of TimeSeries

    Returns
    -------
    matplotlib.pyplot.figure.Figure
    """
    fig = set_figure()
    fig = plot_comparsion_to_figure(fig, args, **kwargs)
    return fig
