# Part 6: Minimal Signal Editor

**Area:** apps/dashboard · **Depends on:** Part 5 · **Size:** S-M

## Goal

Users can create, edit, and delete virtual signals from the UI. That is all. A separate plugin roadmap owns anything richer, so this part is built to be **replaced**: one self-contained component, driven entirely by the backend op catalog, with no knowledge of any specific operation.

## Scope

**In:**
- One modal component, `SignalEditorModal.vue`, for create and edit.
- A "+ New WT Signal" button and edit/delete icons on virtual rows in `SignalTree.vue`.
- Delete confirmation with the existing `ConfirmDialog.vue`, including the 409 "used by" message.

**Out (do not build):** duplicate, drag-and-drop reordering, live preview, templates, category combobox, signal-info editing, dependency badges, per-op help popovers, keyboard shortcuts beyond Esc and Enter, a dry-run validate endpoint. Deferred items are listed in [part-7-deferred-roadmap.md](part-7-deferred-roadmap.md).

## Design

- **Catalog-driven.** Parameter inputs, defaults, units, min/max, and help text come from `ParamSpec`s in `wtsStore.catalog` (`GET /api/wts/operations`). No post-head operation name, parameter, unit, or default is hardcoded in the component. Adding a post-head op in Python must make it appear here with no frontend change; demonstrate with a temporary dummy op in the PR.
- **The backend is the validator.** The modal only does trivial required-field checks. Pressing Save calls `PUT /api/wts/signals/{name}`; a 422 returns `{errors: [{signal, code, message}]}` and the modal lists them. There is no dry-run endpoint in this scope.
- **No code entry.** Users compose typed operations only (D4).

### Fields (top to bottom)

1. **Name.** Fixed `WTS.` prefix shown; regex `^[A-Za-z_][A-Za-z0-9_]{0,63}$`; read-only when editing, with the note "Renaming is not supported: delete and recreate. Charts using the old name will show a missing signal."
2. **Unit** (free text), **category** (free text, default `Custom`), **description** (optional).
3. **Inputs.** Searchable multi-select over `dbcStore.signals` (raw and virtual, excluding the signal being edited and any virtual signal that transitively depends on it in `wtsStore.definitions`). Rendered as an ordered list with move-up/move-down buttons, because order matters for subtract and divide. Show each input's unit. Cap the rendered options (search first, show at most ~100 matches) so large DBCs stay fast.
4. **Combine** (shown only when `inputs.length > 1`): operator select populated from `wtsStore.catalog.combine_operators` (defaulting to the first operator, e.g., `add`).
5. **Operations** (post-head chain). An ordered list of single-input operations. "+ Add operation" offers the entries from `wtsStore.catalog.operations` where `!op.is_head` (so `combine` is never offered in the post-head list). Each step renders its params from `ParamSpec` and has move-up, move-down, and remove buttons.
   - *Save payload assembly:* When `inputs.length > 1`, prepend `{ type: "combine", operator: selectedCombineOperator }` to the post-head operations list to form `definition.operations` (so a multi-input signal with no additional post-head steps sends `operations: [{ type: "combine", operator }]`). When `inputs.length === 1`, `definition.operations` is the post-head operations list (require at least 1 operation when `inputs.length === 1`).
   - *Edit-mode loading:* Load the signal's definition from `wtsStore.definitions` (falling back to `signal.message` if `category` is absent). If `definition.operations[0]?.type === "combine"`, load `definition.operations[0].operator` into Field 4 (Combine) and `definition.operations.slice(1)` into Field 5 (Operations). Otherwise load all of `definition.operations` into Field 5.
6. **Footer.** Error list, Save (disabled while a request is in flight), Cancel.

`kind` is not shown and is sent as `"continuous"` (D10).

### `SignalTree.vue` changes (small)

- "+ New WT Signal" button in the header.
- Pencil and trash icons on rows where `is_virtual`. Delete uses `ConfirmDialog`; a 409 shows "Used by: WTS.X, WTS.Y. Delete those first."
- After the first signal is saved against a legacy `.dbc`, show the single-line `promoted_to` notice ("Saved to new setup `<name>.wts`; your original DBC is unchanged").
- Put row actions in a small child component rather than growing the tree file.

## Tasks

- [x] 6.1 `SignalEditorModal.vue`: identity fields and inputs list (filtering out self and transitive dependents) wired to `wtsStore.save`.
- [x] 6.2 Combine select (when `inputs.length > 1`) and post-head operations list (`!op.is_head`) generated from the catalog (param inputs: number with unit/min/max, enum select, bool toggle, string), including Save payload assembly and Edit-mode splitting of `combine`.
- [x] 6.3 Error display for 422 (list) and generic failures; saving state.
- [x] 6.4 Tree integration: new button, edit/delete icons, delete flow with dependents message, promotion notice.
- [x] 6.5 Vitest component tests: catalog-driven rendering (including a dummy op appearing with no code change and `is_head: true` ops excluded from Field 5), add/remove/reorder inputs and ops, 2-input combine-only save payload shape, edit-mode load splitting `combine` into Field 4 and remaining ops into Field 5, 422 and 409 display.
- [x] 6.6 Esc to close, labels on all inputs, focus moved into the modal on open.
- [x] 6.7 `npm run type-check`, `lint`, `test:unit -- --run`.

## Acceptance criteria

- A user who has never seen the feature can create "Front brake bias (filtered)" from two raw signals in under two minutes, chart it in log mode **and** live mode, and change the filter cutoff with the chart updating.
- A user can create a 2-input `combine` signal (e.g., `Brake_Total` with `add` and no further post-head operations), save it, and reopen it in Edit mode without duplicate `combine` steps appearing.
- An invalid definition cannot be saved and every backend error is readable.
- A new backend op appears in the UI with correct parameter inputs without touching the dashboard code.
- Deleting a signal that others depend on is blocked with a clear message.

## Gotchas

- Do not cache the catalog across backend restarts; refetch it when connecting to a backend.
- Parameter units come from the catalog; do not hardcode "Hz" or "s".
- Exclude the signal being edited (and its dependents) from its own inputs list; the backend still rejects cycles and is the source of truth.
- Keep this component's props and events narrow (`mode`, `initialDefinition`, `@saved`, `@close`) so a plugin-provided editor can replace it without touching the tree.
## Notes from implementation

- Catalog-driven proof lives in the spec: a `dummy` op exists only in the
  mocked catalog JSON and renders with its param, default, unit, and help
  with no component change; `is_head` ops never appear post-head.
- Save payload: `kind: "continuous"` always; `combine` is prepended only
  when inputs > 1 (combine-only signal => exactly one operation); edit
  mode splits a leading `combine` into the Combine select so reopening
  never duplicates it.
- Param number inputs keep the raw string on invalid input — the backend
  422 is the only validator; the modal just lists its errors verbatim.
- Tree integration: `SignalRowActions.vue` child keeps the tree diff small;
  delete confirm + 409 "Used by: …" dialog; promotion notice line rendered
  from `wtsStore.promotionNotice`.
