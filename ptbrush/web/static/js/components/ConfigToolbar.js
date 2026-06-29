import { defineComponent, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';

export default defineComponent({
    name: 'ConfigToolbar',
    emits: ['imported'],
    setup(_, { emit }) {
        const fileInput = ref(null);
        const importing = ref(false);

        function exportConfig() {
            window.location.href = '/api/config/export';
        }

        function chooseFile() {
            fileInput.value?.click();
        }

        async function onFileSelected(e) {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
                await ElMessageBox.confirm(
                    '确认用 "' + file.name + '" 覆盖当前配置？（web 登录设置不会被覆盖；当前配置会备份到 config.toml.bak）',
                    '导入确认',
                    { type: 'warning' },
                );
            } catch (_) {
                e.target.value = '';
                return;
            }

            importing.value = true;
            try {
                const text = await file.text();
                const res = await fetch('/api/config/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/toml' },
                    body: text,
                    credentials: 'same-origin',
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data?.error || ('HTTP ' + res.status));
                ElMessage.success(data?.message || '已导入');
                emit('imported');
            } catch (err) {
                ElMessage.error(err.message || '导入失败');
            } finally {
                importing.value = false;
                e.target.value = '';
            }
        }

        return { fileInput, importing, exportConfig, chooseFile, onFileSelected };
    },
    template: `
        <span>
            <el-button plain @click="exportConfig">导出</el-button>
            <el-button plain :loading="importing" @click="chooseFile">导入</el-button>
            <input
                ref="fileInput"
                type="file"
                accept=".toml"
                style="display:none;"
                @change="onFileSelected" />
        </span>
    `,
});
