"""
SBD 系統異常定義

企業級異常體系，用於取代通用 Exception。
所有異常都繼承自 SBDException，並包含結構化的錯誤資訊。

Author: Senior Python Software Architect
Date: 2026-01-04
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ErrorSeverity(Enum):
    """錯誤嚴重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SBDException(Exception):
    """
    SBD 系統基礎異常類別
    
    所有 SBD 系統異常都應繼承此類別。
    包含結構化錯誤資訊，便於日誌記錄和錯誤追蹤。
    
    Attributes:
        message: 錯誤訊息（人類可讀）
        details: 錯誤詳細資訊（字典格式）
        severity: 錯誤嚴重程度
        timestamp: 錯誤發生時間
        context: 錯誤上下文（如 user_id, request_id 等）
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        初始化異常
        
        Args:
            message: 錯誤訊息
            details: 錯誤詳細資訊
            severity: 錯誤嚴重程度
            context: 錯誤上下文資訊
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.severity = severity
        self.timestamp = datetime.now()
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式（用於日誌記錄）
        
        Returns:
            包含錯誤資訊的字典
        """
        return {
            'exception_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context
        }
    
    def __str__(self) -> str:
        """字串表示"""
        return f"{self.__class__.__name__}: {self.message}"
    
    def __repr__(self) -> str:
        """詳細表示"""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"details={self.details}, "
            f"severity={self.severity.value})"
        )


# ============================================================
# 網路與連線相關異常
# ============================================================

class NetworkError(SBDException):
    """
    網路連線錯誤
    
    當無法連接到外部服務（IWS API, FTP, Google Drive 等）時拋出。
    
    Example:
        >>> raise NetworkError(
        ...     "Failed to connect to IWS endpoint",
        ...     details={'endpoint': 'https://iws.example.com', 'timeout': 30}
        ... )
    """
    
    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if endpoint:
            error_details['endpoint'] = endpoint
        if timeout:
            error_details['timeout'] = timeout
        
        super().__init__(
            message=message,
            details=error_details,
            severity=ErrorSeverity.ERROR
        )


class TimeoutError(NetworkError):
    """
    請求逾時錯誤
    
    當 API 請求或網路操作超過預期時間時拋出。
    """
    pass


class ConnectionRefusedError(NetworkError):
    """
    連線被拒絕錯誤
    
    當目標伺服器拒絕連線時拋出。
    """
    pass


# ============================================================
# 認證與授權相關異常
# ============================================================

class AuthenticationError(SBDException):
    """
    認證失敗錯誤
    
    當用戶認證失敗（如密碼錯誤、API Key 無效）時拋出。
    
    Example:
        >>> raise AuthenticationError(
        ...     "Invalid IWS credentials",
        ...     details={'username': 'user123'}
        ... )
    """
    
    def __init__(
        self,
        message: str,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if username:
            error_details['username'] = username
        
        super().__init__(
            message=message,
            details=error_details,
            severity=ErrorSeverity.CRITICAL
        )


class AuthorizationError(SBDException):
    """
    授權錯誤
    
    當用戶嘗試執行沒有權限的操作時拋出。
    
    Example:
        >>> raise AuthorizationError(
        ...     "User does not have permission to activate device",
        ...     details={'user_role': 'CUSTOMER', 'required_role': 'ASSISTANT'}
        ... )
    """
    
    def __init__(
        self,
        message: str,
        user_role: Optional[str] = None,
        required_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if user_role:
            error_details['user_role'] = user_role
        if required_role:
            error_details['required_role'] = required_role
        
        super().__init__(
            message=message,
            details=error_details,
            severity=ErrorSeverity.ERROR
        )


# ============================================================
# 資料驗證相關異常
# ============================================================

class ValidationError(SBDException):
    """
    資料驗證錯誤
    
    當輸入資料不符合預期格式或規則時拋出。
    
    Example:
        >>> raise ValidationError(
        ...     field='imei',
        ...     value='123',
        ...     reason='IMEI must be exactly 15 digits'
        ... )
    """
    
    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details.update({
            'field': field,
            'value': str(value),
            'reason': reason
        })
        
        message = f"Validation failed for field '{field}': {reason}"
        
        super().__init__(
            message=message,
            details=error_details,
            severity=ErrorSeverity.WARNING
        )


class IMEIValidationError(ValidationError):
    """
    IMEI 驗證錯誤
    
    當 IMEI 格式不正確或檢查碼失敗時拋出。
    
    Example:
        >>> raise IMEIValidationError(
        ...     imei='12345',
        ...     reason='IMEI must be 15 digits'
        ... )
    """
    
    def __init__(self, imei: str, reason: str):
        super().__init__(
            field='imei',
            value=imei,
            reason=reason
        )


class DateRangeValidationError(ValidationError):
    """
    日期範圍驗證錯誤
    
    當開始日期晚於結束日期，或日期格式不正確時拋出。
    """
    
    def __init__(self, start_date: str, end_date: str, reason: str):
        super().__init__(
            field='date_range',
            value=f"{start_date} to {end_date}",
            reason=reason
        )


# ============================================================
# 資源操作相關異常
# ============================================================

class ResourceNotFoundError(SBDException):
    """
    資源不存在錯誤
    
    當嘗試訪問不存在的資源（如 IMEI、檔案、記錄等）時拋出。
    
    Example:
        >>> raise ResourceNotFoundError(
        ...     resource_type='device',
        ...     resource_id='300534066711380'
        ... )
    """
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details.update({
            'resource_type': resource_type,
            'resource_id': resource_id
        })
        
        message = f"{resource_type.capitalize()} not found: {resource_id}"
        
        super().__init__(
            message=message,
            details=error_details,
            severity=ErrorSeverity.WARNING
        )


class ResourceAlreadyExistsError(SBDException):
    """
    資源已存在錯誤
    
    當嘗試創建已存在的資源時拋出。
    """
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details.update({
            'resource_type': resource_type,
            'resource_id': resource_id
        })
        
        message = f"{resource_type.capitalize()} already exists: {resource_id}"
        
        super().__init__(
            message=message,
            details=error_details,
            severity=ErrorSeverity.WARNING
        )


# ============================================================
# 業務邏輯相關異常
# ============================================================

class BillingCalculationError(SBDException):
    """
    計費計算錯誤
    
    當計費過程中發生錯誤時拋出。
    
    Example:
        >>> raise BillingCalculationError(
        ...     "Failed to calculate monthly bill",
        ...     details={'imei': '300534066711380', 'year': 2025, 'month': 10}
        ... )
    """
    pass


class PlanNotFoundError(ResourceNotFoundError):
    """
    資費方案不存在錯誤
    
    當嘗試使用不存在的資費方案時拋出。
    """
    
    def __init__(self, plan_name: str):
        super().__init__(
            resource_type='plan',
            resource_id=plan_name
        )


class InvalidPlanTransitionError(SBDException):
    """
    無效的方案轉換錯誤
    
    當嘗試進行不允許的方案轉換時拋出。
    
    Example:
        >>> raise InvalidPlanTransitionError(
        ...     from_plan='SBD12',
        ...     to_plan='SBD30',
        ...     reason='Cannot upgrade to SBD30 from SBD12 directly'
        ... )
    """
    
    def __init__(self, from_plan: str, to_plan: str, reason: str):
        super().__init__(
            message=f"Invalid plan transition from {from_plan} to {to_plan}: {reason}",
            details={
                'from_plan': from_plan,
                'to_plan': to_plan,
                'reason': reason
            },
            severity=ErrorSeverity.WARNING
        )


class DeviceStatusError(SBDException):
    """
    設備狀態錯誤
    
    當設備狀態不允許執行特定操作時拋出。
    
    Example:
        >>> raise DeviceStatusError(
        ...     imei='300534066711380',
        ...     current_status='SUSPENDED',
        ...     required_status='ACTIVE',
        ...     operation='send_message'
        ... )
    """
    
    def __init__(
        self,
        imei: str,
        current_status: str,
        required_status: str,
        operation: str
    ):
        super().__init__(
            message=(
                f"Cannot perform '{operation}' on device {imei}: "
                f"current status is {current_status}, required {required_status}"
            ),
            details={
                'imei': imei,
                'current_status': current_status,
                'required_status': required_status,
                'operation': operation
            },
            severity=ErrorSeverity.WARNING
        )


# ============================================================
# CDR 處理相關異常
# ============================================================

class CDRParsingError(SBDException):
    """
    CDR 解析錯誤
    
    當 CDR 檔案格式不正確或無法解析時拋出。
    
    Example:
        >>> raise CDRParsingError(
        ...     "Invalid TAP II record format",
        ...     details={'record_length': 140, 'expected': 160}
        ... )
    """
    pass


class CDRFileNotFoundError(ResourceNotFoundError):
    """
    CDR 檔案不存在錯誤
    """
    
    def __init__(self, file_path: str):
        super().__init__(
            resource_type='cdr_file',
            resource_id=file_path
        )


# ============================================================
# IWS API 相關異常
# ============================================================

class IWSException(SBDException):
    """
    IWS API 異常
    
    當 IWS API 呼叫失敗時拋出。
    包含 IWS API 回傳的錯誤代碼和詳細資訊。
    
    Attributes:
        error_code: IWS API 錯誤代碼（如 'IMEI_NOT_FOUND'）
        response_text: IWS API 回應內容（已過濾敏感資訊）
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        response_text: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if error_code:
            error_details['error_code'] = error_code
        if response_text:
            # 過濾敏感資訊後再記錄
            from src.utils.security import SensitiveDataFilter
            error_details['response_text'] = SensitiveDataFilter.sanitize(response_text)
        
        super().__init__(
            message=message,
            details=error_details,
            severity=ErrorSeverity.ERROR
        )
        
        self.error_code = error_code
        self.response_text = response_text


class IWSReportException(IWSException):
    """
    IWS Report API 異常
    
    當 IWS Report API 呼叫失敗時拋出。
    """
    pass


# ============================================================
# 配置相關異常
# ============================================================

class ConfigurationError(SBDException):
    """
    配置錯誤
    
    當系統配置不正確或缺少必要配置時拋出。
    
    Example:
        >>> raise ConfigurationError(
        ...     "Missing required configuration",
        ...     details={'missing_keys': ['IWS_USERNAME', 'IWS_PASSWORD']}
        ... )
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.CRITICAL
        )


class SecretNotFoundError(ConfigurationError):
    """
    密鑰不存在錯誤
    
    當嘗試訪問不存在的 Streamlit secret 時拋出。
    """
    
    def __init__(self, secret_key: str):
        super().__init__(
            message=f"Secret key not found: {secret_key}",
            details={'secret_key': secret_key}
        )


# ============================================================
# FTP 相關異常
# ============================================================

class FTPError(SBDException):
    """
    FTP 操作錯誤
    
    當 FTP 操作失敗時拋出。
    """
    pass


class FTPConnectionError(FTPError):
    """
    FTP 連線錯誤
    """
    
    def __init__(self, host: str, port: int, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details.update({'host': host, 'port': port})
        
        super().__init__(
            message=f"Failed to connect to FTP server {host}:{port}",
            details=error_details,
            severity=ErrorSeverity.ERROR
        )


# ============================================================
# Google Drive 相關異常
# ============================================================

class GoogleDriveError(SBDException):
    """
    Google Drive 操作錯誤
    
    當 Google Drive API 呼叫失敗時拋出。
    """
    pass


class GoogleDriveAuthError(GoogleDriveError, AuthenticationError):
    """
    Google Drive 認證錯誤
    """
    
    def __init__(self, message: str = "Google Drive authentication failed"):
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL
        )


# ============================================================
# 系統內部錯誤
# ============================================================

class InternalError(SBDException):
    """
    系統內部錯誤
    
    當系統發生未預期的內部錯誤時拋出。
    這通常表示程式碼邏輯錯誤，需要開發者介入。
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.CRITICAL
        )


class NotImplementedError(InternalError):
    """
    功能未實作錯誤
    
    當嘗試使用尚未實作的功能時拋出。
    """
    
    def __init__(self, feature: str):
        super().__init__(
            message=f"Feature not implemented: {feature}",
            details={'feature': feature}
        )
