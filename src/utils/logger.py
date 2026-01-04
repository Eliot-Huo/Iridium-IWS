"""
結構化日誌系統

提供 JSON 格式的結構化日誌，便於 ELK、CloudWatch 等工具解析。
整合異常體系，自動記錄錯誤的詳細資訊。

Author: Senior Python Software Architect
Date: 2026-01-04
"""
from __future__ import annotations
import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from src.utils.exceptions import SBDException, ErrorSeverity
from src.utils.security import SensitiveDataFilter


class StructuredFormatter(logging.Formatter):
    """
    結構化日誌格式化器
    
    將日誌格式化為 JSON，包含時間戳、等級、訊息和額外欄位。
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日誌記錄為 JSON
        
        Args:
            record: 日誌記錄
            
        Returns:
            JSON 格式的日誌字串
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 加入額外欄位
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # 如果是異常，加入異常資訊
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # 過濾敏感資訊
        log_data = SensitiveDataFilter.sanitize_dict(log_data)
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """
    結構化日誌記錄器
    
    提供結構化的日誌記錄功能，支援：
    1. JSON 格式輸出
    2. 自動過濾敏感資訊
    3. 整合異常體系
    4. 支援上下文資訊（request_id, user_id 等）
    
    Example:
        >>> logger = StructuredLogger('MyService')
        >>> logger.info("User logged in", user_id='123', ip='1.2.3.4')
        >>> logger.error("Operation failed", error='Connection timeout', retry_count=3)
    """
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        enable_console: bool = True
    ):
        """
        初始化日誌記錄器
        
        Args:
            name: 日誌記錄器名稱（通常是模組名稱）
            level: 日誌等級
            log_file: 日誌檔案路徑（可選）
            enable_console: 是否輸出到控制台
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False
        
        # 移除現有 handlers（避免重複）
        self.logger.handlers.clear()
        
        # 結構化格式化器
        formatter = StructuredFormatter()
        
        # Console Handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File Handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _log(
        self,
        level: str,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs
    ):
        """
        內部日誌方法
        
        Args:
            level: 日誌等級（'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'）
            message: 日誌訊息
            exception: 異常物件（可選）
            **kwargs: 額外的上下文資訊
        """
        # 準備額外欄位
        extra_fields = kwargs.copy()
        
        # 如果是 SBDException，提取詳細資訊
        if isinstance(exception, SBDException):
            extra_fields['exception_details'] = exception.to_dict()
        
        # 創建 LogRecord
        log_record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level),
            '',  # pathname
            0,   # lineno
            message,
            (),  # args
            exc_info=None if exception is None else (type(exception), exception, exception.__traceback__),
        )
        
        # 加入額外欄位
        log_record.extra_fields = extra_fields
        
        # 發送日誌
        self.logger.handle(log_record)
    
    def debug(self, message: str, **kwargs):
        """
        記錄 DEBUG 等級日誌
        
        Args:
            message: 日誌訊息
            **kwargs: 額外的上下文資訊
        """
        self._log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """
        記錄 INFO 等級日誌
        
        Args:
            message: 日誌訊息
            **kwargs: 額外的上下文資訊
        
        Example:
            >>> logger.info("User logged in", user_id='123', ip='1.2.3.4')
        """
        self._log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """
        記錄 WARNING 等級日誌
        
        Args:
            message: 日誌訊息
            **kwargs: 額外的上下文資訊
        """
        self._log('WARNING', message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """
        記錄 ERROR 等級日誌
        
        Args:
            message: 日誌訊息
            exception: 異常物件（可選）
            **kwargs: 額外的上下文資訊
        
        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     logger.error("Operation failed", exception=e, retry_count=3)
        """
        self._log('ERROR', message, exception=exception, **kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """
        記錄 CRITICAL 等級日誌
        
        Args:
            message: 日誌訊息
            exception: 異常物件（可選）
            **kwargs: 額外的上下文資訊
        """
        self._log('CRITICAL', message, exception=exception, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """
        記錄異常（自動捕捉當前異常）
        
        應該在 except 區塊中呼叫。
        
        Args:
            message: 日誌訊息
            **kwargs: 額外的上下文資訊
        
        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception:
            ...     logger.exception("Operation failed", operation='risky')
        """
        import sys
        exc_info = sys.exc_info()
        exception = exc_info[1] if exc_info[1] else None
        
        self.error(message, exception=exception, **kwargs)


class LoggerFactory:
    """
    日誌記錄器工廠
    
    集中管理所有日誌記錄器，確保：
    1. 同名 logger 只創建一次
    2. 統一配置
    3. 便於測試時 mock
    """
    
    _loggers: Dict[str, StructuredLogger] = {}
    _default_level: int = logging.INFO
    _default_log_dir: Optional[Path] = None
    
    @classmethod
    def configure(cls, level: int = logging.INFO, log_dir: Optional[str] = None):
        """
        配置全域日誌設定
        
        Args:
            level: 預設日誌等級
            log_dir: 日誌檔案目錄
        """
        cls._default_level = level
        if log_dir:
            cls._default_log_dir = Path(log_dir)
            cls._default_log_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        level: Optional[int] = None,
        log_file: Optional[str] = None
    ) -> StructuredLogger:
        """
        取得日誌記錄器
        
        Args:
            name: 日誌記錄器名稱
            level: 日誌等級（可選，使用全域設定）
            log_file: 日誌檔案名稱（可選）
            
        Returns:
            結構化日誌記錄器
            
        Example:
            >>> logger = LoggerFactory.get_logger('MyService')
            >>> logger.info("Service started")
        """
        if name not in cls._loggers:
            # 決定日誌檔案路徑
            file_path = None
            if log_file:
                if cls._default_log_dir:
                    file_path = str(cls._default_log_dir / log_file)
                else:
                    file_path = log_file
            
            # 創建新的 logger
            cls._loggers[name] = StructuredLogger(
                name=name,
                level=level or cls._default_level,
                log_file=file_path
            )
        
        return cls._loggers[name]


# 便捷函式
def get_logger(name: str, log_file: Optional[str] = None) -> StructuredLogger:
    """
    取得日誌記錄器（便捷函式）
    
    Args:
        name: 日誌記錄器名稱
        log_file: 日誌檔案名稱（可選）
        
    Returns:
        結構化日誌記錄器
        
    Example:
        >>> from src.utils.logger import get_logger
        >>> logger = get_logger('MyService', 'myservice.log')
        >>> logger.info("Service started")
    """
    return LoggerFactory.get_logger(name, log_file=log_file)
