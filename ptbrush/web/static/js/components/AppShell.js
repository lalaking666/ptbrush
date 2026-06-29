import { defineComponent, ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { api } from '../api.js';
import { refreshAuthState } from '../router.js';

export default defineComponent({
    name: 'AppShell',
    setup() {
        const authState = ref({ login_required: false, authenticated: true });

        async function loadAuthState() {
            try {
                authState.value = await api.get('/api/auth/state');
            } catch (e) {
                // ignore
            }
        }

        async function logout() {
            try {
                await api.post('/api/auth/logout');
                refreshAuthState();
                ElMessage.success('已退出登录');
                setTimeout(() => window.location.replace('/login'), 300);
            } catch (e) {
                ElMessage.error(e.message || '退出失败');
            }
        }

        onMounted(loadAuthState);

        return { authState, logout };
    },
    template: `
        <el-container style="height:100vh;">
            <el-header class="app-header" height="56px">
                <div class="app-brand">PTBrush</div>
                <el-menu
                    mode="horizontal"
                    :ellipsis="false"
                    :default-active="$route.path"
                    background-color="#1f2937"
                    text-color="#cbd5e1"
                    active-text-color="#67c23a"
                    router>
                    <el-menu-item index="/dashboard">仪表盘</el-menu-item>
                    <el-menu-item index="/config">配置</el-menu-item>
                </el-menu>
                <el-button
                    v-if="authState.login_required && authState.authenticated"
                    type="info" plain size="small" @click="logout">
                    退出
                </el-button>
            </el-header>
            <el-main>
                <router-view />
            </el-main>
        </el-container>
    `,
});
