"""WTS file-format tests: round trip, extras preservation, DBC embedding,
atomic writes, and limits (docs/wts §3, I5)."""
from __future__ import annotations

import json
import os

import cantools
import pytest

from tests.helpers.make_blf import SYNTHETIC_DBC
from wts.schema import OperationDef, VirtualSignalDef
from wts.wts_file import (
    WtsFile,
    WtsFileError,
    atomic_write,
    decode_dbc_bytes,
    dbc_hash_hex,
    normalize_dbc_text,
)


def sample_file() -> WtsFile:
    wts = WtsFile.from_dbc_bytes("Test Setup", "synthetic.dbc", SYNTHETIC_DBC.encode())
    wts.signals.append(
        VirtualSignalDef(
            name="Brake_Total",
            category="Brakes",
            unit="psi",
            inputs=("Brakes.Front_Psi", "Brakes.Rear_Psi"),
            operations=(OperationDef(type="combine", params={"operator": "add"}),),
        )
    )
    wts.signal_info["Brakes.Front_Psi"] = {"display_name": "Front brake pressure"}
    wts.extras["x-demo"] = {"hello": "world"}
    return wts


class TestRoundTrip:
    def test_parse_serialize_parse(self):
        text = sample_file().serialize()
        first = WtsFile.parse(text.encode())
        second = WtsFile.parse(first.serialize().encode())
        assert first.serialize() == second.serialize()
        assert [s.name for s in first.signals] == ["Brake_Total"]
        assert first.extras == {"x-demo": {"hello": "world"}}
        assert first.signal_info["Brakes.Front_Psi"]["display_name"] == (
            "Front brake pressure"
        )

    def test_unknown_top_level_keys_preserved(self):
        text = sample_file().serialize()
        data = json.loads(text)
        data["x-future-plugin"] = {"a": [1, 2, 3]}
        wts = WtsFile.parse(json.dumps(data).encode())
        assert wts.extras["x-future-plugin"] == {"a": [1, 2, 3]}
        again = WtsFile.parse(wts.serialize().encode())
        assert again.extras["x-future-plugin"] == {"a": [1, 2, 3]}

    def test_key_order_stable_golden(self):
        text = sample_file().serialize()
        assert text.index('"format"') < text.index('"version"')
        assert text.index('"version"') < text.index('"name"')
        assert text.index('"name"') < text.index('"dbc"')
        assert text.index('"dbc"') < text.index('"signals"')
        assert text.index('"signals"') < text.index('"signal_info"')

    def test_broken_definition_kept_verbatim_in_place(self):
        data = json.loads(sample_file().serialize())
        broken = {
            "name": "Nope",
            "kind": "event",
            "inputs": ["Missing.Signal"],
            "operations": [{"type": "teleport", "warp": 9}],
        }
        data["signals"].insert(1, broken)
        wts = WtsFile.parse(json.dumps(data).encode())
        assert [s.name for s in wts.signals] == ["Brake_Total"]
        assert wts.raw_signals == [broken]
        assert wts.parse_errors[0]["signal"] == "Nope"
        out = json.loads(wts.serialize())
        assert out["signals"][1] == broken  # verbatim, same position


class TestFileFaults:
    def base(self):
        return json.loads(sample_file().serialize())

    def test_rejects_bad_json(self):
        with pytest.raises(WtsFileError):
            WtsFile.parse(b"{not json")

    def test_rejects_non_utf8(self):
        with pytest.raises(WtsFileError):
            WtsFile.parse(b"\xff\xfe\x00garbage\xff")

    def test_rejects_wrong_format(self):
        data = self.base()
        data["format"] = "other-thing"
        with pytest.raises(WtsFileError, match="unsupported format"):
            WtsFile.parse(json.dumps(data).encode())

    def test_rejects_future_version(self):
        data = self.base()
        data["version"] = 99
        with pytest.raises(WtsFileError, match="newer"):
            WtsFile.parse(json.dumps(data).encode())

    def test_rejects_missing_dbc(self):
        data = self.base()
        del data["dbc"]
        with pytest.raises(WtsFileError):
            WtsFile.parse(json.dumps(data).encode())

    def test_rejects_oversize(self):
        with pytest.raises(WtsFileError, match="limit"):
            WtsFile.parse(b"x" * (5 * 1024 * 1024 + 1))

    def test_duplicate_names_kept_broken(self):
        data = self.base()
        data["signals"].append(json.loads(json.dumps(data["signals"][0])))
        wts = WtsFile.parse(json.dumps(data).encode())
        assert len(wts.signals) == 1
        assert "duplicate" in wts.parse_errors[0]["message"]


class TestDbcEmbedding:
    def test_stig25_embedded_matches_file(self):
        """load_file(original) == load_string(embedded) for the repo DBC."""
        path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "dbc", "stig25(1).dbc"
        ))
        with open(path, "rb") as handle:
            content = handle.read()
        text, encoding = decode_dbc_bytes(content)
        lines = normalize_dbc_text(text).split("\n")
        embedded = cantools.database.load_string(
            "\n".join(lines), database_format="dbc"
        )
        from_file = cantools.database.load_file(path)
        assert [m.name for m in embedded.messages] == [
            m.name for m in from_file.messages
        ]
        for embedded_msg, file_msg in zip(embedded.messages, from_file.messages):
            assert [s.name for s in embedded_msg.signals] == [
                s.name for s in file_msg.signals
            ]
            assert embedded_msg.frame_id == file_msg.frame_id
            for a, b in zip(embedded_msg.signals, file_msg.signals):
                assert (a.scale, a.offset) == (b.scale, b.offset)
        assert encoding in ("utf-8", "cp1252")

    def test_dbc_hash_is_content_based(self):
        assert dbc_hash_hex("abc") == dbc_hash_hex("abc")
        assert dbc_hash_hex("abc") != dbc_hash_hex("abd")

    def test_cp1252_fallback(self):
        text, encoding = decode_dbc_bytes("SG_ Ünïcode : 0|8@1+ (1,0) [0|0] \"\" X\n".encode("cp1252"))
        assert encoding == "cp1252"
        assert "code" in text


class TestAtomicWrite:
    def test_write_and_backup(self, tmp_path):
        target = tmp_path / "setup.wts"
        atomic_write(str(target), "one\n")
        atomic_write(str(target), "two\n")
        assert target.read_text() == "two\n"
        assert (tmp_path / "setup.wts.bak").read_text() == "one\n"
        assert list(tmp_path.glob("*.tmp")) == []

    def test_failure_leaves_original_intact(self, tmp_path, monkeypatch):
        target = tmp_path / "setup.wts"
        atomic_write(str(target), "original\n")

        def boom(src, dst):
            raise OSError("replace failed")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(OSError):
            atomic_write(str(target), "broken\n")
        assert target.read_text() == "original\n"
        assert list(tmp_path.glob("*.tmp")) == []
