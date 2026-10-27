# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Percentile bootstrap confidence intervals."""

from collections.abc import Callable

import numpy as np


def bootstrap_ci(
    statistics: Callable[[np.ndarray], dict[str, float | None]],
    n: int,
    n_boot: int,
    confidence: float,
    seed: int,
) -> dict[str, tuple[float, float] | None]:
    """
    Resample row indices with replacement and return a percentile interval per
    statistic.

    ``statistics`` receives an index array and returns ``{key: value}``, with
    None for a value that is undefined on that resample; those resamples are
    left out of that statistic's interval. A fixed seed makes the intervals
    reproducible.
    """
    if n == 0 or n_boot == 0:
        return {}
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, n, (n_boot, n))

    values: dict[str, list[float]] = {}
    for indices in samples:
        for key, value in statistics(indices).items():
            bucket = values.setdefault(key, [])
            if value is not None:
                bucket.append(value)

    alpha = (1 - confidence) / 2
    intervals: dict[str, tuple[float, float] | None] = {}
    for key, bucket in values.items():
        if not bucket:
            intervals[key] = None
            continue
        low, high = np.quantile(bucket, [alpha, 1 - alpha])
        intervals[key] = (float(low), float(high))
    return intervals
