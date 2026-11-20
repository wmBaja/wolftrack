"""The ``.wts`` file format: parse, serialize, atomic write (docs/wts §3).

A WTS file is UTF-8 JSON bundling an embedded DBC, virtual-signal
definitions, and read-only signal annotations. Parsing is forgiving at the
definition level: a bad definition is kept verbatim (and flagged broken by
:func:`wts.graph`-based analysis) instead of failing the whole file;
file-level problems (bad JSON, unsupported version, size) raise.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any

from wts.errors import WtsValidationError
from wts.schema import (
    MAX_SIGNALS,
    NAME_PATTERN,
    VirtualSignalDef,
)

FORMAT = "wolftrack-signals"
SUPPORTED_VERSION = 1
MAX_FILE_BYTES = 5 * 1024 * 1024

_TOP_LEVEL_ORDER = ("format", "version", "name", "dbc", "signals", "signal_info")


class WtsFileError(ValueError):
    """The file cannot be understood at all (bad JSON, unsupported version…)."""


def decode_dbc_bytes(content: bytes) -> tuple[str, str]:
    """Decode DBC bytes; returns (text, encoding). ``cp1252`` is the fallback
    cantools assumes for DBC files without a UTF-8 declaration."""
    try:
        return content.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace"), "cp1252"


def normalize_dbc_text(text: str) -> str:
    """Normalize line endings to ``\\n`` (also written back as ``\\n``)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def dbc_hash_hex(dbc_text: str) -> str:
    """SHA-256 of the normalized DBC text (cache-key basis, D8)."""
    return hashlib.sha256(dbc_text.encode("utf-8")).hexdigest()


@dataclass
class WtsFile:
    """Parsed contents of a ``.wts`` file (or an ephemeral one for a legacy DBC)."""

    name: str = ""
    dbc_filename: str = "embedded.dbc"
    dbc_encoding: str = "utf-8"
    dbc_lines: list[str] = field(default_factory=list)
    signals: list[VirtualSignalDef] = field(default_factory=list)
    #: original file position per signal name (round-trip order; I5)
    signal_indexes: dict[str, int] = field(default_factory=dict)
    #: definitions that failed parsing, kept verbatim for round-trip fidelity
    raw_signals: list[Any] = field(default_factory=list)
    #: original file position of each entry in ``raw_signals``
    raw_signal_indexes: list[int] = field(default_factory=list)
    #: parallel to raw_signals: why each kept-as-raw definition is broken
    parse_errors: list[dict[str, str]] = field(default_factory=list)
    signal_info: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: unknown top-level keys, preserved on save (plugins / future formats)
    extras: dict[str, Any] = field(default_factory=dict)
    source_path: str | None = None
    is_legacy_dbc: bool = False
    #: warnings collected while loading (e.g. signal_info for unknown ids)
    warnings: list[dict[str, str]] = field(default_factory=list)

    # ------------------------------------------------------------- text

    @property
    def dbc_text(self) -> str:
        return "\n".join(self.dbc_lines)

    @property
    def dbc_hash(self) -> str:
        return dbc_hash_hex(self.dbc_text)

    # ------------------------------------------------------------ parse

    @classmethod
    def parse(cls, content: bytes, *, source_path: str | None = None,
              fallback_name: str = "") -> "WtsFile":
        """Parse file bytes. Raises :class:`WtsFileError` for file-level faults."""
        if len(content) > MAX_FILE_BYTES:
            raise WtsFileError(
                f"file is {len(content)} bytes; the limit is {MAX_FILE_BYTES}"
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise WtsFileError("file is not valid UTF-8") from error
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise WtsFileError(f"invalid JSON: {error}") from error
        if not isinstance(data, dict):
            raise WtsFileError("top level must be a JSON object")

        format_name = data.get("format")
        if format_name != FORMAT:
            raise WtsFileError(
                f"unsupported format {format_name!r}; expected {FORMAT!r}"
            )
        version = data.get("version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise WtsFileError("version must be an integer")
        if version > SUPPORTED_VERSION:
            raise WtsFileError(
                f"file version {version} is newer than this app supports "
                f"({SUPPORTED_VERSION})"
            )
        if version < SUPPORTED_VERSION:
            raise WtsFileError(f"unsupported file version {version}")

        dbc = data.get("dbc")
        if not isinstance(dbc, dict):
            raise WtsFileError("'dbc' section is required and must be an object")
        dbc_filename = dbc.get("filename")
        if not isinstance(dbc_filename, str) or not dbc_filename:
            raise WtsFileError("'dbc.filename' must be a non-empty string")
        dbc_encoding = dbc.get("encoding", "utf-8")
        if not isinstance(dbc_encoding, str):
            raise WtsFileError("'dbc.encoding' must be a string")
        dbc_lines = dbc.get("lines")
        if not isinstance(dbc_lines, list) or not all(
            isinstance(line, str) for line in dbc_lines
        ):
            raise WtsFileError("'dbc.lines' must be a list of strings")

        raw_signals = data.get("signals", [])
        if not isinstance(raw_signals, list):
            raise WtsFileError("'signals' must be a list")
        if len(raw_signals) > MAX_SIGNALS:
            raise WtsFileError(
                f"at most {MAX_SIGNALS} virtual signals are allowed"
            )

        signals: list[VirtualSignalDef] = []
        signal_indexes: dict[str, int] = {}
        kept_raw: list[Any] = []
        raw_signal_indexes: list[int] = []
        parse_errors: list[dict[str, str]] = []
        seen_names: set[str] = set()
        for index, item in enumerate(raw_signals):
            name = item.get("name") if isinstance(item, dict) else None
            label = name if isinstance(name, str) and name else f"#{index}"
            try:
                definition = VirtualSignalDef.from_json(item, index=index)
                if definition.name in seen_names:
                    raise WtsValidationError([{
                        "code": "name_duplicate",
                        "signal": definition.name,
                        "message": "duplicate virtual signal name",
                    }])
                seen_names.add(definition.name)
                signals.append(definition)
                signal_indexes[definition.name] = index
            except WtsValidationError as error:
                kept_raw.append(item)
                raw_signal_indexes.append(index)
                parse_errors.append({
                    "signal": label,
                    "code": error.errors[0]["code"],
                    "message": "; ".join(e["message"] for e in error.errors),
                })

        signal_info: dict[str, dict[str, Any]] = {}
        raw_info = data.get("signal_info", {})
        if not isinstance(raw_info, dict):
            raise WtsFileError("'signal_info' must be an object")
        for key, value in raw_info.items():
            if not isinstance(key, str):
                raise WtsFileError("signal_info keys must be strings")
            if not isinstance(value, dict):
                raise WtsFileError(f"signal_info['{key}'] must be an object")
            signal_info[key] = dict(value)

        extras = {
            key: value
            for key, value in data.items()
            if key not in _TOP_LEVEL_ORDER
        }

        name = data.get("name")
        if not isinstance(name, str) or not name:
            name = fallback_name

        wts = cls(
            name=name,
            dbc_filename=dbc_filename,
            dbc_encoding=dbc_encoding,
            dbc_lines=list(dbc_lines),
            signals=signals,
            signal_indexes=signal_indexes,
            raw_signals=kept_raw,
            raw_signal_indexes=raw_signal_indexes,
            parse_errors=parse_errors,
            signal_info=signal_info,
            extras=extras,
            source_path=source_path,
        )
        wts.warnings = wts._check_signal_info()
        return wts

    def _check_signal_info(self) -> list[dict[str, str]]:
        """signal_info entries for unknown ids produce warnings, not errors.

        Raw ``Message.Signal`` ids can only be verified against the parsed
        DBC, which the owning (impure) manager does; this pure check covers
        key shape and WTS references.
        """
        known_wts = {definition.name for definition in self.signals}
        warnings: list[dict[str, str]] = []
        for key in self.signal_info:
            if key.startswith("WTS."):
                if key[len("WTS."):] not in known_wts:
                    warnings.append({
                        "code": "signal_info_unknown",
                        "signal": key,
                        "severity": "warning",
                        "message": "signal_info references an unknown "
                                   "virtual signal",
                    })
            elif "." not in key:
                warnings.append({
                    "code": "signal_info_unknown",
                    "signal": key,
                    "severity": "warning",
                    "message": "signal_info key must be 'Message.Signal' or "
                               "'WTS.<name>'",
                })
        return warnings

    # --------------------------------------------------------------- emit

    def to_json_dict(self) -> dict[str, Any]:
        # Rebuild the signals list at the original file positions so broken
        # definitions stay where the user wrote them (I5). Entries without a
        # recorded index (created via API) keep list order after all parsed
        # entries.
        entries: list[tuple[int, Any]] = []
        total = len(self.signals) + len(self.raw_signals)
        appended_signals = 0
        for definition in self.signals:
            index = self.signal_indexes.get(definition.name)
            if index is None:
                index = total + appended_signals
                appended_signals += 1
            entries.append((index, definition.to_json()))
        for position, item in enumerate(self.raw_signals):
            index = (
                self.raw_signal_indexes[position]
                if position < len(self.raw_signal_indexes)
                else position
            )
            entries.append((index, item))
        stable = sorted(entries, key=lambda pair: pair[0])
        payload: dict[str, Any] = {
            "format": FORMAT,
            "version": SUPPORTED_VERSION,
            "name": self.name,
            "dbc": {
                "filename": self.dbc_filename,
                "encoding": self.dbc_encoding,
                "lines": list(self.dbc_lines),
            },
            "signals": [item for _, item in stable],
        }
        if self.signal_info:
            payload["signal_info"] = self.signal_info
        payload.update(self.extras)
        return payload

    def serialize(self) -> str:
        return json.dumps(
            self.to_json_dict(), indent=2, ensure_ascii=False, allow_nan=False
        ) + "\n"

    # ------------------------------------------------------------- build

    @classmethod
    def from_dbc_bytes(
        cls, name: str, dbc_filename: str, content: bytes
    ) -> "WtsFile":
        """Wrap a legacy DBC as an ephemeral WTS file (no virtual signals)."""
        text, encoding = decode_dbc_bytes(content)
        return cls(
            name=name,
            dbc_filename=dbc_filename,
            dbc_encoding=encoding,
            dbc_lines=normalize_dbc_text(text).split("\n"),
        )


def atomic_write(path: str, text: str) -> None:
    """Write atomically: tmp file → fsync → ``os.replace``; keep one ``.bak``."""
    directory = os.path.dirname(path) or "."
    handle_fd, temp_path = tempfile.mkstemp(
        dir=directory, prefix=os.path.basename(path) + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if os.path.exists(path):
            try:
                with open(path, "rb") as source, open(path + ".bak", "wb") as backup:
                    backup.write(source.read())
            except OSError:  # a missing .bak must not block a save
                pass
        os.replace(temp_path, path)
    except BaseException:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass
        raise
