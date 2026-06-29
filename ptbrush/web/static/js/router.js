import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from './views/Dashboard.js';
import Config from './views/Config.js';

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/', redirect: '/dashboard' },
        { path: '/dashboard', component: Dashboard, meta: { title: '仪表盘' } },
        { path: '/config', component: Config, meta: { title: '配置' } },
    ],
});

router.afterEach((to) => {
    if (to.meta?.title) document.title = `${to.meta.title} - PTBrush`;
});
