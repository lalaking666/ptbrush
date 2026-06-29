import { defineComponent, reactive, ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { api } from '../api.js';
import SizeInput from '../components/SizeInput.js';
import SpeedInput from '../components/SpeedInput.js';
import WorkTimePicker from '../components/WorkTimePicker.js';
import SitesEditor from '../components/SitesEditor.js';
import PasswordCard from '../components/PasswordCard.js';

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
    components: { SizeInput, SpeedInput, WorkTimePicker, SitesEditor, PasswordCard },
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
            if (!form.downloader.url) {
                ElMessage.warning('请先填写 qBittorrent WebUI 地址');
                return;
            }
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

        function disableInactiveCleanup() {
            form.brush.max_no_activate_time = 0;
        }

        onMounted(load);

        return {
            form, supportedSites, loaded, loading, saving, testing, loginRequired,
            load, save, testDownloader, testSite, disableInactiveCleanup,
        };
    },
    template: `
        <div class="config-page">
            <div class="config-page-header">
                <h2>配置</h2>
                <div class="config-actions">
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
                        <div class="form-stack">
                            <el-form-item label="最小剩余磁盘空间">
                                <SizeInput v-model="form.brush.min_disk_space" />
                                <div class="field-help">
                                    指 qBittorrent 通过 Web API 返回的剩余空间，通常是 qBittorrent 默认下载目录所在磁盘或 Docker 挂载卷。低于此值时只会停止新增刷流种子，已存在任务仍按清理规则处理。
                                </div>
                            </el-form-item>
                            <el-form-item label="单个种子最大体积">
                                <SizeInput v-model="form.brush.torrent_max_size" />
                                <div class="field-help">
                                    这是“大包拆包”后的目标下载上限，不是种子大小筛选条件。遇到大包时仍会加入 qBittorrent，再把部分文件设为“不下载”，只保留一部分文件参与下载和上传，用较小磁盘占用吃到大包的刷流收益。
                                </div>
                            </el-form-item>
                            <el-form-item label="期望上传速度">
                                <SpeedInput v-model="form.brush.expect_upload_speed" />
                                <div class="field-help">
                                    最近一个上传统计周期内，qBittorrent 平均上传速度达到此值后会暂停新增刷流任务。建议设置为可用上传带宽的约 50%，例如 30Mbps 上传约等于 1.875 MiB/s。
                                </div>
                            </el-form-item>
                            <el-form-item label="期望下载速度">
                                <SpeedInput v-model="form.brush.expect_download_speed" />
                                <div class="field-help">
                                    最近一个下载统计周期内，qBittorrent 的下载峰值低于此值时才会新增任务。这个值越低，新增任务越保守；越高，则更容易继续加种。
                                </div>
                            </el-form-item>
                            <el-form-item label="最大同时下载种子数">
                                <el-input-number
                                    v-model="form.brush.max_downloading_torrents"
                                    :min="1" :max="100"
                                    controls-position="right" style="width:100%;" />
                                <div class="field-help">
                                    只统计本工具加入到 qBittorrent 的未完成刷流任务。达到上限后不再新增，已完成或其他分类的种子不计入这个数量。
                                </div>
                            </el-form-item>
                            <el-form-item label="无活跃超时（分钟）">
                                <div class="number-action-row">
                                    <el-input-number
                                        v-model="form.brush.max_no_activate_time"
                                        :min="0"
                                        controls-position="right" />
                                    <el-button plain @click="disableInactiveCleanup">关闭清理</el-button>
                                </div>
                                <div class="field-help">
                                    刷流种子连续无上传且无下载超过此时间后会被删除，避免占用硬盘空间。如果不需要定时清理，设为 0 即可关闭；手动配置为负数也会关闭。1-4 分钟会按 5 分钟处理，防止误删短暂无速度的任务。
                                </div>
                            </el-form-item>
                            <el-form-item label="当前工作时间字符串">
                                <el-input :model-value="form.brush.work_time || '（24 小时）'" disabled />
                                <div class="field-help">
                                    由下方小时格自动生成并写入配置文件。显示为“24 小时”时，表示不限制新增刷流任务的时间段。
                                </div>
                            </el-form-item>
                            <el-form-item label="工作时间（点击小时格切换）">
                                <WorkTimePicker v-model="form.brush.work_time" />
                                <div class="field-help">
                                    绿色格子表示该小时允许新增刷流任务；不选任何小时则全天允许。它只限制“新增刷流”，状态采集、清理和已有任务不会因此停止。
                                </div>
                            </el-form-item>
                        </div>
                    </el-form>
                </el-card>

                <el-card style="margin-bottom:16px;" shadow="hover">
                    <template #header>
                        <div class="card-header-row">
                            <strong>qBittorrent 下载器</strong>
                            <el-button
                                size="small" plain
                                native-type="button"
                                :loading="testing"
                                @click="testDownloader">
                                测试连接
                            </el-button>
                        </div>
                    </template>
                    <el-form label-position="top">
                        <div class="form-stack">
                            <el-form-item label="WebUI 地址">
                                <el-input v-model="form.downloader.url" placeholder="http://127.0.0.1:8080" />
                                <div class="field-help">
                                    qBittorrent Web UI 的访问地址。Docker 部署时请填写 PTBrush 容器能够访问到的地址，而不一定是浏览器里的 localhost。
                                </div>
                            </el-form-item>
                            <el-form-item label="用户名">
                                <el-input v-model="form.downloader.username" />
                                <div class="field-help">
                                    qBittorrent Web UI 登录用户名，用于读取状态、添加种子、调整文件优先级和删除本工具管理的任务。
                                </div>
                            </el-form-item>
                            <el-form-item label="密码">
                                <el-input
                                    v-model="form.downloader.password"
                                    type="password" show-password
                                    placeholder="留空则保留原值" />
                                <div class="field-help">
                                    已保存的密码会被隐藏显示。留空或保持星号不会覆盖原密码；只有输入新密码时才会更新。
                                </div>
                            </el-form-item>
                        </div>
                    </el-form>
                </el-card>

                <el-card shadow="hover">
                    <template #header>
                        <div class="card-header-row">
                            <strong>PT 站点</strong>
                            <div class="supported-sites">
                                <span>支持：</span>
                                <el-tag v-for="s in supportedSites" :key="s" type="success" size="small">{{ s }}</el-tag>
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
