import click
from bdschism.set_nudging import set_nudging_cli
from bdschism.hotstart_from_hotstart import hotstart_newgrid_cli
from bdschism.hotstart_date import set_hotstart_date_cli
from bdschism.hotstart_nudging_data import hotstart_nudge_data_cli
from bdschism.uv3d import interpolate_uv3d_cli
from bdschism.port_boundary import port_boundary_cli
from bdschism.ccf_gate_height import ccf_gate_cli
from bdschism.calc_ndoi import calc_indoi_cli
from bdschism.parse_cu import parse_cu_cli, parse_cu_yaml_cli
from bdschism.plot_input_boundaries import plot_bds_bc_cli

import subprocess
import sys
import os

bds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")


@click.group(
    help="Bay-Delta SCHISM CLI tools for managing simulations and data processing."
)
@click.help_option("-h", "--help")  # Add the help option at the group level
def cli():
    """Main entry point for bdschism commands."""
    pass


@cli.command("precheck")
@click.option(
    "--simdir",
    default=".",
    show_default=True,
    help="Simulation directory to check (default: current directory).",
)
def precheck(simdir):
    """Run the Bay-Delta SCHISM precheck test suite using pytest."""
    test_suite_dir = os.path.abspath(os.path.join(bds_dir, "test_suite"))
    cmd = [sys.executable, "-m", "pytest", test_suite_dir, f"--sim_dir={simdir}"]
    click.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


# Register bds sub-commands
cli.add_command(set_nudging_cli, "set_nudge")
cli.add_command(hotstart_newgrid_cli, "hot_from_hot")
cli.add_command(set_hotstart_date_cli, "hot_date")
cli.add_command(hotstart_nudge_data_cli, "hot_nudge_data")
cli.add_command(interpolate_uv3d_cli, "uv3d")
cli.add_command(port_boundary_cli, "port_bc")
cli.add_command(ccf_gate_cli, "ccf_gate")
# create_nudging = "schimpy.nudging:main"
cli.add_command(calc_indoi_cli, "calc_ndoi")
cli.add_command(parse_cu_cli, "parse_cu")
cli.add_command(parse_cu_yaml_cli, "parse_cu_yaml")
cli.add_command(plot_bds_bc_cli, "plot_bds_bc")
cli.add_command(precheck, "precheck")

if __name__ == "__main__":
    cli()
