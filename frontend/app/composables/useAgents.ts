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

import type { CreateAgentForm } from '~/types'

/**
 * Composable for managing individual agents
 */
export function useAgents() {
  const { $api } = useNuxtApp()

  // Create a new agent
  async function createAgent(agentData: CreateAgentForm) {
    try {
      const response = await $api('/agents', {
        method: 'POST',
        body: agentData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating agent:', error)
      return { success: false, error: 'Failed to create agent' }
    }
  }

  // Update an agent
  async function updateAgent(agentId: number, agentData: Partial<CreateAgentForm>) {
    try {
      const response = await $api(`/agents/${agentId}`, {
        method: 'PUT',
        body: agentData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating agent:', error)
      return { success: false, error: 'Failed to update agent' }
    }
  }

  // Delete an agent
  async function deleteAgent(agentId: number) {
    try {
      await $api(`/agents/${agentId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting agent:', error)
      return { success: false, error: 'Failed to delete agent' }
    }
  }

  return {
    createAgent,
    updateAgent,
    deleteAgent,
  }
}
