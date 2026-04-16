from pathlib import Path
import cantools
from logging_config import get_logger

logger = get_logger(__name__)

def load_dbc(file_path: str = None):
    db = None
    try:
        if file_path:
            target_path = Path(file_path)
            if target_path.exists():
                db = cantools.database.load_file(target_path)
                logger.info(f"Loaded explicit DBC for client-side decoding: {target_path.name}")
            else:
                logger.error(f"Explicit DBC path does not exist: {file_path}")
        else:
            dbc_cache = list(Path('dbc').glob('*.dbc'))
            if not dbc_cache:
                dbc_cache = list(Path('.').glob('*.dbc'))
            if dbc_cache:
                db = cantools.database.load_file(dbc_cache[0])
                logger.info(f"Loaded inferred DBC for client-side decoding: {dbc_cache[0].name}")
    except Exception as e:
        logger.warning(f"No DBC loaded: {e}")
    return db
