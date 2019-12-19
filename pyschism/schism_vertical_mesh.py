# -*- coding: utf-8 -*-
"""
SchismVerticalMesh class with a reader
"""

import numpy as np
import warnings
import os

__all__ = ['read_vmesh', ]


class SchismVerticalMesh(object):
    """ SchismVerticalMesh abstract class
    """

    def __init__(self):
        pass

    def n_vert_levels(self):
        return 0


class SchismSzVerticlMesh(SchismVerticalMesh):
    """ Memory model of S-Z hybrid grid for vertical grid
    """

    def __init__(self):
        super(SchismSzVerticlMesh, self).__init__()
        self.ivcor = 2
        self.reset()

    def reset(self):
        """ Reset variables
        """
        self.param = {}
        self.sigma = None
        self.ztot = None
        self.c_s = None
        self._z = None

    def n_vert_levels(self):
        return self.sigma.shape[0]


class SchismLocalVerticalMesh(SchismVerticalMesh):
    """ Memory model of localized vertical grid
    """

    def __init__(self, *args, **kwargs):
        super(SchismLocalVerticalMesh, self).__init__()
        self.ivcor = 1
        self.reset()
        if len(args) == 0:
            pass
        elif len(args) == 1:
            self.init(args[0])

    def init(self, sigma):
        self.reset()
        self.build_kbps(sigma)

    def reset(self):
        """ Reset variables
        """
        self.param = {}
        self.sigma = None
        self.kbps = None
        self._z = None

    def n_vert_levels(self):
        return self.sigma.shape[1]

    def build_kbps(self, sigma):
        """ Build a vertical mesh from sigma

            Parameters
            ----------
            sigma: np.array
            nvrt: int
                number of the total levels
        """
        self.sigma = sigma
        nan = np.isnan(self.sigma)
        self.kbps = (self.n_vert_levels() -
                     np.apply_along_axis(lambda x: np.argmax(x > 0), 1, nan))
        self.kbps[self.kbps == self.n_vert_levels()] = 0

    def build_z(self, mesh, elev=0.):
        """ Build vertical z-coord with the mesh

            Parameters
            ----------
            mesh: schism_mesh.SchismMesh
                Corresponding horizontal mesh
            elev: np.ndarray, optional
                Reference surface elevation

            Returns
            -------
            np.ndarray
                Vertical coordinates in the fashion in SCHISM
                the shape of the array is (n_nodes, n_vert_levels)
                z values from the surface are filled from the right.
                
            todo: behavior with dry locations not described
        """
        if self.sigma is None:
            raise ValueError("Sigma values are not provided")
        if type(elev) == float:
            elev = np.ones((mesh.n_nodes(), ))*elev
        n_vert = self.n_vert_levels()
        self._z = np.empty((mesh.n_nodes(), n_vert))
        for i, (node, eta) in enumerate(zip(mesh.nodes, elev)):
            self._z[i] = -node[2]
            self._z[i, self.kbps[i]:] = (
                eta+(eta + node[2]) * self.sigma[i, :n_vert - self.kbps[i]])
        return self._z


class SchismVerticalMeshIoFactory(object):
    registered_readers = {'sz': 'SchismSzVerticalMeshReader',
                          'local': 'SchismLocalVerticalMeshReader'}
    registered_writers = {'local': 'SchismLocalVerticalMeshWriter'}

    def get_reader(self, name):
        if name in self.registered_readers:
            return globals()[self.registered_readers[name]]()
        else:
            raise ValueError("Not in SchismVerticalMeshIoFactory")

    def get_writer(self, name):
        if name in self.registered_readers:
            return globals()[self.registered_writers[name]]()
        else:
            raise ValueError("Not in SchismVerticalMeshIoFactory")


class SchismSzVerticalMeshReader(object):

    def __init__(self, logger=None):
        self.logger = logger
        self._vgrid = None

    def _check_first_group(self):
        """ Check the first group
        """
        vgrid = self._vgrid
        nvrt = vgrid.param['nvrt']
        if nvrt < 3:
            raise ValueError("Wrong nvrt: nvrt < 3")
        kz = vgrid.param['kz']
        if kz < 1:
            raise ValueError("Wrong kz: kz < 1")
        if kz > nvrt - 2:
            raise ValueError("Wrong kz: kz > nvrt - 2")
        h_s = vgrid.param['h_s']
        if h_s < 10.:
            raise ValueError("Wrong h_s: h_s < 10")

    def _check_second_group(self):
        """ Check the second group
        """
        vgrid = self._vgrid
        h_c = vgrid.param['h_c']
        if h_c < 5.:
            raise ValueError("Wrong h_c: h_c < 5.")
        theta_b = vgrid.param['theta_b']
        if theta_b < 0.:
            raise ValueError("Wrong theta_b: theta_b < 0.")
        if theta_b > 1.:
            raise ValueError("Wrong theta_b: theta_b > 1.")
        theta_f = vgrid.param['theta_f']
        if theta_f <= 0.:
            raise ValueError("Wrong theta_f: theta_f <= 0.")

    def read(self, fpath='vgrid.in'):
        """ Read vgrid.in
        """
        vgrid = SchismSzVerticlMesh()
        self._vgrid = vgrid
        with open(fpath, 'r') as fin:
            ivcor = int(fin.readline().split()[0])
            nvrt, kz, h_s = list(map(float, fin.readline().split()[:3]))
            nvrt = int(nvrt)
            vgrid.param['nvrt'] = nvrt
            kz = int(kz)
            vgrid.param['kz'] = kz
            vgrid.param['h_s'] = h_s
            self._check_first_group()
            fin.readline()  # Z levels
            ztot = []
            for _ in range(kz):
                tkn = fin.readline().split()
                k = int(float(tkn[0]))
                z = float(tkn[1])
                if k > 1:
                    if z <= ztot[-1] or z > -h_s:
                        raise ValueError("z level inverted")
                ztot.append(z)
            if ztot[-1] != -h_s:
                warnings.warn("The last z level must be h_s")
                ztot[-1] = -h_s
            vgrid.ztot = ztot

            fin.readline()  # S levels
            h_c, theta_b, theta_f = list(map(float, fin.readline().split()[:3]))
            vgrid.param['h_c'] = h_c
            vgrid.param['theta_b'] = theta_b
            vgrid.param['theta_f'] = theta_f
            self._check_second_group()
            nsig = nvrt - len(ztot) + 1
            sigma = []
            for _ in range(nsig):
                tkn = fin.readline().split()
                k = int(float(tkn[0]))
                s = float(tkn[1])
                if k > 1:
                    if s <= sigma[-1]:
                        raise ValueError("Wrong sigma: sigma level inverted")
                    if s > 0.:
                        raise ValueError("Wrong sigma: simga > 0")
                sigma.append(s)
            if sigma[0] != -1.:
                warnings.warn("The first sigma must be -1")
                sigma[0] = -1.
            if sigma[-1] != 0.:
                warnings.warn("The last sigma must be 0")
                sigma[-1] = 0.
            sigma = np.array(sigma)
            vgrid.sigma = sigma
            c_s = (1. - theta_b) * np.sinh(theta_f * sigma) / np.sinh(theta_f) \
                + theta_b * (np.tanh(theta_f * (sigma + 0.5))
                             - np.tanh(theta_f * 0.5)) * 0.5 / np.tanh(theta_f * 0.5)
            vgrid.c_s = c_s
        return vgrid


class SchismLocalVerticalMeshReader(object):

    def __init__(self, logger=None):
        self.logger = logger
        self._vgrid = None

    def _check_first_group(self):
        """ Check the first group
        """
        vgrid = self._vgrid
        nvrt = vgrid.param['nvrt']
        if nvrt < 3:
            raise ValueError("Wrong nvrt: nvrt < 3")
        kz = vgrid.param['kz']
        if kz < 1:
            raise ValueError("Wrong kz: kz < 1")
        if kz > nvrt - 2:
            raise ValueError("Wrong kz: kz > nvrt - 2")
        h_s = vgrid.param['h_s']
        if h_s < 10.:
            raise ValueError("Wrong h_s: h_s < 10")

    def _check_second_group(self):
        """ Check the second group
        """
        vgrid = self._vgrid
        h_c = vgrid.param['h_c']
        if h_c < 5.:
            raise ValueError("Wrong h_c: h_c < 5.")
        theta_b = vgrid.param['theta_b']
        if theta_b < 0.:
            raise ValueError("Wrong theta_b: theta_b < 0.")
        if theta_b > 1.:
            raise ValueError("Wrong theta_b: theta_b > 1.")
        theta_f = vgrid.param['theta_f']
        if theta_f <= 0.:
            raise ValueError("Wrong theta_f: theta_f <= 0.")

    def read(self, fpath='vgrid.in'):
        """ Read vgrid.in
        """
        vgrid = SchismLocalVerticalMesh()
        self._vgrid = vgrid
        with open(fpath, 'r') as fin:
            ivcor = int(fin.readline().split()[0])
            nvrt = int(fin.readline().strip().split()[0])
            vgrid.param['nvrt'] = nvrt
            sigmas = list()
            kbps = list()
            while True:
                tkns = fin.readline().strip().split()
                if len(tkns) < 1:
                    break
                kbp = int(tkns[1]) - 1
                kbps.append(kbp)
                sigma = np.full((nvrt,), np.nan)
                sigma[:nvrt - kbp] = list(map(float, tkns[2:nvrt - kbp + 2]))
                sigmas.append(sigma)
            vgrid.sigma = np.array(sigmas)
            vgrid.kbps = np.array(kbps)
        return vgrid


class SchismLocalVerticalMeshWriter(object):

    def __init__(self, logger=None):
        self.logger = logger

    def write(self, vmesh, fpath='vgrid.in'):
        """ Write vgrid.in
        """
        with open(fpath, 'w') as f:
            buf = "{}\n".format(vmesh.ivcor)
            f.write(buf)
            n_max_levels = vmesh.n_vert_levels()
            buf = "{}\n".format(n_max_levels)
            f.write(buf)
            for i in range(len(vmesh.sigma)):
                kbps = vmesh.kbps[i]
                n_levels = n_max_levels - kbps
                buf = "{}\t{}\t".format(i + 1, kbps + 1)
                buf += '\t'.join(['{:.6f}'.format(d)
                                  for d in vmesh.sigma[i][:n_levels]])
                buf += '\n'
                f.write(buf)


def read_vmesh(fpath_vmesh):
    """ Read a vgrid file
    """
    if fpath_vmesh is None:
        raise ValueError("File not given")
    if not os.path.exists(fpath_vmesh):
        raise ValueError("File not found: %s" % fpath_vmesh)
    with open(fpath_vmesh, 'r') as f:
        ivcor = int(f.readline().strip().split()[0])

    if ivcor == 1:
        reader = SchismVerticalMeshIoFactory().get_reader('local')
        return reader.read(fpath_vmesh)
    elif ivcor == 2:
        reader = SchismVerticalMeshIoFactory().get_reader('sz')
        return reader.read(fpath_vmesh)
    else:
        raise ValueError('Unsupported vgrid type')


def write_vmesh(vmesh, fpath_vmesh='vgrid.in'):
    if vmesh.ivcor == 1:
        writer = SchismVerticalMeshIoFactory().get_writer('local')
        writer.write(vmesh, fpath_vmesh)
    else:
        raise ValueError('Unsupported vgrid type')
