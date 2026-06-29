import { defineComponent } from 'vue';

export default defineComponent({
    name: 'AppShell',
    template: `
        <el-container style="height:100vh;">
            <el-header class="app-header" height="56px">
                <div class="app-brand">PTBrush</div>
                <el-menu
                    mode="horizontal"
                    :ellipsis="false"
                    :default-active="$route.path"
                    background-color="#1f2937"
                    text-color="#cbd5e1"
                    active-text-color="#67c23a"
                    router>
                    <el-menu-item index="/dashboard">仪表盘</el-menu-item>
                    <el-menu-item index="/config">配置</el-menu-item>
                </el-menu>
            </el-header>
            <el-main>
                <router-view />
            </el-main>
        </el-container>
    `,
});
