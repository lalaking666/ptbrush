import { defineComponent, computed } from 'vue';

const UNITS = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];

export default defineComponent({
    name: 'SizeInput',
    props: {
        modelValue: { type: Object, default: () => ({ value: 0, unit: 'GiB' }) },
        disabled: { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const value = computed({
            get: () => props.modelValue?.value ?? 0,
            set: (v) => emit('update:modelValue', {
                value: v ?? 0,
                unit: props.modelValue?.unit ?? 'GiB',
            }),
        });
        const unit = computed({
            get: () => props.modelValue?.unit ?? 'GiB',
            set: (u) => emit('update:modelValue', {
                value: props.modelValue?.value ?? 0,
                unit: u,
            }),
        });
        return { value, unit, UNITS };
    },
    template: `
        <div style="display:flex;gap:8px;">
            <el-input-number
                v-model="value"
                :min="0"
                :step="1"
                :precision="3"
                :disabled="disabled"
                controls-position="right"
                style="flex:1;" />
            <el-select v-model="unit" :disabled="disabled" style="width:100px;">
                <el-option v-for="u in UNITS" :key="u" :label="u" :value="u" />
            </el-select>
        </div>
    `,
});
