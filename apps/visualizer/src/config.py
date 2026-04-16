"""
Configuration module for CAN Visualizer Backend
src/config.py

Defines all configuration dataclasses and loading methods.
"""
from dataclasses import dataclass, field
import os

@dataclass
class ZMQConfig:
    """ZMQ Client Configuration"""
    enabled: bool = True
    port: int = 5555
    host: str = '127.0.0.1'
    
    @classmethod
    def from_env(cls) -> 'ZMQConfig':
        return cls(
            enabled=os.getenv('ZMQ_ENABLED', 'true').lower() == 'true',
            port=int(os.getenv('ZMQ_PORT', '5555')),
            host=os.getenv('ZMQ_HOST', '127.0.0.1')
        )

@dataclass
class FastAPIConfig:
    """FastAPI Server Configuration"""
    host: str = '127.0.0.1'
    port: int = 0  # 0 means ephemeral by default
    
    @classmethod
    def from_env(cls) -> 'FastAPIConfig':
        return cls(
            host=os.getenv('FASTAPI_HOST', '127.0.0.1'),
            port=int(os.getenv('FASTAPI_PORT', '0'))
        )

@dataclass
class AppLogConfig:
    """Application logging configuration"""
    log_dir: str = './app_logs'
    log_level: str = 'INFO'
    log_to_console: bool = True
    log_to_file: bool = True
    max_log_file_size_mb: int = 10
    log_backup_count: int = 5
    log_format: str = 'detailed'
    
    @classmethod
    def from_env(cls) -> 'AppLogConfig':
        return cls(
            log_dir=os.getenv('APP_LOG_DIR', './app_logs'),
            log_level=os.getenv('APP_LOG_LEVEL', 'INFO').upper(),
            log_to_console=os.getenv('APP_LOG_TO_CONSOLE', 'true').lower() == 'true',
            log_to_file=os.getenv('APP_LOG_TO_FILE', 'true').lower() == 'true',
            max_log_file_size_mb=int(os.getenv('APP_LOG_MAX_FILE_SIZE_MB', '10')),
            log_backup_count=int(os.getenv('APP_LOG_BACKUP_COUNT', '5')),
            log_format=os.getenv('APP_LOG_FORMAT', 'detailed')
        )

@dataclass
class PipelineConfig:
    """Data Pipeline Configuration"""
    source: str = 'zmq'  # 'zmq' or 'logfile'
    log_file: str = 'data.blf'
    dbc_file: str = None
    playback_speed: float = 1.0
    
    @classmethod
    def from_env(cls) -> 'PipelineConfig':
        return cls(
            source=os.getenv('PIPELINE_SOURCE', 'zmq').lower(),
            log_file=os.getenv('PIPELINE_LOG_FILE', 'data.blf'),
            dbc_file=os.getenv('PIPELINE_DBC_FILE', None),
            playback_speed=float(os.getenv('PIPELINE_PLAYBACK_SPEED', '1.0'))
        )

@dataclass
class AppConfig:
    """Main application configuration"""
    zmq: ZMQConfig = field(default_factory=ZMQConfig)
    fastapi: FastAPIConfig = field(default_factory=FastAPIConfig)
    appLog: AppLogConfig = field(default_factory=AppLogConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        return cls(
            zmq=ZMQConfig.from_env(),
            fastapi=FastAPIConfig.from_env(),
            appLog=AppLogConfig.from_env(),
            pipeline=PipelineConfig.from_env()
        )
