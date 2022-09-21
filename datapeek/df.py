"""Module to generate dataframes to test rendering in the terminal"""
from __future__ import annotations

from itertools import cycle
from random import choice
from random import randint
from random import random
from typing import Any
from typing import Callable
from typing import Iterable

import pandas as pd
from faker import Faker

fake = Faker()


def pd_mixed_table(num_rows: int, num_cols: int) -> pd.DataFrame:
    series_makers: Iterable[Callable[[int], pd.Series[Any]]] = [
        pd_int_series,
        pd_float_series,
        pd_string_series,
    ]

    series_dict = {}

    # add cols to test multi-line rendering
    series_dict["str_smol"] = pd_string_series(num_rows, "multi_string_smol")
    series_dict["str_large"] = pd_string_series(num_rows, "multi_string_large")

    col_num = 2
    for maker in cycle(series_makers):
        if col_num > num_cols:
            break

        s = maker(num_rows)

        if s.name:
            col_name = f"{s.name}_{col_num}"

        else:
            col_name = f"column_{col_num}"

        series_dict[col_name] = s

        col_num += 1

    df = pd.DataFrame(series_dict)

    return df


def pd_mixed_table_mindex(
    num_rows: int,
    num_cols: int,
    row_index_depth: int = 1,
    col_index_depth: int = 1,
) -> pd.DataFrame:
    df = pd_mixed_table(num_rows, num_cols)

    if row_index_depth > 1:
        df.index = sindex_to_mindex(df.index, row_index_depth)

    if col_index_depth > 1:
        df.columns = sindex_to_mindex(df.columns, col_index_depth)

    return df


def sindex_to_mindex(sindex: pd.Index, max_level: int) -> pd.MultiIndex:
    """Convert a single index to a multi-index (mindex) of depth `depth`.

    Uses equal-spaced index levels (as equal as possible) - so each
    index level will try to have the same amount of "children" as others on that level,
    and half as many entries as the next level down.

    As each level needs at least one item, if `depth` is too deep it can result in
    multiple single-entry indexes at the top of the mindex.
    """
    if max_level <= 1:
        raise ValueError("`max_level` must be greater than 2 for a multi-index")

    if sindex.nlevels != 1:
        raise ValueError(f"sindex must be a single index - but {sindex.nlevels=}")

    length = len(sindex)

    def _level_tuples_for_level(level: int) -> tuple[int, ...]:
        """Generates an array of tuples, representing the values of the
        index at level `depth`."""
        # split by square rule, ensuring at least one item
        level_length = max(int(length // 2 ** (level - 1)), 1)

        multiplier = length // level_length
        leftovers = length % level_length

        # these are evenly split
        level_array_base = tuple(sorted(list(range(level_length)) * multiplier))

        # any leftovers, add to last value in level
        # (no leftovers will just be an empty array)
        leftover_array = (level_length - 1,) * leftovers

        return level_array_base + leftover_array

    return pd.MultiIndex.from_tuples(
        zip(*(_level_tuples_for_level(l) for l in range(max_level, 1, -1)), sindex),
    )


def pd_int_series(num_rows: int) -> pd.Series[Any]:
    # pick a range, then fill with random values up to that range
    range_mapping = {
        "smol_ints": 100,
        "large_ints": 1000,
        "larger_ints": 1_000_000,
    }
    range_name = choice(list(range_mapping.keys()))
    max_range = range_mapping[range_name]

    s = pd.Series(list(randint(0, max_range) for _ in range(num_rows)))
    s.name = range_name

    return s


def pd_float_series(num_rows: int) -> pd.Series[Any]:
    # pick a range, then fill with random values up to that range
    magnitude_mapping = {
        "smol_floats": 100,
        "large_floats": 1000,
        "larger_floats": 1_000_000,
    }
    magnitude_name = choice(list(magnitude_mapping.keys()))
    magnitude = magnitude_mapping[magnitude_name]
    s = pd.Series(list(random() * magnitude for _ in range(num_rows)))
    s.name = magnitude_name
    return s


def multi_line_string(min_lines: int = 1, max_lines: int = 4) -> str:
    num_lines = choice(range(min_lines, max_lines + 1))
    return "\n".join(fake.name() for _ in range(num_lines))


def pd_string_series(num_rows: int, provider_name: str | None = None) -> pd.Series[Any]:
    provider_mapping = {
        "address": fake.address,
        "bank-iban": fake.iban,
        "favourite_colour": fake.color_name,
        "phone_number": fake.phone_number,
        "name": fake.name,
        "multi_string_smol": lambda: multi_line_string(max_lines=2),
        "multi_string_large": lambda: multi_line_string(max_lines=3),
    }

    if provider_name is None:
        # pick a provider for a string - use that provider to give values
        provider_name = choice(list(provider_mapping.keys()))

    provider = provider_mapping[provider_name]

    s = pd.Series(list(provider() for _ in range(num_rows)))
    s.name = provider_name

    return s
