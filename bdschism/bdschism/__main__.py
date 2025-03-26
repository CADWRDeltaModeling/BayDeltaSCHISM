import click
from bdschism.set_nudging import set_nudging_cli  # Import the set_nudging command
from bdschism.hotstart_from_hotstart import hotstart_newgrid_cli
from bdschism.hotstart_date import set_hotstart_date_cli
from bdschism.hotstart_nudging_data import hotstart_nudge_data_cli
from bdschism.uv3d import interpolate_uv3d


@click.group(
    help="Bay-Delta SCHISM CLI tools for managing simulations and data processing."
)
@click.help_option("-h", "--help")  # Add the help option at the group level
def cli():
    """Main entry point for bdschism commands."""
    pass


# Register the set_nudging command
cli.add_command(set_nudging_cli, "set_nudge")
cli.add_command(hotstart_newgrid_cli, "hot_from_hot")
cli.add_command(set_hotstart_date_cli, "hot_date")
cli.add_command(hotstart_nudge_data_cli, "hot_nudge_data")
cli.add_command(interpolate_uv3d, "uv3d")
# create_nudging = "schimpy.nudging:main"

if __name__ == "__main__":
    cli()
