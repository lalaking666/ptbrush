import { defineComponent, computed, ref } from 'vue';
import HeadersEditor from './HeadersEditor.js';

const SITE_TEMPLATES = {
    'M-Team': {
        label: 'M-Team',
        description: '使用 x-api-key Header 鉴权',
        usesCookie: false,
        site: {
            name: 'M-Team',
            cookie: '',
            headers: [{ key: 'x-api-key', value: '' }],
        },
    },
};

function cloneTemplateSite(name) {
    const template = SITE_TEMPLATES[name];
    if (!template) return { name, cookie: '', headers: [] };
    return {
        ...template.site,
        headers: template.site.headers.map(h => ({ ...h })),
    };
}

function templateUsesCookie(name) {
    const template = SITE_TEMPLATES[name];
    return template ? template.usesCookie !== false : true;
}

export default defineComponent({
    name: 'SitesEditor',
    components: { HeadersEditor },
    props: {
        modelValue: { type: Array, default: () => [] },
        supported: { type: Array, default: () => [] },
        disabled: { type: Boolean, default: false },
    },
    emits: ['update:modelValue', 'test'],
    setup(props, { emit }) {
        const sites = computed(() => props.modelValue || []);
        const selectedTemplate = ref(Object.keys(SITE_TEMPLATES)[0] || '');

        const templateOptions = computed(() => {
            const supported = props.supported.length ? props.supported : Object.keys(SITE_TEMPLATES);
            return supported.map(name => ({
                name,
                label: SITE_TEMPLATES[name]?.label || name,
                description: SITE_TEMPLATES[name]?.description || '内置站点模板',
                configured: sites.value.some(site => site.name === name),
            }));
        });

        const addableTemplateOptions = computed(() =>
            templateOptions.value.filter(option => !option.configured),
        );

        function updateField(idx, field, value) {
            const next = sites.value.map((s, i) =>
                i === idx ? { ...s, [field]: value } : s,
            );
            emit('update:modelValue', next);
        }
        function updateTemplate(idx, name) {
            const nextTemplate = cloneTemplateSite(name);
            const next = sites.value.map((s, i) =>
                i === idx
                    ? {
                        ...nextTemplate,
                        cookie: templateUsesCookie(name) ? (s.cookie || nextTemplate.cookie) : '',
                    }
                    : s,
            );
            emit('update:modelValue', next);
        }
        function usesCookie(name) {
            return templateUsesCookie(name);
        }
        function updateHeaders(idx, headers) {
            updateField(idx, 'headers', headers);
        }
        function addSite() {
            const name = selectedTemplate.value || addableTemplateOptions.value[0]?.name;
            if (!name) return;
            emit('update:modelValue', [
                ...sites.value,
                cloneTemplateSite(name),
            ]);
        }
        function removeSite(idx) {
            emit('update:modelValue', sites.value.filter((_, i) => i !== idx));
        }
        function isSupported(name) {
            return !name || templateOptions.value.some(option => option.name === name);
        }
        function testSite(site) {
            emit('test', site);
        }
        return {
            sites,
            selectedTemplate,
            templateOptions,
            addableTemplateOptions,
            updateField,
            updateTemplate,
            usesCookie,
            updateHeaders,
            addSite,
            removeSite,
            isSupported,
            testSite,
        };
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
                        <div>
                            <el-button
                                size="small" plain
                                :disabled="disabled || !site.name"
                                @click="testSite(site)">测试此站点</el-button>
                            <el-button
                                type="danger" plain size="small"
                                :disabled="disabled"
                                @click="removeSite(idx)">删除此站点</el-button>
                        </div>
                    </div>
                </template>
                <el-form label-position="top">
                    <el-form-item label="站点模板">
                        <el-select
                            style="width:100%;"
                            :model-value="site.name"
                            placeholder="选择站点模板"
                            :disabled="disabled"
                            @update:model-value="v => updateTemplate(idx, v)">
                            <el-option
                                v-if="site.name && !isSupported(site.name)"
                                :label="site.name + '（未支持）'"
                                :value="site.name"
                                disabled />
                            <el-option
                                v-for="option in templateOptions"
                                :key="option.name"
                                :label="option.label"
                                :value="option.name">
                                <div class="site-option-row">
                                    <span>{{ option.label }}</span>
                                    <small>{{ option.description }}</small>
                                </div>
                            </el-option>
                        </el-select>
                        <div class="field-help">
                            站点名称由模板写入配置，用于选择对应的抓取解析器。
                        </div>
                        <el-alert
                            v-if="!isSupported(site.name)"
                            type="warning"
                            :closable="false"
                            show-icon
                            style="margin-top:8px;"
                            :title="'当前配置中的站点 “' + site.name + '” 不在内置模板中，运行时可能失败。支持：' + templateOptions.map(s => s.label).join(', ')" />
                    </el-form-item>
                    <el-form-item v-if="usesCookie(site.name)" label="Cookie（可选）">
                        <el-input
                            type="textarea"
                            :rows="2"
                            :model-value="site.cookie"
                            placeholder="留空则保留原值"
                            :disabled="disabled"
                            @update:model-value="v => updateField(idx, 'cookie', v)" />
                        <div class="field-help">
                            用于以你的账号访问 PT 站点。若站点改用 Header 鉴权，可不填 Cookie；留空或保持星号会沿用原配置。
                        </div>
                    </el-form-item>
                    <el-form-item label="Headers">
                        <HeadersEditor
                            :model-value="site.headers"
                            :disabled="disabled"
                            @update:model-value="h => updateHeaders(idx, h)" />
                        <div class="field-help">
                            需要额外请求头时填写，例如 API Key、User-Agent 或站点要求的鉴权头。敏感值会被隐藏，留空会保留原值。
                        </div>
                    </el-form-item>
                </el-form>
            </el-card>
            <div class="site-add-row">
                <el-select
                    v-model="selectedTemplate"
                    placeholder="选择站点模板"
                    :disabled="disabled || !addableTemplateOptions.length">
                    <el-option
                        v-for="option in addableTemplateOptions"
                        :key="option.name"
                        :label="option.label"
                        :value="option.name" />
                </el-select>
                <el-button
                    type="primary" plain
                    :disabled="disabled || !addableTemplateOptions.length"
                    @click="addSite">新增站点</el-button>
            </div>
        </div>
    `,
});
