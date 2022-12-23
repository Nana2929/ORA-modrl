import os

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

PATH_PREFIX = 'MoDRL_'


def to_range(l):
    return range(len(l))
