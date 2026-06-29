import { defineComponent, computed } from 'vue';
import HeadersEditor from './HeadersEditor.js';

export default defineComponent({
    name: 'SitesEditor',
    components: { HeadersEditor },
    props: {
        modelValue: { type: Array, default: () => [] },
        supported: { type: Array, default: () => [] },
        disabled: { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const sites = computed(() => props.modelValue || []);
        function updateField(idx, field, value) {
            const next = sites.value.map((s, i) =>
                i === idx ? { ...s, [field]: value } : s,
            );
            emit('update:modelValue', next);
        }
        function updateHeaders(idx, headers) {
            updateField(idx, 'headers', headers);
        }
        function addSite() {
            emit('update:modelValue', [
                ...sites.value,
                { name: '', cookie: '', headers: [] },
            ]);
        }
        function removeSite(idx) {
            emit('update:modelValue', sites.value.filter((_, i) => i !== idx));
        }
        function isSupported(name) {
            return !name || props.supported.includes(name);
        }
        return { sites, updateField, updateHeaders, addSite, removeSite, isSupported };
    },
    template: `
        <div>
            <div v-if="!sites.length" style="color:#909399;margin-bottom:12px;">
                尚未配置任何 PT 站点。
            </div>
            <el-card v-for="(site, idx) in sites" :key="idx" class="site-card" shadow="never">
                <template #header>
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong>站点 {{ idx + 1 }}</strong>
                        <el-button
                            type="danger" plain size="small"
                            :disabled="disabled"
                            @click="removeSite(idx)">删除此站点</el-button>
                    </div>
                </template>
                <el-form label-position="top">
                    <el-form-item label="站点名称">
                        <el-input
                            :model-value="site.name"
                            placeholder="如 M-Team"
                            :disabled="disabled"
                            @update:model-value="v => updateField(idx, 'name', v)" />
                        <el-alert
                            v-if="!isSupported(site.name)"
                            type="warning"
                            :closable="false"
                            show-icon
                            style="margin-top:8px;"
                            :title="'站点名称 “' + site.name + '” 不在程序支持列表内，运行时会失败。支持的站点：' + supported.join(', ')" />
                    </el-form-item>
                    <el-form-item label="Cookie（可选）">
                        <el-input
                            type="textarea"
                            :rows="2"
                            :model-value="site.cookie"
                            placeholder="留空则保留原值"
                            :disabled="disabled"
                            @update:model-value="v => updateField(idx, 'cookie', v)" />
                    </el-form-item>
                    <el-form-item label="Headers">
                        <HeadersEditor
                            :model-value="site.headers"
                            :disabled="disabled"
                            @update:model-value="h => updateHeaders(idx, h)" />
                    </el-form-item>
                </el-form>
            </el-card>
            <el-button
                type="primary" plain
                style="margin-top:12px;"
                :disabled="disabled"
                @click="addSite">+ 新增站点</el-button>
        </div>
    `,
});
