import { defineComponent, reactive, ref, onMounted, onUnmounted } from 'vue';
import { api } from '../api.js';
import { formatBytes, formatSpeed, formatGiB, truncate } from '../utils.js';

const TIME_OPTIONS = [
    { value: 10, label: '10分钟' },
    { value: 30, label: '30分钟' },
    { value: 60, label: '1小时' },
    { value: 360, label: '6小时' },
    { value: 1440, label: '24小时' },
];

export default defineComponent({
    name: 'Dashboard',
    setup() {
        const stats = reactive({
            upspeed: 0,
            dlspeed: 0,
            up_total: 0,
            dl_total: 0,
            free_space: 0,
            timestamp: '',
        });
        const torrents = ref([]);
        const totalActive = ref(0);
        const selectedRange = ref(10);

        async function loadStats() {
            try {
                const data = await api.get('/api/stats');
                Object.assign(stats, data.status);
                torrents.value = data.torrents;
                totalActive.value = data.total_active;
            } catch (e) {
                console.error('加载统计数据出错:', e);
            }
        }

        async function loadHistory(minutes) {
            try {
                const data = await api.get(`/api/history?minutes=${minutes}`);
                const plotData = [
                    {
                        x: data.timestamps,
                        y: data.upspeed.map(s => s / (1024 * 1024)),
                        type: 'scatter', mode: 'lines',
                        name: '上传速度 (MiB/s)',
                        line: { color: '#67c23a' },
                    },
                    {
                        x: data.timestamps,
                        y: data.dlspeed.map(s => s / (1024 * 1024)),
                        type: 'scatter', mode: 'lines',
                        name: '下载速度 (MiB/s)',
                        line: { color: '#409eff' },
                    },
                ];
                const layout = {
                    margin: { l: 50, r: 30, t: 30, b: 60 },
                    xaxis: { title: '时间', automargin: true },
                    yaxis: { title: '速度 (MiB/s)' },
                    legend: { orientation: 'h', y: 1.15 },
                };
                window.Plotly.newPlot('speedChart', plotData, layout, { responsive: true });
            } catch (e) {
                console.error('加载历史数据出错:', e);
            }
        }

        function selectRange(value) {
            selectedRange.value = value;
            loadHistory(value);
        }

        let statsTimer = null;
        let historyTimer = null;

        onMounted(() => {
            loadStats();
            loadHistory(selectedRange.value);
            statsTimer = setInterval(loadStats, 10000);
            historyTimer = setInterval(() => loadHistory(selectedRange.value), 60000);
        });

        onUnmounted(() => {
            if (statsTimer) clearInterval(statsTimer);
            if (historyTimer) clearInterval(historyTimer);
            if (window.Plotly) window.Plotly.purge('speedChart');
        });

        return {
            stats,
            torrents,
            totalActive,
            selectedRange,
            timeOptions: TIME_OPTIONS,
            selectRange,
            formatBytes,
            formatSpeed,
            formatGiB,
            truncate,
        };
    },
    template: `
        <div>
            <el-row :gutter="16">
                <el-col :xs="12" :sm="6" v-for="card in [
                    { label: '上传速度', unit: 'MiB/s', val: formatSpeed(stats.upspeed) },
                    { label: '下载速度', unit: 'MiB/s', val: formatSpeed(stats.dlspeed) },
                    { label: '活跃种子数', unit: '', val: totalActive },
                    { label: '剩余空间', unit: 'GiB', val: formatGiB(stats.free_space) }
                ]" :key="card.label">
                    <el-card class="stat-card" shadow="hover">
                        <div class="stat-value">{{ card.val }}</div>
                        <div class="stat-label">
                            {{ card.label }}
                            <span class="speed-unit" v-if="card.unit">({{ card.unit }})</span>
                        </div>
                    </el-card>
                </el-col>
            </el-row>

            <el-card class="mt-4" shadow="hover" style="margin-top:16px;">
                <template #header>
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span>速度历史</span>
                        <el-radio-group :model-value="selectedRange" @update:model-value="selectRange" size="small">
                            <el-radio-button
                                v-for="opt in timeOptions"
                                :key="opt.value"
                                :label="opt.value">
                                {{ opt.label }}
                            </el-radio-button>
                        </el-radio-group>
                    </div>
                </template>
                <div id="speedChart"></div>
            </el-card>

            <el-card class="mt-4" shadow="hover" style="margin-top:16px;">
                <template #header>
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span>活跃种子</span>
                        <span style="color:#909399;font-size:12px;">
                            最后更新: {{ stats.timestamp || '-' }}
                        </span>
                    </div>
                </template>
                <el-table :data="torrents" stripe size="small">
                    <el-table-column label="名称" min-width="240">
                        <template #default="{ row }">
                            <el-tooltip :content="row.name" placement="top" :show-after="300">
                                <span>{{ truncate(row.name, 36) }}</span>
                            </el-tooltip>
                        </template>
                    </el-table-column>
                    <el-table-column prop="site" label="站点" width="100" />
                    <el-table-column label="上传速度" width="110">
                        <template #default="{ row }">{{ formatSpeed(row.upspeed) }} MiB/s</template>
                    </el-table-column>
                    <el-table-column label="下载速度" width="110">
                        <template #default="{ row }">{{ formatSpeed(row.dlspeed) }} MiB/s</template>
                    </el-table-column>
                    <el-table-column label="已上传" width="110">
                        <template #default="{ row }">{{ formatBytes(row.up_total) }}</template>
                    </el-table-column>
                    <el-table-column label="已下载" width="110">
                        <template #default="{ row }">{{ formatBytes(row.dl_total) }}</template>
                    </el-table-column>
                    <el-table-column prop="free_end_time" label="Free 截止" width="170" />
                    <el-table-column prop="score" label="分数" width="70" />
                    <template #empty>
                        <span style="color:#909399;">暂无活跃种子</span>
                    </template>
                </el-table>
            </el-card>
        </div>
    `,
});
