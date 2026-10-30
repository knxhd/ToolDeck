<template>
  <a-modal :visible="visible" width="900px" :footer="false" unmount-on-close @cancel="onClose">
    <template #title>Generate Code</template>

    <div class="gc-toolbar">
      <a-select v-model="lang" style="width: 180px" @change="onLangChange">
        <a-option v-for="l in CODE_LANGUAGES" :key="l.key" :value="l.key">{{ l.label }}</a-option>
      </a-select>
      <a-radio-group v-model="variant" type="button">
        <a-radio v-for="v in currentLang.variants" :key="v.key" :value="v.key">{{ v.label }}</a-radio>
      </a-radio-group>
      <a-checkbox v-model="interpolate" class="gc-interp">Interpolate Variables</a-checkbox>
    </div>

    <div class="gc-code">
      <MonacoEditor :model-value="code" :language="currentLang.monaco" read-only height="440px" />
      <a-tooltip content="复制代码">
        <a-button class="gc-copy" size="small" @click="onCopy">
          <template #icon><icon-copy /></template>
        </a-button>
      </a-tooltip>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useEnvironmentsStore } from '@/stores/environments'
import { CODE_LANGUAGES, generateCode } from '@/utils/codegen'
import type { CodeLang, CodeLanguage } from '@/utils/codegen'
import { resolveRequest } from '@/utils/env'
import { toast } from '@/utils/feedback'
import type { HttpRequestData } from '@/api/types'

const props = defineProps<{ visible: boolean; request: HttpRequestData }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const env = useEnvironmentsStore()

/** 记住上次选择的语言 / 实现 / 插值开关。 */
const PREF_KEY = 'api-tool.codegen'

interface CodegenPref {
  lang?: CodeLang
  variant?: string
  interpolate?: boolean
}

function loadPref(): CodegenPref {
  try {
    return JSON.parse(localStorage.getItem(PREF_KEY) || '{}') as CodegenPref
  } catch {
    return {}
  }
}

const pref = loadPref()
const initLang = CODE_LANGUAGES.find((l) => l.key === pref.lang) ?? CODE_LANGUAGES[0]

const lang = ref<CodeLang>(initLang.key)
const variant = ref<string>(
  initLang.variants.some((v) => v.key === pref.variant) ? pref.variant! : initLang.variants[0].key,
)
const interpolate = ref<boolean>(pref.interpolate ?? true)

const currentLang = computed<CodeLanguage>(
  () => CODE_LANGUAGES.find((l) => l.key === lang.value) ?? CODE_LANGUAGES[0],
)

/** 切换语言时默认选中第一个实现。 */
function onLangChange() {
  variant.value = currentLang.value.variants[0].key
}

watch([lang, variant, interpolate], () => {
  try {
    localStorage.setItem(
      PREF_KEY,
      JSON.stringify({ lang: lang.value, variant: variant.value, interpolate: interpolate.value }),
    )
  } catch {
    /* 忽略存储异常 */
  }
})

const code = computed(() => {
  const req = interpolate.value ? resolveRequest(props.request, env.scopeVars) : props.request
  return generateCode(req, lang.value, variant.value)
})

async function onCopy() {
  try {
    await navigator.clipboard.writeText(code.value)
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败，请手动选择复制')
  }
}

function onClose() {
  emit('update:visible', false)
}
</script>

<style lang="less" scoped>
.gc-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;

  .gc-interp {
    margin-left: auto;
  }
}

.gc-code {
  position: relative;

  .gc-copy {
    position: absolute;
    top: 8px;
    right: 20px;
    z-index: 10;
  }
}
</style>
