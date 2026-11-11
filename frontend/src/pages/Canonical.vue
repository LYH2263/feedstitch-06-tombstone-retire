<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const rows = ref([])
const selected = ref(null)
const err = ref('')

async function load() {
  try {
    rows.value = await getJSON('/api/canonical')
  } catch (e) {
    err.value = String(e.message || e)
  }
}

async function openDetail(key) {
  selected.value = await getJSON(`/api/canonical/${encodeURIComponent(key)}`)
}

onMounted(load)
</script>
<template>
  <div class="page">
    <h1>Canonical</h1>
    <p class="muted">归并后的权威货号表。列表条数应与最近 Run 报告中的 canonical_count 对得上。</p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="panel">
      <p>共 <strong>{{ rows.length }}</strong> 条</p>
      <table>
        <thead>
          <tr>
            <th>key</th><th>title</th><th>price</th><th>category</th><th>source</th><th>rev</th><th>event_ts</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.business_key">
            <td class="mono">{{ r.business_key }}</td>
            <td>{{ r.title }}</td>
            <td class="mono">{{ r.price }}</td>
            <td>{{ r.category }}</td>
            <td>{{ r.source_id }}</td>
            <td>{{ r.source_revision }}</td>
            <td class="mono">{{ r.event_ts }}</td>
            <td><button class="secondary" @click="openDetail(r.business_key)">详情</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="panel" v-if="selected">
      <h3>详情 · {{ selected.business_key }}</h3>
      <pre class="mono">{{ JSON.stringify(selected, null, 2) }}</pre>
    </div>
  </div>
</template>
<style scoped>
pre {
  background: #0a1422;
  padding: 0.75rem;
  border-radius: 8px;
  overflow: auto;
}
</style>
