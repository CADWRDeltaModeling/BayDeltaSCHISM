# -*- coding: UTF-8 -*-
""" Convenient routines to set up and to tweak matplotlib plots.
"""


import vtools.data.timeseries
from unit_conversions import m_to_ft, cms_to_cfs, celcius_to_fahrenheit, psu_ec_25c, psu_ec_25c_scalar, ec_sea
import palettable
from matplotlib.ticker import AutoLocator, ScalarFormatter
import matplotlib.gridspec as gridspec
import matplotlib as mpl
import numpy as np
from cycler import cycler

__all__ = ['set_color_cycle_dark2', 'set_dual_axes', 'set_dual_axes_elev', 'set_dual_axes_salt']

# A few global variables
font = { # 'family': '',
         # 'weight': 'regular',
        'size': 12,}
brewer_colors = [palettable.colorbrewer.qualitative.Dark2_5.mpl_colors[i]
                 for i in [1, 0, 2, 3, 4]]
line_thickness = 1.

# Metrics format dictionary
metrics_dpi = 300
metrics_fig_size = (12,  7.5)  # Metrics figure size in inches
metrics_plot_kwargs = {'linewidth': 1}

metrics_plot_format = {
    'dpi': metrics_dpi,
    'fig_size': metrics_fig_size,
    'color': brewer_colors,
    'metrics_plot_kwargs': metrics_plot_kwargs}


##############################################################################
# Global settings
def set_color_cycle_dark2():
    """ Set color cycles of Dark2 theme of colorbrewer.org globally.
        Just calling this function once before finalize a plot is enough
        to change the color cycles.

        Returns
        -------
        brewer_colors: list
            list of the colors
    """
    
    mpl.rcParams['axes.prop_cycle'] = cycler(color=brewer_colors)
    return brewer_colors


def get_color_cycle():
    """ Get the default color cycle.
        The color cycle is based on the colorbrewer dark2, but
        it is rearranged to start with orange first.

        Returns
        -------
        brewe_colors: list
            list of the colors
    """
    return brewer_colors


##############################################################################
# Tools to create the second axis of salt plots

class SaltConversionLocator(AutoLocator):
    def tick_values(self, vmin, vmax):
        ''' The idea of this function is to determine tick locations in psu
            that will be neat numbers once converted and labeled as EC. The
            way we do this is to convert the bounds vmin and vmax to ec and
            using AutoLocator to come up with neat EC values. Then we back
            convert these values to psu.
        '''
        # vmin and vmax are in psu
        # Determine "neat values of EC for tick locations
        vmin_ec = psu_ec_25c(vmin) if vmin >= 0. else -psu_ec_25c(abs(vmin))
        vmax_ec = psu_ec_25c(vmax) if vmax >= 0. else -psu_ec_25c(abs(vmax))
        # Determine "neat" values of EC for tick locations
        auto_ticks = AutoLocator.tick_values(self, vmin_ec, vmax_ec)
        # Now determine the locations in psu, since the axis is psu for
        # locations and EC for labeling.
        convert_ticks = [x for x in ec_psu_25c(auto_ticks)
                         if x >= 0. and x <= 35.]
        return convert_ticks


class SaltConversionFormatter(ScalarFormatter):
    def __call__(self, x, pos=None):
        # The location will come in psu. Need to convert to EC.
        # We have already done the work in ConversionLocator to make sure
        # that these will turn out attractive
        xnew = psu_ec_25c(x) if x >= 0.0 else -psu_ec_25c(abs(x))
        n_digits = int(np.log10(xnew)) + 1
        if n_digits == 1:
            xnew = 0.
        elif n_digits == 2:
            xnew = np.around(xnew, -1)
        elif n_digits > 2:
            xnew = np.around(xnew, np.max((-n_digits+2, -2)))
        else:
            raise Exception()
        t = "%5.0f" % xnew
        return t


##############################################################################
# Some functions to control axes

M_LABEL = 'Elev (m)'
FT_LABEL = 'Elev (ft)'
FILTERED_M_LABEL = 'Tidal Avg Elev (m)'
FILTERED_FT_LABEL = 'Tidal Avg Elev (ft)'
elev_axis_labels = [[None, M_LABEL],
                    [None, FT_LABEL]]
elev_filtered_axis_labels = [[None, FILTERED_M_LABEL],
                             [None, FILTERED_FT_LABEL]]

CMS_LABEL = 'Flow (cms)'
CFS_LABEL = 'Flow (cfs)'
FILTERED_CMS_LABEL = 'Tidal Avg Flow (cms)'
FILTERED_CFS_LABEL = 'Tidal Avg Flow (cfs)'
flow_axis_labels = [[None, CMS_LABEL],  # m$\mathsf{^3}$/s
                    [None, CFS_LABEL]]
flow_filtered_axis_labels = [[None, FILTERED_CMS_LABEL], # m$\mathsf{^3}$/s
                             [None, FILTERED_CFS_LABEL]]

MPS_LABEL = 'Velocity (m/s)'
FTPS_LABEL = 'Velocity (ft/s)'
FILTERED_MPS_LABEL = 'Tidal Avg Vel (m/s)'
FILTERED_FTPS_LABEL = 'Tidal Avg Vel (ft/s)'
vel_axis_labels = [[None, MPS_LABEL],
                    [None, FTPS_LABEL]]
vel_filtered_axis_labels = [[None, FILTERED_MPS_LABEL],
                             [None, FILTERED_FTPS_LABEL]]

DEG_C_LABEL = u'Temperature (\u00b0 C)'
DEG_F_LABEL = u'Temperature (\u00b0 F)'
FILTERED_DEG_C_LABEL = u'Tidal Avg Temp (\u00b0 C)'
FILTERED_DEG_F_LABEL = u'Tidal Avg Temp (\u00b0 F)'
temp_axis_labels = [[None, DEG_C_LABEL],
                    [None, DEG_F_LABEL]]
temp_filtered_axis_labels = [[None, FILTERED_DEG_C_LABEL],
                             [None, FILTERED_DEG_F_LABEL]]


def set_dual_axes(ax, ts, cell_method = 'inst'):
    """ Create a dual y-axis with unit information in the given time series.
        It converts SI units to non-SI one.

        Parameters
        ----------
        ax: matplotlib.axes
            axes of a plot to manage
        ts: vtools.data.TimeSeries
            timeseries with unit information
    """
    if ts is None:
        return
    filtered = (cell_method == 'filtered') or (cell_method == 'ave')
    if hasattr(ts,'unit'):
        unit = ts.unit
        if unit == 'm' or unit == 'meter':
            ax2 = set_dual_axes_elev(ax, filtered=filtered)
            return ax2
        elif unit.lower() == 'cms':
            ax2 = set_dual_axes_flow(ax, filtered=filtered)
            return ax2
        elif unit.lower() == 'psu':
            ax2 = set_dual_axes_salt(ax, filtered=filtered)
            return ax2
        elif unit == 'm/s':
            ax2 = create_second_axis(ax, m_to_ft)
            if filtered:
                ax.set_ylabel(FILTERED_MPS_LABEL)
                ax2.set_ylabel(FILTERED_FTPS_LABEL)
            else:
                ax.set_ylabel(MPS_LABEL)
                ax2.set_ylabel(FTPS_LABEL)
            return ax2
        elif unit == 'deg C' or unit == 'degC':
            ax2 = create_second_axis(ax, celcius_to_fahrenheit)
            if filtered:
                ax.set_ylabel(FILTERED_DEG_C_LABEL)
                ax2.set_ylabel(FILTERED_DEG_F_LABEL)
            else:
                ax.set_ylabel(DEG_C_LABEL)
                ax2.set_ylabel(DEG_F_LABEL)
            return ax2
    else:
        raise ValueError("No unit provided for output and not inferred")
    print("Warning: set_dual_axes: Time series unit missing or not supported.")
    return None


def set_dual_axes_elev(ax1, filtered=False):
    """ Set dual axes for elevation.

        Parameters
        ----------

        ax: matplotlib axes
    """
    ax2 = create_second_axis(ax1, m_to_ft)
    if filtered:
        ax1.set_ylabel(FILTERED_M_LABEL)
        ax2.set_ylabel(FILTERED_FT_LABEL)
    else:
        ax1.set_ylabel(M_LABEL)
        ax2.set_ylabel(FT_LABEL)
    return ax2


def set_dual_axes_flow(ax1, filtered=False):
    """ Set dual axes for flow.

        Parameters
        ----------

        ax: matplotlib axes
    """
    ax2 = create_second_axis(ax1, cms_to_cfs)
    if filtered:
        ax1.set_ylabel(FILTERED_CMS_LABEL)
        ax2.set_ylabel(FILTERED_CFS_LABEL)
    else:
        ax1.set_ylabel(CMS_LABEL)
        ax2.set_ylabel(CFS_LABEL)
    return ax2


def set_dual_axes_temp(ax1, filtered=False):
    """ Set dual axes for temperature.

        Parameters
        ----------

        ax: matplotlib axes
    """
    ax2 = create_second_axis(ax1, celcius_to_fahrenheit)
    if filtered:
        ax1.set_ylabel(FILTERED_DEG_C_LABEL)
        ax2.set_ylabel(FILTERED_DEG_F_LABEL)
    else:
        ax1.set_ylabel(DEG_C_LABEL)
        ax2.set_ylabel(DEG_F_LABEL)
    return ax2


EC_LABEL = 'EC ($\mathsf{\mu}$S/cm)'
PSU_LABEL = 'Salinity (PSU)'
FILTERED_EC_LABEL = 'Tidal Avg EC ($\mathsf{\mu}$S/cm)'
FILTERED_PSU_LABEL = 'Tidal Avg Salinity (PSU)'
salt_axis_labels = [[None, PSU_LABEL],
                    [None, EC_LABEL]]
salt_filtered_axis_labels = [[None, FILTERED_PSU_LABEL],
                             [None, FILTERED_EC_LABEL]]


def psu_ec_25c_neg_scalar(psu,refine=True,hill_correction=True):
    ''' Modified version of psu_ec_25c to return zero EC with negative PSU
        instead of invoking ValueError
    '''
    if psu < 0.:
        return 0.
    elif psu > 34.99969:
        return ec_sea
    return psu_ec_25c_scalar(psu, refine, hill_correction)


def psu_ec_25c_neg(psu, refine=True, hill_correction=True):
    """ Modified version of pus_ec_25c to return zero EC with negative PSU
    """
    if type(psu) == float:
        return psu_ec_25c_neg_scalar(psu,refine,hill_correction)
    else:
        return psu_ec_25c_neg_vec(psu,refine,hill_correction)


psu_ec_25c_neg_vec = np.vectorize(psu_ec_25c_neg_scalar,
                            otypes='d',excluded=["refine","hill_correction"])


def set_dual_axes_salt(ax1, filtered=False):
    """ Set a dual y-axis for salt with a PSU y-axis

        Parameters
        ----------
        ax: axis
            a Matplotlib axes
    """
    yrange = ax1.get_ylim()
    if yrange[0] < 0.001:
        ax1.set_ylim((-1.e-6, yrange[1]))  # Value that make EC 0
    ax2 = create_second_axis(ax1, psu_ec_25c_neg)
    if filtered is True:
        ax1.set_ylabel(FILTERED_PSU_LABEL)
        ax2.set_ylabel(FILTERED_EC_LABEL)
    else:
        ax1.set_ylabel(PSU_LABEL)
        ax2.set_ylabel(EC_LABEL)
    return ax2


def set_xaxis_dateformat(ax, date_format=None,
                         major_locator=None, rotate=None, pad=None):
    """ Set the date format of the ticks of the x-axis.

        Parameters
        ----------

        ax: a Matplotlib axes

        date_format: A format of the ticks of the x-axis.
    """
    if major_locator is None:
        major_locator = mpl.dates.AutoDateLocator()
    ax.xaxis.set_major_locator(major_locator)
    if date_format is None:
        xformat = mpl.dates.AutoDateFormatter(major_locator)
    else:
        xformat = mpl.dates.DateFormatter(date_format)
    ax.xaxis.set_major_formatter(xformat)
    if pad is not None:
        ax.tick_params(axis='x', pad=pad)
    if rotate is not None:
        rotate_xticks(ax, rotate)


def set_xaxis_day(ax, date_format="%m/%d/%y", rotate=None, pad=None):
    """ Set axis with date format:
        1. Use daylocator
        2. The default format is "%m/%d/%f"
        3. Add a slight gap to prevent overlapping of x and y ticks

        Parameters
        ----------
        ax:
            a Matplotlib axes
        dateformat:
            date format
        rotate: angle to rotate ticks
        pad: padding between the x-axis and ticks
    """
    set_xaxis_dateformat(ax,
                         date_format=date_format,
                         major_locator=mpl.dates.DayLocator(),
                         rotate=rotate,
                         pad=pad)


def set_xaxis_month(ax, date_format="%b %y", rotate=None, pad=None, n_ticks=5):
    """ Set axis with date format:
        1. Use monthlocator
        2. The default format is "%b %y"
        3. Add a slight gap to prevent overlapping of x and y ticks

        Parameters
        ----------

        ax: a Matplotlib axes

        dateformat: date format

        rotate: angle to rotate ticks

        pad: padding between the x-axis and ticks
    """
    set_xaxis_dateformat(ax, date_format=date_format, major_locator=mpl.dates.MonthLocator(), rotate=rotate, pad=pad)
    if n_ticks is not None:
        ticks = ax.xaxis.get_major_ticks()
        keepers = get_nice_tick_indices(len(ticks), n_ticks)
        for i, tick in enumerate(ticks):
            if i not in keepers:
                tick.tick1line.set_visible(False)
                tick.tick2line.set_visible(False)
                tick.label1.set_visible(False)


def get_nice_tick_indices(n_ticks, n_wanted):
    interval = int(n_ticks / n_wanted)
    remnants = n_ticks % n_wanted
    return np.arange(remnants // 2 + 1, n_ticks, interval)


def set_nice_tick_intervals(ax, n_ticks):
    ticks = ax.xaxis.get_major_ticks()
    keepers = get_nice_tick_indices(len(ticks), n_ticks)
    for i, tick in enumerate(ticks):
        if i not in keepers:
            tick.tick1line.set_visible(False)
            tick.tick2line.set_visible(False)
            tick.label1.set_visible(False)


def auto_ylabels(axes, timeseries, dual=True):
    """ Put y-labels automatically inferring from props of a time series

        Parameters
        ----------
        timeseries: vtools.data.timeseries.TimeSeries
        dual: boolean, optional
            If true, create a second y-axis
    """
    if isinstance(timeseries, (list, tuple)):
        for item in timeseries:
            if isinstance(item, vtools.data.timeseries.TimeSeries):
                ts = item
    unit = ts.props['unit']
    if unit == 'm' or unit == 'meter':
        if 'filtered' in ts.props:
            axes.set_ylabel(FILTERED_M_LABEL)
        else:
            axes.set_ylabel(M_LABEL)
        if dual is True:
            axes2 = create_second_axis(axes, m_to_ft)
            if 'filtered' in ts.props:
                axes2.set_ylabel(FILTERED_FT_LABEL)
            else:
                axes2.set_ylabel(FT_LABEL)
    elif unit == 'cms':
        if 'filtered' in ts.props:
            axes.set_ylabel(FILTERED_CMS_LABEL)
        else:
            axes.set_ylabel(CMS_LABEL)
        if dual is True:
            axes2 = create_second_axis(axes, cms_to_cfs)
            if 'filtered' in ts.props:
                axes2.set_ylabel(FILTERED_CFS_LABEL)
            else:
                axes2.set_ylabel(CFS_LABEL)
    elif unit == 'PSU':
        ylim = axes.get_ylim()
        if ylim[0] < 0.:
            axes.set_ylim((0, ylim[1]))
        if 'filtered' in ts.props:
            axes.set_ylabel(FILTERED_PSU_LABEL)
        else:
            axes.set_ylabel(PSU_LABEL)
        if dual is True:
            axes2 = create_second_axis(axes, psu_ec_25c_neg)
            if 'filtered' in ts.props:
                axes2.set_ylabel(FILTERED_EC_LABEL)
            else:
                axes2.set_ylabel(EC_LABEL)
    elif unit == 'deg C':
        ylim = axes.get_ylim()
        if ylim[0] < 0.:
            axes.set_ylim((0, ylim[1]))
        if 'filtered' in ts.props:
            axes.set_ylabel(FILTERED_DEG_C_LABEL)
        else:
            axes.set_ylabel(DEG_C_LABEL)
        if dual is True:
            axes2 = create_second_axis(axes, psu_ec_25c_neg)
            if 'filtered' in ts.props:
                axes2.set_ylabel(FILTERED_DEG_F_LABEL)
            else:
                axes2.set_ylabel(DEG_F_LABEL)



def create_second_axis(ax1, y_converter_f=None,
                       y_major_locator=None, y_major_formatter=None):
    """ Create a second y-axis

        Parameters
        ----------

        ax1:  first axes

        y_converter:second axis converter callback

        y_major_formatter: y tick formatter for the second axis

        return: second axes
    """
    major_locator = ax1.xaxis.get_major_locator()
    major_formatter = ax1.xaxis.get_major_formatter()
    shared_x = ax1.get_shared_x_axes().get_siblings(ax1)
    if len(shared_x) > 1:
        for axes in shared_x:
            if axes != ax1:
                ax2 = axes
                axes.cla()
    else:
        ax2 = ax1.twinx()
    ax1.xaxis.set_major_locator(major_locator)
    ax1.xaxis.set_major_formatter(major_formatter)

    if y_converter_f:
        ax2.set_ylim(y_converter_f(np.array(ax1.get_ylim())))
    else:
        ax2.set_ylim(ax1.get_ylim())
    if y_major_locator:
        ax2.yaxis.set_major_locator(y_major_locator)
    if y_major_formatter:
        ax2.yaxis.set_major_formatter(y_major_formatter)
    return ax2


def rotate_xticks(ax, angle, align=None):
    if not align:
        align = 'right'
    for label in ax.get_xticklabels():
        label.set_rotation(angle)
        label.set_horizontalalignment(align)


def change_tick_label_size(ax1, size=None):
    if not size:
        size = "small"
    for tick in ax1.xaxis.get_major_ticks():
        tick.label.set_fontsize(size)
    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(size)
    ax1.yaxis.get_label().set_fontsize(size)


def set_scatter_color(artist):
    mpl.pyplot.setp(artist, alpha=0.15, edgecolor='grey',facecolor=brewer_colors[0])


def make_plot_isometric(axes):
    xlim = axes.get_xlim()
    ylim = axes.get_ylim()
    common_lim = (min(xlim[0], ylim[0]), max(xlim[1], ylim[1]))
    axes.set_xlim(*common_lim)
    axes.set_ylim(*common_lim)
    axes.set_aspect('equal')
