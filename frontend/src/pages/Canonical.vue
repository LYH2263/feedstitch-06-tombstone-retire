<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const rows = ref([])
const view = ref('alive')
const selected = ref(null)
const err = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  err.value = ''
  try {
    rows.value = await getJSON(`/api/canonical?status=${view.value}`)
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    loading.value = false
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
    <p class="muted">
      归并后的权威货号表。默认只展示存活（在售/有效）项；退役键被软删保留、可在“退役列表”查看，
      刷新后仍在。条数与最近 Run 报告中的 canonical_alive_count / canonical_retired_count 同源。
    </p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="panel">
      <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap">
        <label>
          视图
          <select v-model="view" @change="load">
            <option value="alive">存活主数据（alive）</option>
            <option value="retired">退役列表（retired）</option>
            <option value="all">全部（alive + retired）</option>
          </select>
        </label>
        <button class="secondary" @click="load">刷新</button>
        <span class="muted">{{ loading ? '加载中…' : `共 ${rows.length} 条` }}</span>
      </div>
      <table style="margin-top:0.75rem">
        <thead>
          <tr>
            <th>key</th><th>状态</th><th>title</th><th>price</th><th>category</th>
            <th>source</th><th>rev</th><th>event_ts</th><th>退役时间</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.business_key">
            <td class="mono">{{ r.business_key }}</td>
            <td>
              <span class="tag" :class="r.status === 'retired' ? 'danger' : 'ok'">{{ r.status }}</span>
            </td>
            <td :class="{ muted: r.status === 'retired' }">{{ r.title || '—' }}</td>
            <td class="mono">{{ r.price }}</td>
            <td>{{ r.category || '—' }}</td>
            <td>{{ r.source_id }}</td>
            <td>{{ r.source_revision }}</td>
            <td class="mono">{{ r.event_ts }}</td>
            <td class="mono">{{ r.retired_at || '—' }}</td>
            <td><button class="secondary" @click="openDetail(r.business_key)">详情</button></td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="muted">该视图下暂无记录。</p>
    </div>
    <div class="panel" v-if="selected">
      <h3>
        详情 · {{ selected.business_key }}
        <span class="tag" :class="selected.status === 'retired' ? 'danger' : 'ok'">{{ selected.status }}</span>
      </h3>
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
