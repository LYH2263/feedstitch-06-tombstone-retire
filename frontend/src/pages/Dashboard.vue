<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const stats = ref(null)
const err = ref('')
onMounted(async () => {
  try {
    stats.value = await getJSON('/api/dashboard')
  } catch (e) {
    err.value = String(e.message || e)
  }
})
</script>
<template>
  <div class="page">
    <header>
      <h1>归并总览</h1>
      <p class="muted">多源 Feed 解析 → 去重 / 冲突隔离 → 水位线落库</p>
    </header>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="tiles" v-if="stats">
      <div class="tile"><div class="hero-num">{{ stats.source_count }}</div><div class="muted">源</div></div>
      <div class="tile"><div class="hero-num">{{ stats.canonical_count }}</div><div class="muted">Canonical</div></div>
      <div class="tile"><div class="hero-num">{{ stats.conflict_count }}</div><div class="muted">冲突</div></div>
      <div class="tile"><div class="hero-num">{{ stats.run_count }}</div><div class="muted">Runs</div></div>
      <div class="tile"><div class="hero-num">{{ stats.staging_count }}</div><div class="muted">Staging</div></div>
      <div class="tile"><div class="hero-num">{{ stats.enabled_sources }}</div><div class="muted">启用源</div></div>
    </div>
    <router-link to="/workbench">去运行台跑一趟 →</router-link>
  </div>
</template>
