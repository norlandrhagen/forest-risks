import os
import warnings

import numpy as np
import rioxarray
import xarray as xr

from carbonplan_forest_risks import load
from carbonplan_forest_risks.utils import get_store

# flake8: noqa


warnings.filterwarnings('ignore')

impacts_to_consolidate = ['insects', 'drought']  #'fire',
account_key = os.environ.get('BLOB_ACCOUNT_KEY')

# specify the kind of mask you want to use
website_mask = (
    load.nlcd(store="az", year=2001).sel(band=[41, 42, 43, 90]).sum("band") > 0.5
).astype("float")
gcms = [
    ("ACCESS-CM2", "r1i1p1f1"),
    ("ACCESS-ESM1-5", "r10i1p1f1"),
    ("MRI-ESM2-0", "r1i1p1f1"),
    ("MIROC-ES2L", "r1i1p1f2"),
    ("MPI-ESM1-2-LR", "r10i1p1f1"),
    ("CanESM5-CanOE", "r3i1p2f1"),
]

if 'fire' in impacts_to_consolidate:
    run_name = 'v3_high_res'

    all_scenarios_ds = xr.Dataset()
    for scenario in ['ssp245', 'ssp370', 'ssp585']:
        ds = xr.Dataset()
        for (cmip_model, member) in gcms:
            path = get_store(
                'carbonplan-scratch',
                'data/fire_future_{}_{}_{}.zarr'.format(run_name, cmip_model, scenario),
                account_key=account_key,
            )
            ds[cmip_model] = (
                ['year', 'y', 'x'],
                xr.open_zarr(
                    path,  # consolidated=True
                )
                .groupby("time.year")
                .sum()
                .coarsen(year=10)
                .mean()
                .compute()['{}_{}'.format(cmip_model, scenario)],
            )

        # average across all variables
        ds = ds.assign_coords(
            {
                "x": website_mask.x,
                "y": website_mask.y,
                'year': list(map(lambda x: str(x), np.arange(1975, 2100, 10))),
            }
        ).where(website_mask)
        all_scenarios_ds[scenario] = ds.to_array(dim="vars").mean(dim="vars")

    out_path = get_store('carbonplan-scratch', 'data/website/fire.zarr', account_key=account_key)
    all_scenarios_ds.to_zarr(out_path)

if 'insects' in impacts_to_consolidate:
    insect_url_template = "https://carbonplan.blob.core.windows.net/carbonplan-scratch/from_bill/InsectProjections_3-30/InsectModelProjection_{}.{}.{}-{}.{}-v14climate_3-30-2021.tif"
    ds = load.impacts(insect_url_template, website_mask, mask=website_mask) * 100
    ds = (
        ds.to_array(dim="vars")
        .mean("vars")
        .to_dataset(dim='scenario')
        .assign_coords({'year': list(map(lambda x: str(x), np.arange(1975, 2100, 10)))})
    )
    out_path = get_store('carbonplan-scratch', 'data/website/insects.zarr')
    ds.to_zarr(out_path, mode='w')

if 'drought' in impacts_to_consolidate:
    drought_url_template = "https://carbonplan.blob.core.windows.net/carbonplan-scratch/from_bill/DroughtProjections_3-31/DroughtModelProjection_{}.{}.{}-{}.{}-v14climate_3-30-2021.tif"
    ds = load.impacts(drought_url_template, website_mask, mask=website_mask) * 100
    ds = (
        ds.to_array(dim="vars")
        .mean("vars")
        .to_dataset(dim='scenario')
        .assign_coords({'year': list(map(lambda x: str(x), np.arange(1975, 2100, 10)))})
    )
    out_path = get_store('carbonplan-scratch', 'data/website/drought.zarr', account_key=account_key)
    ds.to_zarr(out_path, mode='w')
