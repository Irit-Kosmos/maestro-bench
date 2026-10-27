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

interface ToastOptions {
  description?: string
  /** A shortcut to what the toast is about, e.g. the experiment that was just created */
  action?: { label: string, to: string }
}

/**
 * The app's one way to tell the outcome of an action: the title states the fact
 * ("Dataset created", "Couldn’t delete the model"), the description adds the reason.
 */
export function useStandardToast() {
  const toast = useToast()

  function ok(title: string, { description, action }: ToastOptions = {}) {
    toast.add({
      title,
      description,
      color: 'success',
      icon: 'i-ph-check-circle-bold',
      actions: action ? [{ label: action.label, color: 'neutral', variant: 'outline', to: action.to }] : undefined,
    })
  }

  function info(title: string, description?: string) {
    toast.add({ title, description, color: 'neutral', icon: 'i-ph-info-bold' })
  }

  function fail(title: string, description?: string) {
    // Stays until closed: an error that fades after five seconds may never be read
    toast.add({ title, description, color: 'error', icon: 'i-ph-warning-circle-bold', duration: 0 })
  }

  // Create, update and delete share their wording across the lists and detail pages
  const noun = (entityName: string) => entityName.toLowerCase()

  function showCreateSuccess(entityName: string, options?: ToastOptions) {
    ok(`${entityName} created`, options)
  }

  function showUpdateSuccess(entityName: string, options?: ToastOptions) {
    ok(`${entityName} updated`, options)
  }

  function showDeleteSuccess(entityName: string, options?: ToastOptions) {
    ok(`${entityName} deleted`, options)
  }

  function showCreateError(entityName: string, error?: string) {
    fail(`Couldn’t create the ${noun(entityName)}`, error)
  }

  function showUpdateError(entityName: string, error?: string) {
    fail(`Couldn’t update the ${noun(entityName)}`, error)
  }

  function showDeleteError(entityName: string, error?: string) {
    fail(`Couldn’t delete the ${noun(entityName)}`, error)
  }

  return {
    ok,
    info,
    fail,
    showCreateSuccess,
    showUpdateSuccess,
    showDeleteSuccess,
    showCreateError,
    showUpdateError,
    showDeleteError,
  }
}
