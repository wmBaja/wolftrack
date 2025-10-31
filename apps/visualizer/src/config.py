from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class FlaskConfig:
    """Flask application configuration"""
    
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False # Enable/disable debug mode for Flask app 
    enable_cors: bool = True  # Enable/disable CORS for API

    @classmethod
    def from_env(cls) -> 'FlaskConfig':
        """Load configuration from environment variables"""
        return cls(
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', '5000')),
            debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
            enable_cors=os.getenv('ENABLE_CORS', 'true').lower() == 'true'
        )
    
    def __repr__(self) -> str:
        return (f"FlaskConfig(host={self.host}, port={self.port}, debug={self.debug}, "
                f"enable_cors={self.enable_cors})")
    
@dataclass
class AppLogConfig:
    """Application logging configuration"""
    
    log_dir: str = './app.log'
    log_level: str = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_to_console: bool = True
    log_to_file: bool = True
    max_log_file_size_mb: int = 10  # Max size for log file before rotation
    log_backup_count: int = 5  # Number of backup log files to keep
    log_format : str = 'detailed'  # 'simple' or 'detailed'
    
    @classmethod
    def from_env(cls) -> 'AppLogConfig':
        """Load configuration from environment variables"""
        return cls(
            log_dir=os.getenv('APP_LOG_DIR', './app.log'),
            log_level=os.getenv('APP_LOG_LEVEL', 'INFO').upper(),
            log_to_console=os.getenv('APP_LOG_TO_CONSOLE', 'true').lower() == 'true',
            log_to_file=os.getenv('APP_LOG_TO_FILE', 'true').lower() == 'true',
            max_log_file_size_mb=int(os.getenv('APP_LOG_MAX_FILE_SIZE_MB', '10')),
            log_backup_count=int(os.getenv('APP_LOG_BACKUP_COUNT', '5')),
            log_format=os.getenv('APP_LOG_FORMAT', 'detailed')
        )
    
    def __repr__(self) -> str:
        return (f"AppLogConfig(log_dir={self.log_dir}, log_level={self.log_level}, "
                f"log_to_console={self.log_to_console}, log_to_file={self.log_to_file}, "
                f"max_log_file_size_mb={self.max_log_file_size_mb}, log_backup_count={self.log_backup_count}, "
                f"log_format={self.log_format})")
    
@dataclass
class AppConfig:
    """Main application configuration"""

    appLog: AppLogConfig = field(default_factory=AppLogConfig)
    flask: FlaskConfig = field(default_factory=FlaskConfig)

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load entire configuration from environment variables"""
        return cls(
            appLog=AppLogConfig.from_env(),
            flask=FlaskConfig.from_env()
        )
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'AppConfig':
        """Load configuration from dictionary (for config files)"""
        app_log_config = AppLogConfig(**config_dict.get('appLog', {}))
        flask_config = FlaskConfig(**config_dict.get('flask', {}))
        
        return cls(
            appLog=app_log_config,
            flask=flask_config
        )

    def __repr__(self) -> str:
        return (f"AppConfig(can={self.can}, appLog={self.appLog}, flask={self.flask})")
    
