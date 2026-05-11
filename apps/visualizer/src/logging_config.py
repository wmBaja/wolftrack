"""
Logging configuration for CAN Logger Backend
src/logging_config.py

Sets up application-wide logging with console and rotating file handlers.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


# Global flag to prevent multiple initializations
_logging_initialized = False


def setup_logging(
    log_dir: str = './app_logs',
    log_level: str = 'INFO',
    console_output: bool = True,
    log_to_file: bool = True,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    format_style: str = 'detailed'
) -> logging.Logger:
    """
    Setup application-wide logging configuration.
    
    This should be called ONCE at application startup.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to log to console
        log_to_file: Whether to log to file
        max_file_size_mb: Max size of each log file before rotation
        backup_count: Number of backup files to keep
        format_style: 'detailed' or 'simple'
    
    Returns:
        Configured root logger
    
    Example:
        >>> from logging_config import setup_logging
        >>> setup_logging(log_level='DEBUG')
    """
    global _logging_initialized
    
    if _logging_initialized:
        return logging.getLogger()
    
    # Create log directory
    log_path = Path(log_dir) 
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers (in case setup is called multiple times)
    root_logger.handlers.clear()
    
    # Set logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)
    
    # Create formatters
    if format_style == 'detailed':
        # Detailed format for files - includes everything
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Cleaner format for console - more readable
        console_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        # Simple format for both
        simple_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_formatter = simple_formatter
        console_formatter = simple_formatter
    
    # Console handler (stdout)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Main file handler with rotation
    if log_to_file:
        log_file = log_path / 'app.log'
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Error-only file handler (captures just errors and critical)
    if log_to_file:
        error_log_file = log_path / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
    
    # Mark as initialized
    _logging_initialized = True
    
    # Log initial startup message
    root_logger.info("=" * 80)
    root_logger.info(f"Logging initialized - Level: {log_level}")
    root_logger.info(f"Log directory: {log_path.absolute()}")
    root_logger.info(f"Console output: {console_output}")
    root_logger.info(f"File logging: {log_to_file}")
    root_logger.info("=" * 80)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Usage in any module:
        from logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    
    Args:
        name: Logger name, typically __name__ of the module
    
    Returns:
        Logger instance for the specified name
    
    Example:
        >>> from logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)

def setup_test_logger() -> logging.Logger:
    return setup_logging(
        log_dir='./app_logs',
        log_level='DEBUG',
        console_output=True,
        log_to_file=True,
        max_file_size_mb=10000,
        backup_count=5,
        format_style='detailed'
    )


def set_level(logger_name: str, level: str):
    """
    Change the logging level for a specific logger.
    
    Useful for debugging specific modules without changing global level.
    
    Args:
        logger_name: Name of the logger (e.g., 'src.can_interface')
        level: New level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Example:
        >>> set_level('src.can_interface', 'DEBUG')
    """
    logger = logging.getLogger(logger_name)
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.info(f"Logger '{logger_name}' level changed to {level}")


def reset_logging():
    """
    Reset logging configuration (useful for testing).
    
    This removes all handlers and allows setup_logging() to be called again.
    """
    global _logging_initialized
    _logging_initialized = False
    
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)


# ============================================================================
# Advanced: Structured logging helper
# ============================================================================

class StructuredLogger:
    """
    Helper for logging with consistent structured data.
    
    Useful for log aggregation systems or when you want consistent
    formatting across different log types.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> structured = StructuredLogger(logger)
        >>> structured.log_can_message(can_msg)
        >>> structured.log_session_event('START', session='drive_test')
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_can_message(self, msg, level: int = logging.DEBUG):
        """Log a CAN message with structured format"""

        data_str = ''.join(f"[{i}]{b:02X}" for i, b in enumerate(msg.data))

        self.logger.log(
            level,
            f"CAN | ID: 0x{msg.arbitration_id:03X} | "
            f"DLC: {msg.dlc} | "
            f"Data: {data_str} | "
            f"Timestamp: {msg.timestamp:.6f}"
        )
    
    def log_session_event(self, event: str, level: int = logging.INFO, **kwargs):
        """Log a session-related event"""
        extra = ' | '.join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.log(level, f"SESSION | {event} | {extra}")
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics"""
        extra = ' | '.join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(
            f"PERF | {operation} | {duration_ms:.2f}ms | {extra}"
        )
    
    def log_dbc_event(self, event: str, **kwargs):
        """Log DBC-related events"""
        extra = ' | '.join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"DBC | {event} | {extra}")


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    # Setup logging for development
    logger = setup_logging(
        log_dir='./app_logs',
        log_level='DEBUG',
        console_output=True,
        log_to_file=True,
        format_style='detailed'
    )

    # Get logger for this module
    logger = get_logger(__name__)
    
    print("\n=== Testing Different Log Levels ===\n")
    
    # Test different log levels
    logger.debug("This is a DEBUG message - very detailed info")
    logger.info("This is an INFO message - normal operation")
    logger.warning("This is a WARNING message - something unusual")
    logger.error("This is an ERROR message - something went wrong")
    logger.critical("This is a CRITICAL message - system unstable")
    
    print("\n=== Testing Exception Logging ===\n")
    
    # Test exception logging
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("Division by zero occurred", exc_info=True)
    
    print("\n=== Testing Structured Logging ===\n")
    
    # Test structured logging
    structured = StructuredLogger(logger)
    
    # Mock CAN message
    class MockCANMessage:
        def __init__(self):
            self.arbitration_id = 0x123
            self.dlc = 8
            self.data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
            self.timestamp = 1234567890.123456
    
    mock_msg = MockCANMessage()
    structured.log_can_message(mock_msg)
    structured.log_session_event('START', session_name='test_drive', user='admin')
    structured.log_performance('log_write', 45.67, file_size_mb=12.3, signal_count=150)
    structured.log_dbc_event('LOADED', filename='vehicle.dbc', message_count=245)
    
    print("\n=== Testing Module-Specific Logging ===\n")
    
    # Create loggers for different modules
    can_logger = get_logger('src.can_interface')
    dbc_logger = get_logger('src.dbc_manager')
    session_logger = get_logger('src.session_manager')
    
    can_logger.info("CAN interface initialized")
    dbc_logger.info("DBC database loaded")
    session_logger.info("Session started")

    print(f"\n=== Log files created in: ./app_logs/===")
    print("Check these files:")
    print("  - app.log (all messages)")
    print("  - errors.log (errors only)")