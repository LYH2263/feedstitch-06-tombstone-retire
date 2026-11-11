<script setup>
import { onMounted, ref, watch } from 'vue'
import { getJSON } from '../api'
const sources = ref([])
const sourceId = ref(null)
const preview = ref(null)
const err = ref('')

async function loadPreview() {
  if (!sourceId.value) return
  err.value = ''
  try {
    preview.value = await getJSON(`/api/sources/${sourceId.value}/preview`)
  } catch (e) {
    preview.value = null
    err.value = String(e.message || e)
  }
}

onMounted(async () => {
  sources.value = await getJSON('/api/sources')
  if (sources.value.length) {
    sourceId.value = sources.value[0].id
  }
})
watch(sourceId, loadPreview)
</script>
<template>
  <div class="page">
    <h1>样本预览</h1>
    <p class="muted">解析夹具到统一 staging 字段，不落库。</p>
    <div class="panel">
      <label>
        源
        <select v-model.number="sourceId">
          <option v-for="s in sources" :key="s.id" :value="s.id">{{ s.id }}. {{ s.name }}</option>
        </select>
      </label>
      <button class="secondary" style="margin-left:0.75rem" @click="loadPreview">刷新</button>
    </div>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="panel" v-if="preview">
      <p>共 <strong>{{ preview.count }}</strong> 条（最多展示 50）</p>
      <table>
        <thead>
          <tr>
            <th>business_key</th><th>title</th><th>price</th><th>category</th><th>event_ts</th><th>rev</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(it, i) in preview.items" :key="i">
            <td class="mono">{{ it.business_key }}</td>
            <td>{{ it.title }}</td>
            <td class="mono">{{ it.price }}</td>
            <td>{{ it.category }}</td>
            <td class="mono">{{ it.event_ts }}</td>
            <td>{{ it.source_revision }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
