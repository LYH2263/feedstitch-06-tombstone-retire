<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, patchJSON, putJSON } from '../api'

const marks = ref([])
const settings = ref([])
const err = ref('')
const msg = ref('')

async function refresh() {
  marks.value = await getJSON('/api/watermarks')
  settings.value = await getJSON('/api/settings')
}

async function saveLookback(row) {
  err.value = ''
  msg.value = ''
  try {
    await patchJSON(`/api/sources/${row.source_id}/lookback`, {
      lookback_seconds: Number(row.lookback_seconds) || 0,
    })
    msg.value = `已写入源 ${row.source_id} 的 lookback_seconds（底座 ingest 暂忽略此字段，留给 0-1）`
    await refresh()
  } catch (e) {
    err.value = String(e.message || e)
  }
}

async function saveSetting(row) {
  await putJSON(`/api/settings/${encodeURIComponent(row.key)}`, { value: row.value })
  msg.value = `设置 ${row.key} 已保存`
  await refresh()
}

onMounted(async () => {
  try {
    await refresh()
  } catch (e) {
    err.value = String(e.message || e)
  }
})
</script>
<template>
  <div class="page">
    <h1>水位线与设置</h1>
    <p class="muted">增量跑依赖每源 watermark_ts；lookback_seconds 字段已预留。</p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <p v-if="msg" class="tag ok">{{ msg }}</p>
    <div class="panel">
      <h3>水位线</h3>
      <table>
        <thead>
          <tr><th>源</th><th>watermark</th><th>lookback_seconds</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="m in marks" :key="m.source_id">
            <td>{{ m.source_id }}. {{ m.name }}</td>
            <td class="mono">{{ m.watermark_ts || '—' }}</td>
            <td><input type="number" v-model.number="m.lookback_seconds" min="0" style="width:7rem" /></td>
            <td><button class="secondary" @click="saveLookback(m)">保存 lookback</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="panel">
      <h3>设置</h3>
      <table>
        <thead><tr><th>key</th><th>value</th><th></th></tr></thead>
        <tbody>
          <tr v-for="s in settings" :key="s.key">
            <td class="mono">{{ s.key }}</td>
            <td><input v-model="s.value" style="width:16rem" /></td>
            <td><button class="secondary" @click="saveSetting(s)">保存</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
