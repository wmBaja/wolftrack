"""Manages setups: legacy ``*.dbc`` files and WolfTrack Signals ``*.wts`` files.

``<user_data>/dbc/`` stays legacy-only; ``<user_data>/wts/`` holds ``.wts``
files. ``active_dbc_filename`` keeps its historic meaning (the active setup
file, either type); ``active_wts`` adds the parsed WTS view of it. A legacy
DBC behaves as an ephemeral WTS file with no virtual signals until the user
saves their first signal, at which point it is *promoted* (D3): a new
``wts/<stem>.wts`` embedding the DBC is created and selected, and the
original ``.dbc`` is never modified.
"""
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cantools

from logging_config import get_logger
from wts.analysis import analyze
from wts.errors import WtsValidationError
from wts.graph import compute_definition_hashes, transitive_dependents
from wts.schema import NAME_PATTERN, WTS_PREFIX, VirtualSignalDef
from wts.wts_file import WtsFile, atomic_write

logger = get_logger(__name__)

VALID_EXTENSIONS = (".dbc", ".wts")


class DbcConflictError(ValueError):
    """A file with that name already exists (maps to HTTP 409)."""


class SignalDependentsError(ValueError):
    """A virtual signal is referenced by others (maps to HTTP 409)."""

    def __init__(self, dependents: List[str]) -> None:
        self.dependents = dependents
        super().__init__(f"used by: {', '.join(dependents)}")


class DBCManager:
    def __init__(self, user_data_dir: str):
        self.user_data_dir = user_data_dir
        self.dbc_dir = Path(user_data_dir) / "dbc"
        self.wts_dir = Path(user_data_dir) / "wts"
        self.dbc_dir.mkdir(parents=True, exist_ok=True)
        self.wts_dir.mkdir(parents=True, exist_ok=True)

        self.active_dbc_filename: Optional[str] = None
        self.db: Optional[cantools.database.Database] = None
        self.active_wts: Optional[WtsFile] = None
        self._wts_version = 0
        self._on_changed: Optional[Callable[[Optional[set[str]]], None]] = None
        self._last_active_file = Path(user_data_dir) / "wts_last_active.json"

        # Load the previously active setup if it still exists, else the
        # first available one.
        setups = self.get_available_dbcs()
        if setups:
            preferred = self._read_last_active()
            if preferred and any(s["name"] == preferred for s in setups):
                if self.select_dbc(preferred):
                    return
            self.select_dbc(setups[0]["name"])

    # ------------------------------------------------- last-active memory

    def _read_last_active(self) -> Optional[str]:
        try:
            with open(self._last_active_file, "r", encoding="utf-8") as handle:
                return json.load(handle).get("filename")
        except (OSError, ValueError, AttributeError):
            return None

    def _write_last_active(self, filename: Optional[str]) -> None:
        try:
            tmp = self._last_active_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump({"filename": filename}, handle)
            tmp.replace(self._last_active_file)
        except OSError:
            logger.warning("Could not persist last active setup")

    # ----------------------------------------------------------- versions

    def get_wts_version(self) -> int:
        """Bumped on any signal/DBC/active-file change (live hot-reload, D13)."""
        return self._wts_version

    def set_changed_callback(
        self, callback: Optional[Callable[[Optional[set[str]]], None]]
    ) -> None:
        """Hook called after mutations/select/DBC changes (Part 2.8).

        ``changed_ids`` is the set of affected ``WTS.*`` ids, or ``None`` for
        file-level changes (select/upload/delete/rename).
        """
        self._on_changed = callback

    def _notify_changed(self, changed_ids: Optional[set[str]] = None) -> None:
        self._wts_version += 1
        if self._on_changed is not None:
            try:
                self._on_changed(changed_ids)
            except Exception:  # a broken hook must never corrupt state
                logger.exception("WTS changed callback failed")

    # ----------------------------------------------------------- listing

    def get_available_dbcs(self) -> List[Dict[str, Any]]:
        """Return available setup files: legacy ``.dbc`` and ``.wts``."""
        results: List[Dict[str, Any]] = []
        for directory, file_type in (
            (self.dbc_dir, "dbc"),
            (self.wts_dir, "wts"),
        ):
            for entry in sorted(directory.glob(f"*{file_type}")):
                results.append(
                    {
                        "name": entry.name,
                        "size": entry.stat().st_size,
                        "mtime": entry.stat().st_mtime,
                        "type": file_type,
                    }
                )
        return results

    def _directory_for(self, suffix: str) -> Path:
        return self.dbc_dir if suffix == ".dbc" else self.wts_dir

    def _get_dbc_path(self, filename: str) -> Path:
        """Return a validated path within the managed setup directories."""
        if (
            not isinstance(filename, str)
            or not filename.strip()
            or filename != filename.strip()
            or '/' in filename
            or '\\' in filename
            or '..' in filename
            or Path(filename).name != filename
            or Path(filename).suffix not in VALID_EXTENSIONS
        ):
            raise ValueError('Filename must be a plain .dbc or .wts filename')

        return self._directory_for(Path(filename).suffix) / filename

    # ----------------------------------------------------------- loading

    def _load_wts(self, wts: WtsFile) -> cantools.database.Database:
        return cantools.database.load_string(
            wts.dbc_text, database_format="dbc"
        )

    def select_dbc(self, filename: str) -> bool:
        """Select a setup file (``.dbc`` or ``.wts``) as the active database."""
        file_path = self._get_dbc_path(filename)
        if not file_path.exists():
            logger.error(f"Setup file not found to select: {filename}")
            return False
        suffix = file_path.suffix
        try:
            if suffix == ".dbc":
                db = cantools.database.load_file(file_path)
                with open(file_path, "rb") as handle:
                    content = handle.read()
                wts = WtsFile.from_dbc_bytes(
                    file_path.stem, file_path.name, content
                )
                wts.is_legacy_dbc = True
                wts.source_path = str(file_path)
            else:
                with open(file_path, "rb") as handle:
                    content = handle.read()
                wts = WtsFile.parse(
                    content, source_path=str(file_path),
                    fallback_name=file_path.stem,
                )
                db = self._load_wts(wts)
                wts.source_path = str(file_path)
        except Exception as error:
            logger.error(f"Failed to load setup {filename}: {error}")
            return False

        self.db = db
        self.active_wts = wts
        self.active_dbc_filename = filename
        self._write_last_active(filename)
        self._notify_changed(None)
        logger.info(f"Setup selected and loaded: {filename}")
        return True

    def get_active_dbc(self) -> Optional[cantools.database.Database]:
        """Return the active cantools database."""
        return self.db

    def get_active_dbc_hash(self) -> Optional[str]:
        """SHA-256 of the active setup's DBC text (cache key part, D8)."""
        if self.active_wts is None:
            return None
        return self.active_wts.dbc_hash

    def get_active_setup_path(self) -> Optional[str]:
        """Filesystem path of the active setup file, or None."""
        if self.active_dbc_filename is None:
            return None
        return str(self._get_dbc_path(self.active_dbc_filename))

    def get_virtual_signals(self) -> List[VirtualSignalDef]:
        """Valid (computable) virtual signals of the active setup."""
        if self.active_wts is None:
            return []
        return list(self.active_analysis().valid)

    def get_broken_signals(self) -> Dict[str, str]:
        """name -> broken reason for the active setup."""
        if self.active_wts is None:
            return {}
        return dict(self.active_analysis().broken)

    def get_definition_hashes(self) -> Dict[str, str]:
        """name -> def_hash for the valid definitions (cache freshness, D8)."""
        if self.active_wts is None:
            return {}
        analysis = self.active_analysis()
        cache = getattr(self, "_hash_cache", None)
        cache_key = (self._wts_version, id(self.active_wts))
        if cache is not None and cache[0] == cache_key:
            return cache[1]
        from wts.graph import topological_order

        order, _ = topological_order(analysis.valid)
        hashes = compute_definition_hashes(analysis.valid, order)
        self._hash_cache = (cache_key, hashes)
        return hashes

    # ------------------------------------------------------- analysis

    def active_analysis(self):
        """Analyze active definitions against the loaded DBC (cached)."""
        wts = self.active_wts
        if wts is None:
            from wts.analysis import AnalysisResult

            return AnalysisResult()
        cache_key = (self._wts_version, id(wts))
        cached = getattr(self, "_analysis_cache", None)
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        dbc_ids = self._dbc_signal_ids()
        raw_broken = {
            error["signal"]: error["message"]
            for error in wts.parse_errors
            if error.get("signal")
        }
        result = analyze(list(wts.signals), dbc_ids, raw_broken=raw_broken)
        result.issues.extend({"severity": w.get("severity", "warning"), **w}
                             for w in wts.warnings)
        # signal_info entries for raw ids that are not in the DBC: warnings.
        for key in wts.signal_info:
            if key.startswith("WTS.") or "." not in key:
                continue  # shape and WTS refs handled by the pure check
            if dbc_ids is not None and key not in dbc_ids:
                result.issues.append({
                    "code": "signal_info_unknown",
                    "signal": key,
                    "severity": "warning",
                    "message": "signal_info references an unknown signal id",
                })
        self._analysis_cache = (cache_key, result)
        return result

    def _dbc_signal_ids(self) -> Optional[set[str]]:
        if self.db is None:
            return None
        return {
            f"{message.name}.{signal.name}"
            for message in self.db.messages
            for signal in message.signals
        }

    # ------------------------------------------------------- upload

    def upload_dbc(self, filename: str, file_content: bytes) -> str:
        """Save a ``.dbc`` or ``.wts`` file to its managed directory."""
        file_path = self._get_dbc_path(filename)
        suffix = file_path.suffix

        if suffix == ".wts":
            # Fully validate before touching disk (I6).
            try:
                wts = WtsFile.parse(
                    file_content, fallback_name=Path(filename).stem
                )
                cantools.database.load_string(
                    wts.dbc_text, database_format="dbc"
                )
            except Exception as error:
                raise ValueError(f"Invalid .wts file: {error}") from error
            if file_path.exists():
                raise DbcConflictError(
                    f"A setup named {filename} already exists"
                )

        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"Setup uploaded: {filename}")

        # If this is the only one, select it automatically
        if len(self.get_available_dbcs()) == 1:
            self.select_dbc(filename)
        else:
            self._notify_changed(None)

        return str(file_path)

    # -------------------------------------------------- delete / rename

    def delete_dbc(self, filename: str) -> bool:
        """Delete a setup file. Return True if successful."""
        file_path = self._get_dbc_path(filename)
        if file_path.exists():
            file_path.unlink()
            for sidecar in (Path(str(file_path) + ".bak"),):
                if sidecar.exists():
                    sidecar.unlink()
            logger.info(f"Setup deleted: {filename}")
            if self.active_dbc_filename == filename:
                self.active_dbc_filename = None
                self.db = None
                self.active_wts = None
                # Try to load another one
                setups = self.get_available_dbcs()
                if setups:
                    self.select_dbc(setups[0]["name"])
                else:
                    self._notify_changed(None)
            else:
                self._notify_changed(None)
            return True
        return False

    def rename_dbc(self, filename: str, new_filename: str) -> bool:
        """Rename a setup file, keeping its active state when applicable."""
        file_path = self._get_dbc_path(filename)
        new_file_path = self._get_dbc_path(new_filename)

        if file_path.suffix != new_file_path.suffix:
            raise ValueError(
                "Renaming must keep the file extension (.dbc or .wts)"
            )
        if not file_path.exists():
            return False
        if new_file_path.exists():
            raise ValueError('A setup with that name already exists')

        file_path.rename(new_file_path)
        bak_path = Path(str(file_path) + ".bak")
        if bak_path.exists():
            bak_path.rename(Path(str(new_file_path) + ".bak"))
        if self.active_dbc_filename == filename:
            self.active_dbc_filename = new_filename
            self._write_last_active(new_filename)
            if self.active_wts is not None:
                self.active_wts.source_path = str(new_file_path)
                self.active_wts.name = Path(new_filename).stem

        logger.info(f"Setup renamed: {filename} -> {new_filename}")
        self._notify_changed(None)
        return True

    # ------------------------------------------------------- mutations

    def upsert_virtual_signal(
        self, definition: VirtualSignalDef
    ) -> Dict[str, Any]:
        """Create or update one virtual signal in the active setup.

        Returns ``{signal, def_hash, wts_version, promoted_to}``. Raises
        :class:`WtsValidationError` listing every validation problem, or
        :class:`ValueError` when no setup is active.
        """
        if self.active_wts is None or self.db is None:
            raise ValueError("No active setup file; upload or select one first")
        if not NAME_PATTERN.match(definition.name):
            raise WtsValidationError([{
                "code": "name_invalid",
                "signal": definition.name,
                "message": "name must match ^[A-Za-z_][A-Za-z0-9_]{0,63}$",
            }])

        wts = self.active_wts
        siblings = [
            item for item in wts.signals if item.name != definition.name
        ]
        if len(wts.signals) - len(siblings) == 0 and (
            len(wts.signals) + len(wts.raw_signals) >= 200
        ):
            raise WtsValidationError([{
                "code": "signals_too_many",
                "signal": definition.name,
                "message": "at most 200 virtual signals are allowed",
            }])

        raw_broken = {
            error["signal"]: error["message"]
            for error in wts.parse_errors
            if error.get("signal")
        }
        from wts.analysis import check_definition_write

        issues = check_definition_write(
            definition, siblings, self._dbc_signal_ids(), raw_broken=raw_broken
        )
        if issues:
            raise WtsValidationError(issues)

        promoted_to: Optional[str] = None
        if wts.is_legacy_dbc:
            promoted_to = self._promote_legacy_dbc()
            wts = self.active_wts  # type: ignore[assignment]
            siblings = [
                item for item in wts.signals if item.name != definition.name
            ]

        # Replace in place, else append (broken definitions with this name
        # are superseded and dropped from the raw list).
        replaced = False
        for index, item in enumerate(wts.signals):
            if item.name == definition.name:
                wts.signals[index] = definition
                replaced = True
                break
        if not replaced:
            wts.signals.append(definition)
            wts.signal_indexes.setdefault(
                definition.name, len(wts.signals) + len(wts.raw_signals) + 100
            )
        wts.raw_signals = [
            item for item in wts.raw_signals
            if not (isinstance(item, dict) and item.get("name") == definition.name)
        ]
        wts.parse_errors = [
            error for error in wts.parse_errors
            if error.get("signal") != definition.name
        ]

        self._save_active_wts()
        self._notify_changed({f"WTS.{definition.name}"})

        definition_hash = self.get_definition_hashes().get(definition.name)
        if definition_hash is None:  # should not happen; defensive
            logger.error(
                "Saved definition %s unexpectedly has no def_hash",
                definition.name,
            )

        return {
            "signal": definition.to_json(),
            "def_hash": definition_hash,
            "wts_version": self._wts_version,
            "promoted_to": promoted_to,
        }

    def delete_virtual_signal(self, name: str) -> Dict[str, Any]:
        """Delete one virtual signal. Raises ValueError with dependents (409)."""
        if self.active_wts is None:
            raise ValueError("No active setup file")
        if not NAME_PATTERN.match(name):
            raise ValueError(f"Invalid signal name {name!r}")

        wts = self.active_wts
        existing = next(
            (item for item in wts.signals if item.name == name), None
        )
        raw_existing = any(
            isinstance(item, dict) and item.get("name") == name
            for item in wts.raw_signals
        )
        if existing is None and not raw_existing:
            raise FileNotFoundError(name)

        dependents = transitive_dependents(
            list(wts.signals), name
        )
        if dependents:
            raise SignalDependentsError(dependents)

        wts.signals = [item for item in wts.signals if item.name != name]
        wts.raw_signals = [
            item for item in wts.raw_signals
            if not (isinstance(item, dict) and item.get("name") == name)
        ]
        wts.parse_errors = [
            error for error in wts.parse_errors if error.get("signal") != name
        ]
        wts.signal_info.pop(f"WTS.{name}", None)

        self._save_active_wts()
        self._notify_changed({f"WTS.{name}"})
        return {"wts_version": self._wts_version}

    def rename_virtual_signal(self, name: str, new_name: str) -> Dict[str, Any]:
        """Rename a virtual signal, rewriting every reference to it.

        Returns ``{signal, def_hash, wts_version, renamed_from, dependents}``.
        Raises :class:`FileNotFoundError` for unknown names, ``ValueError``
        for invalid/colliding names or un-renamable broken definitions, and
        :class:`WtsValidationError` when the renamed set would be invalid.
        """
        if self.active_wts is None:
            raise ValueError("No active setup file")
        if not NAME_PATTERN.match(name):
            raise ValueError(f"Invalid signal name {name!r}")
        if not NAME_PATTERN.match(new_name):
            raise WtsValidationError([{
                "code": "name_invalid",
                "signal": new_name,
                "message": "name must match ^[A-Za-z_][A-Za-z0-9_]{0,63}$",
            }])
        if name == new_name:
            raise ValueError("New name must differ from the current name")

        wts = self.active_wts
        existing = next(
            (item for item in wts.signals if item.name == name), None
        )
        if existing is None:
            broken_only = any(
                isinstance(item, dict) and item.get("name") == name
                for item in wts.raw_signals
            )
            if broken_only:
                raise ValueError(
                    f"{name} is broken and cannot be renamed; delete and recreate it"
                )
            raise FileNotFoundError(name)
        if any(item.name == new_name for item in wts.signals):
            raise ValueError(f"A signal named {new_name} already exists")

        old_id, new_id = f"{WTS_PREFIX}{name}", f"{WTS_PREFIX}{new_name}"
        renamed = replace(existing, name=new_name)
        dependents = transitive_dependents(list(wts.signals), name)

        rewritten = [
            replace(item, inputs=tuple(
                new_id if input_id == old_id else input_id
                for input_id in item.inputs
            ))
            for item in wts.signals
            if item.name != name
        ]
        from wts.analysis import check_definition_write

        issues = check_definition_write(
            renamed, rewritten, self._dbc_signal_ids(),
            raw_broken={
                error["signal"]: error["message"]
                for error in wts.parse_errors
                if error.get("signal")
            },
        )
        if issues:
            raise WtsValidationError(issues)

        wts.signals = [
            renamed if item.name == name
            else replace(item, inputs=tuple(
                new_id if input_id == old_id else input_id
                for input_id in item.inputs
            ))
            for item in wts.signals
        ]
        # Preserve file position of the renamed entry.
        index = wts.signal_indexes.pop(name, None)
        if index is not None:
            wts.signal_indexes[new_name] = index

        def swap_ids(value: Any) -> Any:
            if isinstance(value, str):
                return new_id if value == old_id else value
            if isinstance(value, list):
                return [swap_ids(item) for item in value]
            if isinstance(value, dict):
                return {
                    (new_id if key == old_id else key): swap_ids(item)
                    for key, item in value.items()
                }
            return value

        for item in wts.raw_signals:
            if isinstance(item, dict):
                for key, value in list(item.items()):
                    item[key] = swap_ids(value)
        if old_id in wts.signal_info:
            info = wts.signal_info.pop(old_id)
            wts.signal_info.setdefault(new_id, info)
        wts.parse_errors = [
            error for error in wts.parse_errors
            if error.get("signal") != name
        ]

        self._save_active_wts()
        self._notify_changed(
            {old_id, new_id} | {f"WTS.{item}" for item in dependents}
        )
        definition_hash = self.get_definition_hashes().get(new_name)
        logger.info("Virtual signal renamed: %s -> %s", name, new_name)
        return {
            "signal": renamed.to_json(),
            "def_hash": definition_hash,
            "wts_version": self._wts_version,
            "renamed_from": name,
            "dependents": [f"WTS.{item}" for item in dependents],
        }

    # --------------------------------------------------------- helpers

    def _promote_legacy_dbc(self) -> str:
        """Wrap the active legacy DBC in a new ``.wts`` file (D3)."""
        legacy_path = Path(self._get_dbc_path(self.active_dbc_filename))
        stem = legacy_path.stem
        candidate = stem
        counter = 1
        target = self.wts_dir / f"{candidate}.wts"
        while target.exists():
            candidate = f"{stem}-{counter}"
            counter += 1
            target = self.wts_dir / f"{candidate}.wts"

        with open(legacy_path, "rb") as handle:
            content = handle.read()
        wts = WtsFile.from_dbc_bytes(candidate, legacy_path.name, content)
        atomic_write(str(target), wts.serialize())
        logger.info(
            "Promoted legacy DBC %s to %s", legacy_path.name, target.name
        )
        self.select_dbc(target.name)
        return target.name

    def _save_active_wts(self) -> None:
        wts = self.active_wts
        assert wts is not None and wts.source_path is not None
        atomic_write(wts.source_path, wts.serialize())
        # Stale analysis cache is keyed on version; version bump refreshes it.

    # -------------------------------------------------------- signals API

    def get_signals(self) -> List[Dict[str, Any]]:
        """Return raw DBC signals plus virtual signals of the active setup.

        Additive fields (older clients ignore them): virtual entries carry
        ``is_virtual``/``kind``/``category``/``inputs``/``operations``/
        ``broken``/``broken_reason``; both kinds merge optional
        ``display_name``/``description``/``min``/``max`` from ``signal_info``
        (precedence: signal_info > virtual's own fields > DBC).
        """
        signals: List[Dict[str, Any]] = []
        if self.db:
            for msg in self.db.messages:
                nodes = msg.senders if msg.senders else ["Unassigned"]
                for node in nodes:
                    for sig in msg.signals:
                        signals.append({
                            "id": f"{msg.name}.{sig.name}",
                            "node": node,
                            "message": msg.name,
                            "name": sig.name,
                            "unit": sig.unit
                        })

        wts = self.active_wts
        if wts is None:
            return signals

        analysis = self.active_analysis()
        valid_names = {definition.name for definition in analysis.valid}
        for definition in wts.signals:
            is_broken = definition.name in analysis.broken
            entry: Dict[str, Any] = {
                "id": definition.signal_id,
                "node": "WT Signals",
                "message": definition.category,
                "category": definition.category,
                "name": definition.name,
                "unit": definition.unit,
                "is_virtual": True,
                "kind": definition.kind,
                "description": definition.description,
                "inputs": list(definition.inputs),
                "operations": [
                    op.to_json() for op in definition.operations
                ],
                "broken": is_broken,
                "broken_reason": analysis.broken.get(definition.name),
            }
            signals.append(entry)
        for item in wts.raw_signals:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name:
                continue
            reason = analysis.broken.get(name)
            signals.append({
                "id": f"WTS.{name}",
                "node": "WT Signals",
                "message": item.get("category") or "Custom",
                "category": item.get("category") or "Custom",
                "name": name,
                "unit": item.get("unit") or "",
                "is_virtual": True,
                "kind": item.get("kind") or "continuous",
                "description": item.get("description") or "",
                "inputs": item.get("inputs") or [],
                "operations": item.get("operations") or [],
                "broken": True,
                "broken_reason": reason or "invalid definition",
            })

        signal_info = wts.signal_info
        for entry in signals:
            info = signal_info.get(entry["id"])
            if not info:
                continue
            display_name = info.get("display_name")
            if isinstance(display_name, str) and display_name:
                entry["display_name"] = display_name
            description = info.get("description")
            if isinstance(description, str) and description:
                entry["description"] = description
            for key in ("min", "max"):
                value = info.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    entry[key] = value
        return signals
