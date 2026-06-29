import { defineComponent, computed } from 'vue';

const UNITS = ['B/s', 'KiB/s', 'MiB/s', 'GiB/s'];

const DEFAULT_PRESETS = [
    { value: 1.875, unit: 'MiB/s', label: '1.875 MiB/s (30M)' },
    { value: 5, unit: 'MiB/s', label: '5 MiB/s (80M)' },
    { value: 15, unit: 'MiB/s', label: '15 MiB/s (240M)' },
    { value: 30, unit: 'MiB/s', label: '30 MiB/s (500M)' },
];

export default defineComponent({
    name: 'SpeedInput',
    props: {
        modelValue: { type: Object, default: () => ({ value: 0, unit: 'MiB/s' }) },
        disabled: { type: Boolean, default: false },
        presets: { type: Array, default: () => DEFAULT_PRESETS },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const value = computed({
            get: () => props.modelValue?.value ?? 0,
            set: (v) => emit('update:modelValue', {
                value: v ?? 0,
                unit: props.modelValue?.unit ?? 'MiB/s',
            }),
        });
        const unit = computed({
            get: () => props.modelValue?.unit ?? 'MiB/s',
            set: (u) => emit('update:modelValue', {
                value: props.modelValue?.value ?? 0,
                unit: u,
            }),
        });
        function applyPreset(p) {
            emit('update:modelValue', { value: p.value, unit: p.unit });
        }
        return { value, unit, UNITS, applyPreset };
    },
    template: `
        <div>
            <div style="display:flex;gap:8px;">
                <el-input-number
                    v-model="value"
                    :min="0"
                    :step="0.5"
                    :precision="3"
                    :disabled="disabled"
                    controls-position="right"
                    style="flex:1;" />
                <el-select v-model="unit" :disabled="disabled" style="width:100px;">
                    <el-option v-for="u in UNITS" :key="u" :label="u" :value="u" />
                </el-select>
            </div>
            <div class="preset-row" v-if="!disabled">
                <el-button
                    v-for="p in presets" :key="p.label"
                    size="small" plain
                    @click="applyPreset(p)">
                    {{ p.label }}
                </el-button>
            </div>
        </div>
    `,
});
