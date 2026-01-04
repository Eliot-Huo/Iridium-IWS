"""
服務工廠 - 依賴注入容器

統一管理所有服務實例，實作單例模式和依賴注入。

核心原則：
1. 所有服務透過工廠創建
2. UI 層不直接創建服務
3. 便於測試時 mock
4. 集中管理生命週期

Author: Senior Python Software Architect
Date: 2026-01-04
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from pathlib import Path

from src.infrastructure.iws_gateway import IWSGateway
from src.infrastructure.gdrive_client import GoogleDriveClient
from src.infrastructure.ftp_client import FTPClient
from src.services.cdr_service import CDRService
from src.services.billing_service import BillingService
from src.services.sbd_service import SBDService
from src.services.billing_calculator import BillingCalculator
from src.config.price_rules import get_price_manager
from src.utils.logger import get_logger, LoggerFactory
from src.utils.exceptions import ConfigurationError, SecretNotFoundError


logger = get_logger('ServiceFactory')


class ServiceFactory:
    """
    服務工廠（單例模式）
    
    統一管理所有服務實例，確保：
    1. 同一服務只創建一次
    2. 依賴關係正確注入
    3. 配置統一管理
    4. 便於測試和維護
    
    Example:
        >>> # 初始化（通常在 app.py 啟動時）
        >>> factory = ServiceFactory()
        >>> factory.initialize_from_secrets(st.secrets)
        >>>
        >>> # 使用服務
        >>> gateway = factory.gateway
        >>> billing_service = factory.billing_service
    """
    
    _instance: Optional['ServiceFactory'] = None
    
    def __new__(cls):
        """單例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化（只執行一次）"""
        if self._initialized:
            return
        
        # 服務實例
        self._gateway: Optional[IWSGateway] = None
        self._gdrive_client: Optional[GoogleDriveClient] = None
        self._ftp_client: Optional[FTPClient] = None
        self._cdr_service: Optional[CDRService] = None
        self._billing_service: Optional[BillingService] = None
        self._sbd_service: Optional[SBDService] = None
        self._billing_calculator: Optional[BillingCalculator] = None
        
        # 配置
        self._secrets: Optional[Dict[str, Any]] = None
        self._initialized = False
        
        logger.info("ServiceFactory created")
    
    def initialize_from_secrets(self, secrets: Dict[str, Any]) -> None:
        """
        從 Streamlit secrets 初始化所有服務
        
        Args:
            secrets: Streamlit secrets 字典
            
        Raises:
            ConfigurationError: 配置錯誤
            SecretNotFoundError: 缺少必要的 secret
            
        Example:
            >>> import streamlit as st
            >>> factory = ServiceFactory()
            >>> factory.initialize_from_secrets(st.secrets)
        """
        if self._initialized:
            logger.warning("ServiceFactory already initialized, skipping")
            return
        
        logger.info("Initializing ServiceFactory from secrets")
        
        try:
            self._secrets = secrets
            self._validate_secrets(secrets)
            
            # 初始化基礎設施層
            self._initialize_infrastructure(secrets)
            
            # 初始化服務層
            self._initialize_services()
            
            self._initialized = True
            logger.info("ServiceFactory initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize ServiceFactory", exception=e)
            raise ConfigurationError(
                "Failed to initialize services",
                details={'error': str(e)}
            )
    
    def _validate_secrets(self, secrets: Dict[str, Any]) -> None:
        """
        驗證必要的 secrets 是否存在
        
        Args:
            secrets: Streamlit secrets 字典
            
        Raises:
            SecretNotFoundError: 缺少必要的 secret
        """
        required_secrets = [
            'IWS_USERNAME',
            'IWS_PASSWORD',
            'IWS_SP_ACCOUNT',
            'IWS_ENDPOINT',
        ]
        
        missing_secrets = [
            key for key in required_secrets
            if key not in secrets
        ]
        
        if missing_secrets:
            raise SecretNotFoundError(
                f"Missing required secrets: {', '.join(missing_secrets)}"
            )
    
    def _initialize_infrastructure(self, secrets: Dict[str, Any]) -> None:
        """
        初始化基礎設施層服務
        
        Args:
            secrets: Streamlit secrets 字典
        """
        logger.info("Initializing infrastructure services")
        
        # IWS Gateway
        self._gateway = IWSGateway(
            username=secrets['IWS_USERNAME'],
            password=secrets['IWS_PASSWORD'],
            sp_account=secrets['IWS_SP_ACCOUNT'],
            endpoint=secrets['IWS_ENDPOINT']
        )
        logger.info("IWS Gateway initialized", endpoint=secrets['IWS_ENDPOINT'])
        
        # Google Drive Client（可選）
        if 'GDRIVE_FOLDER_ID' in secrets:
            try:
                self._gdrive_client = GoogleDriveClient()
                logger.info("Google Drive Client initialized")
            except Exception as e:
                logger.warning("Failed to initialize Google Drive Client", exception=e)
                self._gdrive_client = None
        
        # FTP Client（可選）
        if all(key in secrets for key in ['FTP_HOST', 'FTP_USERNAME', 'FTP_PASSWORD']):
            try:
                self._ftp_client = FTPClient(
                    host=secrets['FTP_HOST'],
                    username=secrets['FTP_USERNAME'],
                    password=secrets['FTP_PASSWORD'],
                    port=secrets.get('FTP_PORT', 21)
                )
                logger.info("FTP Client initialized", host=secrets['FTP_HOST'])
            except Exception as e:
                logger.warning("Failed to initialize FTP Client", exception=e)
                self._ftp_client = None
    
    def _initialize_services(self) -> None:
        """初始化服務層"""
        logger.info("Initializing service layer")
        
        # CDR Service
        self._cdr_service = CDRService()
        logger.info("CDR Service initialized")
        
        # Billing Calculator
        price_manager = get_price_manager()
        self._billing_calculator = BillingCalculator(price_manager=price_manager)
        logger.info("Billing Calculator initialized")
        
        # Billing Service（依賴 Gateway, CDR Service, Calculator）
        self._billing_service = BillingService(
            gateway=self._gateway,
            cdr_service=self._cdr_service,
            calculator=self._billing_calculator
        )
        logger.info("Billing Service initialized")
        
        # SBD Service（需要 repository）
        # 注意：SBDService 需要 InMemoryRepository，這裡不初始化
        # 因為 repository 通常在 session_state 中管理
        # 如果需要，可以在 app.py 中單獨創建
        self._sbd_service = None
        logger.info("SBD Service skipped (requires repository from session_state)")
    
    @property
    def gateway(self) -> IWSGateway:
        """
        取得 IWS Gateway
        
        Returns:
            IWS Gateway 實例
            
        Raises:
            ConfigurationError: 服務未初始化
        """
        if not self._initialized or self._gateway is None:
            raise ConfigurationError("ServiceFactory not initialized. Call initialize_from_secrets() first.")
        return self._gateway
    
    @property
    def gdrive_client(self) -> Optional[GoogleDriveClient]:
        """
        取得 Google Drive Client
        
        Returns:
            Google Drive Client 實例（可能為 None）
        """
        if not self._initialized:
            raise ConfigurationError("ServiceFactory not initialized")
        return self._gdrive_client
    
    @property
    def ftp_client(self) -> Optional[FTPClient]:
        """
        取得 FTP Client
        
        Returns:
            FTP Client 實例（可能為 None）
        """
        if not self._initialized:
            raise ConfigurationError("ServiceFactory not initialized")
        return self._ftp_client
    
    @property
    def cdr_service(self) -> CDRService:
        """
        取得 CDR Service
        
        Returns:
            CDR Service 實例
            
        Raises:
            ConfigurationError: 服務未初始化
        """
        if not self._initialized or self._cdr_service is None:
            raise ConfigurationError("ServiceFactory not initialized")
        return self._cdr_service
    
    @property
    def billing_service(self) -> BillingService:
        """
        取得 Billing Service
        
        Returns:
            Billing Service 實例
            
        Raises:
            ConfigurationError: 服務未初始化
        """
        if not self._initialized or self._billing_service is None:
            raise ConfigurationError("ServiceFactory not initialized")
        return self._billing_service
    
    @property
    def sbd_service(self) -> Optional[SBDService]:
        """
        取得 SBD Service
        
        Returns:
            SBD Service 實例（可能為 None）
            
        Note:
            SBD Service 需要 InMemoryRepository，
            通常在 app.py 的 session_state 中單獨創建
        """
        if not self._initialized:
            raise ConfigurationError("ServiceFactory not initialized")
        return self._sbd_service
    
    @property
    def billing_calculator(self) -> BillingCalculator:
        """
        取得 Billing Calculator
        
        Returns:
            Billing Calculator 實例
            
        Raises:
            ConfigurationError: 服務未初始化
        """
        if not self._initialized or self._billing_calculator is None:
            raise ConfigurationError("ServiceFactory not initialized")
        return self._billing_calculator
    
    @property
    def is_initialized(self) -> bool:
        """
        檢查是否已初始化
        
        Returns:
            True 如果已初始化
        """
        return self._initialized
    
    def reset(self) -> None:
        """
        重置工廠（主要用於測試）
        
        Warning:
            這會清除所有服務實例，僅用於測試環境
        """
        logger.warning("Resetting ServiceFactory")
        
        self._gateway = None
        self._gdrive_client = None
        self._ftp_client = None
        self._cdr_service = None
        self._billing_service = None
        self._sbd_service = None
        self._billing_calculator = None
        self._secrets = None
        self._initialized = False


def get_service_factory() -> ServiceFactory:
    """
    取得服務工廠實例（便捷函式）
    
    Returns:
        ServiceFactory 實例（單例）
        
    Example:
        >>> factory = get_service_factory()
        >>> if not factory.is_initialized:
        ...     factory.initialize_from_secrets(st.secrets)
        >>> gateway = factory.gateway
    """
    return ServiceFactory()
