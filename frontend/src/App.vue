<template>
  <div class="layout-pipe">
    <aside class="pipe-rail">
      <div class="brand">信汇 Feedstitch</div>
      <router-link to="/">总览</router-link>
      <router-link to="/sources">源管理</router-link>
      <router-link to="/preview">样本预览</router-link>
      <router-link to="/workbench">运行台</router-link>
      <router-link to="/staging">Staging</router-link>
      <router-link to="/conflicts">冲突队列</router-link>
      <router-link to="/canonical">Canonical</router-link>
      <router-link to="/watermarks">水位线</router-link>
    </aside>
    <main><router-view /></main>
  </div>
</template>
