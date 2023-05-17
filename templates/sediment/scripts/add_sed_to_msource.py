""" Add the concentrations of suspended sediments in the source flow (or
    return flow) in msource.th.
"""
import numpy as np
import pandas as pd
import click


@click.command()
@click.option('--msource_input', default='msource.th',
              help='Original msource.th without sediment values')
@click.option('--msource_output', default='msource_sed.th',
              help='Output msource.th with sediment values')
@click.option('--n_sediments', type=int,
              help='Number of sediment classes')
def main(msource_input, msource_output, n_sediments):
    msource_in = pd.read_csv(msource_input, header=None, delim_whitespace=True)
    n_sources = (len(msource_in.columns) - 1) // 2
    n_rows = len(msource_in)
    fill_value = -9999.0
    print(n_rows, n_sources)
    msource_added = pd.DataFrame(np.full((n_rows, n_sources * n_sediments),
                                         fill_value))
    msource_out = pd.concat([msource_in, msource_added], axis=1)
    msource_out.to_csv(msource_output, sep=' ', float_format='%.2f',
                       header=None, index=False)


if __name__ == '__main__':
    main()
