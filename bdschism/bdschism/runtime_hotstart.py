import subprocess
import os
import re
import math
import shutil

import click
from schimpy.param import read_params


def tail(f, n, offset=0):
    if isinstance(n, int):
        n = str(n)
    if isinstance(offset, int):
        offset = str(offset)
    proc = subprocess.Popen(["tail", "-n", n + offset, f], stdout=subprocess.PIPE)
    lines = proc.stdout.readlines()
    return b"".join(lines[int(offset) :])


class rst_fm_hotstart(object):

    def __init__(self, mod_dir, param, iteration=None):
        self.mod_dir = mod_dir
        self.param = param

        if iteration is None:
            self.get_ts_info()
            self.get_mirror_crash()
            self.get_last_hotstart()

    def get_ts_info(self):

        self.start_time = self.param.get_run_start()
        self.interval = self.param["dt"]  # get computational interval in seconds
        self.nspool = self.param["nspool"]  # output is done every nspool steps
        self.ihfskip = self.param[
            "ihfskip"
        ]  # new output stack is opened every ihfskip steps
        self.nhot_write = self.param[
            "nhot_write"
        ]  # hotstart file is written every nhot_write time steps

    def get_mirror_crash(self):

        mirrortail = tail(os.path.join(self.mod_dir, "outputs/mirror.out"), 40)
        mmatches = re.findall(r"TIME STEP=\s+(\d+);", str(mirrortail))

        self.crash_timestep = int(max(mmatches))
        print(f"\tcrash_timestep = {self.crash_timestep}")

    def get_last_hotstart(self):

        num_timesteps = (
            math.floor(self.crash_timestep / self.nhot_write) * self.nhot_write
        )

        # hotstart files are written as hotstart_[process_id]_[time_step].nc
        self.last_hotstart = str(int(num_timesteps))
        print(f"last_hotstart = {self.last_hotstart}")

    def combine_hotstart(self, iteration, machine="linux", printout=False):

        os.chdir("outputs")
        if machine.lower() == "linux":
            modld = f"module purge; module load intel/2024.0 hmpt/2.29 hdf5/1.14.3 netcdf-c/4.9.2 netcdf-fortran/4.6.1 schism/5.11.1; "
        else:
            modld = ""
        command = f"{modld}combine_hotstart7 --iteration {iteration}"
        print(f"\t{command}")

        ret = subprocess.run(command, capture_output=True, shell=True)
        os.chdir("../")

        if printout:
            print(ret.stdout.decode())

    def param_mod(self, iteration, param_in="param.nml.clinic"):

        # os.chdir(os.path.join(self.mod_dir))

        # replace hotstart variables ihot
        with open(param_in, "r") as file:
            param_text = file.read()
        param_out = re.sub(r"ihot = \d+", "ihot = 2", param_text)

        param_fn_out = f"{param_in}.hot"
        with open(param_fn_out, "w") as file:
            file.write(param_out)

        # copy the hotstart file
        hotstart_fn = f"outputs/hotstart_it={iteration}.nc"
        hotstart_link_fn = "hotstart.nc"
        shutil.copyfile(hotstart_fn, hotstart_fn.replace("outputs/", ""))

        # copy the mirror.out file
        mirr_in = "outputs/mirror.out"
        if os.path.exists(mirr_in):
            shutil.copyfile(
                mirr_in, os.path.join(self.mod_dir, f"{mirr_in}.pre-{iteration}")
            )


@click.command()
@click.option(
    "--mod_dir",
    default="./",
    type=click.Path(exists=True, file_okay=False),
    help="Directory for the model. Default is current directory.",
)
@click.option(
    "--baro",
    default=None,
    help='"clinic" or "tropic" mode. Looks at relevant param.nml. If not provided, will look for param.nml in mod_dir.',
)
@click.option(
    "--iteration",
    default=None,
    type=int,
    help="Iteration to combine. If None then the last iteration from the mirror.out is used.",
)
@click.option(
    "--machine",
    default="linux",
    show_default=True,
    type=str,
    help="linux or azure, decides which command to submit to cli. Default is linux",
)
@click.option("--no-combine", is_flag=True, help="Disable combine mode")
@click.help_option("-h", "--help")  # Add the help option at the group level
def restart_from_hotstart_cli(mod_dir, baro, iteration, machine, no_combine):
    """Combine hotstarts from SCHISM run."""
    if baro is None:
        try:
            param = read_params(os.path.join(mod_dir, "param.nml"))
            baro = param.get_baro()
        except FileNotFoundError:
            raise FileNotFoundError(
                "param.nml not found in mod_dir. Please specify --baro option."
            )
    else:
        param_fn = os.path.join(mod_dir, f"param.nml.{baro}")
        param = read_params(param_fn)

    rfh = rst_fm_hotstart(mod_dir, param, iteration=iteration)
    if iteration is None:
        iteration = rfh.last_hotstart
    print(f"Using iteration {iteration}")

    if not no_combine:
        rfh.combine_hotstart(iteration, machine=machine)
        rfh.param_mod(iteration, param_in=f"param.nml.{baro}")
        print(f"Combined Hotstart files for timestep {iteration}")
    else:
        print(f"Did not combine hotstart files for timestep {iteration}")


if __name__ == "__main__":
    restart_from_hotstart_cli()
