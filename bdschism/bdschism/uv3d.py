import argparse


def uv3d(
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

    The default, run in the barotropic directory, will run without input

    Parameters
    ----------

    bg_dir : str
        Name of background simulation (e.g. larger or barotropic) directory

    bg_output_dir :str
        Name of output directory in background. If None, will try outputs.tropic then outputs

    fg_dir : str
        Name of foreground oclinic run directory. If None, will copy from tropic_dir

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
        help="Name of foreground oclinic run directory. If None, will copy from tropic_dir (str)",
    )
    parser.add_argument(
        "--hgrid_bg",
        default="hgrid.gr3",
        help="Name of hgrid.gr3 file in tropic_, which will be linked to bg.gr3 This will almost never change "
        "but could if you use a larger barotropic mesh which is a recommended practice (str)",
    )
    parser.add_argument(
        "--hgrid_fg",
        default=None,
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
        "--write_clinic",
        default=True,
        help="If true, the file will be moved to run_dir. Otherwise will be done in place in outputs",
    )

    return parser


def main():
    """Main function"""
    parser = create_arg_parser()
    args = parser.parse_args()
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


if __name__ == "__main__":
    main()
