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
