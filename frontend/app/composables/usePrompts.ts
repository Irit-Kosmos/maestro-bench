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

/**
 * Composable for managing prompts and their versions
 */
export function usePrompts() {
  const { $api } = useNuxtApp()

  // Create a new prompt
  async function createPrompt(promptData: { name: string, description?: string, tag_ids?: number[] }) {
    try {
      const response = await $api('/prompts', {
        method: 'POST',
        body: promptData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating prompt:', error)
      return { success: false, error: 'Failed to create prompt' }
    }
  }

  // Update a prompt
  async function updatePrompt(promptId: number, promptData: { name?: string, description?: string, tag_ids?: number[] }) {
    try {
      const response = await $api(`/prompts/${promptId}`, {
        method: 'PUT',
        body: promptData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating prompt:', error)
      return { success: false, error: 'Failed to update prompt' }
    }
  }

  // Delete a prompt
  async function deletePrompt(promptId: number) {
    try {
      await $api(`/prompts/${promptId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting prompt:', error)
      return { success: false, error: 'Failed to delete prompt' }
    }
  }

  // Get prompt versions for a specific prompt
  async function getPromptVersions(promptId: number) {
    try {
      const response = await $api(`/prompts/${promptId}/versions`)
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching prompt versions:', error)
      return { success: false, error: 'Failed to fetch prompt versions' }
    }
  }

  // Create a new prompt version
  async function createPromptVersion(promptId: number, versionData: {
    version: string
    system_prompt?: string | null
    user_prompt?: string | null
    variables?: string | null
    is_active?: boolean
    is_default?: boolean
    notes?: string | null
  }) {
    try {
      const response = await $api(`/prompts/${promptId}/versions`, {
        method: 'POST',
        body: versionData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating prompt version:', error)
      return { success: false, error: 'Failed to create prompt version' }
    }
  }

  // Update a prompt version
  async function updatePromptVersion(versionId: number, versionData: {
    version?: string
    system_prompt?: string | null
    user_prompt?: string | null
    variables?: string | null
    is_active?: boolean
    is_default?: boolean
    notes?: string | null
  }) {
    try {
      const response = await $api(`/prompt-versions/${versionId}`, {
        method: 'PUT',
        body: versionData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating prompt version:', error)
      return { success: false, error: 'Failed to update prompt version' }
    }
  }

  // Delete a prompt version
  async function deletePromptVersion(versionId: number) {
    try {
      await $api(`/prompt-versions/${versionId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting prompt version:', error)
      return { success: false, error: 'Failed to delete prompt version' }
    }
  }

  // The prompts as an agent would receive them with these values (nothing is saved or sent to a model)
  async function renderPrompts(body: { system_prompt: string | null, user_prompt: string | null, variables: Record<string, unknown> }) {
    try {
      const data = await $api<{ system: string, user: string }>('/prompts/render', { method: 'POST', body })
      return { success: true as const, data }
    }
    catch (error) {
      const detail = (error as { data?: { detail?: unknown } })?.data?.detail
      return { success: false as const, error: typeof detail === 'string' ? detail : 'Failed to render the prompt' }
    }
  }

  return {
    renderPrompts,
    createPrompt,
    updatePrompt,
    deletePrompt,
    getPromptVersions,
    createPromptVersion,
    updatePromptVersion,
    deletePromptVersion,
  }
}
