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
 * Swap themes in a single frame. Without this, every element with a color
 * transition (buttons, links, rows) fades on its own schedule, so the page
 * briefly shows a mix of both themes. The theme icon opts out via
 * `data-theme-icon` so its own crossfade still plays.
 */
export default defineNuxtPlugin(() => {
  const colorMode = useColorMode()

  watch(() => colorMode.value, () => {
    const style = document.createElement('style')
    style.textContent = '*:not([data-theme-icon]),*::before,*::after{transition:none!important}'
    document.head.appendChild(style)

    // Flush styles with transitions off, then restore them next tick
    void window.getComputedStyle(document.body).opacity
    setTimeout(() => style.remove(), 1)
  }, { flush: 'post' })
})
