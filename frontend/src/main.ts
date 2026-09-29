import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ArcoVue from '@arco-design/web-vue'
import ArcoVueIcon from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/dist/arco.css'

// Monaco Editor worker 配置（Vite 环境必需）
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'

import VMdPreview from '@kangc/v-md-editor/lib/preview';
import '@kangc/v-md-editor/lib/style/preview.css';
import githubTheme from '@kangc/v-md-editor/lib/theme/github.js';
import '@kangc/v-md-editor/lib/theme/style/github.css';

// monaco-editor 已提供全局 MonacoEnvironment 类型声明，此处仅赋值
self.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    if (label === 'json') return new jsonWorker()
    return new editorWorker()
  },
}

// highlightjs
import hljs from 'highlight.js';

VMdPreview.use(githubTheme, {
  Hljs: hljs,
});

import App from './App.vue'
import router from './router'
import { useSettingsStore } from './stores/settings'
import './styles/main.less'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(VMdPreview);
app.use(router)
app.use(ArcoVue)
app.use(ArcoVueIcon)

useSettingsStore(pinia).init()

app.mount('#app')
