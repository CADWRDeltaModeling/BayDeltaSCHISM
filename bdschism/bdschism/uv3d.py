import argparse
from schimpy import param
import bdschism.settings as config
import subprocess
import os
import shutil
import errno


def uv3d(
    param_nml="param.nml",
    bg_dir=".",
    bg_output_dir=None,
    fg_dir=None,
    hgrid_bg="hgrid.gr3",
    hgrid_fg="hgrid.gr3",
    vgrid_bg="vgrid.in.2d",
    vgrid_fg="vgrid.in.3d",
    interp_template=None,
    nday=None,
    write_clinic=True,
):
    """Runs interpolate_variables utility to generate uv3d.th.nc.

    This is based on facilitating a barotropic run, but with a a modified
    interp_template file you could do far field to near field cases.

    The default, run in the barotropic directory (one level above /outputs), will run without input

    Parameters
    ----------

    param_nml : str
        Name of parameter file

    bg_dir : str
        Name of background simulation (e.g. larger or barotropic) directory

    bg_output_dir :str
        Name of output directory in background. If None, will try outputs.tropic then outputs

    fg_dir : str
        Name of foreground baroclinic run directory. If None, will copy from tropic_dir

    hgrid_bg : str
        Name of hgrid.gr3 file in tropic_, which will be linked to bg.gr3 This will almost never change,
        but could if you use a larger barotropic mesh which is a recommended practice.

    hgrid_fg : str
        Name of hgrid.gr3 file in clinic_, which will be linked to fg.gr3. This will almost never change,
        but could if you use a smaller baroclinic mesh.

    vgrid_bg : str
        Name of the (2D barotropic) vgrid file

    vgrid_fg : str
        Name of the (3D) baroclinic vgrid file

    interp_template : [None | str]
        Name of interpolate_variables.in file. If None, will use an internal version with nday as template.

    nday :  int
        Number of days to process.  If None, param.nml is parsed in tropic_dir and the
        full length of the run is used

    write_clinic: bool
        If true, the file will be moved to run_dir. Otherwise will be done in place in outputs


    Notes
    -----

    Side effect is uv3D.th.nc, which may be moved to the baroclinic directory. The file
    uv3D.th.nc is produced by the interpolate_variables script, the current version
    of which is interpolate_variables7 (can move to config later). It expects four links,
    bg.gr3 -> tropic hgrid.gr3, fg.gr3 -> clinic/hgrid.gr3, vgrid.bg -> vgrid.in.2d and
    vgrid.fg -> vgrid.in.3d. The defaults will take care of the normal case. There
    are reasonable extensions (supersetting the grid for tropic and near field modeling)
    that are in use and make it reasonable to prepare for modifications. The script also
    expects a file called interpolate_variables.in, which you can find in the templates
    and which doesn't normally change for our standard runs except for the number of days
    (second arg on the first line). This could of course be inferred from param.nml.tropic.

    """

    # interp_exe = "interpolate_variables7"

    # This content for the file interpolate_variables.in will work with the interpolate_variables
    # for all normal runs.
    # The user would want to change if they are isolating a subdomain
    # interpolate_template = f"3 {nday}  !ifile ndays. ifile=1: generate elev2D.th; =2: salt3D.th and temp3D.th; =3: uv3D.th); ndays is the # of days needed;\n1 1   !total # of boundary segments that need *3D.th, followed by list of boundary segment indices\n0     !0: normal; 1: more outputs for debug"


def create_arg_parser():
    """Create an argument parser"""
    parser = argparse.ArgumentParser(
        description="Runs interpolate_variables utility to generate uv3d.th.nc. "
    )
    parser.add_argument(
        "--bg_dir",
        default=".",
        help="Name of background simulation (e.g. larger or barotropic) directory (str)",
    )
    parser.add_argument(
        "--bg_output_dir",
        default=None,
        help="Name of output directory in background. If None, will try outputs.tropic then outputs (str)",
    )
    parser.add_argument(
        "--fg_dir",
        default=None,
        help="Name of foreground baroclinic run directory. If None, will copy from tropic_dir (str)",
    )
    parser.add_argument(
        "--hgrid_bg",
        default="hgrid.gr3",
        help="Name of hgrid.gr3 file in tropic_, which will be linked to bg.gr3 This will almost never change "
        "but could if you use a larger barotropic mesh which is a recommended practice (str)",
    )
    parser.add_argument(
        "--hgrid_fg",
        default="hgrid.gr3",
        help="Name of hgrid.gr3 file in clinic_, which will be linked to fg.gr3. This will almost never change, "
        "but could if you use a smaller baroclinic mesh (str)",
    )
    parser.add_argument(
        "--vgrid_bg",
        default="vgrid.in.2d",
        help="Name of the (2D barotropic) vgrid file  (str)",
    )
    parser.add_argument(
        "--vgrid_fg",
        default="vgrid.in.3d",
        help="Name of the (3D) baroclinic vgrid file  (str)",
    )
    parser.add_argument(
        "--interp_template",
        default=None,
        help="Name of interpolate_variables.in file. If None, will use an internal version with nday as template (str)",
    )
    parser.add_argument(
        "--nday",
        default=None,
        help="Number of days to process.  If None, param.nml is parsed in tropic_dir and "
        "the full length of the run is used (int)",
    )
    parser.add_argument(
        "--param_nml", type=str,
        default=None,
        help="Name of parameter file (str)",
    )    
    parser.add_argument(
        "--write_clinic",
        default=True,
        help="If true, the file will be moved to run_dir. Otherwise will be done in place in outputs",
    )

    return parser

def main():
    """Main function"""
    parser = create_arg_parser()
    args = parser.parse_args()
    param_nml = args.param_nml
    bg_dir = args.bg_dir
    bg_output_dir = args.bg_output_dir
    fg_dir = args.fg_dir
    hgrid_bg = args.hgrid_bg
    hgrid_fg = args.hgrid_fg
    vgrid_bg = args.vgrid_bg
    vgrid_fg = args.vgrid_fg
    interp_template = args.interp_template
    nday = args.nday
    write_clinic = args.write_clinic

    #
    # Validate directory paths
    #

    # bg_dir
    try:
        assert os.path.exists(bg_dir)
    except AssertionError:
        print("Path does not exist: " + bg_dir)
    bg_dir = os.path.abspath(bg_dir)

    # bg_output_dir
    if bg_output_dir is None:
        if os.path.exists(os.path.join(bg_dir, "outputs.tropic")):
            bg_output_dir = "outputs.tropic"
        elif os.path.exists(os.path.join(bg_dir, "outputs")):
            bg_output_dir = "outputs"
        else:
            print("Invalid path:" + bg_output_dir + "(Default is outputs.tropic or outputs)")
            raise ValueError

    # Directory in which interpolate_variables executable will be run
    interp_dir = os.path.join(bg_dir, bg_output_dir)
    try:
        assert os.path.exists(interp_dir)
    except AssertionError:
        print("Path does not exist: " + interp_dir)

    # fg_dir
    if fg_dir is None:
        fg_dir = bg_dir
    #
    # Make sure "interpolate_variables.in" is present
    #
    if interp_template is None:
        print("interpolate_variables.in is not specified. Extracting nday from user input.")
        if nday is None:
            print("nday not specified in user input. Extracting nday from parm.nml")
            #
            # Parse param.nml
            #
            if param_nml is None:
                param_nml = os.path.join(bg_dir, "param.nml")
            params = param.read_params(param_nml)            
            nday = params["rnday"]

        f = open(os.path.join(interp_dir, "interpolate_variables.in"), "w")
        f.write(f"3 {nday}\n")
        f.write("1 1\n")
        f.write("0")
        f.close()

    else:
        if os.path.abspath(interp_template) == os.path.join(
            interp_dir, "interpolate_variables.in"
        ):
            pass

        else:
            print(
                os.path.abspath(interp_template)
                + "\ncopied to\n"
                + os.path.join(interp_dir, "interpolate_variables.in")
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
                Exception("The first parameter in the interpolate_variables.in file must be 3 for uv3d.th.nc")

    #
    # Create symbolic links
    #
    config.create_link(os.path.join(bg_dir, hgrid_bg), os.path.join(interp_dir, "bg.gr3"))
    config.create_link(os.path.join(bg_dir, hgrid_fg), os.path.join(interp_dir, "fg.gr3"))
    config.create_link(os.path.join(bg_dir, vgrid_bg), os.path.join(interp_dir, "vgrid.bg"))
    config.create_link(os.path.join(bg_dir, vgrid_fg), os.path.join(interp_dir, "vgrid.fg"))

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
    print(f"Running `interpolate_variables8` in {bg_output_dir}")
    os.chdir(bg_output_dir)
    command = "module load intel/2024.0 hmpt/2.29 hdf5/1.14.3 netcdf-c/4.9.2 netcdf-fortran/4.6.1 schism/5.11.1 \n interpolate_variables8"
    os.system(command)

if __name__ == "__main__":

    main()
