import click
from schimpy import param
import bdschism.settings as config
import os
import shutil


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
    write_clinic,
):
    """Main function to run interpolate_variables utility."""
    #
    # Validate directory paths
    #

    # bg_dir
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

    """
    #
    # Load SCHISM module and execute interpolate_variables
    #
    os.chdir(interp_dir)
    subprocess.run("module purge", shell=True)
    subprocess.run("module load schism/5.10_intel2022.1", shell=True)
    subprocess.run(["ulimit","-s","unlimited"], shell=True)
    subprocess.run(["interpolate_variables8"], shell=True)

    if write_clinic == True:
        shutil.move(os.path.join(interp_dir, "uv3D.th.nc"), os.path.join(bg_dir, "uv3D.th.nc"))
    """
    print(
        f"Running `interpolate_variables8` in {os.path.abspath(os.path.join(bg_dir,bg_output_dir))}"
    )
    os.chdir(os.path.abspath(interp_dir))
    command = "module purge \n module load intel/2024.0 hmpt/2.29 hdf5/1.14.3 netcdf-c/4.9.2 netcdf-fortran/4.6.1 schism/5.11.1 \n ulimit -s unlimited \n interpolate_variables8"
    os.system(command)


@click.command(help="Runs interpolate_variables utility to generate uv3d.th.nc.")
@click.option(
    "--param_nml",
    default=None,
    type=click.Path(exists=True),
    help="Name of parameter file (default: param.nml).",
)
@click.option(
    "--bg_dir",
    default=".",
    type=click.Path(exists=True),
    help="Name of background simulation (e.g., larger or barotropic) directory (default: current directory).",
)
@click.option(
    "--bg_output_dir",
    default=None,
    type=click.Path(),
    help="Name of output directory in background. If None, will try outputs.tropic then outputs.",
)
@click.option(
    "--fg_dir",
    default=None,
    type=click.Path(),
    help="Name of foreground baroclinic run directory. If None, will copy from tropic_dir.",
)
@click.option(
    "--hgrid_bg",
    default="hgrid.gr3",
    type=click.Path(),
    help="Name of hgrid.gr3 file in tropic_, which will be linked to bg.gr3.",
)
@click.option(
    "--hgrid_fg",
    default="hgrid.gr3",
    type=click.Path(),
    help="Name of hgrid.gr3 file in clinic_, which will be linked to fg.gr3.",
)
@click.option(
    "--vgrid_bg",
    default="vgrid.in.2d",
    type=click.Path(),
    help="Name of the (2D barotropic) vgrid file.",
)
@click.option(
    "--vgrid_fg",
    default="vgrid.in.3d",
    type=click.Path(),
    help="Name of the (3D) baroclinic vgrid file.",
)
@click.option(
    "--interp_template",
    default=None,
    type=click.Path(),
    help="Name of interpolate_variables.in file. If None, will use an internal version with nday as template.",
)
@click.option(
    "--nday",
    default=None,
    type=int,
    help="Number of days to process. If None, param.nml is parsed in tropic_dir and the full length of the run is used.",
)
@click.option(
    "--write_clinic",
    default=True,
    type=bool,
    help="If true, the file will be moved to run_dir. Otherwise, it will be done in place in outputs.",
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
    write_clinic,
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
        write_clinic,
    )


if __name__ == "__main__":
    interpolate_uv3d_cli()
