<template>
  <a-modal :visible="modelValue" title="修改个人信息" width="460px" :mask-closable="false"
    @update:visible="(v: boolean) => emit('update:modelValue', v)">
    <div class="profile-form">
      <div class="avatar-block">
        <div class="avatar-preview" :title="'点击更换头像'" @click="pickFile">
          <img v-if="draft.avatar" :src="draft.avatar" alt="头像预览" />
          <span v-else class="avatar-initial">{{ initial }}</span>
          <span class="avatar-mask"><icon-camera /> 更换</span>
        </div>
        <div class="avatar-side">
          <div class="avatar-actions">
            <a-button size="small" @click="pickFile">
              <template #icon><icon-upload /></template>
              上传图片
            </a-button>
            <a-button size="small" :disabled="!draft.avatar" @click="draft.avatar = ''">
              移除
            </a-button>
          </div>
          <p class="avatar-tip">支持 JPG / PNG / WebP，原图 ≤ 1MB；保存时自动压缩到 20KB 以内。</p>
        </div>
      </div>

      <div class="form-row">
        <span class="form-label">昵称</span>
        <a-input v-model="draft.display_name" :max-length="32" show-word-limit placeholder="请输入显示名称" />
      </div>
      <div class="form-row">
        <span class="form-label">账号</span>
        <span class="form-static">{{ user.user?.username || '-' }}</span>
      </div>
    </div>

    <template #footer>
      <a-button @click="emit('update:modelValue', false)">取消</a-button>
      <a-button type="primary" :loading="saving" @click="onSave">保存</a-button>
    </template>

    <input ref="fileRef" type="file" accept="image/png,image/jpeg,image/webp" style="display:none"
      @change="onFileChange" />
  </a-modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import { useUserStore } from '@/stores/user'
import { toast } from '@/utils/feedback'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean]; saved: [] }>()

const user = useUserStore()
const fileRef = ref<HTMLInputElement | null>(null)
const saving = ref(false)
const draft = reactive({ display_name: '', avatar: '' })

/** 原图大小上限 1MB；入库 base64 上限 20KB（与后端 auth.MAX_AVATAR_LEN 一致）。 */
const MAX_UPLOAD_BYTES = 1024 * 1024
const MAX_AVATAR_CHARS = 20 * 1024

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    draft.display_name = user.user?.display_name || ''
    draft.avatar = user.user?.avatar || ''
  },
)

/** 无头像时显示昵称首字（中文首字 / 英文首字母）。 */
const initial = computed(() => {
  const name = (draft.display_name || '').trim() || user.user?.username || '?'
  return name.charAt(0).toUpperCase()
})

function pickFile() {
  fileRef.value?.click()
}

/** 是否支持 webp 编码（体积比 jpeg 小很多）。 */
function supportsWebp(): boolean {
  try {
    return document.createElement('canvas').toDataURL('image/webp').startsWith('data:image/webp')
  } catch {
    return false
  }
}

/**
 * 把图片裁成正方形并逐级降低尺寸/质量，直到 base64 长度 ≤ 20KB。
 * 头像只需小尺寸展示，256px 已足够清晰。
 */
async function compressToAvatar(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('当前浏览器不支持图片处理')

  const type = supportsWebp() ? 'image/webp' : 'image/jpeg'
  const sizes = [256, 220, 192, 160, 128, 96]
  const qualities = [0.82, 0.74, 0.66, 0.58, 0.5, 0.42, 0.34]
  let smallest = ''

  for (const size of sizes) {
    canvas.width = size
    canvas.height = size
    // JPEG 不支持透明，统一铺白底，避免 PNG 透明区域变黑
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, size, size)
    const scale = Math.max(size / bitmap.width, size / bitmap.height)
    const w = bitmap.width * scale
    const h = bitmap.height * scale
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(bitmap, (size - w) / 2, (size - h) / 2, w, h)

    for (const q of qualities) {
      const url = canvas.toDataURL(type, q)
      smallest = url
      if (url.length <= MAX_AVATAR_CHARS) {
        bitmap.close?.()
        return url
      }
    }
  }
  bitmap.close?.()
  return smallest
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选择同一文件
  if (!file) return
  if (!file.type.startsWith('image/')) {
    toast.warning('请选择图片文件')
    return
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    toast.warning('图片不能超过 1MB，请先裁剪或压缩')
    return
  }
  try {
    draft.avatar = await compressToAvatar(file)
  } catch {
    toast.error('图片读取失败，请换一张试试')
  }
}

async function onSave() {
  const name = draft.display_name.trim()
  if (!name) {
    toast.warning('昵称不能为空')
    return
  }
  saving.value = true
  try {
    await user.updateProfile({ display_name: name, avatar: draft.avatar })
    toast.success('个人信息已更新')
    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style lang="less" scoped>
.profile-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.avatar-block {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
}

.avatar-preview {
  position: relative;
  width: 68px;
  height: 68px;
  flex-shrink: 0;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  background: rgb(var(--primary-6));
  box-shadow: 0 0 0 3px var(--ui-bg-panel), 0 0 0 4px var(--ui-border);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .avatar-initial {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    color: #fff;
    font-size: 24px;
    font-weight: 700;
  }

  .avatar-mask {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    background: rgba(0, 0, 0, 0.52);
    color: #fff;
    font-size: 11px;
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  &:hover .avatar-mask {
    opacity: 1;
  }
}

.avatar-side {
  flex: 1;
  min-width: 0;
}

.avatar-actions {
  display: flex;
  gap: 8px;
}

.avatar-tip {
  margin: 8px 0 0;
  color: var(--color-text-3);
  font-size: 11.5px;
  line-height: 1.6;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;

  .form-label {
    width: 52px;
    flex-shrink: 0;
    color: var(--color-text-2);
    font-size: 12.5px;
    font-weight: 500;
  }

  .form-static {
    color: var(--color-text-3);
    font-family: var(--ui-font-mono);
    font-size: 12.5px;
  }
}
</style>
