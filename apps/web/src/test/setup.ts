import '@testing-library/jest-dom/vitest'

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = ResizeObserverStub as typeof ResizeObserver

// 即使测试未覆盖响应式行为，Ant Design 仍会订阅媒体查询。jsdom 未实现
// matchMedia，因此为所有组件测试提供符合标准形状的最小桩实现。
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
})

// jsdom 不支持伪元素样式查询；测试只需元素本身的样式，因此保留非伪元素调用，
// 并将伪元素调用降级为原生 API 的无伪元素调用。
const nativeGetComputedStyle = window.getComputedStyle.bind(window)
window.getComputedStyle = ((element: Element, pseudoElement?: string | null) => {
  if (pseudoElement) {
    return nativeGetComputedStyle(element)
  }

  return pseudoElement === undefined
    ? nativeGetComputedStyle(element)
    : nativeGetComputedStyle(element, pseudoElement)
}) as typeof window.getComputedStyle

const knownJsdomErrors = new Set([
  'Could not parse CSS stylesheet',
  "Not implemented: Window's getComputedStyle() method: with pseudo-elements",
])

type JsdomErrorListener = (error: Error) => void
type JsdomVirtualConsole = {
  listeners(eventName: 'jsdomError'): JsdomErrorListener[]
  removeAllListeners(eventName: 'jsdomError'): void
  on(eventName: 'jsdomError', listener: JsdomErrorListener): void
}

const jsdomVirtualConsole = (
  window as typeof window & { _virtualConsole?: JsdomVirtualConsole }
)._virtualConsole

// 仅隐藏上述 jsdom 已知限制产生的输出。恢复既有监听器后继续转发所有其他错误，
// 因而 console.error 的其余行为保持不变，真实的测试失败或组件警告不会被掩盖。
if (jsdomVirtualConsole) {
  const jsdomErrorListeners = jsdomVirtualConsole.listeners('jsdomError')
  jsdomVirtualConsole.removeAllListeners('jsdomError')
  jsdomVirtualConsole.on('jsdomError', error => {
    if (knownJsdomErrors.has(error.message)) {
      return
    }

    for (const listener of jsdomErrorListeners) {
      listener(error)
    }
  })
}
