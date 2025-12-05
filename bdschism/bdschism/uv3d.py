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
    output_dir,
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
    output_dir : str
        Directory where the final uv3d output will be written (moved).
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
    # Canonical filename from settings
    canonical = config.get_output_from_interpolate_variables("uv3d")

    # If --output was not provided, default to ./canonical
    if output is None:
        output = os.path.abspath(canonical)
    else:
        output = os.path.abspath(output)

    # Early overwrite check
    if os.path.exists(output) and not overwrite:
        raise Exception(
            f"Error: output file already exists: {output}. "
            f"Use --overwrite to replace it."
        )


    if os.path.exists(destination_file):
        if overwrite:
            print(
                f"Warning: {destination_file} already exists and will be overwritten "
                f"(use --overwrite to suppress this check)."
            )
        else:
            raise Exception(
                f"Error: {destination_file} already exists. "
                f"Delete it or rerun with --overwrite."
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
        f"Moving {src_file} to {destination_file}"
    )
    shutil.move(src_file, output)


@click.command(help="Runs interpolate_variables utility to generate uv3d.th.nc.")
@click.option(``
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


if __name__ == "__main__":
    interpolate_uv3d_cli()
