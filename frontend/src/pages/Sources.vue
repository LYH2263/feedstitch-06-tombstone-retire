<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const rows = ref([])
const err = ref('')
onMounted(async () => {
  try {
    rows.value = await getJSON('/api/sources')
  } catch (e) {
    err.value = String(e.message || e)
  }
})
</script>
<template>
  <div class="page">
    <h1>源管理</h1>
    <p class="muted">本地夹具源（json / jsonl / xml），不含活网爬虫。</p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>名称</th><th>格式</th><th>夹具</th><th>水位线</th><th>lookback</th><th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in rows" :key="s.id">
            <td>{{ s.id }}</td>
            <td>{{ s.name }}</td>
            <td><span class="mono">{{ s.format }}</span></td>
            <td class="mono">{{ s.fixture_path }}</td>
            <td class="mono">{{ s.watermark_ts || '—' }}</td>
            <td>{{ s.lookback_seconds }}s</td>
            <td class="muted">{{ s.note }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
