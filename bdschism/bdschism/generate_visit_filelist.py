import click
import os

def visit_list(
    output_dir,
    var,
    start,
    end,
    filename,
):
    """Generate a file containing a list of SCHISM output files to be visualized on VisIt.

    Parameters
    ----------
    output_dir : str
        Outputs directory containing SCHISM output files.
    var: str
        variable name for SCHISM output files (e.g., horizontalVelX).
    start : int
        Starting index for the file list.
    end : int
        Ending index for the file list.
    filename : str
        Filename for the list of SCHISM output files.
    """

    # Make sure output_dir exists
    try:
        assert os.path.exists(output_dir)
    except AssertionError:
        print(f"Path does not exist: {output_dir}")

    # Make sure var is a SCHISM output variable
    try:
        assert var in ["horizontalVelX", "horizontalVelY", "zCoordinates", "out2d", "salinity",
                        "sedConcentration_1", "sedConcentration_2", "sedConcentration_3"]
    except AssertionError:
        print(f"Invalid SCHISM output variable: {var}")

    # start should be less than end
    try:
        assert start <= end
    except AssertionError:
        print(f"Invalid start and end indices: start ({start}) should be less than or equal to end ({end})")

    # filename should have .visit extension
    try:
        assert filename.endswith(".visit")
    except AssertionError:
        print(f"File being generated should have .visit extension: {filename}")

    # Generate file list
    file_list = []
    for i in range(start, end + 1):
        file_name = f"{var}_{i}.nc"
        file_path = os.path.join(output_dir, file_name)
        if os.path.exists(file_path):
            file_list.append(file_path)
        else:
            print(f"Warning: File does not exist and will be skipped: {file_path}")

    # Write to file
    with open(filename, "w") as f:
        for file_path in file_list:
            f.write(f"{file_path}\n")

    print(f"File list generated: `{filename}` with {len(file_list)} files.")

@click.command(help="Generates a file list for visualizaing multiple, consecutive files in VisIt. \n Example: visit_list --output_dir . --var horizontalVelX --start 1 --end 10 --filename list_winter.visit")
@click.option(
    "--output_dir",
    default=None,
    required=True,
    type=click.Path(exists=True),
    help="Path to the `outputs` directory containing SCHISM output files.",
)
@click.option(
    "--var",
    default=None,
    required=True,
    type=str,
    help="variable name for SCHISM output files (e.g., horizontalVelX).",
)
@click.option(
    "--start",
    default=None,
    required=True,
    type=int,
    help=(
        "Starting index for the file list."
    ),
)
@click.option(
    "--end",
    default=None,
    required=True,
    type=int,
    help="Ending index for the file list.",
)
@click.option(
    "--filename",
    default=None,
    required=True,
    type=str,
    help=("Filename for the list of SCHISM output files."
    ),
)

@click.help_option("-h", "--help")
def visit_list_cli(
    output_dir,
    var,
    start,
    end,
    filename,
):
    """
    Command-line interface to create a file containing a list of SCHISM output files to be visualized on VisIt.
    """
    visit_list(
    output_dir,
    var,
    start,
    end,
    filename,
)


if __name__ == "__main__":
    visit_list_cli()