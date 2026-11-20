# WolfTrack Signals (WTS): Implementation Plan (rev 3.1)

Adds **user-defined virtual signals** to WolfTrack for **both `.blf` log analysis and live DAQ streaming**: scale, bias, multi-signal math, and filters applied to decoded CAN signals, plus a `.wts` file that bundles a DBC with those definitions.

Reviewed against `apps/visualizer` and `apps/dashboard` (monorepo). Behaviors cited in these docs were read from that code.

## Scope (rev 3.1)

**In scope:** getting signal processing working in live and log mode, and laying groundwork so later work does not require rewrites.

- A pure, mode-agnostic signal engine and a small op registry (five ops).
- The `.wts` file format (embedded DBC, virtual signal definitions, read-only signal info, forward-compatible), with legacy `.dbc` still supported and visible.
- Log mode: virtual signals computed once on full-resolution data, cached safely in SQLite, recomputed only when compute-affecting fields change.
- Live mode: always-on stateful processing, hot reload on edit, reset on reconnect, tolerant of DAQ clock steps (DAQ reboots, looped ZMQ replay streams, or RTC jumps).
- A minimal API, minimal file-manager/tree integration, and a minimal editor.

**Explicitly out of scope** (each item's groundwork and design notes are in [part-7-deferred-roadmap.md](part-7-deferred-roadmap.md)): event signals and aggregates (lap times, averages), GPS, tracks, lap/sector timing, map widget, plugin system, rich signal-editing UI (preview, templates, signal-info editor), raw-history buffers, live-session recording, `.wtc` dashboards container.

## How to use this plan

- Read **[00-architecture.md](00-architecture.md)** first: decisions, `.wts` spec, engine semantics, invariants.
- Each part is one PR (or a small series). Give an agent **one part file + the repo's `AGENTS.md`**.
- Instructions for both halves live in the monorepo root `AGENTS.md`.

## Parts

| Part | Title | Repo | Depends on | Size |
| :-- | :-- | :-- | :-- | :-- |
| 0 | [Prep and cleanup](part-0-prep.md) | visualizer | n/a | S |
| 1 | [Signal engine](part-1-engine.md) | visualizer | 0 | M |
| 2 | [`.wts` file, persistence, API](part-2-wts-file-and-api.md) | visualizer | 1 | L |
| 3 | [Log path (SQLite derived signals)](part-3-log-path.md) | visualizer | 2 | L |
| 4 | [Live path (ZMQ stream)](part-4-live-path.md) | visualizer | 2 | M |
| 5 | [Frontend foundation](part-5-frontend-foundation.md) | dashboard | 2 (mock) / 3+4 (real data) | M |
| 6 | [Minimal signal editor](part-6-minimal-editor.md) | dashboard | 5 | S-M |
| 7 | [Deferred roadmap and groundwork](part-7-deferred-roadmap.md) | n/a | n/a | n/a |

```
0 -> 1 -> 2 -+-> 3 -+
             +-> 4 -+-> (real data for 5, 6)
             +-> 5 -+-> 6
```

Parts 3 and 4 can be built in parallel, and Part 5 can start against a mocked API once Part 2's contract is merged. Land backend parts first: the dashboard CI downloads the backend's `nightly` build, so dashboard PRs can only be tested against backend changes already on `dev`.

**Milestones**
- **M1 (Parts 0-4):** virtual signals work end to end in logs and live via the API, testable with curl and pytest.
- **M2 (Parts 5-6):** users can create, edit, and chart virtual signals in the app.

## Status checklist

- [x] Part 0: prep and cleanup
- [x] Part 1: signal engine
- [x] Part 2: `.wts` file and API
- [ ] Part 3: log path
- [ ] Part 4: live path
- [ ] Part 5: frontend foundation
- [ ] Part 6: minimal signal editor

## Answered questions (and what they changed)

| # | Answer | Consequence |
| :-- | :-- | :-- |
| Q1 | DAQ timestamps are UTC from an RTC. While not NTP-synced mid-run, the DAQ can reboot/brown-out mid-session or replay looped captures. | Timestamps are absolute epoch seconds and can **step backward or forward mid-session** (on DAQ restart, RTC reset, or stream replay). The live runtime resets the engine on a large backward step and flags it to the frontend (D11, Part 4, I10); the engine skips non-increasing timestamps and supports gap notification. Virtual-signal timing never uses the backend's wall clock. |
| Q2 | GPS is not implemented; lat/lon likely in one message; do not depend on it. | GPS, tracks, and lap timing removed from scope. Multi-input ops (`HeadOp`) keep the door open without assuming message layout (Part 7). |
| Q3 | A map widget will come later. | Out of scope. |
| Q4 | Python 3.12. | Part 0 sets `.python-version` to 3.12; CI keeps 3.12. |
| Q5 | Legacy `.dbc` files stay visible. | Confirmed (D3): `.dbc` and `.wts` are listed together; a `.dbc` is promoted to `.wts` only when the user first saves a virtual signal. |

## Remaining items to verify or decide

| # | Item | Needed by |
| :-- | :-- | :-- |
| V1 | Confirm the DAQ `timestamp` unit is **seconds** (not ms/ns) and is present on every frame. Check against a real capture. | Part 4 (task 4.6) |
| Q6 | Should the existing CSV export include virtual signals? It is the last task of Part 3, in a separate PR, and easy to drop. | Part 3 |
| Q7 | Plugin-roadmap owner: review the extension seam (op registry, catalog endpoint, `HeadOp`, namespaced `.wts` keys, replaceable editor) before Part 1 merges. | Part 1 |

## Naming debt (accepted for v1)

- `/api/dbc/*` endpoints and `DBCManager` also manage `.wts` files. A rename to `/api/setups` is deferred.
- "WTS" means the **file format** (`.wts`) and the **`WTS.` id prefix** of virtual signals. In code and docs, say "WTS file" and "virtual signal".