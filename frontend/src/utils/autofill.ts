/**
 * 全局禁止表单自动填充：除登录 / 注册对话框（带 data-allow-autofill）外，
 * 所有 input / textarea 都关闭浏览器的自动补全与输入历史建议。
 *
 * Arco 组件的输入框是运行时渲染的，这里用 MutationObserver 统一兜住，
 * 避免逐个组件手写 autocomplete="off"。
 */
const ALLOW_SELECTOR = '[data-allow-autofill]'

function harden(el: Element): void {
  if (!(el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement)) return
  if (el.type === 'hidden') return
  // 登录 / 注册卡片内保留自动填充（用户名、密码）
  if (el.closest(ALLOW_SELECTOR)) return
  if (el.getAttribute('autocomplete') === 'off') return
  el.setAttribute('autocomplete', 'off')
  el.setAttribute('autocorrect', 'off')
  el.setAttribute('autocapitalize', 'off')
  el.setAttribute('spellcheck', 'false')
}

function scan(root: Element | Document): void {
  if (root instanceof Element) harden(root)
  root.querySelectorAll('input, textarea').forEach(harden)
}

let installed = false

export function installAutofillGuard(): void {
  if (installed) return
  installed = true

  scan(document)

  let pending = false
  const observer = new MutationObserver((records) => {
    if (pending) return
    pending = true
    // 合并同一帧内的多次 DOM 变更，避免频繁扫描
    requestAnimationFrame(() => {
      pending = false
      for (const r of records) {
        r.addedNodes.forEach((n) => {
          if (n instanceof Element) scan(n)
        })
      }
    })
  })
  observer.observe(document.documentElement, { childList: true, subtree: true })
}
