import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import cantools

from logging_config import get_logger

logger = get_logger(__name__)

class DBCManager:
    def __init__(self, user_data_dir: str):
        self.dbc_dir = Path(user_data_dir) / "dbc"
        self.dbc_dir.mkdir(parents=True, exist_ok=True)
        self.active_dbc_filename: Optional[str] = None
        self.db: Optional[cantools.database.Database] = None
        
        # Load initially if there is one available
        dbcs = self.get_available_dbcs()
        if dbcs:
            self.select_dbc(dbcs[0]["name"])
            
    def get_available_dbcs(self) -> List[Dict[str, Any]]:
        """Return a list of available DBC file info."""
        return [
            {
                "name": f.name,
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime
            }
            for f in self.dbc_dir.glob("*.dbc")
        ]

    def _get_dbc_path(self, filename: str) -> Path:
        """Return a validated path within the managed DBC directory."""
        if (
            not isinstance(filename, str)
            or not filename.strip()
            or filename != filename.strip()
            or '/' in filename
            or '\\' in filename
            or '..' in filename
            or Path(filename).name != filename
            or Path(filename).suffix != '.dbc'
        ):
            raise ValueError('Filename must be a plain .dbc filename')

        return self.dbc_dir / filename
        
    def upload_dbc(self, filename: str, file_content: bytes) -> str:
        """Save a DBC file to the dbc directory."""
        file_path = self._get_dbc_path(filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"DBC uploaded: {filename}")
        
        # If this is the only one, select it automatically
        if len(self.get_available_dbcs()) == 1:
            self.select_dbc(filename)
            
        return str(file_path)
        
    def delete_dbc(self, filename: str) -> bool:
        """Delete a DBC file. Return True if successful."""
        file_path = self._get_dbc_path(filename)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"DBC deleted: {filename}")
            if self.active_dbc_filename == filename:
                self.active_dbc_filename = None
                self.db = None
                # Try to load another one
                dbcs = self.get_available_dbcs()
                if dbcs:
                    self.select_dbc(dbcs[0]["name"])
            return True
        return False

    def rename_dbc(self, filename: str, new_filename: str) -> bool:
        """Rename a DBC file and retain its active state when applicable."""
        file_path = self._get_dbc_path(filename)
        new_file_path = self._get_dbc_path(new_filename)

        if not file_path.exists():
            return False
        if new_file_path.exists():
            raise ValueError('A DBC with that name already exists')

        file_path.rename(new_file_path)
        if self.active_dbc_filename == filename:
            self.active_dbc_filename = new_filename

        logger.info(f"DBC renamed: {filename} -> {new_filename}")
        return True
        
    def select_dbc(self, filename: str) -> bool:
        """Select a DBC file to be the active database."""
        file_path = self._get_dbc_path(filename)
        if file_path.exists():
            try:
                self.db = cantools.database.load_file(file_path)
                self.active_dbc_filename = filename
                logger.info(f"DBC selected and loaded: {filename}")
                return True
            except Exception as e:
                logger.error(f"Failed to load DBC {filename}: {e}")
                return False
        else:
            logger.error(f"DBC file not found to select: {filename}")
            return False
            
    def get_active_dbc(self) -> Optional[cantools.database.Database]:
        """Return the active cantools database."""
        return self.db
        
    def get_signals(self) -> List[Dict[str, Any]]:
        """Return a list of all signals in the active DBC."""
        if not self.db:
            return []
            
        signals = []
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
        return signals
