import { defineComponent, reactive, ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { api } from '../api.js';
import SizeInput from '../components/SizeInput.js';
import SpeedInput from '../components/SpeedInput.js';
import WorkTimePicker from '../components/WorkTimePicker.js';
import SitesEditor from '../components/SitesEditor.js';
import PasswordCard from '../components/PasswordCard.js';
import ConfigToolbar from '../components/ConfigToolbar.js';

function emptyForm() {
    return {
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
    };
}

function stripPayload(form) {
    return {
        brush: {
            min_disk_space: { value: form.brush.min_disk_space.value, unit: form.brush.min_disk_space.unit },
            torrent_max_size: { value: form.brush.torrent_max_size.value, unit: form.brush.torrent_max_size.unit },
            expect_upload_speed: { value: form.brush.expect_upload_speed.value, unit: form.brush.expect_upload_speed.unit },
            expect_download_speed: { value: form.brush.expect_download_speed.value, unit: form.brush.expect_download_speed.unit },
            max_downloading_torrents: form.brush.max_downloading_torrents,
            max_no_activate_time: form.brush.max_no_activate_time,
            work_time: form.brush.work_time || '',
            upload_cycle: form.brush.upload_cycle,
            download_cycle: form.brush.download_cycle,
        },
        downloader: { ...form.downloader },
        sites: form.sites.map(s => ({
            name: s.name,
            cookie: s.cookie || '',
            headers: (s.headers || []).map(h => ({ key: h.key, value: h.value || '' })),
        })),
    };
}

export default defineComponent({
    name: 'Config',
    components: { SizeInput, SpeedInput, WorkTimePicker, SitesEditor, PasswordCard, ConfigToolbar },
    setup() {
        const form = reactive(emptyForm());
        const supportedSites = ref([]);
        const loaded = ref(false);
        const loading = ref(false);
        const saving = ref(false);
        const testing = ref(false);
        const loginRequired = ref(false);

        async function load() {
            loading.value = true;
            try {
                const [data, auth] = await Promise.all([
                    api.get('/api/config'),
                    api.get('/api/auth/state'),
                ]);
                Object.assign(form.brush, data.brush);
                Object.assign(form.downloader, data.downloader);
                form.sites = data.sites || [];
                supportedSites.value = data.supported_sites || [];
                loginRequired.value = !!auth?.login_required;
                loaded.value = true;
            } catch (e) {
                ElMessage.error(e.message || '加载失败');
            } finally {
                loading.value = false;
            }
        }

        async function save() {
            saving.value = true;
            try {
                const payload = stripPayload(form);
                const res = await api.put('/api/config', payload);
                ElMessage.success(res?.message || '已保存');
                await load();
            } catch (e) {
                if (e.details?.length) {
                    const first = e.details[0];
                    ElMessage.error(`${first.loc?.join('.')}: ${first.msg}`);
                } else {
                    ElMessage.error(e.message || '保存失败');
                }
            } finally {
                saving.value = false;
            }
        }

        async function testDownloader() {
            testing.value = true;
            try {
                const res = await api.post('/api/config/test-downloader', {
                    url: form.downloader.url,
                    username: form.downloader.username,
                    password: form.downloader.password,
                });
                if (res?.ok) ElMessage.success(res.message);
                else ElMessage.error(res?.message || '连接失败');
            } catch (e) {
                ElMessage.error(e.message || '请求失败');
            } finally {
                testing.value = false;
            }
        }

        async function testSite(site) {
            try {
                const res = await api.post('/api/config/test-site', {
                    name: site.name,
                    cookie: site.cookie,
                    headers: site.headers,
                });
                if (res?.ok) ElMessage.success(res.message);
                else ElMessage.error(res?.message || '站点测试失败');
            } catch (e) {
                ElMessage.error(e.message || '请求失败');
            }
        }

        onMounted(load);

        return {
            form, supportedSites, loaded, loading, saving, testing, loginRequired,
            load, save, testDownloader, testSite,
        };
    },
    template: `
        <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <h2 style="margin:0;">配置</h2>
                <div>
                    <ConfigToolbar @imported="load" />
                    <el-button :loading="loading" plain @click="load">重新加载</el-button>
                    <el-button type="primary" :loading="saving" :disabled="!loaded" @click="save">保存</el-button>
                </div>
            </div>

            <el-alert
                type="warning"
                :closable="false"
                show-icon
                style="margin-bottom:16px;"
                title="提示：通过 UI 保存会重写 config.toml 并丢失原有注释，原文件备份在 config.toml.bak。配置将在下次任务周期（最长 15 分钟）自动生效，无需重启。" />

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
                                    <SizeInput v-model="form.brush.min_disk_space" />
                                    <div class="field-help">磁盘剩余空间低于此值时将不再新增刷流种子。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="单个种子最大体积">
                                    <SizeInput v-model="form.brush.torrent_max_size" />
                                    <div class="field-help">超过此体积的大包种子会被自动瘦身（仅下载部分文件）。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="期望上传速度">
                                    <SpeedInput v-model="form.brush.expect_upload_speed" />
                                    <div class="field-help">建议为上传带宽的 50%（30Mbps 带宽 ≈ 1.875 MiB/s）。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="期望下载速度">
                                    <SpeedInput v-model="form.brush.expect_download_speed" />
                                    <div class="field-help">下载速度低于此值时才会触发新增刷流任务。</div>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="最大同时下载种子数">
                                    <el-input-number
                                        v-model="form.brush.max_downloading_torrents"
                                        :min="1" :max="100"
                                        controls-position="right" style="width:100%;" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="无活跃超时（分钟）">
                                    <el-input-number
                                        v-model="form.brush.max_no_activate_time"
                                        :min="1"
                                        controls-position="right" style="width:100%;" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="当前工作时间字符串">
                                    <el-input :model-value="form.brush.work_time || '（24 小时）'" disabled />
                                </el-form-item>
                            </el-col>
                            <el-col :span="24">
                                <el-form-item label="工作时间（点击小时格切换）">
                                    <WorkTimePicker v-model="form.brush.work_time" />
                                    <div class="field-help">绿色格子表示该小时允许新增刷流任务；不选则全天运行。</div>
                                </el-form-item>
                            </el-col>
                        </el-row>
                    </el-form>
                </el-card>

                <el-card style="margin-bottom:16px;" shadow="hover">
                    <template #header>
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <strong>qBittorrent 下载器</strong>
                            <el-button size="small" plain :loading="testing" @click="testDownloader">测试连接</el-button>
                        </div>
                    </template>
                    <el-form label-position="top">
                        <el-row :gutter="16">
                            <el-col :xs="24" :sm="12">
                                <el-form-item label="WebUI 地址">
                                    <el-input v-model="form.downloader.url" placeholder="http://127.0.0.1:8080" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="6">
                                <el-form-item label="用户名">
                                    <el-input v-model="form.downloader.username" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="6">
                                <el-form-item label="密码">
                                    <el-input
                                        v-model="form.downloader.password"
                                        type="password" show-password
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
                            <div>
                                <span style="color:#909399;font-size:12px;margin-right:8px;">支持：</span>
                                <el-tag v-for="s in supportedSites" :key="s" type="success" size="small" style="margin-right:4px;">{{ s }}</el-tag>
                            </div>
                        </div>
                    </template>
                    <SitesEditor
                        v-model="form.sites"
                        :supported="supportedSites"
                        @test="testSite" />
                </el-card>

                <div style="margin-top:16px;">
                    <PasswordCard :login-required="loginRequired" />
                </div>
            </template>
        </div>
    `,
});
