<template>
    <div class="body-toolbar">
        <el-select v-model="formatType" size="small" style="width: 110px">
            <el-option label="Text" value="text" />
            <el-option label="JSON" value="json" />
            <el-option label="HTML" value="html" />
        </el-select>
        <span class="content-type">{{ contentTypeName }}</span>
    </div>
    <div class="body-view">
        <template>
            <MonacoEditor v-if="formatType !== 'html'" :model-value="rendered(data)"
                :language="formatType === 'json' ? 'json' : 'plaintext'" read-only height="100%" />
            <iframe v-if="formatType === 'html'" class="html-frame" :srcdoc="data" sandbox=""></iframe>
        </template>
    </div>

</template>

<script setup lang='ts'>
import { ref } from 'vue'
import MonacoEditor from '@/components/MonacoEditor.vue'
const props = defineProps({
    data: {
        type: String,
        required: true
    }
})

const formatType = ref('text')

const rendered = (raw: string) => {
    if (formatType.value !== 'json' || !raw) {
        return raw || ''
    }
    try {
        return JSON.stringify(JSON.parse(raw), null, 2)
    } catch {
        return raw
    }
}
</script>

<style scoped lang='less'>
.body-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 2px 0 6px;

    .content-type {
        font-size: 12px;
        color: var(--el-text-color-placeholder);
    }
}


.body-view {
    overflow: auto;
    .html-frame {
        width: 100%;
        height: 100%;
        border: 1px solid var(--el-border-color);
        border-radius: 4px;
        background: #fff;
    }
}
</style>
