# %%
import os
import pandas as pd
from enum import Enum

EXP_PATH = os.path.abspath(os.path.join(
    os.path.abspath(__file__),
    os.pardir,
    'experiment'
))

DATA_PATH = os.path.abspath(os.path.join(
    os.path.abspath(__file__),
    os.pardir,
    'data'
))

FIG_PATH = os.path.abspath(os.path.join(
    os.path.abspath(__file__),
    os.pardir,
    'figures'
))

PATH_PREFIX = 'MoDRL_'


def to_range(l):
    return range(len(l))


def getSupplierAADistance(
        distance_info_path,
        supplier_info_path,
):
    # supplier: AA distance
    distance = pd.read_csv(distance_info_path, index_col=0)
    supplier = pd.read_csv(supplier_info_path)
    suppliers = supplier['Suppliers'].tolist()

    all_dists = [[] for _ in to_range(suppliers)]
    for i in to_range(suppliers):
        sup_name = suppliers[i]
        sup_dists = distance[sup_name]
        all_dists[i] = sup_dists.tolist()
    return all_dists


class OptimizationMethod(Enum):
    WEIGHTED_SUM = 1
    LP_METRIC = 2

# %%
