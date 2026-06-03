import numpy as np
from schimpy.laplace_smooth_data import laplace_smooth_data2
import numpy as np

def _gg_taper(mesh, nodes_sel,
              xgg=542699., ygg=4183642.,
              zero_dist=30_000.,
              full_dist=45_000.):
    x = mesh.nodes[:, 0]
    y = mesh.nodes[:, 1]
    r = np.sqrt((x - xgg)**2 + (y - ygg)**2)

    w = np.clip((r - zero_dist) / (full_dist - zero_dist), 0.0, 1.0)

    out = np.zeros(mesh.nodes.shape[0])
    out[nodes_sel] = w[nodes_sel]
    return out


def ocean_bathy_smooth_blend(mesh, nodes_sel,
                             zero_dist=25_000.,
                             full_dist=40_000.,
                             kappa=0.25,      # 0.1
                             dt=1.0,
                             iter_total=800):  # 180
    z0 = mesh.nodes[:, 2].copy()
    zs = laplace_smooth_data2(mesh, z0, kappa=kappa, dt=dt, iter_total=iter_total)

    w = _gg_taper(mesh, nodes_sel, zero_dist=zero_dist, full_dist=full_dist)
    zout = (1.0 - w) * z0 + w * zs

    return zout[nodes_sel]


def ocean_manning_ramp(mesh, nodes_sel,
                       zero_dist=30_000.,
                       full_dist=45_000.,
                       n_inner=0.023,     # Pretty good 0.0245, 0.0255. What about n_inner = 0.024, n_outer = 0.026?
                       n_outer=0.0255):
    w = _gg_taper(mesh, nodes_sel, zero_dist=zero_dist, full_dist=full_dist)
    n = n_inner + w * (n_outer - n_inner)

    return n[nodes_sel]