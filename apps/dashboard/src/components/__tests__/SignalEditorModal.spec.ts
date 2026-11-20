import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SignalEditorModal from '@/components/SignalEditorModal.vue'
import SignalTree from '@/components/SignalTree.vue'
import { useWtsStore } from '@/stores/wtsStore'
import { useDbcStore } from '@/stores/dbcStore'
import { confirmDialog } from '@/types/dialog'
import type { OperationCatalog, OperationCatalogEntry, VirtualSignalDefinition } from "@/types/wts"

vi.mock('@/lib/visualizer', () => ({
  getVisualizerBase: vi.fn().mockResolvedValue('http://visualizer.test'),
}))

vi.mock('@/types/dialog', async importOriginal => {
  const actual = await importOriginal<typeof import('@/types/dialog')>()
  return { ...actual, confirmDialog: vi.fn().mockResolvedValue(true) }
})

const DUMMY_OP: OperationCatalogEntry = {
  type: 'dummy',
  label: 'Dummy Op',
  is_head: false,
  params: [
    {
      name: 'amount',
      type: 'float',
      default: 3,
      required: true,
      min: 0,
      max: 10,
      choices: null,
      unit: 'W',
      help: 'A dummy amount in watts.',
    },
  ],
}

const CATALOG: OperationCatalog = {
  operations: [
    { type: 'combine', label: 'Combine', is_head: true, params: [
      { name: 'operator', type: 'enum', default: null, required: true, min: null, max: null,
        choices: ['add', 'subtract'], unit: null, help: 'Combine mode.' },
    ] },
    { type: 'scale', label: 'Scale', is_head: false, params: [
      { name: 'factor', type: 'float', default: null, required: true, min: null, max: null,
        choices: null, unit: null, help: 'Multiply by this number.' },
    ] },
    { type: 'lowpass', label: 'Low-pass filter', is_head: false, params: [
      { name: 'cutoff_hz', type: 'float', default: null, required: true, min: 0, max: null,
        choices: null, unit: 'Hz', help: 'Cutoff frequency.' },
    ] },
    DUMMY_OP,
  ],
  combine_operators: ['add', 'subtract', 'multiply', 'divide'],
}

const SIGNALS = [
  { id: 'Brakes.Front_Psi', node: 'ECU', message: 'Brakes', name: 'Front_Psi', unit: 'psi' },
  { id: 'Brakes.Rear_Psi', node: 'ECU', message: 'Brakes', name: 'Rear_Psi', unit: 'psi' },
  { id: 'WTS.Total', node: 'WT Signals', message: 'Custom', name: 'Total', unit: 'psi',
    is_virtual: true },
  { id: 'WTS.Bias', node: 'WT Signals', message: 'Custom', name: 'Bias', unit: '%',
    is_virtual: true },
]

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

function setupStores() {
  setActivePinia(createPinia())
  const wtsStore = useWtsStore()
  wtsStore.catalog = CATALOG
  const dbcStore = useDbcStore()
  dbcStore.signals = SIGNALS
  return { wtsStore, dbcStore }
}

function mountEditor(props: {
  mode: 'create' | 'edit'
  initialDefinition?: VirtualSignalDefinition | null
}) {
  return mount(SignalEditorModal, {
    props: { mode: props.mode, initialDefinition: props.initialDefinition ?? null },
  })
}

function clickFirstInputs(wrapper: ReturnType<typeof mountEditor>, count = 2) {
  const buttons = wrapper.find('[data-testid="input-options"]').findAll('button')
  return buttons.slice(0, count)
}

describe('SignalEditorModal', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('renders post-head ops from the catalog and excludes is_head ops', () => {
    setupStores()
    const wrapper = mountEditor({ mode: 'create' })
    const options = wrapper.find('[data-testid="add-op-select"]').findAll('option')
    const values = options.map(option => option.attributes('value')).filter(Boolean)
    // 'dummy' comes from the catalog with zero frontend code changes;
    // combine (is_head) is never offered post-head.
    expect(values).toEqual(['scale', 'lowpass', 'dummy'])
    expect(options.map(option => option.text())).toContain('Dummy Op')
  })

  it('adds inputs in order with move controls and combine select when >1 input', async () => {
    setupStores()
    const wrapper = mountEditor({ mode: 'create' })
    expect(wrapper.find('[data-testid="combine-select"]').exists()).toBe(false)

    const buttons = clickFirstInputs(wrapper)
    await buttons[0]!.trigger('click') // Brakes.Front_Psi
    await buttons[1]!.trigger('click') // Brakes.Rear_Psi

    let items = wrapper.find('[data-testid="input-list"]').findAll('li')
    expect(items.map(item => item.find('.input-name').text()))
      .toEqual(['Brakes.Front_Psi', 'Brakes.Rear_Psi'])
    expect(wrapper.find('[data-testid="combine-select"]').exists()).toBe(true)

    // reorder: second input up
    await items[1]!.findAll('button')[0]!.trigger('click')
    items = wrapper.find('[data-testid="input-list"]').findAll('li')
    expect(items.map(item => item.find('.input-name').text()))
      .toEqual(['Brakes.Rear_Psi', 'Brakes.Front_Psi'])

    // remove first -> single input -> combine select disappears
    await items[0]!.findAll('button')[2]!.trigger('click')
    expect(wrapper.find('[data-testid="combine-select"]').exists()).toBe(false)
  })

  it('excludes itself and transitive dependents from the inputs list when editing', () => {
    const { wtsStore } = setupStores()
    wtsStore.definitions = [
      { name: 'Total', inputs: ['Brakes.Front_Psi'], operations: [] },
      { name: 'Bias', inputs: ['WTS.Total'], operations: [] },
      { name: 'Deep', inputs: ['WTS.Bias'], operations: [] },
    ]
    const wrapper = mountEditor({
      mode: 'edit',
      initialDefinition: { name: 'Total', inputs: [], operations: [] },
    })
    const optionText = wrapper.find('[data-testid="input-options"]').text()
    expect(optionText).toContain('Brakes.Front_Psi')
    expect(optionText).not.toContain('WTS.Total') // self
    expect(optionText).not.toContain('WTS.Bias') // dependent
    expect(optionText).not.toContain('WTS.Deep') // transitive dependent
    expect(optionText).toContain('Brakes.Rear_Psi')
  })

  it('saves a 2-input combine-only payload with the exact wire shape', async () => {
    setupStores()
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes('/api/wts/signals/Brake_Total') && init?.method === 'PUT') {
        return jsonResponse(200, { signal: 'Brake_Total', wts_version: 2 })
      }
      if (String(url).includes('/api/wts/signals')) {
        return jsonResponse(200, { signals: [], issues: [], wts_version: 2 })
      }
      return jsonResponse(200, { signals: SIGNALS })
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountEditor({ mode: 'create' })
    await wrapper.find('[data-testid="signal-name"]').setValue('Brake_Total')
    const buttons = clickFirstInputs(wrapper)
    await buttons[0]!.trigger('click')
    await buttons[1]!.trigger('click')
    await wrapper.find('[data-testid="combine-select"]').setValue('add')

    await wrapper.find('[data-testid="save-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('saved')).toBeTruthy()
    expect(wrapper.emitted('close')).toBeTruthy()
    const put = fetchMock.mock.calls.find(
      call => String(call[0]).includes('/api/wts/signals/Brake_Total')
        && (call[1] as RequestInit | undefined)?.method === 'PUT',
    )
    expect(put).toBeTruthy()
    expect(JSON.parse(String((put![1] as RequestInit).body))).toEqual({
      definition: {
        name: 'Brake_Total',
        kind: 'continuous',
        category: 'Custom',
        unit: '',
        description: '',
        inputs: ['Brakes.Front_Psi', 'Brakes.Rear_Psi'],
        // combine-only chain: exactly one operation, no post-head steps
        operations: [{ type: 'combine', params: { operator: 'add' } }],
      },
    })
  })

  it('edit mode splits leading combine into the Combine field and the rest into ops', () => {
    setupStores()
    const wrapper = mountEditor({
      mode: 'edit',
      initialDefinition: {
        name: 'Bias',
        inputs: ['Brakes.Front_Psi', 'Brakes.Rear_Psi'],
        operations: [
          { type: 'combine', params: { operator: 'subtract' } },
          { type: 'scale', params: { factor: 2 } },
        ],
      },
    })
    const combine = wrapper.find('[data-testid="combine-select"]')
    expect((combine.element as HTMLSelectElement).value).toBe('subtract')
    const opLabels = wrapper.find('[data-testid="op-list"]').findAll('.op-label')
    expect(opLabels.map(label => label.text())).toEqual(['Scale'])
    const factor = wrapper.find('[data-testid="param-scale-factor"]')
    expect((factor.element as HTMLInputElement).value).toBe('2')
  })

  it('lists 422 validation errors from the backend and stays open', async () => {
    setupStores()
    const validation = {
      errors: [{ signal: 'Bad', code: 'cycle', message: 'definition contains a cycle' }],
      warnings: [],
    }
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(422, { detail: validation })))

    const wrapper = mountEditor({ mode: 'create' })
    await wrapper.find('[data-testid="signal-name"]').setValue('Bad')
    const buttons = clickFirstInputs(wrapper)
    await buttons[0]!.trigger('click')
    await buttons[1]!.trigger('click')

    await wrapper.find('[data-testid="save-btn"]').trigger('click')
    await flushPromises()

    const errors = wrapper.find('[data-testid="error-list"]')
    expect(errors.exists()).toBe(true)
    expect(errors.text()).toContain('definition contains a cycle')
    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('renders param controls from the catalog for a newly added dummy op', async () => {
    setupStores()
    const wrapper = mountEditor({ mode: 'create' })
    await wrapper.find('[data-testid="signal-name"]').setValue('X')
    await clickFirstInputs(wrapper, 1)[0]!.trigger('click')

    await wrapper.find('[data-testid="add-op-select"]').setValue('dummy')

    const param = wrapper.find('[data-testid="param-dummy-amount"]')
    expect(param.exists()).toBe(true)
    expect((param.element as HTMLInputElement).value).toBe('3') // catalog default
    expect(wrapper.text()).toContain('A dummy amount in watts.')
    expect(wrapper.text()).toContain('(W)') // unit from ParamSpec, not hardcoded
  })

  it('closes on Escape and saves nothing', async () => {
    setupStores()
    const wrapper = mountEditor({ mode: 'create' })
    await wrapper.vm.$nextTick()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})

describe('SignalTree virtual-signal actions', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('shows edit/delete actions on virtual rows and surfaces 409 dependents', async () => {
    const { wtsStore } = setupStores()
    wtsStore.definitions = [{ name: 'Total', inputs: ['Brakes.Front_Psi'], operations: [] }]

    vi.mocked(confirmDialog).mockResolvedValue(true)
    vi.stubGlobal('fetch', vi.fn(async () =>
      jsonResponse(409, { detail: { dependents: ['WTS.Bias'] } })))

    const wrapper = mount(SignalTree, {
      props: { signals: SIGNALS, selectedSignals: [] },
      global: { stubs: { SignalEditorModal: true } },
    })

    const virtualRow = wrapper.findAll('.tree-item.leaf')
      .find(row => row.text().includes('Total'))
    expect(virtualRow).toBeTruthy()
    await virtualRow!.find('[aria-label="Delete virtual signal"]').trigger('click')
    await flushPromises()

    expect(confirmDialog).toHaveBeenCalledTimes(2)
    expect(String(vi.mocked(confirmDialog).mock.calls[1]![1])).toContain('Used by: WTS.Bias')
  })

  it('opens the editor from the New WT Signal button', async () => {
    setupStores()
    const wrapper = mount(SignalTree, {
      props: { signals: SIGNALS, selectedSignals: [] },
      global: { stubs: { SignalEditorModal: true } },
    })
    expect(wrapper.findComponent({ name: 'SignalEditorModal' }).exists()).toBe(false)
    await wrapper.find('[data-testid="new-wt-btn"]').trigger('click')
    expect(wrapper.findComponent({ name: 'SignalEditorModal' }).exists()).toBe(true)
  })
})
