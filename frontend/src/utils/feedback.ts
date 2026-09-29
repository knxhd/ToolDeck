/** Arco Design Vue 反馈工具：Message / Confirm / Prompt 的命令式封装。 */
import { createVNode, reactive, render } from 'vue'
import { Message, Modal, Input } from '@arco-design/web-vue'

export const toast = {
  success: (msg: string) => Message.success(msg),
  error: (msg: string) => Message.error(msg),
  warning: (msg: string) => Message.warning(msg),
  info: (msg: string) => Message.info(msg),
}

export function confirmDialog(title: string, content: string): Promise<boolean> {
  return new Promise((resolve) => {
    Modal.confirm({
      title,
      content,
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
}

/** 带输入框的对话框，resolve 输入值；取消返回 null。 */
export function promptInput(title: string, initial = ''): Promise<string | null> {
  return new Promise((resolve) => {
    const container = document.createElement('div')
    const state = reactive({ value: initial })

    const cleanup = () => {
      render(null, container)
      container.remove()
    }

    const vnode = createVNode(
      Modal,
      {
        title,
        visible: true,
        onBeforeOk: () => {
          resolve(state.value)
          cleanup()
          return true
        },
        onCancel: () => {
          resolve(null)
          cleanup()
        },
      },
      {
        default: () =>
          createVNode(Input, {
            modelValue: state.value,
            'onUpdate:modelValue': (v: string) => {
              state.value = v
            },
            placeholder: '请输入',
          }),
      },
    )
    render(vnode, container)
    document.body.appendChild(container)
  })
}
