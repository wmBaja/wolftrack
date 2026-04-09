from pathlib import Path
import cantools
from logging_config import get_logger

logger = get_logger(__name__)

def load_dbc():
    db = None
    try:
        dbc_cache = list(Path('.').glob('*.dbc'))
        if dbc_cache:
            db = cantools.database.load_file(dbc_cache[0])
            logger.info(f"Loaded DBC for client-side decoding: {dbc_cache[0].name}")
    except Exception as e:
        logger.warning(f"No DBC loaded: {e}")
    return db
