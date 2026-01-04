"""
Utils 模組

提供工具函式和異常定義。

包含：
- exceptions: 企業級異常體系
- security: 安全工具（敏感資訊過濾、IMEI 驗證等）
- logger: 結構化日誌系統
"""

# 導出日誌相關
from src.utils.logger import (
    StructuredLogger,
    LoggerFactory,
    get_logger,
)

# 導出所有異常類別，方便其他模組使用
from src.utils.exceptions import (
    # 基礎異常
    SBDException,
    ErrorSeverity,
    
    # 網路相關
    NetworkError,
    TimeoutError,
    ConnectionRefusedError,
    
    # 認證授權
    AuthenticationError,
    AuthorizationError,
    
    # 資料驗證
    ValidationError,
    IMEIValidationError,
    DateRangeValidationError,
    
    # 資源操作
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    
    # 業務邏輯
    BillingCalculationError,
    PlanNotFoundError,
    InvalidPlanTransitionError,
    DeviceStatusError,
    
    # CDR 處理
    CDRParsingError,
    CDRFileNotFoundError,
    
    # IWS API
    IWSException,
    IWSReportException,
    
    # 配置
    ConfigurationError,
    SecretNotFoundError,
    
    # FTP
    FTPError,
    FTPConnectionError,
    
    # Google Drive
    GoogleDriveError,
    GoogleDriveAuthError,
    
    # 系統內部
    InternalError,
    NotImplementedError,
)

# 導出安全工具
from src.utils.security import (
    SensitiveDataFilter,
    mask_imei,
    validate_imei_checksum,
)

__all__ = [
    # 日誌相關
    'StructuredLogger',
    'LoggerFactory',
    'get_logger',
    
    # 基礎異常
    'SBDException',
    'ErrorSeverity',
    
    # 網路相關
    'NetworkError',
    'TimeoutError',
    'ConnectionRefusedError',
    
    # 認證授權
    'AuthenticationError',
    'AuthorizationError',
    
    # 資料驗證
    'ValidationError',
    'IMEIValidationError',
    'DateRangeValidationError',
    
    # 資源操作
    'ResourceNotFoundError',
    'ResourceAlreadyExistsError',
    
    # 業務邏輯
    'BillingCalculationError',
    'PlanNotFoundError',
    'InvalidPlanTransitionError',
    'DeviceStatusError',
    
    # CDR 處理
    'CDRParsingError',
    'CDRFileNotFoundError',
    
    # IWS API
    'IWSException',
    'IWSReportException',
    
    # 配置
    'ConfigurationError',
    'SecretNotFoundError',
    
    # FTP
    'FTPError',
    'FTPConnectionError',
    
    # Google Drive
    'GoogleDriveError',
    'GoogleDriveAuthError',
    
    # 系統內部
    'InternalError',
    'NotImplementedError',
    
    # 安全工具
    'SensitiveDataFilter',
    'mask_imei',
    'validate_imei_checksum',
]
