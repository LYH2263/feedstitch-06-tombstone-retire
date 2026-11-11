<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const rows = ref([])
const err = ref('')
onMounted(async () => {
  try {
    rows.value = await getJSON('/api/conflicts')
  } catch (e) {
    err.value = String(e.message || e)
  }
})
</script>
<template>
  <div class="page">
    <h1>冲突队列</h1>
    <p class="muted">同业务键、非键字段分歧 → quarantine；不得静默覆盖 Canonical。</p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="panel" v-for="c in rows" :key="c.id">
      <p>
        #{{ c.id }} · run {{ c.run_id }} ·
        <span class="mono">{{ c.business_key }}</span> ·
        <span class="tag danger">{{ c.reason }}</span>
        <span class="muted"> · {{ c.created_at }}</span>
      </p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem">
        <div>
          <div class="muted">existing</div>
          <pre class="mono">{{ JSON.stringify(c.existing, null, 2) }}</pre>
        </div>
        <div>
          <div class="muted">incoming</div>
          <pre class="mono">{{ JSON.stringify(c.incoming, null, 2) }}</pre>
        </div>
      </div>
    </div>
    <p v-if="!rows.length" class="muted">暂无冲突。</p>
  </div>
</template>
<style scoped>
pre {
  background: #0a1422;
  padding: 0.75rem;
  border-radius: 8px;
  overflow: auto;
  max-height: 240px;
}
</style>
