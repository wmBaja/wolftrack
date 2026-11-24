/** Place a click-opened menu directly below its trigger. */
export function menuPositionBelow(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return { x: 0, y: 0 }

  const bounds = target.getBoundingClientRect()
  return { x: bounds.left, y: bounds.bottom }
}
