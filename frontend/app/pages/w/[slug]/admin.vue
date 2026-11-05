<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { AdminAccount, AdminField, AdminHealth, AdminMonthUsage, AdminVisibility, AdminWorkspace } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

definePageMeta({
  title: 'Administration',
  // For instance administrators only; the API refuses everyone else anyway
  middleware: [() => {
    if (!useAuth().user.value?.is_instance_admin)
      return navigateTo('/')
  }],
})

useSeoMeta({
  title: 'Administration',
})

const { data: health, error: healthError } = await useMyLazyFetch<AdminHealth>('/admin/health')
const { data: workspaces, pending: workspacesPending, error: workspacesError } = await useMyLazyFetch<AdminWorkspace[]>('/admin/workspaces')
const { data: accounts, pending: accountsPending, error: accountsError } = await useMyLazyFetch<AdminAccount[]>('/admin/accounts')
// The column names are the declared ones, the same everyone reads on "What administrators can see"
const { data: visibility } = await useMyLazyFetch<AdminVisibility>('/admin/visibility')

function fieldsOf(section: string): AdminField[] {
  return visibility.value?.sections.find(s => s.key === section)?.fields ?? []
}

function label(section: string, key: string, fallback: string): string {
  return fieldsOf(section).find(f => f.key === key)?.label ?? fallback
}

function purpose(section: string, key: string): string | undefined {
  return fieldsOf(section).find(f => f.key === key)?.purpose
}

// "Nov 2026": the months of the usage columns, the current one first
const months = computed(() => workspaces.value?.[0]?.usage.map(m => m.month) ?? [])
// "Nov", with the year in the tooltip: the three months are consecutive
function monthLabel(month: string, options: Intl.DateTimeFormatOptions = { month: 'short' }): string {
  const [year, number] = month.split('-').map(Number)
  return new Date(Date.UTC(year!, number! - 1, 1)).toLocaleDateString('en-US', { ...options, timeZone: 'UTC' })
}

function usageTooltip(month: AdminMonthUsage): string {
  const when = monthLabel(month.month, { month: 'long', year: 'numeric' })
  return `${formatCount(month.tokens)} tokens on the instance's keys in ${when}`
}

const activeAccounts = computed(() => (accounts.value ?? []).filter(a => a.active).length)
const saturated = computed(() => !!health.value && health.value.running_executions >= health.value.max_concurrent_executions)

// The first column takes the spare width, the others hug their content; numbers align right, header included
const th = 'h-8 px-3 text-xs font-medium text-muted whitespace-nowrap first:ps-4 last:pe-4'
const thStart = `${th} text-start`
const thEnd = `${th} text-end`
const td = 'h-10 px-3 text-sm text-toned whitespace-nowrap first:ps-4 last:pe-4'
const tdNum = `${td} text-end tabular-nums`
</script>

<template>
  <div class="flex flex-col gap-6">
    <p class="max-w-3xl text-sm text-muted">
      What this page shows, and only that, is listed for every user on
      <NuxtLink to="/what-admins-see" class="text-highlighted underline underline-offset-2 decoration-dotted hover:decoration-solid">
        What administrators can see
      </NuxtLink>.
      Use it to run the instance, nothing else. Actions (deactivating an account, changing a member) stay in
      <code class="text-xs">manage.py</code>.
    </p>

    <BaseSection title="Instance health">
      <BaseErrorState v-if="healthError" :message="apiErrorMessage(healthError)" />
      <dl v-else class="grid grid-cols-1 divide-y divide-default sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <div class="flex flex-col gap-1 px-4 py-3" :title="purpose('health', 'running_executions')">
          <dt class="text-xs text-muted">
            {{ label('health', 'running_executions', 'Running executions') }}
          </dt>
          <dd class="text-lg font-semibold tabular-nums" :class="saturated ? 'text-warning' : 'text-highlighted'">
            {{ health ? health.running_executions : '—' }}
            <span class="text-sm font-normal text-muted">/ {{ health?.max_concurrent_executions ?? '—' }}</span>
          </dd>
        </div>
        <div class="flex flex-col gap-1 px-4 py-3" :title="purpose('health', 'failed_last_24h')">
          <dt class="text-xs text-muted">
            {{ label('health', 'failed_last_24h', 'Failed executions, last 24 hours') }}
          </dt>
          <dd class="text-lg font-semibold tabular-nums" :class="health?.failed_last_24h ? 'text-error' : 'text-highlighted'">
            {{ health ? health.failed_last_24h : '—' }}
          </dd>
        </div>
      </dl>
    </BaseSection>

    <BaseSection title="Workspaces">
      <template #meta>
        <span v-if="workspaces?.length" class="text-xs text-muted" :title="purpose('workspaces', 'usage')">
          Monthly cost on the instance's keys only
        </span>
      </template>
      <BaseLoadingState v-if="workspacesPending && !workspaces" />
      <BaseErrorState v-else-if="workspacesError" :message="apiErrorMessage(workspacesError)" />
      <p v-else-if="!workspaces?.length" class="px-4 py-3 text-sm text-muted">
        No workspace yet.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-default">
            <tr>
              <th class="w-full" :class="[thStart]" :title="purpose('workspaces', 'name')">
                {{ label('workspaces', 'name', 'Name') }}
              </th>
              <th :class="thStart" :title="purpose('workspaces', 'owner_emails')">
                {{ label('workspaces', 'owner_emails', 'Owners') }}
              </th>
              <th :class="thEnd" :title="purpose('workspaces', 'member_count')">
                {{ label('workspaces', 'member_count', 'Members') }}
              </th>
              <th :class="thStart" :title="purpose('workspaces', 'created_on')">
                {{ label('workspaces', 'created_on', 'Created') }}
              </th>
              <th :class="thStart" :title="purpose('workspaces', 'last_activity_on')">
                {{ label('workspaces', 'last_activity_on', 'Last activity') }}
              </th>
              <th :class="thEnd" :title="purpose('workspaces', 'disk_bytes')">
                {{ label('workspaces', 'disk_bytes', 'Disk') }}
              </th>
              <th
                v-for="month in months"
                :key="month"
                :class="thEnd"
                :title="monthLabel(month, { month: 'long', year: 'numeric' })"
              >
                {{ monthLabel(month) }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-default">
            <tr v-for="workspace in workspaces" :key="workspace.slug">
              <td :class="td">
                <div class="flex min-w-0 items-center gap-2">
                  <span class="truncate font-medium text-highlighted" :title="workspace.name">{{ workspace.name }}</span>
                  <span class="shrink-0 text-xs text-dimmed" :title="purpose('workspaces', 'slug')">{{ workspace.slug }}</span>
                  <UBadge v-if="workspace.archived" color="neutral" variant="subtle" size="sm" class="shrink-0">
                    Archived
                  </UBadge>
                </div>
              </td>
              <td :class="td">
                <span class="block max-w-64 truncate" :title="workspace.owner_emails.join(', ')">
                  {{ workspace.owner_emails.join(', ') || '—' }}
                </span>
              </td>
              <td :class="tdNum">
                {{ workspace.member_count }}
              </td>
              <td class="tabular-nums" :class="[td]">
                {{ workspace.created_on ?? '—' }}
              </td>
              <td class="tabular-nums" :class="[td, !workspace.last_activity_on && 'text-dimmed']">
                {{ workspace.last_activity_on ?? '—' }}
              </td>
              <td :class="[tdNum, !workspace.disk_bytes && 'text-dimmed']">
                {{ workspace.disk_bytes ? formatBytes(workspace.disk_bytes) : '—' }}
              </td>
              <td v-for="month in workspace.usage" :key="month.month" :class="tdNum" :title="usageTooltip(month)">
                <span v-if="month.cost_usd">{{ formatCost(month.cost_usd) }}</span>
                <span v-else class="text-dimmed">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseSection>

    <BaseSection title="Accounts">
      <template #meta>
        <span v-if="accounts?.length" class="text-xs text-muted tabular-nums">{{ activeAccounts }} active of {{ accounts.length }}</span>
      </template>
      <BaseLoadingState v-if="accountsPending && !accounts" />
      <BaseErrorState v-else-if="accountsError" :message="apiErrorMessage(accountsError)" />
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-default">
            <tr>
              <th class="w-full" :class="[thStart]" :title="purpose('accounts', 'email')">
                {{ label('accounts', 'email', 'Email') }}
              </th>
              <th :class="thStart" :title="purpose('accounts', 'last_sign_in_on')">
                {{ label('accounts', 'last_sign_in_on', 'Last sign-in') }}
              </th>
              <th :class="thEnd" :title="purpose('accounts', 'workspace_count')">
                {{ label('accounts', 'workspace_count', 'Workspaces') }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-default">
            <tr v-for="account in accounts ?? []" :key="account.id">
              <td :class="td">
                <div class="flex min-w-0 items-center gap-2">
                  <span class="truncate" :class="account.active ? 'text-highlighted' : 'text-muted'" :title="account.email ?? undefined">{{ account.email ?? '—' }}</span>
                  <span class="shrink-0 text-xs text-dimmed tabular-nums" :title="purpose('accounts', 'id')">#{{ account.id }}</span>
                  <!-- Active is the usual case: only the exception is marked -->
                  <UBadge v-if="!account.active" color="neutral" variant="subtle" size="sm" class="shrink-0">
                    Deactivated
                  </UBadge>
                </div>
              </td>
              <td class="tabular-nums" :class="[td, !account.last_sign_in_on && 'text-dimmed']">
                {{ account.last_sign_in_on ?? 'Never' }}
              </td>
              <td :class="[tdNum, !account.workspace_count && 'text-dimmed']">
                {{ account.workspace_count }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseSection>
  </div>
</template>
