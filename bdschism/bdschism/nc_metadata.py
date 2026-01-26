import click
from netCDF4 import Dataset

def nc_metadata(ncfile, attr_name, attr_value, write, read, overwrite):
    """
    Read or write NetCDF global metadata.
    """

    if write == read:
        raise click.UsageError("Specify exactly one of --read or --write")

    with Dataset(ncfile, "r+" if write else "r") as ds:

        if write:
            if attr_name is None:
                raise click.UsageError("--attr_name is required with --write")
            if attr_value is None:
                raise click.UsageError("--attr_value is required with --write")

            if hasattr(ds, attr_name):
                if not overwrite:
                    raise click.UsageError(
                        f"{attr_name} already has value {attr_value}. Use --overwrite flag to overwrite."
                    )
            else:
                ds.setncattr(attr_name, attr_value)
            click.echo(f"Wrote attribute: {attr_name} = {attr_value}")

        if read:
            if attr_name is None:

                if len(ds.ncattrs()) == 0:
                    raise click.ClickException(f"{ncfile} has no attributes")
                else:
                    raise click.ClickException(
                        f"--attr_name not provided. List of attributes: \n{ds.ncattrs()}"
                    )

            if not hasattr(ds, attr_name):
                raise click.ClickException(
                    f"Attribute '{attr_name}' not found in file. List of attributes: \n{ds.ncattrs()}"
                )

            value = ds.getncattr(attr_name)
            click.echo(value)


@click.command(help="Insert and modify metadata of NetCDF files")
@click.option(
    "--file",
    "ncfile",
    required=True,
    type=click.Path(exists=True),
    help="NetCDF file to operate on",
)
@click.option(
    "--write",
    is_flag=True,
    help="Write or update (requires --overwrite flag) an attribute",
)
@click.option(
    "--read",
    is_flag=True,
    help="Read an attribute. Running the function with --read flag and no other option will print list of operable attributes.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Enable overwriting when --write flag is used.",
)
@click.option(
    "--attr_name",
    required=False,
    help="Name of the NetCDF attribute.",
)
@click.option(
    "--attr_value",
    required=False,
    help="Value of the NetCDF attribute (required for --write)",
)
@click.help_option("-h", "--help")
def nc_metadata_cli(ncfile, attr_name, attr_value, write, read, overwrite):

    nc_metadata(ncfile, attr_name, attr_value, write, read, overwrite)


if __name__ == "__main__":
    nc_metadata_cli()
