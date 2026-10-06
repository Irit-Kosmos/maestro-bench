import type { InjectionKey } from 'vue'

/** The first rows of the dataset an experiment runs on, provided by the page that picks it, to preview prompts with */
export const DATASET_SAMPLE: InjectionKey<Ref<readonly Record<string, unknown>[]>> = Symbol('datasetSample')
