// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

// Experiments of a batch are named "<batch name> · <variant> · <variant>…" (see backend/api/batches.py).
// In a list the batch is already shown next to the experiment, so what tells the rows apart is the variant.
const SEPARATOR = ' · '

export interface ExperimentNameParts {
  /** What identifies the experiment: the whole name, or its variant when the batch prefix is stripped */
  segments: string[]
  /** The batch prefix that was stripped, if any */
  batch: string | null
}

export function splitExperimentName(name: string, batchName?: string | null): ExperimentNameParts {
  const prefix = batchName ? batchName + SEPARATOR : null
  // A renamed batch no longer matches its experiments' names: keep those whole rather than guess
  if (prefix && name.startsWith(prefix) && name.length > prefix.length) {
    return { segments: name.slice(prefix.length).split(SEPARATOR), batch: batchName ?? null }
  }
  return { segments: [name], batch: null }
}

/** Plain-text form, e.g. for search */
export function shortExperimentName(name: string, batchName?: string | null): string {
  return splitExperimentName(name, batchName).segments.join(SEPARATOR)
}
