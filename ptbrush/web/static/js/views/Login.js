import { defineComponent, ref, onMounted } from 'vue';
import { api } from '../api.js';

export default defineComponent({
    name: 'Login',
    setup() {
        const password = ref('');
        const submitting = ref(false);
        const errMsg = ref('');

        onMounted(async () => {
            try {
                const s = await api.get('/api/auth/state');
                if (!s.login_required || s.authenticated) {
                    const from = new URLSearchParams(location.search).get('from') || '/dashboard';
                    window.location.replace(from);
                }
            } catch (e) {
                // 状态接口失败时让用户照常输入
            }
        });

        async function submit() {
            if (!password.value) {
                errMsg.value = '请输入密码';
                return;
            }
            submitting.value = true;
            errMsg.value = '';
            try {
                await api.post('/api/auth/login', { password: password.value });
                const from = new URLSearchParams(location.search).get('from') || '/dashboard';
                window.location.replace(from);
            } catch (e) {
                errMsg.value = e.message || '登录失败';
            } finally {
                submitting.value = false;
            }
        }

        return { password, submitting, errMsg, submit };
    },
    template: `
        <div style="max-width:360px;margin:96px auto;">
            <el-card shadow="hover">
                <template #header>
                    <strong>登录 PTBrush</strong>
                </template>
                <el-form @submit.prevent="submit" label-position="top">
                    <el-form-item label="密码">
                        <el-input
                            v-model="password"
                            type="password"
                            show-password
                            placeholder="config.toml 中 [web].password"
                            @keyup.enter="submit" />
                    </el-form-item>
                    <el-alert
                        v-if="errMsg"
                        type="error"
                        :closable="false"
                        :title="errMsg"
                        show-icon
                        style="margin-bottom:12px;" />
                    <el-button type="primary" :loading="submitting" @click="submit" style="width:100%;">
                        登录
                    </el-button>
                </el-form>
            </el-card>
        </div>
    `,
});
