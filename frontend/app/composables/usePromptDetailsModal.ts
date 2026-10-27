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

import type { PromptVersion } from '~/types'

/**
 * State of the "prompt details" modal, opened from an agent's prompt version.
 */
export function usePromptDetailsModal(allPromptVersions: Ref<PromptVersion[] | null | undefined>) {
  const showPromptDetailsModal = ref(false)
  const selectedPromptVersionForDetails = ref<PromptVersion | null>(null)

  function openPromptDetails(promptVersionId: number) {
    const promptVersion = allPromptVersions.value?.find(v => v.id === promptVersionId)
    if (promptVersion) {
      selectedPromptVersionForDetails.value = promptVersion
      showPromptDetailsModal.value = true
    }
  }

  return {
    showPromptDetailsModal,
    selectedPromptVersionForDetails,
    openPromptDetails,
  }
}
