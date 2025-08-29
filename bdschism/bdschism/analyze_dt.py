import click
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import csv
import matplotlib.cm as cm


@click.group()
@click.help_option("-h", "--help")
def analyze_dt_cli():
    """Analyze SCHISM minTransportTimeStep fields from NetCDF output."""
    pass


def load_data(ncfile, time_step=None):
    """Load time step and mesh data from a SCHISM NetCDF file.

    Parameters
    ----------
    ncfile : str
        Path to the NetCDF file.
    time_step : int or None
        Specific time index to select. If None, load all.

    Returns
    -------
    tuple of (np.ndarray, np.ndarray, np.ndarray)
        Time step values, x-coordinates, y-coordinates.
    """
    ds = xr.open_dataset(ncfile)
    dt = ds["minTransportTimeStep"]
    if time_step is not None:
        dt = dt.isel(time=time_step)
    face_x = ds["SCHISM_hgrid_face_x"].values
    face_y = ds["SCHISM_hgrid_face_y"].values
    return dt.values, face_x, face_y


@click.command()
@click.argument("filename")
@click.option("--file_step", type=int, default=None, help="Time index to analyze.")
def hist(filename, file_step):
    """Plot histogram of time steps."""
    dt, _, _ = load_data(filename, file_step)
    clean = dt[~np.isnan(dt)]
    plt.hist(clean, bins=200, range=(0, np.percentile(clean, 10)))
    plt.xlabel("Time Step (s)")
    plt.ylabel("Frequency")
    plt.title("Histogram of minTransportTimeStep")
    plt.grid()
    plt.show()


@click.command()
@click.argument("filename")
@click.option("--file_step", required=True, type=int, help="Time index to analyze.")
@click.option(
    "--n", required=True, type=int, help="Number of lowest time steps to list."
)
def list(filename, file_step, n):
    """List lowest N time steps with coordinates and indices."""
    dt, x, y = load_data(filename, file_step)
    flat = [(i, dt[i], x[i], y[i]) for i in range(len(dt)) if not np.isnan(dt[i])]
    flat.sort(key=lambda tup: tup[1])
    print("ndx,el,x,y,dt")
    for idx, (el, val, xi, yi) in enumerate(flat[:n]):
        print(f"{idx},{el},{xi:.2f},{yi:.2f},{val:.6f}")


@click.command()
@click.argument("filename")
@click.option("--file_step", required=True, type=int, help="Time index to analyze.")
@click.option(
    "--n", required=True, type=int, help="Number of lowest time steps to highlight."
)
def plot(filename, file_step, n):
    """Plot time steps with lowest N highlighted."""
    dt, x, y = load_data(filename, file_step)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(x, y, s=2, c="gray", alpha=0.5)
    valid = [(dt[i], x[i], y[i]) for i in range(len(dt)) if not np.isnan(dt[i])]
    valid.sort()
    sel = valid[:n]
    sel_x = [v[1] for v in sel]
    sel_y = [v[2] for v in sel]
    ax.scatter(sel_x, sel_y, s=12, c="red", label="Lowest dt")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(f"Time Step Distribution (highlighting {n} lowest)")
    ax.legend()
    plt.grid()
    plt.show()


def summarize_elements(ncfile, top_n, min_count):
    ds = xr.open_dataset(ncfile)
    dt_all = ds["minTransportTimeStep"]
    face_x = ds["SCHISM_hgrid_face_x"].values
    face_y = ds["SCHISM_hgrid_face_y"].values
    appearances = Counter()
    for t in range(dt_all.sizes["time"]):
        dt = dt_all.isel(time=t).values
        valid = [(i, dt[i]) for i in range(len(dt)) if not np.isnan(dt[i])]
        valid.sort(key=lambda x: x[1])
        top_indices = [i for i, _ in valid[:top_n]]
        appearances.update(top_indices)
    filtered = [
        (el, appearances[el], face_x[el], face_y[el])
        for el in appearances
        if appearances[el] >= min_count
    ]
    filtered.sort(key=lambda x: (-x[1], x[0]))
    return filtered, face_x, face_y


def plot_summarized_bad_actors(bad_actors, all_x, all_y, label_top=None):
    counts = np.array([x[1] for x in bad_actors])
    xs = np.array([x[2] for x in bad_actors])
    ys = np.array([x[3] for x in bad_actors])
    els = np.array([x[0] for x in bad_actors])
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(all_x, all_y, s=2, c="0.5", alpha=0.4)
    norm = plt.Normalize(vmin=np.min(counts), vmax=np.max(counts))
    cmap = cm.get_cmap("Reds")
    ax.scatter(
        xs, ys, s=10 + 3 * counts, c=cmap(norm(counts)), label="Frequent bad actors"
    )
    if label_top is None:
        label_top = len(counts)
    top_idx = np.argsort(-counts)[:label_top]
    for i in top_idx:
        ax.text(
            xs[i],
            ys[i],
            str(els[i]),
            fontsize=8,
            ha="center",
            va="bottom",
            color="black",
        )
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label("Number of Appearances")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Elements Frequently Among Lowest Time Steps")
    ax.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


@click.command()
@click.argument("filename")
@click.option(
    "--num_elements",
    required=True,
    type=int,
    help="Top (smallest dt) N elements to consider at each timestep.",
)
@click.option(
    "--num_active",
    required=True,
    type=int,
    help="Minimum times an element must appear in top N.",
)
@click.option("--plot", is_flag=True, help="Plot flagged elements.")
@click.option(
    "--label_top",
    type=int,
    default=None,
    help="Number of top elements to label. Default labels all.",
)
@click.option("--csv_out", type=str, default=None, help="Optional CSV output file.")
def summarize(filename, num_elements, num_active, plot, label_top, csv_out):
    """Summarize elements frequently appearing in the worst time steps."""
    points, all_x, all_y = summarize_elements(filename, num_elements, num_active)
    if csv_out:
        with open(csv_out, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["el", "count", "x", "y"])
            for row in points:
                writer.writerow(row)
    else:
        print("el,count,x,y")
        for el, count, xi, yi in points:
            print(f"{el},{count},{xi:.2f},{yi:.2f}")
    if plot:
        plot_summarized_bad_actors(points, all_x, all_y, label_top=label_top)


analyze_dt_cli.add_command(hist)
analyze_dt_cli.add_command(list)
analyze_dt_cli.add_command(plot)
analyze_dt_cli.add_command(summarize)

if __name__ == "__main__":
    analyze_dt_cli()

# ```bash
# Plot histogram and CDF
# python analyze_dt.py dist out2d_21.nc --file_step 5
# python analyze_dt.py hist out2d_21.nc --file_step 5

# List 20 smallest time steps at timestep 3
# python analyze_dt.py list out2d_21.nc --file_step 3 --n 20

# Plot the smallest 20 time steps at timestep 2
# python analyze_dt.py plot out2d_21.nc --file_step 2 --n 20

# Summarize elements appearing in the worst 20 at least 10 times
# python analyze_dt.py summarize out2d_21.nc --summarize 20 --num_active 10

# Plot and export to CSV
# python analyze_dt.py summarize out2d_21.nc --summarize 20 --num_active 10 --plot --csv_out offenders.csv
