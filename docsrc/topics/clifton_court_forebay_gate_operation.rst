####################################
Clifton Court Forebay Gate Operation Prediction (ccfb_gate.th)
####################################

In case of syntheic hydrolgic condition such as planning mode, we need to estimate the opening 
height of the Clifton Court Forebay (CCFB) radial gates. We estimates the opening height of the 
CCFB radial gates based on SWP export, eligible intervals for opening and priority level, maximum gate height allowed,
OH4 stage level, CVP pump rate, and other operational rules for a given period.

    Gate Opening Conditions
    -----------------------
    - **Priority Eligibility**: The gate opens only if priority eligibility criteria are met.
    - **Water Level Difference**: The gate opens if the water level outside the forebay is higher than the water level inside.

    Early Gate Closure
    ------------------

    The gate will close early if the volume of water above the 2 ft contour is sufficient to cover
    the remaining water allocation for the day. This simulates field operations where operators aim to
    maintain water elevation as close to 2 ft as possible.

    Gate Remains Open
    -----------------

    The gate will remain open if the volume of water above the 2 ft contour is insufficient to cover
    the daily allocation, preventing the water level inside the forebay from dropping too low.

    Gate Height Calculation
    -----------------------
    - The default gate height is 16 ft, but a maximum height based on export level is applied.
    - The height is adjusted to prevent flow from exceeding 12,000 cfs, reflecting operational constraints.
    - The gate height is calculated using a simplified version of the flow rating equation:

        Gate Height = 11 × (Head)^-0.3 - 0.5

      where Head = Water level upstream - Water level in the reservoir.

Core Function: `ccf_gate()`
============================

The main programmatic interface for gate height generation is the :py:func:`bdschism.ccf_gate_height.ccf_gate` function.

.. py:function:: ccf_gate(sdate, edate, dest, astro_ts, swp_ts, cvp_ts, sffpx_elev_ts, plot=False, save_intermediate=False)

    Generate the predicted gate height for the Clifton Court Forebay.

    **Parameters**

    - **sdate** (*datetime.datetime*): Start date for simulation
    - **edate** (*datetime.datetime*): End date for simulation
    - **dest** (*str*): Destination file path for output (e.g., "ccfb_gate_syn.th")
    - **astro_ts** (*pd.DataFrame*): Astronomical OH4 tide time series
    - **swp_ts** (*pd.DataFrame*): SWP (State Water Project) export time series in cfs
    - **cvp_ts** (*pd.DataFrame*): CVP (Central Valley Project) pump rate time series in cfs
    - **sffpx_elev_ts** (*pd.DataFrame*): SFFPX (San Francisco Bay near Pier IX) elevation time series
    - **plot** (*bool, optional*): If True, displays a plot of the predicted gate height (default: False)
    - **save_intermediate** (*bool, optional*): If True, saves intermediate priority time series to files (default: False)

    **Returns**

    The function saves the predicted gate height data to a CSV file with the following columns:

    - **height**: Gate opening height in meters
    - **install**: Installation number (1 for CCFB gates)
    - **ndup**: Number of duplicates (5)
    - **op_down**: Operating opening rate (1.0 m/s)
    - **op_up**: Operating closing rate (0.0 m/s)
    - **elev**: Gate sill elevation (-4.0244 m, NAVD88)
    - **width**: Gate width (6.096 m)

    **Example Usage in Python**

    .. code-block:: python

        import datetime as dtm
        import pandas as pd
        from bdschism.ccf_gate_height import ccf_gate
        from dms_datastore.read_ts import read_ts

        # Define date range
        sdate = dtm.datetime(2021, 1, 1)
        edate = dtm.datetime(2021, 5, 1)

        # Load required time series data
        astro_ts = read_ts(
            'W:/repo/continuous/processed/dms_oh4_elev@harmonic_2001_2025.csv',
            force_regular=True
        ).squeeze()
        swp_ts = read_ts('../ccfb_gate/flux.th')['swp']
        cvp_ts = read_ts('../ccfb_gate/flux.th')['cvp']
        sffpx_elev_ts = read_ts(
            'W:/repo/continuous/processed/dms_sffpx_elev_2000_2026.csv'
        )

        # Generate gate heights
        ccf_gate(
            sdate,
            edate,
            dest='./ccfb_gate_syn.th',
            astro_ts=astro_ts,
            swp_ts=swp_ts,
            cvp_ts=cvp_ts,
            sffpx_elev_ts=sffpx_elev_ts,
            plot=True,
            save_intermediate=False
        )

Command Line Interface
======================

The :py:func:`bdschism.ccf_gate_height.ccf_gate_cli` function provides a command-line interface for generating gate heights.

**Command Syntax**

.. code-block:: bash

    ccf_gate_height [OPTIONS]

**Required Options**

- ``--sdate TEXT``: Start date in YYYY-MM-DD format (e.g., 2021-01-01)
- ``--edate TEXT``: End date in YYYY-MM-DD format (e.g., 2021-05-01)
- ``--oh4-astro-datasrc TEXT``: Path to OH4 astronomical tide data (file path or CSV file)
- ``--export-datasrc TEXT``: Path to export flux file (typically flux.th from SCHISM)
- ``--sffpx-datasrc TEXT``: Path to SFFPX elevation data (file/pattern or repository name like "screened")

**Optional Options**

- ``--output PATH``: Output file path (default: ./ccfb_gate_syn.th)
- ``--length-unit {ft,m}``: Output gate-height length unit (default: ft)
- ``--plot``: Flag to plot predicted gate height (default: False)
- ``--save-intermediate, -si``: Flag to save intermediate priority time series (default: False)
- ``-h, --help``: Show help message

**Example Usage**

.. code-block:: bash

    ccf_gate_height \
        --sdate 2021-01-01 \
        --edate 2021-05-01 \
        --output ./ccfb_gate_syn.th \
        --oh4-astro-datasrc W:/repo/continuous/processed/dms_oh4_elev@harmonic_2001_2025.csv \
        --export-datasrc ../ccfb_gate/flux.th \
        --sffpx-datasrc W:/repo/continuous/processed/dms_sffpx_elev_2000_2026.csv \
        --plot

This command will:

1. Read the astronomical tide data from the specified OH4 source
2. Extract SWP and CVP pumping rates from the flux file
3. Load SFFPX elevation data for tidal analysis
4. Generate predicted gate heights for the period 2021-01-01 to 2021-05-01
5. Save the output to ``./ccfb_gate_syn.th``
6. Display an interactive plot of the predicted gate heights

**Output File Format**

The output file is a space-separated text file with the following structure:

.. code-block:: text

    datetime height install ndup op_down op_up elev width
    2021-01-01T00:00 0.000 1 5 1.0 0.0 -4.024 6.096
    2021-01-01T00:02 0.152 1 5 1.0 0.0 -4.024 6.096
    ...

Where:

- **datetime**: Time stamp in ISO format (YYYY-MM-DDTHH:MM)
- **height**: Gate opening height in meters (or feet if ``--length-unit ft`` is specified)
- Other columns are SCHISM-specific parameters for radial gate operation

Data Requirements
=================

**OH4 Astronomical Tide Data**

- Regular time series (typically 15-minute or hourly intervals)
- Water elevation in meters, NAVD88
- Should cover the analysis period plus a few days margin for computational stability

**Export (SWP/CVP) Data**

- SCHISM ``.th`` format or CSV with datetime index
- Pumping rates in cubic meters per second (will be converted to cfs internally)
- Should include both "swp" and "cvp" columns/records

**SFFPX Elevation Data**

- Regular time series of San Francisco Bay elevation
- Used for tidal phase analysis and priority scheduling
- Can be obtained from DMS datastore or water level monitoring stations

Notes
=====

- The module uses a 2-minute time step for internal calculations by default
- Gate heights are smoothed using a 6-minute relaxation period for realistic gate operation
- The output time step is 2 minutes, coarsened from the high-frequency internal calculations
- Missing or NaN values in input time series will cause errors; ensure data is properly filled or interpolated before processing