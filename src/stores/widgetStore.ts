import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { createWidget, WIDGET_TYPES, type Widget } from '@/types/widgets'

const GRID_COLUMNS = 16

interface GridPosition {
  x: number
  y: number
}

interface GridSize {
  w: number
  h: number
}

export const useWidgetStore = defineStore('widgets', () => {
  // State - Only ONE source of truth
  const widgets = ref<Widget[]>([])

  // Getters
  function getWidgetById(id: string): Widget | undefined {
    return widgets.value.find(w => w.i === id)
  }

  const widgetCount = computed(() => widgets.value.length)

  // Actions
  function addWidget(type: WIDGET_TYPES, position: {x: number, y: number, w?: number, h?: number}): Widget {
    const newWidget = createWidget(type, position)
    const availablePosition = findAvailablePosition(position, newWidget)
    newWidget.x = availablePosition.x
    newWidget.y = availablePosition.y
    widgets.value.push(newWidget)
    saveToLocalStorage()
    return newWidget
  }

  function findAvailablePosition(preferredPosition: GridPosition, size: GridSize): GridPosition {
    const maxX = Math.max(0, GRID_COLUMNS - size.w)
    const preferred = {
      x: Math.max(0, Math.min(Math.round(preferredPosition.x), maxX)),
      y: Math.max(0, Math.round(preferredPosition.y)),
    }

    if (isSpaceAvailable(preferred, size)) return preferred

    let closestPosition: GridPosition | undefined
    let closestDistance = Number.POSITIVE_INFINITY
    const maxWidgetBottom = widgets.value.reduce((bottom, widget) => Math.max(bottom, widget.y + widget.h), 0)

    for (let y = 0; y <= maxWidgetBottom; y += 1) {
      for (let x = 0; x <= maxX; x += 1) {
        const position = { x, y }
        if (!isSpaceAvailable(position, size)) continue

        const distance = Math.hypot(x - preferred.x, y - preferred.y)
        if (distance < closestDistance) {
          closestDistance = distance
          closestPosition = position
        }
      }
    }

    return closestPosition ?? { x: preferred.x, y: maxWidgetBottom }
  }

  function isSpaceAvailable(position: GridPosition, size: GridSize): boolean {
    return widgets.value.every((widget) => !widgetsOverlap({ ...position, ...size }, widget))
  }

  function widgetsOverlap(a: GridPosition & GridSize, b: GridPosition & GridSize): boolean {
    return a.x < b.x + b.w &&
      a.x + a.w > b.x &&
      a.y < b.y + b.h &&
      a.y + a.h > b.y
  }

  function removeWidget(id: string): void {
    const index = widgets.value.findIndex(w => w.i === id)
    if (index !== -1) {
      widgets.value.splice(index, 1)
      saveToLocalStorage()
    }
  }

  function updateWidget(id: string, updates: Partial<Widget>): void {
    const widget = widgets.value.find(w => w.i === id)
    if (widget) {
      Object.assign(widget, updates)
      saveToLocalStorage()
    }
  }

  function updateLayout(newLayout: Widget[]): void {
    // GridLayout passes back updated layout with new positions
    newLayout.forEach(item => {
      const widget = widgets.value.find(w => w.i === item.i)
      if (widget) {
        widget.x = item.x
        widget.y = item.y
        widget.w = item.w
        widget.h = item.h
      }
    })
    saveToLocalStorage()
  }

  function saveToLocalStorage(): void {
    try {
      localStorage.setItem('dashboard-widgets', JSON.stringify(widgets.value))
    } catch (error) {
      console.error('Failed to save widgets:', error)
    }
  }

  function loadFromLocalStorage(): void {
    try {
      const saved = localStorage.getItem('dashboard-widgets')
      if (saved) {
        widgets.value = JSON.parse(saved)
      }
    } catch (error) {
      console.error('Failed to load widgets:', error)
    }
  }

  function exportLayout(): void {
    try {
      const jsonData = JSON.stringify(widgets.value);
      const blob = new Blob([jsonData], { type : 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = "export.json";
      link.click();
      URL.revokeObjectURL(url);
    }
    catch (error) {
      console.error('Failed to export widgets:', error);
    }
  }

  async function parseImportedLayout(file: File): Promise<Widget[] | null> {
    try {
      const contents = await file.text()
      const widgetsRaw = JSON.parse(contents)

      if (!Array.isArray(widgetsRaw)) {
        return null
      }

      const parsed: Widget[] = []

      for (const widget of widgetsRaw) {
        if (!widget || typeof widget !== 'object') {
          throw new Error('Invalid widget entry')
        }

        if (!widget.type || !Object.values(WIDGET_TYPES).includes(widget.type)) {
          throw new Error(`Invalid widget type: ${String(widget.type)}`)
        }

        if (
          typeof widget.x !== 'number' ||
          typeof widget.y !== 'number' ||
          typeof widget.w !== 'number' ||
          typeof widget.h !== 'number'
        ) {
          throw new Error('Invalid widget size/position')
        }

        if (!Array.isArray(widget.signals)) {
          throw new Error('Invalid widget signals')
        }

        if (typeof widget.title !== 'string') {
          throw new Error('Invalid widget title')
        }

        if (typeof widget.i !== 'string' && typeof widget.i !== 'number') {
          throw new Error('Invalid widget id')
        }

        if (typeof widget.createdAt !== 'number') {
          throw new Error('Invalid widget createdAt')
        }

        const newWidget = createWidget(widget.type, {
          x: widget.x,
          y: widget.y,
          w: widget.w,
          h: widget.h,
        })

        newWidget.signals = widget.signals
        newWidget.title = widget.title
        newWidget.i = String(widget.i)
        newWidget.createdAt = widget.createdAt

        parsed.push(newWidget)
      }

      return parsed
    } catch (error) {
      console.error('Imported layout file has improper format', error)
      return null
    }
  }

  function clearAll(): void {
    widgets.value = []
    saveToLocalStorage()
  }

  function overwriteLayout(newWidgets: Widget[]): void {
    widgets.value = newWidgets
    saveToLocalStorage()
  }

  return {
    widgets,

    getWidgetById,
    widgetCount,

    addWidget,
    findAvailablePosition,
    removeWidget,
    updateWidget,
    updateLayout,
    exportLayout,
    parseImportedLayout,
    loadFromLocalStorage,
    clearAll,
    overwriteLayout,
  }
})
