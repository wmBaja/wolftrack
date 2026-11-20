// WTS (virtual signal) frontend types — mirrors the backend API shapes
// (docs/wts/api.md). All backend fields are additive: older backends omit
// them, so everything except the core identity fields is optional here.

/** One operation on the wire and in .wts files: params are FLATTENED
 * alongside `type` (schema.py `to_json`), e.g. {type: "lowpass", cutoff_hz: 5}. */
export interface OperationDef {
  type: string
  [param: string]: string | number | boolean | null | undefined
}

/** Split a wire operation into type + params record. */
export function opParams(operation: OperationDef): Record<string, string | number | boolean | null> {
  const params: Record<string, string | number | boolean | null> = {}
  for (const [key, value] of Object.entries(operation)) {
    if (key !== 'type' && value !== undefined) params[key] = value
  }
  return params
}

/** Parameter spec from the operation catalog (GET /api/wts/operations). */
export interface ParamSpec {
  name: string
  type: 'float' | 'int' | 'string' | 'bool' | 'enum'
  default: string | number | boolean | null
  required: boolean
  min: number | null
  max: number | null
  choices: string[] | null
  unit: string | null
  help: string
}

/** One catalog entry; `is_head` ops (combine) consume N inputs and can
 * only be the first operation; the rest are single-input post-head ops. */
export interface OperationCatalogEntry {
  type: string
  label: string
  is_head: boolean
  params: ParamSpec[]
}

export interface OperationCatalog {
  operations: OperationCatalogEntry[]
  /** e.g. ["add", "subtract", "multiply", "divide"] (strings). */
  combine_operators: string[]
}

/** A virtual signal definition as returned by GET /api/wts/signals. */
export interface VirtualSignalDefinition {
  name: string
  kind?: string
  category?: string
  unit?: string
  description?: string
  inputs: string[]
  operations: OperationDef[]
  broken?: boolean
  broken_reason?: string | null
  def_hash?: string | null
}

export interface WtsIssue {
  code: string
  signal?: string
  severity?: string
  message: string
}

/** 422 detail from PUT /api/wts/signals/{name}. */
export interface WtsValidationErrorDetail {
  errors: { signal: string; code: string; message: string }[]
  warnings?: { signal?: string; code?: string; message?: string }[]
}

/** 409 detail from DELETE /api/wts/signals/{name}. */
export interface WtsDependentsDetail {
  dependents: string[]
}

/** PUT/DELETE success payload. */
export interface WtsMutationResult {
  signal?: string
  def_hash?: string
  wts_version?: number
  promoted_to?: string | null
  removed?: string[]
  /** Rename only: previous name and affected dependent ids. */
  renamed_from?: string
  dependents?: string[]
}

export function isWtsValidationErrorDetail(
  detail: unknown,
): detail is WtsValidationErrorDetail {
  return (
    typeof detail === 'object' &&
    detail !== null &&
    Array.isArray((detail as WtsValidationErrorDetail).errors)
  )
}

export function isWtsDependentsDetail(detail: unknown): detail is WtsDependentsDetail {
  return (
    typeof detail === 'object' &&
    detail !== null &&
    Array.isArray((detail as WtsDependentsDetail).dependents)
  )
}
