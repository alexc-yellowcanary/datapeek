from __future__ import annotations

from itertools import cycle
from random import choice
from random import randint
from random import random
from typing import Any

import pandas as pd


def pd_mixed_table(num_rows: int, num_cols: int) -> pd.DataFrame:
    if min(num_rows, num_cols) < 10:
        raise ValueError('I thought you wanted a big table!')

    series_makers = [pd_int_series, pd_float_series, pd_string_series]

    df = pd.DataFrame()

    col_num = 0
    for maker in cycle(series_makers):
        if col_num > num_cols:
            break

        df[f'column_{col_num}'] = maker(num_rows)
        col_num += 1

    return df


def pd_int_series(num_rows: int) -> pd.Series[Any]:
    return pd.Series(list(randint(0, 100) for _ in range(num_rows)))


def pd_float_series(num_rows: int) -> pd.Series[Any]:
    return pd.Series(list(random() for _ in range(num_rows)))


def pd_string_series(num_rows: int) -> pd.Series[Any]:
    string_options = [
        'Hello hello',
        'I am a string',
        'This string is a little longer',
        'short',
        'abc',
        'string for string in strings',
    ]

    return pd.Series(list(choice(string_options) for _ in range(num_rows)))
