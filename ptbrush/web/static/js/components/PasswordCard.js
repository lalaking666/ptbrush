import { defineComponent, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { api } from '../api.js';

export default defineComponent({
    name: 'PasswordCard',
    props: {
        loginRequired: { type: Boolean, default: false },
    },
    setup() {
        const form = reactive({
            current_password: '',
            new_password: '',
            confirm_password: '',
        });
        const submitting = ref(false);

        async function submit() {
            if (form.new_password !== form.confirm_password) {
                ElMessage.error('两次输入的新密码不一致');
                return;
            }
            if (!form.new_password) {
                try {
                    await ElMessageBox.confirm(
                        '将清空密码并关闭 Web 登录，所有人都能访问。确定继续？',
                        '关闭登录确认',
                        { type: 'warning' },
                    );
                } catch (e) {
                    return;
                }
            }
            submitting.value = true;
            try {
                const res = await api.post('/api/auth/change-password', {
                    current_password: form.current_password,
                    new_password: form.new_password,
                });
                ElMessage.success(res?.message || '已更新');
                form.current_password = '';
                form.new_password = '';
                form.confirm_password = '';
                if (res?.require_relogin) {
                    setTimeout(() => window.location.replace('/login'), 800);
                }
            } catch (e) {
                ElMessage.error(e.message || '修改失败');
            } finally {
                submitting.value = false;
            }
        }

        return { form, submitting, submit };
    },
    template: `
        <el-card shadow="hover">
            <template #header>
                <strong>Web 访问</strong>
            </template>
            <el-alert
                type="info" :closable="false" show-icon
                style="margin-bottom:12px;"
                :title="loginRequired
                    ? '当前已启用登录密码。清空新密码可关闭登录。'
                    : '当前未启用登录。设置新密码后启用，下次刷新生效。'" />
            <el-form label-position="top">
                <el-row :gutter="16">
                    <el-col :xs="24" :sm="8" v-if="loginRequired">
                        <el-form-item label="当前密码">
                            <el-input
                                v-model="form.current_password"
                                type="password" show-password
                                placeholder="必填" />
                        </el-form-item>
                    </el-col>
                    <el-col :xs="24" :sm="8">
                        <el-form-item label="新密码">
                            <el-input
                                v-model="form.new_password"
                                type="password" show-password
                                placeholder="留空表示关闭登录" />
                        </el-form-item>
                    </el-col>
                    <el-col :xs="24" :sm="8">
                        <el-form-item label="确认新密码">
                            <el-input
                                v-model="form.confirm_password"
                                type="password" show-password
                                placeholder="再输一次" />
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-button type="primary" :loading="submitting" @click="submit">
                    更新密码
                </el-button>
            </el-form>
        </el-card>
    `,
});
