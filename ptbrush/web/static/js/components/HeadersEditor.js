import { defineComponent } from 'vue';

export default defineComponent({
    name: 'HeadersEditor',
    props: {
        modelValue: { type: Array, default: () => [] },
        disabled: { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        function update(idx, field, value) {
            const next = props.modelValue.map((row, i) =>
                i === idx ? { ...row, [field]: value } : row,
            );
            emit('update:modelValue', next);
        }
        function addRow() {
            emit('update:modelValue', [...props.modelValue, { key: '', value: '' }]);
        }
        function removeRow(idx) {
            emit('update:modelValue', props.modelValue.filter((_, i) => i !== idx));
        }
        return { update, addRow, removeRow };
    },
    template: `
        <div>
            <div v-if="!modelValue.length" style="color:#909399;font-size:12px;margin-bottom:8px;">
                尚未配置 Header
            </div>
            <div v-for="(row, idx) in modelValue" :key="idx" class="headers-row">
                <el-input
                    :model-value="row.key"
                    placeholder="key (如 x-api-key)"
                    :disabled="disabled"
                    @update:model-value="v => update(idx, 'key', v)" />
                <el-input
                    :model-value="row.value"
                    type="password"
                    show-password
                    placeholder="value（留空则保留原值）"
                    :disabled="disabled"
                    @update:model-value="v => update(idx, 'value', v)" />
                <el-button
                    type="danger" plain size="small"
                    :disabled="disabled"
                    @click="removeRow(idx)">删除</el-button>
            </div>
            <el-button
                size="small" plain
                :disabled="disabled"
                @click="addRow">+ 添加 Header</el-button>
        </div>
    `,
});
