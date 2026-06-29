import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import { router } from './router.js';
import AppShell from './components/AppShell.js';

const app = createApp(AppShell);
app.use(router);
app.use(ElementPlus);
app.mount('#app');
