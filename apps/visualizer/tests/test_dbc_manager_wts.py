"""DBCManager setup management: dual directories, selection, promotion,
mutations, versioning, and the /api signals view (I6, I7)."""
from __future__ import annotations

import json
import os

import pytest

from dbc_manager import (
    DBCManager,
    DbcConflictError,
    SignalDependentsError,
)
from tests.helpers.make_blf import SYNTHETIC_DBC
from wts.errors import WtsValidationError
from wts.schema import OperationDef, VirtualSignalDef


@pytest.fixture
def manager(tmp_user_data) -> DBCManager:
    return DBCManager(str(tmp_user_data))


@pytest.fixture
def dbc_bytes() -> bytes:
    return SYNTHETIC_DBC.encode()


def scale_sig(name="Scale_Test", factor=2.0, input_id="Brakes.Front_Psi", **kw):
    return VirtualSignalDef(
        name=name,
        inputs=(input_id,),
        operations=(OperationDef(type="scale", params={"factor": factor}),),
        **kw,
    )


class TestListingsAndSelection:
    def test_directories_and_types(self, manager, dbc_bytes):
        assert manager.dbc_dir.exists() and manager.wts_dir.exists()
        manager.upload_dbc("a.dbc", dbc_bytes)
        available = manager.get_available_dbcs()
        assert [(f["name"], f["type"]) for f in available] == [("a.dbc", "dbc")]
        assert manager.active_dbc_filename == "a.dbc"  # first upload auto-selects
        assert manager.active_wts is not None
        assert manager.active_wts.is_legacy_dbc is True
        assert manager.active_wts.signals == []

    def test_rejects_traversal_and_bad_extension(self, manager):
        for bad in ("../evil.dbc", "x.exe", "sub/dir.dbc", ".dbc", "a.dbc ", ""):
            with pytest.raises(ValueError):
                manager._get_dbc_path(bad)

    def test_legacy_ephemeral_dbc_hash(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        from wts.wts_file import dbc_hash_hex, normalize_dbc_text

        assert manager.get_active_dbc_hash() == dbc_hash_hex(
            normalize_dbc_text(dbc_bytes.decode())
        )

    def test_setup_path_and_dbc_file_semantics(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        assert manager.get_active_setup_path().endswith("a.dbc")
        assert os.path.dirname(manager.get_active_setup_path()) == str(manager.dbc_dir)

    def test_select_missing_returns_false(self, manager):
        assert manager.select_dbc("nope.dbc") is False
        assert manager.select_dbc("nope.wts") is False


class TestUpload:
    def test_upload_invalid_wts_never_hits_disk(self, manager):
        with pytest.raises(ValueError):
            manager.upload_dbc("bad.wts", b"{not json")
        assert not (manager.wts_dir / "bad.wts").exists()

    def test_wts_with_bad_embedded_dbc_rejected(self, manager, dbc_bytes):
        from wts.wts_file import WtsFile

        wts = WtsFile.from_dbc_bytes("x", "x.dbc", dbc_bytes)
        wts.dbc_lines = ["NOT A DBC"]
        with pytest.raises(ValueError):
            manager.upload_dbc("broken.wts", wts.serialize().encode())
        assert not (manager.wts_dir / "broken.wts").exists()

    def test_wts_name_collision_409(self, manager, dbc_bytes):
        manager.upload_dbc("dup.dbc", dbc_bytes)
        from wts.wts_file import WtsFile

        payload = WtsFile.from_dbc_bytes(
            "dup", "dup.dbc", dbc_bytes
        ).serialize().encode()
        # create the .wts first via promotion to force a name clash scenario
        manager.upload_dbc("dup.wts", payload)
        with pytest.raises(DbcConflictError):
            manager.upload_dbc("dup.wts", payload)

    def test_upload_wts_roundtrip_lists_identical_signals(self, manager, dbc_bytes):
        from wts.wts_file import WtsFile

        wts = WtsFile.from_dbc_bytes("S", "s.dbc", dbc_bytes)
        wts.signals.append(scale_sig())
        text = wts.serialize()
        manager.upload_dbc("setup.wts", text.encode())
        manager.select_dbc("setup.wts")
        virtual = [s for s in manager.get_signals() if s.get("is_virtual")]
        assert [s["id"] for s in virtual] == ["WTS.Scale_Test"]
        # re-upload under another name and compare
        manager.upload_dbc("setup2.wts", text.encode())
        manager.select_dbc("setup2.wts")
        virtual2 = [s for s in manager.get_signals() if s.get("is_virtual")]
        assert virtual2 == virtual


class TestRenameDelete:
    def test_rename_keeps_active_and_extension_required(self, manager, dbc_bytes):
        manager.upload_dbc("a.wts", WtsFile_from(dbc_bytes))
        assert manager.rename_dbc("a.wts", "b.wts") is True
        assert manager.active_dbc_filename == "b.wts"
        assert manager.get_active_setup_path().endswith("b.wts")
        with pytest.raises(ValueError, match="extension"):
            manager.rename_dbc("b.wts", "b.dbc")

    def test_delete_active_falls_back(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upload_dbc("b.dbc", dbc_bytes)
        assert manager.delete_dbc(manager.active_dbc_filename) is True
        assert manager.active_dbc_filename is not None
        assert manager.delete_dbc("ghost.wts") is False

    def test_delete_removes_sidecar_bak(self, manager, dbc_bytes):
        from wts.wts_file import WtsFile

        wts = WtsFile.from_dbc_bytes("x", "x.dbc", dbc_bytes)
        manager.upload_dbc("x.wts", wts.serialize().encode())
        manager.select_dbc("x.wts")
        manager.upsert_virtual_signal(scale_sig())
        bak = manager.wts_dir / "x.wts.bak"
        assert bak.exists()
        manager.delete_dbc("x.wts")
        assert not bak.exists()


def WtsFile_from(dbc_bytes: bytes) -> bytes:
    from wts.wts_file import WtsFile

    return WtsFile.from_dbc_bytes("a", "a.dbc", dbc_bytes).serialize().encode()


class TestPromotion:
    def test_first_save_promotes_legacy(self, manager, dbc_bytes):
        manager.upload_dbc("old.dbc", dbc_bytes)
        result = manager.upsert_virtual_signal(scale_sig())
        assert result["promoted_to"] == "old.wts"
        assert manager.active_dbc_filename == "old.wts"
        # original DBC byte-identical
        assert (manager.dbc_dir / "old.dbc").read_bytes() == dbc_bytes
        # the .wts embeds the same DBC text
        assert "Brakes" in (manager.wts_dir / "old.wts").read_text()

    def test_promotion_collision_suffix(self, manager, dbc_bytes):
        from wts.wts_file import WtsFile

        existing = WtsFile.from_dbc_bytes("pre", "old.dbc", dbc_bytes)
        manager.upload_dbc("old.wts", existing.serialize().encode())
        manager.upload_dbc("old.dbc", dbc_bytes)
        manager.select_dbc("old.dbc")  # legacy active, name taken by the .wts
        result = manager.upsert_virtual_signal(scale_sig())
        assert result["promoted_to"] == "old-1.wts"


class TestMutations:
    def test_upsert_updates_in_place(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(factor=2))
        manager.upsert_virtual_signal(scale_sig(factor=3))
        defs = manager.get_virtual_signals()
        assert len(defs) == 1
        assert defs[0].operations[0].params["factor"] == 3

    def test_upsert_rejects_invalid(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        with pytest.raises(WtsValidationError) as exc:
            manager.upsert_virtual_signal(scale_sig(input_id="Nope.Nope"))
        assert exc.value.errors[0]["code"] == "input_unknown"
        with pytest.raises(WtsValidationError):
            manager.upsert_virtual_signal(scale_sig(name="1bad"))

    def test_upsert_rejects_unknown_wts_input(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        a = VirtualSignalDef(
            "A", inputs=("WTS.B",),
            operations=(OperationDef(type="scale", params={"factor": 1}),),
        )
        # B does not exist (valid or broken) -> rejected as unknown input.
        with pytest.raises(WtsValidationError) as exc:
            manager.upsert_virtual_signal(a)
        assert exc.value.errors[0]["code"] == "input_unknown"

    def test_upsert_cycle_detected_with_pair(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="A", input_id="Brakes.Front_Psi"))
        b = VirtualSignalDef(
            "B", inputs=("WTS.A",),
            operations=(OperationDef(type="scale", params={"factor": 1}),),
        )
        manager.upsert_virtual_signal(b)
        cyclical = VirtualSignalDef(
            "A", inputs=("WTS.B",),
            operations=(OperationDef(type="scale", params={"factor": 1}),),
        )
        with pytest.raises(WtsValidationError) as exc:
            manager.upsert_virtual_signal(cyclical)
        assert any(
            error["code"] == "dependency_cycle" for error in exc.value.errors
        )

    def test_delete_with_dependents(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="A"))
        manager.upsert_virtual_signal(
            VirtualSignalDef(
                "B", inputs=("WTS.A",),
                operations=(OperationDef(type="bias", params={"offset": 1}),),
            )
        )
        with pytest.raises(SignalDependentsError) as exc:
            manager.delete_virtual_signal("A")
        assert exc.value.dependents == ["B"]
        assert manager.delete_virtual_signal("B")["wts_version"] >= 1
        manager.delete_virtual_signal("A")

    def test_upsert_without_setup_raises(self, manager):
        with pytest.raises(ValueError):
            manager.upsert_virtual_signal(scale_sig())


class TestRenameVirtualSignal:
    def test_rename_updates_definition_and_file(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="Old_Name"))
        result = manager.rename_virtual_signal("Old_Name", "New_Name")
        assert result["renamed_from"] == "Old_Name"
        assert result["def_hash"]
        defs = manager.get_virtual_signals()
        assert [definition.name for definition in defs] == ["New_Name"]
        # The first save promoted the legacy .dbc to a.wts; the file on disk
        # holds the renamed definition and no trace of the old name.
        assert manager.active_dbc_filename == "a.wts"
        text = (manager.wts_dir / "a.wts").read_text()
        assert "New_Name" in text and "Old_Name" not in text

    def test_rename_rewrites_dependent_inputs(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="A"))
        manager.upsert_virtual_signal(
            VirtualSignalDef(
                "B", inputs=("WTS.A",),
                operations=(OperationDef(type="bias", params={"offset": 1}),),
            )
        )
        result = manager.rename_virtual_signal("A", "A2")
        assert result["dependents"] == ["WTS.B"]
        defs = {definition.name: definition for definition in
                manager.get_virtual_signals()}
        assert defs["B"].inputs == ("WTS.A2",)
        assert defs["A2"].inputs == ("Brakes.Front_Psi",)

    def test_rename_moves_signal_info(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="S"))
        manager.active_wts.signal_info["WTS.S"] = {"display_name": "Speedo"}
        manager.rename_virtual_signal("S", "S2")
        assert manager.active_wts.signal_info.get("WTS.S2") == {
            "display_name": "Speedo"
        }
        assert "WTS.S" not in manager.active_wts.signal_info

    def test_rename_collisions_and_invalid(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="A"))
        manager.upsert_virtual_signal(scale_sig(name="B"))
        with pytest.raises(ValueError, match="already exists"):
            manager.rename_virtual_signal("A", "B")
        with pytest.raises(ValueError, match="differ"):
            manager.rename_virtual_signal("A", "A")
        with pytest.raises(FileNotFoundError):
            manager.rename_virtual_signal("Ghost", "X")
        with pytest.raises(WtsValidationError):
            manager.rename_virtual_signal("A", "9bad")

    def test_rename_blocked_by_cycle(self, manager, dbc_bytes):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="A"))
        manager.upsert_virtual_signal(
            VirtualSignalDef(
                "B", inputs=("WTS.A", "Brakes.Front_Psi"),
                operations=(
                    OperationDef(type="combine", params={"operator": "add"}),
                ),
            )
        )
        # An existing signal is literally named WTS.Target: renaming A to it
        # would collide with that name.
        manager.upsert_virtual_signal(
            scale_sig(name="Target", input_id="Brakes.Front_Psi")
        )
        with pytest.raises(ValueError, match="already exists"):
            manager.rename_virtual_signal("A", "Target")

    def test_rename_notifies_changed_ids(self, manager, dbc_bytes):
        seen = []
        manager.set_changed_callback(lambda ids: seen.append(ids))
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upsert_virtual_signal(scale_sig(name="A"))
        manager.upsert_virtual_signal(
            VirtualSignalDef(
                "B", inputs=("WTS.A",),
                operations=(OperationDef(type="bias", params={"offset": 1}),),
            )
        )
        manager.rename_virtual_signal("A", "A2")
        assert seen[-1] == {"WTS.A", "WTS.A2", "WTS.B"}


class TestLastActiveSetup:
    def test_restart_restores_active_setup(self, manager, dbc_bytes, tmp_user_data):
        manager.upload_dbc("a.dbc", dbc_bytes)
        manager.upload_dbc("z.dbc", dbc_bytes)
        manager.select_dbc("z.dbc")
        assert manager.active_dbc_filename == "z.dbc"

        restarted = DBCManager(str(tmp_user_data))
        # Without memory this would pick "a.dbc" (alphabetically first).
        assert restarted.active_dbc_filename == "z.dbc"

    def test_missing_last_active_falls_back(self, manager, dbc_bytes, tmp_user_data):
        manager.upload_dbc("a.dbc", dbc_bytes)
        (tmp_user_data / "wts_last_active.json").write_text(
            '{"filename": "gone.dbc"}'
        )
        restarted = DBCManager(str(tmp_user_data))
        assert restarted.active_dbc_filename == "a.dbc"


class TestVersionAndHook:
    def test_version_bumps_and_hook_fires(self, manager, dbc_bytes):
        seen = []
        manager.set_changed_callback(lambda ids: seen.append(ids))
        manager.upload_dbc("a.dbc", dbc_bytes)  # selects -> hook with None
        version_after_select = manager.get_wts_version()
        manager.upsert_virtual_signal(scale_sig())
        assert manager.get_wts_version() > version_after_select
        assert seen[-1] == {"WTS.Scale_Test"}
        manager.delete_virtual_signal("Scale_Test")
        assert seen[-1] == {"WTS.Scale_Test"}

    def test_hook_exception_does_not_break_state(self, manager, dbc_bytes):
        def bad_hook(ids):
            raise RuntimeError("hook blew up")

        manager.set_changed_callback(bad_hook)
        manager.upload_dbc("a.dbc", dbc_bytes)
        result = manager.upsert_virtual_signal(scale_sig())
        assert result["def_hash"]


class TestBrokenOnLoad:
    def test_file_with_one_bad_input_opens_others_work(self, manager, dbc_bytes):
        from wts.wts_file import WtsFile

        wts = WtsFile.from_dbc_bytes("mix", "mix.dbc", dbc_bytes)
        wts.signals.append(scale_sig(name="Good"))
        wts.signals.append(
            VirtualSignalDef(
                "Bad",
                inputs=("Ghost.Signal",),
                operations=(OperationDef(type="scale", params={"factor": 2}),),
            )
        )
        manager.upload_dbc("mix.wts", wts.serialize().encode())
        manager.select_dbc("mix.wts")
        assert {d.name for d in manager.get_virtual_signals()} == {"Good"}
        broken = manager.get_broken_signals()
        assert "Bad" in broken and "Ghost.Signal" in broken["Bad"]
        entries = {s["id"]: s for s in manager.get_signals() if s.get("is_virtual")}
        assert entries["WTS.Good"]["broken"] is False
        assert entries["WTS.Bad"]["broken"] is True

    def test_signal_info_merge_and_warnings(self, manager, dbc_bytes):
        from wts.wts_file import WtsFile

        wts = WtsFile.from_dbc_bytes("si", "si.dbc", dbc_bytes)
        wts.signals.append(scale_sig(name="V"))
        wts.signal_info["Brakes.Front_Psi"] = {"display_name": "Front", "min": 0, "max": 2000}
        wts.signal_info["WTS.V"] = {"display_name": "Virtual V"}
        wts.signal_info["Ghost.Nope"] = {"display_name": "who?"}
        manager.upload_dbc("si.wts", wts.serialize().encode())
        manager.select_dbc("si.wts")
        entries = {s["id"]: s for s in manager.get_signals()}
        assert entries["Brakes.Front_Psi"]["display_name"] == "Front"
        assert entries["Brakes.Front_Psi"]["max"] == 2000
        assert entries["WTS.V"]["display_name"] == "Virtual V"
        issues = manager.active_analysis().issues
        assert any(
            issue["signal"] == "Ghost.Nope" and issue["severity"] == "warning"
            for issue in issues
        )
        assert not any(issue["signal"] == "WTS.V" for issue in issues)
