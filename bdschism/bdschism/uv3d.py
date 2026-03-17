import click
from schimpy import param
import bdschism.settings as config
import os
import shutil
import datetime


def interpolate_uv3d(
    param_nml,
    bg_dir,
    bg_output_dir,
    fg_dir,
    hgrid_bg,
    hgrid_fg,
    vgrid_bg,
    vgrid_fg,
    interp_template,
    nday,
    output,
    overwrite,
):
    """Run interpolate_variables utility to generate uv3d.th.nc.

    Parameters
    ----------
    param_nml : str or None
        Path to param.nml. If None, defaults to bg_dir/param.nml.
    bg_dir : str
        Background simulation directory.
    bg_output_dir : str or None
        Output directory inside bg_dir where interpolate_variables is run.
    fg_dir : str or None
        Foreground (baroclinic) run directory. Used for hgrid_fg/vgrid_fg links.
        If None, defaults to bg_dir.
    hgrid_bg : str
        Background hgrid filename (relative to bg_dir).
    hgrid_fg : str
        Foreground hgrid filename (relative to fg_dir).
    vgrid_bg : str
        Background vgrid filename (relative to bg_dir).
    vgrid_fg : str
        Foreground vgrid filename (relative to fg_dir).
    interp_template : str or None
        Path to interpolate_variables.in template. If None, a minimal file
        is written based on nday (or rnday from param.nml).
    nday : int or None
        Number of days to process when interp_template is None. If None,
        rnday is read from param_nml.
    output : str
        Path where the final uv3d output will be written (moved).
    overwrite : bool
        If True, overwrite an existing file in output_dir. If False, fail
        fast if the file already exists.
    """
    #
    # Validate directory paths
    #
    try:
        assert os.path.exists(bg_dir)
    except AssertionError:
        print(f"Path does not exist: {bg_dir}")
    bg_dir = os.path.abspath(bg_dir)

    # bg_output_dir
    if bg_output_dir is None:
        if os.path.exists(os.path.join(bg_dir, "outputs.tropic")):
            bg_output_dir = "outputs.tropic"
        elif os.path.exists(os.path.join(bg_dir, "outputs")):
            bg_output_dir = "outputs"
        else:
            print(
                f"Invalid path: {bg_output_dir} (Default is outputs.tropic or outputs)"
            )
            raise ValueError

    # Directory in which interpolate_variables executable will be run
    interp_dir = os.path.join(bg_dir, bg_output_dir)
    try:
        assert os.path.exists(interp_dir)
    except AssertionError:
        print(f"Path does not exist: {interp_dir}")

    # fg_dir
    if fg_dir is None:
        print("`fg_dir` is not specified. Setting it to `bg_dir`.")
        fg_dir = bg_dir
    fg_dir = os.path.abspath(fg_dir)



    #
    # Determine final output filename and check overwrite EARLY
    #

    # Canonical name of the file produced by interpolate_variables in interp_dir
    output_from_interpolate_variables = config.get_output_from_interpolate_variables("uv3d")

    # Determine final output path (full path to the file we will write)
    if output is None:
        # Default: write into the current working directory with the canonical name
        output = os.path.abspath(output_from_interpolate_variables)
    else:
        # Honor whatever the user passed, relative or absolute
        output = os.path.abspath(output)

    # Early overwrite check
    if os.path.exists(output) and not overwrite:
        raise Exception(
            f"Error: output file already exists: {output}. "
            f"Use --overwrite to replace it."
        )


    #
    # Make sure "interpolate_variables.in" is present
    #
    if interp_template is None:
        print(
            "interpolate_variables.in is not specified. Extracting nday from user input."
        )
        if nday is None:
            print("nday not specified in user input. Extracting nday from param.nml.")
            #
            # Parse param.nml
            #
            if param_nml is None:
                param_nml = os.path.join(bg_dir, "param.nml")
            params = param.read_params(param_nml)
            nday = params["rnday"]

        with open(os.path.join(interp_dir, "interpolate_variables.in"), "w") as f:
            f.write(f"3 {nday}\n")
            f.write("1 1\n")
            f.write("0")

    else:
        if os.path.abspath(interp_template) == os.path.join(
            interp_dir, "interpolate_variables.in"
        ):
            pass
        else:
            print(
                f"{os.path.abspath(interp_template)}\ncopied to\n"
                f"{os.path.join(interp_dir, 'interpolate_variables.in')}"
            )
            shutil.copy(
                interp_template, os.path.join(interp_dir, "interpolate_variables.in")
            )

        if nday is not None:
            print("Argument 'nday' is not accepted when interp_template is specified.")
            raise ValueError

        # Make sure the first parameter in the interpolate_variables.in file is 3 for uv3d.th.nc
        with open(os.path.join(interp_dir, "interpolate_variables.in"), "r") as f:
            lines = f.readlines()

            if lines[0].split()[0] != "3":
                raise ValueError(
                    "The first parameter in the interpolate_variables.in file must be 3 for uv3d.th.nc"
                )

    #
    # Create symbolic links
    #
    print("\nFiles linked:")
    print(f"{os.path.join(bg_dir, hgrid_bg)} -> {os.path.join(interp_dir, 'bg.gr3')}")
    print(f"{os.path.join(fg_dir, hgrid_fg)} -> {os.path.join(interp_dir, 'fg.gr3')}")
    print(f"{os.path.join(bg_dir, vgrid_bg)} -> {os.path.join(interp_dir, 'vgrid.bg')}")
    print(f"{os.path.join(fg_dir, vgrid_fg)} -> {os.path.join(interp_dir, 'vgrid.fg')}")

    config.create_link(
        os.path.join(bg_dir, hgrid_bg), os.path.join(interp_dir, "bg.gr3")
    )
    config.create_link(
        os.path.join(fg_dir, hgrid_fg), os.path.join(interp_dir, "fg.gr3")
    )
    config.create_link(
        os.path.join(bg_dir, vgrid_bg), os.path.join(interp_dir, "vgrid.bg")
    )
    config.create_link(
        os.path.join(fg_dir, vgrid_fg), os.path.join(interp_dir, "vgrid.fg")
    )

    #
    # Load SCHISM module and execute interpolate_variables
    #
    print(
        f"Running interpolate_variables utility in "
        f"{os.path.abspath(os.path.join(bg_dir, bg_output_dir))}"
    )
    os.chdir(os.path.abspath(interp_dir))
    config.interpolate_variables()

    #
    # Move the resulting file to output_dir
    #
    src_file = os.path.join(interp_dir, output_from_interpolate_variables)
    if not os.path.exists(src_file):
        raise Exception(
            f"Expected output file {src_file} not found after interpolate_variables."
        )

    print(
        f"Moving {src_file} to {output}"
    )
    shutil.move(src_file, output)


@click.command(help="Runs interpolate_variables utility to generate uv3d.th.nc.")
@click.option(
    "--param_nml",
    default=None,
    type=click.Path(exists=True),
    help="Name of parameter file (default: param.nml in bg_dir).",
)
@click.option(
    "--bg_dir",
    default=".",
    type=click.Path(exists=True),
    help=(
        "Background simulation directory (e.g., larger or barotropic) "
        "(default: current directory)."
    ),
)
@click.option(
    "--bg_output_dir",
    default=None,
    type=click.Path(),
    help="Output directory in background. If None, will try outputs.tropic then outputs.",
)
@click.option(
    "--fg_dir",
    default=None,
    type=click.Path(),
    help=(
        "Foreground baroclinic run directory used for fg hgrid/vgrid links. "
        "If None, will use bg_dir."
    ),
)
@click.option(
    "--hgrid_bg",
    default="hgrid.gr3",
    type=click.Path(),
    help="Name of hgrid.gr3 file in bg_dir, which will be linked to bg.gr3.",
)
@click.option(
    "--hgrid_fg",
    default="hgrid.gr3",
    type=click.Path(),
    help="Name of hgrid.gr3 file in fg_dir, which will be linked to fg.gr3.",
)
@click.option(
    "--vgrid_bg",
    default="vgrid.in.2d",
    type=click.Path(),
    help="Name of the (2D barotropic) vgrid file in bg_dir.",
)
@click.option(
    "--vgrid_fg",
    default="vgrid.in.3d",
    type=click.Path(),
    help="Name of the (3D) baroclinic vgrid file in fg_dir.",
)
@click.option(
    "--interp_template",
    default=None,
    type=click.Path(),
    help=(
        "Path to interpolate_variables.in file. If None, a minimal file is "
        "created using nday or rnday from param.nml."
    ),
)
@click.option(
    "--nday",
    default=None,
    type=int,
    help=(
        "Number of days to process when interp_template is not given. "
        "If None, rnday is parsed from param.nml."
    ),
)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help=(
        "Full path to the output file (including filename). "
        "Default: ./<canonical_output_name>."
    ),
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite an existing uv3d output file in output_dir, if present.",
)
@click.help_option("-h", "--help")
def interpolate_uv3d_cli(
    param_nml,
    bg_dir,
    bg_output_dir,
    fg_dir,
    hgrid_bg,
    hgrid_fg,
    vgrid_bg,
    vgrid_fg,
    interp_template,
    nday,
    output,
    overwrite,
):
    """
    Command-line interface for the interpolate_uv3d function.
    """
    interpolate_uv3d(
        param_nml,
        bg_dir,
        bg_output_dir,
        fg_dir,
        hgrid_bg,
        hgrid_fg,
        vgrid_bg,
        vgrid_fg,
        interp_template,
        nday,
        output,
        overwrite,
    )

def setup_tmp_dir(bg_output_dir, tmp_bg_output_dir, nfile):
    """Set up a temporary directory with links to the specific output files for uv3d interpolation."""

    print("\n\tOutput files linked:")
    print(
        f"\t\t{os.path.join(bg_output_dir, f"out2d_{nfile}.nc")} -> {os.path.join(tmp_bg_output_dir, "out2d_1.nc")}"
    )
    print(
        f"\t\t{os.path.join(bg_output_dir, f"zCoordinates_{nfile}.nc")} -> {os.path.join(tmp_bg_output_dir, "zCoordinates_1.nc")}"
    )
    print(
        f"\t\t{os.path.join(bg_output_dir, f"horizontalVelX_{nfile}.nc")} -> {os.path.join(tmp_bg_output_dir, "horizontalVelX_1.nc")}"
    )
    print(
        f"\t\t{os.path.join(bg_output_dir, f"horizontalVelY_{nfile}.nc")} -> {os.path.join(tmp_bg_output_dir, "horizontalVelY_1.nc")}\n"
    )

    config.create_link(
        os.path.join(bg_output_dir, f"out2d_{nfile}.nc"),
        os.path.join(tmp_bg_output_dir, "out2d_1.nc"),
    )
    config.create_link(
        os.path.join(bg_output_dir, f"zCoordinates_{nfile}.nc"),
        os.path.join(tmp_bg_output_dir, "zCoordinates_1.nc"),
    )
    config.create_link(
        os.path.join(bg_output_dir, f"horizontalVelX_{nfile}.nc"),
        os.path.join(tmp_bg_output_dir, "horizontalVelX_1.nc"),
    )
    config.create_link(
        os.path.join(bg_output_dir, f"horizontalVelY_{nfile}.nc"),
        os.path.join(tmp_bg_output_dir, "horizontalVelY_1.nc"),
    )


def single_uv3d(
    nfile,
    param_nml="param.nml",
    bg_dir="./",
    bg_output_dir="./outputs",
    fg_dir="./",
    hgrid_bg="./hgrid.gr3",
    hgrid_fg="./hgrid.gr3",
    vgrid_bg="./vgrid.in.2d",
    vgrid_fg="./vgrid.in.3d",
    out_dir="./",
    overwrite=True,
    cleanup=True,
):
    """
    Process a single uv3d output file for the specified nfile index.
    """
    base_dir = os.path.abspath(bg_dir)

    # Determine outputs directory to link to tmp dir
    if bg_output_dir is None:
        if os.path.exists(os.path.join(bg_dir, "outputs.tropic")):
            bg_output_dir = "../outputs.tropic"
        elif os.path.exists(os.path.join(bg_dir, "outputs")):
            bg_output_dir = "../outputs"
        else:
            print(
                f"Invalid path: {bg_output_dir} (Default is outputs.tropic or outputs)"
            )
            raise ValueError

    # Create a temporary directory for the single uv3d output file
    tmp_bg_output_dir = f"./tmp_outputs_{nfile}"
    os.makedirs(tmp_bg_output_dir, exist_ok=True)
    print(f"Linking outputs in {tmp_bg_output_dir}...")
    
    os.makedirs(out_dir, exist_ok=True)

    try:
        # Symlink all _{nfile}.nc files from bg_dir outputs to bg_output_dir
        setup_tmp_dir(bg_output_dir, tmp_bg_output_dir, nfile)

        print("Running interpolate_uv3d...")
        interpolate_uv3d(
            param_nml,
            bg_dir,
            tmp_bg_output_dir,
            fg_dir,
            hgrid_bg,
            hgrid_fg,
            vgrid_bg,
            vgrid_fg,
            None,
            1,
            f"{out_dir}/uv3d_{nfile}.th.nc",
            overwrite,
        )

    finally:
        os.chdir(base_dir)
        print(f"\nCurrent dir: {os.getcwd()}")
        if cleanup and os.path.exists(tmp_bg_output_dir):
            print(f"\nDeleting temporary directory {tmp_bg_output_dir}...")
            shutil.rmtree(tmp_bg_output_dir)


@click.command(
    help=(
        "Generate a single uv3d boundary file from one SCHISM output index.\n\n"
        "Links out2d/zCoordinates/horizontalVel files for one index into a "
        "temporary folder, runs interpolate_variables, and writes "
        "uv3d_<NFILE>.th.nc into --out_dir.\n\n"
        "Example:\n"
        "  bds uv3d_single 10 --out_dir outputs.tropic/uv3d --overwrite"
    )
)
@click.argument(
    "nfile",
    type=int,
)
@click.option(
    "--param",
    default=None,
    type=click.Path(exists=True),
    help="Name of parameter file (default: param.nml in bg_dir).",
)
@click.option(
    "--bg-dir",
    default=".",
    type=click.Path(exists=True),
    help=(
        "Background simulation directory (e.g., larger or barotropic) "
        "(default: current directory)."
    ),
)
@click.option(
    "--bg-output-dir",
    default=None,
    type=click.Path(),
    help="Output directory in background. If None, will try outputs.tropic then outputs.",
)
@click.option(
    "--fg-dir",
    default=None,
    type=click.Path(),
    help=(
        "Foreground baroclinic run directory used for fg hgrid/vgrid links. "
        "If None, will use bg_dir."
    ),
)
@click.option(
    "--hgrid-bg",
    default="hgrid.gr3",
    type=click.Path(),
    help="Name of hgrid.gr3 file in bg_dir, which will be linked to bg.gr3.",
)
@click.option(
    "--hgrid-fg",
    default="hgrid.gr3",
    type=click.Path(),
    help="Name of hgrid.gr3 file in fg_dir, which will be linked to fg.gr3.",
)
@click.option(
    "--vgrid-bg",
    default="vgrid.in.2d",
    type=click.Path(),
    help="Name of the (2D barotropic) vgrid file in bg_dir.",
)
@click.option(
    "--vgrid-fg",
    default="vgrid.in.3d",
    type=click.Path(),
    help="Name of the (3D) baroclinic vgrid file in fg_dir.",
)
@click.option(
    "-o",
    "--out-dir",
    default="./",
    show_default=True,
    type=click.Path(),
    help="Directory where the generated uv3d file will be written.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite an existing uv3d output file in output_dir, if present.",
)
@click.option(
    "--cleanup/--no-cleanup",
    default=True,
    show_default=True,
    help="Remove temporary linked files after interpolation.",
)
@click.help_option("-h", "--help")
def single_uv3d_cli(
    nfile,
    param,
    bg_dir,
    bg_output_dir,
    fg_dir,
    hgrid_bg,
    hgrid_fg,
    vgrid_bg,
    vgrid_fg,
    out_dir,
    overwrite,
    cleanup,
):
    """Generate one uv3d file for output index NFILE."""
    single_uv3d(
        nfile,
        param,
        bg_dir,
        bg_output_dir,
        fg_dir,
        hgrid_bg,
        hgrid_fg,
        vgrid_bg,
        vgrid_fg,
        out_dir,
        overwrite,
        cleanup,
    )

if __name__ == "__main__":
    interpolate_uv3d_cli()
