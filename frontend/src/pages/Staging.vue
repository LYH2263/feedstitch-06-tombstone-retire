<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const rows = ref([])
const err = ref('')
onMounted(async () => {
  try {
    rows.value = await getJSON('/api/staging')
  } catch (e) {
    err.value = String(e.message || e)
  }
})
</script>
<template>
  <div class="page">
    <h1>Staging</h1>
    <p class="muted">最近写入的 staging 行（含 disposition）。</p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>run</th><th>source</th><th>key</th><th>event_ts</th><th>rev</th><th>disposition</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.run_id }}</td>
            <td>{{ r.source_id }}</td>
            <td class="mono">{{ r.business_key }}</td>
            <td class="mono">{{ r.event_ts }}</td>
            <td>{{ r.source_revision }}</td>
            <td>
              <span
                class="tag"
                :class="r.disposition === 'quarantine' ? 'danger' : (r.disposition.startsWith('skip') || r.disposition.includes('skip') ? 'warn' : 'ok')"
              >{{ r.disposition }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
