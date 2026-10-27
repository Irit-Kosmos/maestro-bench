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
 * Paper is white: print always uses the light theme, whatever is on screen.
 * Swaps the class around the print dialog, so it also covers Ctrl/Cmd+P and leaves the saved preference untouched.
 * Also flags the print state so the charts can switch to their fixed print width (see `usePrinting`).
 */
export function usePrintLight() {
  const { printing } = usePrinting()
  let restoreDark = false

  function beforePrint() {
    const root = document.documentElement
    restoreDark = root.classList.contains('dark')
    root.classList.remove('dark')
    printing.value = true
  }

  function afterPrint() {
    if (restoreDark)
      document.documentElement.classList.add('dark')
    restoreDark = false
    printing.value = false
  }

  onMounted(() => {
    window.addEventListener('beforeprint', beforePrint)
    window.addEventListener('afterprint', afterPrint)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('beforeprint', beforePrint)
    window.removeEventListener('afterprint', afterPrint)
  })
}
