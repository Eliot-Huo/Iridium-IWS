"""
Custom Exceptions for SBD System
自訂例外類別 - 提供清晰的錯誤處理
"""

from typing import Optional, Dict, Any


class SBDBaseException(Exception):
    """所有 SBD 系統例外的基礎類別"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        初始化例外
        
        Args:
            message: 錯誤訊息
            details: 額外的錯誤細節
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ========== Domain Exceptions (領域例外) ==========

class ValidationError(SBDBaseException):
    """資料驗證失敗"""
    pass


class BusinessRuleViolationError(SBDBaseException):
    """違反業務規則"""
    pass


# ========== Repository Exceptions (資料存取例外) ==========

class RepositoryError(SBDBaseException):
    """資料存取層基礎例外"""
    pass


class RecordNotFoundError(RepositoryError):
    """找不到記錄"""
    pass


class DuplicateRecordError(RepositoryError):
    """記錄重複"""
    pass


class DatabaseConnectionError(RepositoryError):
    """資料庫連線失敗"""
    pass


# ========== Infrastructure Exceptions (基礎設施例外) ==========

class InfrastructureError(SBDBaseException):
    """基礎設施層基礎例外"""
    pass


class APIConnectionError(InfrastructureError):
    """API 連線失敗"""
    pass


class APIResponseError(InfrastructureError):
    """API 回應錯誤"""
    pass


class APIAuthenticationError(InfrastructureError):
    """API 認證失敗"""
    pass


class FTPConnectionError(InfrastructureError):
    """FTP 連線失敗"""
    pass


class GoogleDriveError(InfrastructureError):
    """Google Drive 操作失敗"""
    pass


# ========== Service Exceptions (服務層例外) ==========

class ServiceError(SBDBaseException):
    """服務層基礎例外"""
    pass


class SubscriberNotFoundError(ServiceError):
    """找不到訂戶"""
    pass


class InvalidSubscriberStateError(ServiceError):
    """訂戶狀態無效"""
    pass


class PlanChangeError(ServiceError):
    """方案變更失敗"""
    pass


class DSGSetupError(ServiceError):
    """DSG 設定失敗"""
    pass


class BillingCalculationError(ServiceError):
    """費用計算失敗"""
    pass


# ========== Configuration Exceptions (設定例外) ==========

class ConfigurationError(SBDBaseException):
    """設定錯誤"""
    pass


class MissingConfigurationError(ConfigurationError):
    """缺少必要設定"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """設定值無效"""
    pass
