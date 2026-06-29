import { defineComponent, computed } from 'vue';
import { expandWorkTime, compressWorkTime } from '../utils.js';

export default defineComponent({
    name: 'WorkTimePicker',
    props: {
        modelValue: { type: String, default: '' },
        disabled: { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const selected = computed(() => new Set(expandWorkTime(props.modelValue || '')));
        const hours = Array.from({ length: 24 }, (_, i) => i);
        function toggle(h) {
            if (props.disabled) return;
            const next = new Set(selected.value);
            if (next.has(h)) next.delete(h);
            else next.add(h);
            emit('update:modelValue', compressWorkTime([...next]));
        }
        return { selected, hours, toggle };
    },
    template: `
        <div class="hour-grid">
            <el-button
                v-for="h in hours" :key="h"
                size="small"
                :type="selected.has(h) ? 'success' : ''"
                :disabled="disabled"
                @click="toggle(h)">
                {{ h.toString().padStart(2, '0') }}
            </el-button>
        </div>
    `,
});
