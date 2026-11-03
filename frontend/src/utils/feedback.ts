/** Arco Design Vue 反馈工具：Message / Confirm / Prompt 的命令式封装。 */
import { createVNode, reactive, render } from 'vue'
import { Button, Message, Modal, Input } from '@arco-design/web-vue'

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

/**
 * 关闭未保存标签前的三按钮对话框。
 * resolve：'save' 保存并关闭 / 'discard' 不保存 / null 取消操作。
 */
export function closeUnsavedDialog(tabTitle: string): Promise<'save' | 'discard' | null> {
  return new Promise((resolve) => {
    const container = document.createElement('div')

    const finish = (v: 'save' | 'discard' | null) => {
      resolve(v)
      render(null, container)
      container.remove()
    }

    const vnode = createVNode(
      Modal,
      {
        title: '未保存的修改',
        visible: true,
        width: 420,
        maskClosable: false,
        onCancel: () => finish(null),
      },
      {
        default: () =>
          createVNode('div', { style: 'line-height:1.6' }, [
            createVNode('span', null, `「${tabTitle}」有未保存的修改，关闭前是否保存？`),
          ]),
        footer: () => [
          createVNode(Button, { onClick: () => finish(null) }, { default: () => '取消' }),
          createVNode(Button, { onClick: () => finish('discard') }, { default: () => '不保存' }),
          createVNode(Button, { type: 'primary', onClick: () => finish('save') }, { default: () => '保存并关闭' }),
        ],
      },
    )
    render(vnode, container)
    document.body.appendChild(container)
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
