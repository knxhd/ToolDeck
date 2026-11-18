<template>
  <div class="collection-doc-pane">
    <!-- 文档工具栏：编辑 / 分屏 / 预览 切换 + 全屏（与接口文档保持一致） -->
    <div class="cdp-head">
      <span class="cdp-title" :title="tab.title">{{ tab.title }}</span>
      <div class="cdp-actions">
        <a-radio-group v-model="mode" type="button" size="small">
          <a-radio value="edit">编辑</a-radio>
          <a-radio value="split">分屏</a-radio>
          <a-radio value="preview">预览</a-radio>
        </a-radio-group>
        <a-button size="small" type="text" title="全屏查看 (Esc 退出)" @click="fullscreen = true">
          <template #icon><icon-fullscreen /></template>
        </a-button>
      </div>
    </div>

    <div class="cdp-body">
      <DocumentEditor
        v-model="doc"
        v-model:mode="mode"
        v-model:fullscreen="fullscreen"
        :title="tab.title"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import DocumentEditor from '@/components/DocumentEditor.vue'
import type { DocMode, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

/** 编辑中的 Markdown；初始取标签上的快照（节点文档或未保存修改）。 */
const doc = ref(props.tab.doc ?? '')
/** 已有文档默认预览，否则默认分屏便于边写边看。 */
const mode = ref<DocMode>(doc.value.trim() ? 'preview' : 'split')
const fullscreen = ref(false)

/** 进入编辑时的内容快照，用于判断是否有未保存修改。 */
let snapshot = props.tab.doc ?? ''

watch(doc, (v) => {
  props.tab.doc = v
  props.tab.dirty = v !== snapshot
})

/** 保存完成后（父级把 dirty 置回 false），以当前内容作为新快照。 */
watch(
  () => props.tab.dirty,
  (dirty) => {
    if (!dirty) snapshot = doc.value
  },
)
</script>

<style lang="less" scoped>
.collection-doc-pane {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部工具栏：左标题，右模式切换与全屏 */
.cdp-head {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 12px;
  border-bottom: 1px solid var(--color-border-1);
  background: var(--color-bg-1);
}

.cdp-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--color-text-3);
}

.cdp-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cdp-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
