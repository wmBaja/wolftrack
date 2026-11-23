if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  })
}

if (typeof globalThis.matchMedia !== 'function' && typeof window !== 'undefined') {
  Object.assign(globalThis, { matchMedia: window.matchMedia.bind(window) })
}
