from .three_point_linear_norm import *
import matplotlib 

location_labels = {
    54: "Martinez",
    82: "Collinsville",
    92: "Emmaton",
    75: "Mallard",
    101: "Rio Vista",
}

MAX_STATION = 0
MIN_STATION = 0
MAX_DEPTH = 0


def set_index_bounds(min_station, max_station, max_depth):
    global MAX_STATION
    global MIN_STATION
    global MAX_DEPTH
    MIN_STATION = min_station
    MAX_STATION = max_station
    MAX_DEPTH = max_depth


def get_index_bounds():
    return (MIN_STATION, MAX_STATION, MAX_DEPTH)


def nearest_neighbor_fill(arr):
    from scipy.spatial import KDTree
    import numpy as np

    a = arr.copy()
    x, y = np.mgrid[0 : a.shape[0], 0 : a.shape[1]]
    xygood = np.array((x[~a.mask], y[~a.mask])).T
    xybad = np.array((x[a.mask], y[a.mask])).T
    a[a.mask] = a[~a.mask][KDTree(xygood).query(xybad)[1]]
    return a


def vertical_fill(arr):
    import numpy as np
    out = arr.copy()
    column_max = np.tile(np.amax(out, axis=0), (out.shape[0], 1))
    idx = out.mask.copy()
    out[idx] = column_max[idx]
    return out


def profile_plot(
    x,
    z,
    data,
    ax,
    context_label=None,
    add_labels=False,
    xlabel=None,
    xmin=None,
    xmax=None,
    max_depth=None,
    add_context_label=True,
    context_loc="upper right",
    ylabel=True,
    show_xticklabels=True,
):
    """
    UnTRIM-like longitudinal profile plot of salinity.

    Parameters
    ----------
    x, z, data : array-like
        Distance, depth, and salinity arrays.
    ax : matplotlib.axes.Axes
        Target axes.
    context_label : str, optional
        Text annotation, typically a date or case label.
    add_labels : bool, default False
        Add named location labels. This is intentionally respected so
        multi-row paper figures can label only the top row.
    xlabel : str, optional
        X-axis label. Pass this only for the axes where the km marker should appear.
    xmin, xmax : float, optional
        Bounds in km.
    max_depth : int, optional
        Maximum plotted depth.
    add_context_label : bool, default True
        Draw context_label when supplied.
    context_loc : {"upper right", "upper left"}, default "upper right"
        Placement for the context label.
    ylabel : bool, default True
        Draw the Depth label.
    show_xticklabels : bool, default True
        Show x tick labels.
    """

    import matplotlib
    import numpy as np
    import matplotlib.cm as cm
    import matplotlib.colors as colors

    global x_part
    global z_part

    matplotlib.rcParams["xtick.direction"] = "out"
    matplotlib.rcParams["ytick.direction"] = "out"

    if not max_depth:
        max_depth = data.shape[0]

    if xmin is not None:
        min_station = x[0, :].searchsorted(xmin)
    else:
        min_station = 0

    if xmax is not None:
        max_station = x[0, :].searchsorted(xmax)
    else:
        max_station = x.shape[1]

    set_index_bounds(min_station, max_station, max_depth)

    x_part = x[0:max_depth, min_station:max_station]
    z_part = z[0:max_depth, min_station:max_station]

    data_part = data[0:max_depth, min_station:max_station]
    data_part = np.ma.masked_where(np.isnan(data_part), data_part)

    cmap = matplotlib.colormaps["RdBu_r"].copy()
    cmap.set_bad("white", 0.0)

    im = None

    do_line_contour = True
    if do_line_contour:
        lev = np.array([2.0, 4.0, 8.0, 16.0])
        greys = 1.0-lev/32.
        cs = ax.contour(x_part,z_part,data_part,levels = lev,colors=['black','black','black','black'],linewidths=2)
        greylev = 1.0
        try:
            for c in cs.collections:
                c.set_linestyle('solid')
            #Thicken the zero contour.
            zc = cs.collections[0]
            #ax.setp(zc, linewidth=3)
            #ax.setp(zc, linestyle = 'dotted')
        except (AttributeError, IndexError):
            # Matplotlib version may not support collections attribute
            pass
        ax.clabel(cs, lev,  # label every second level
               inline=1,
               inline_spacing = 3,
               fmt='%1.1f',
               fontsize=12)
    else:
        cs = None


    filled_levels = [0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
    norml = colors.BoundaryNorm(filled_levels, 256)
    filled_data_part = vertical_fill(data_part)
    bad_data = np.ma.masked_where(~data_part.mask, data_part.mask, copy=True)
    maxz = np.argmax(bad_data, axis=0)

    maxz[maxz == 0] = max_depth
    maxz = np.concatenate(([max_depth], maxz, [max_depth]))
    xstat = np.concatenate(([x_part[0, 0]], x_part[0, :], [x_part[0, -1]]))
    ax.set_ylim([max_depth, 1])
    cs = ax.contourf(
        x_part,
        z_part,
        filled_data_part,
        levels=filled_levels,
        cmap=cmap,
        norm=norml,
        extent=(x[0, min_station], x[0, max_station - 1], max_depth, 1),
    )
    ax.fill(xstat, maxz, "darkgray")

    if add_labels:
        inbound_label_dists = [
            x for x in location_labels.keys() if (x > xmin and x < xmax)
        ]
        bbox_props = dict(boxstyle="rarrow,pad=0.25", fc="white", lw=0.8)
        for dist in inbound_label_dists:
            ax.text(
                dist,
                max_depth - 2,
                location_labels[dist],
                ha="center",
                va="bottom",
                rotation=270,
                size=7,
                bbox=bbox_props,
                zorder=10,
            )

    ttxt = None
    if context_label and add_context_label:
        if context_loc == "upper left":
            x_text = x_part[0, 0] + 2
            ha = "left"
        else:
            x_text = x_part[0, -1] - 2
            ha = "right"
        ttxt = ax.text(
            x_text,
            2.0,
            context_label,
            size=8,
            color="black",
            ha=ha,
            va="top",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.65, pad=1.5),
            zorder=20,
        )

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel("Depth (m)")
    else:
        ax.set_ylabel("")

    ax.set_yticks([1, 5, 10, 15, 20, 25, 30])
    ax.tick_params(labelbottom=show_xticklabels)

    return im, cs, ttxt
