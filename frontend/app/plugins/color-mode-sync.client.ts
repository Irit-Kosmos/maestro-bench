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
 * Keep the `dark` / `light` class of `<html>` on the color mode's value.
 * The head script sets the class from the OS scheme it sees at load; the color mode plugin then
 * reads the scheme again and may land on the other one (the scheme changed in between, as when a
 * browser applies an emulated or synced theme) without touching the class. The page then shows dark
 * while the value says light, so picking Light changes nothing and it takes a second pick to apply.
 */
export default defineNuxtPlugin(() => {
  const colorMode = useColorMode()

  watch(() => colorMode.value, (value) => {
    const root = document.documentElement
    root.classList.toggle('dark', value === 'dark')
    root.classList.toggle('light', value === 'light')
  }, { immediate: true })
})
