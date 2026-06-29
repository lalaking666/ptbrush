import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from './views/Dashboard.js';
import Config from './views/Config.js';
import Login from './views/Login.js';

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/', redirect: '/dashboard' },
        { path: '/dashboard', component: Dashboard, meta: { title: '仪表盘' } },
        { path: '/config', component: Config, meta: { title: '配置' } },
        { path: '/login', component: Login, meta: { title: '登录', public: true } },
    ],
});

router.afterEach((to) => {
    if (to.meta?.title) document.title = `${to.meta.title} - PTBrush`;
});

let authStatePromise = null;
function fetchAuthState() {
    if (!authStatePromise) {
        authStatePromise = fetch('/api/auth/state', { credentials: 'same-origin' })
            .then(r => r.ok ? r.json() : { login_required: false, authenticated: true })
            .catch(() => ({ login_required: false, authenticated: true }));
    }
    return authStatePromise;
}

export function refreshAuthState() {
    authStatePromise = null;
}

router.beforeEach(async (to) => {
    if (to.meta?.public) return true;
    const state = await fetchAuthState();
    if (state.login_required && !state.authenticated) {
        return { path: '/login', query: { from: to.fullPath } };
    }
    return true;
});
