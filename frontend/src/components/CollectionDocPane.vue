<template>
  <div class="collection-doc-pane">
    <DocumentEditor
      v-model="doc"
      v-model:mode="mode"
      v-model:fullscreen="fullscreen"
      :title="tab.title"
    />
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
</style>
