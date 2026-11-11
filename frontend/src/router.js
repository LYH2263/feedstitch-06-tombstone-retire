import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './pages/Dashboard.vue'
import Sources from './pages/Sources.vue'
import Preview from './pages/Preview.vue'
import Workbench from './pages/Workbench.vue'
import Staging from './pages/Staging.vue'
import Conflicts from './pages/Conflicts.vue'
import Canonical from './pages/Canonical.vue'
import Watermarks from './pages/Watermarks.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/sources', component: Sources },
    { path: '/preview', component: Preview },
    { path: '/workbench', component: Workbench },
    { path: '/staging', component: Staging },
    { path: '/conflicts', component: Conflicts },
    { path: '/canonical', component: Canonical },
    { path: '/watermarks', component: Watermarks },
  ],
})
