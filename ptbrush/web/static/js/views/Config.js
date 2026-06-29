import { defineComponent, reactive, ref, onMounted } from 'vue';
import { api } from '../api.js';
import SizeInput from '../components/SizeInput.js';
import SpeedInput from '../components/SpeedInput.js';
import WorkTimePicker from '../components/WorkTimePicker.js';
import SitesEditor from '../components/SitesEditor.js';

export default defineComponent({
    name: 'Config',
    components: { SizeInput, SpeedInput, WorkTimePicker, SitesEditor },
    setup() {
        const form = reactive({
            brush: {
                min_disk_space: { value: 0, unit: 'GiB' },
                torrent_max_size: { value: 0, unit: 'GiB' },
                expect_upload_speed: { value: 0, unit: 'MiB/s' },
                expect_download_speed: { value: 0, unit: 'MiB/s' },
                max_downloading_torrents: 6,
                max_no_activate_time: 10,
                work_time: '',
                work_time_hours: [],
                upload_cycle: 600,
                download_cycle: 600,
            },
            downloader: { url: '', username: '', password: '' },
            sites: [],
        });
        const supportedSites = ref([]);
        const loaded = ref(false);
        const loading = ref(false);
        // 只读模式（Commit 1 阶段；Commit 2 会改成 false 开启编辑）
        const readonly = ref(true);

        async function load() {
            loading.value = true;
            try {
                const data = await api.get('/api/config');
                Object.assign(form.brush, data.brush);
                Object.assign(form.downloader, data.downloader);
                form.sites = data.sites || [];
                supportedSites.value = data.supported_sites || [];
                loaded.value = true;
            } catch (e) {
                window.ElMessage?.error?.(e.message || '加载失败');
            } finally {
                loading.value = false;
            }
        }

        onMounted(load);

        return { form, supportedSites, loaded, loading, readonly, load };
    },
    template: `
        <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <h2 style="margin:0;">配置</h2>
                <el-button :loading="loading" plain @click="load">重新加载</el-button>
            </div>

            <el-alert
                v-if="readonly"
                type="info"
                :closable="false"
                show-icon
                style="margin-bottom:16px;"
                title="当前为只读预览。下一阶段会开放编辑、测试连接和保存功能。" />

            <div v-if="loading && !loaded" style="text-align:center;padding:48px;color:#909399;">
                加载中...
            </div>

            <template v-if="loaded">
                <el-card style="margin-bottom:16px;" shadow="hover">
                    <template #header><strong>刷流策略</strong></template>
                    <el-form label-position="top">
                        <el-row :gutter="16">
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="最小剩余磁盘空间">
                                    <SizeInput v-model="form.brush.min_disk_space" :disabled="readonly" />
                                    <div class="field-help">磁盘剩余空间低于此值时将不再新增刷流种子。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="单个种子最大体积">
                                    <SizeInput v-model="form.brush.torrent_max_size" :disabled="readonly" />
                                    <div class="field-help">超过此体积的大包种子会被自动瘦身（仅下载部分文件）。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="期望上传速度">
                                    <SpeedInput v-model="form.brush.expect_upload_speed" :disabled="readonly" />
                                    <div class="field-help">建议为上传带宽的 50%（30Mbps 带宽 ≈ 1.875 MiB/s）。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="期望下载速度">
                                    <SpeedInput v-model="form.brush.expect_download_speed" :disabled="readonly" />
                                    <div class="field-help">下载速度低于此值时才会触发新增刷流任务。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="最大同时下载种子数">
                                    <el-input-number
                                        v-model="form.brush.max_downloading_torrents"
                                        :min="1" :max="100"
                                        :disabled="readonly"
                                        controls-position="right" style="width:100%;" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="无活跃超时（分钟）">
                                    <el-input-number
                                        v-model="form.brush.max_no_activate_time"
                                        :min="1"
                                        :disabled="readonly"
                                        controls-position="right" style="width:100%;" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="工作时间字符串">
                                    <el-input :model-value="form.brush.work_time || '（24 小时）'" disabled />
                                </el-form-item>
                            </el-col>
                            <el-col :span="24">
                                <el-form-item label="工作时间（点击小时格切换）">
                                    <WorkTimePicker v-model="form.brush.work_time" :disabled="readonly" />
                                    <div class="field-help">绿色格子表示该小时允许新增刷流任务；不选则全天运行。</div>
                                </el-form-item>
                            </el-col>
                        </el-row>
                    </el-form>
                </el-card>

                <el-card style="margin-bottom:16px;" shadow="hover">
                    <template #header><strong>qBittorrent 下载器</strong></template>
                    <el-form label-position="top">
                        <el-row :gutter="16">
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="WebUI 地址">
                                    <el-input v-model="form.downloader.url" :disabled="readonly" placeholder="http://127.0.0.1:8080" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="6">
                                <el-form-item label="用户名">
                                    <el-input v-model="form.downloader.username" :disabled="readonly" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="6">
                                <el-form-item label="密码">
                                    <el-input
                                        v-model="form.downloader.password"
                                        type="password" show-password
                                        :disabled="readonly"
                                        placeholder="留空则保留原值" />
                                </el-form-item>
                            </el-col>
                        </el-row>
                    </el-form>
                </el-card>

                <el-card shadow="hover">
                    <template #header>
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <strong>PT 站点</strong>
                            <el-tag v-for="s in supportedSites" :key="s" type="success" size="small" style="margin-left:6px;">{{ s }}</el-tag>
                        </div>
                    </template>
                    <SitesEditor
                        v-model="form.sites"
                        :supported="supportedSites"
                        :disabled="readonly" />
                </el-card>
            </template>
        </div>
    `,
});
