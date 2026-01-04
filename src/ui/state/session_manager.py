"""
Session State 管理器

統一管理 Streamlit session state，提供：
1. 服務工廠初始化
2. Repository 管理
3. 角色管理
4. 輪詢狀態管理

Author: Senior Python Software Architect
Date: 2026-01-04
"""
import streamlit as st
from typing import Optional

from src.di import get_service_factory, ServiceFactory
from src.repositories.repo import InMemoryRepository
from src.models.models import UserRole
from src.infrastructure.iws_gateway import IWSGateway
from src.services.billing_service import BillingService
from src.services.cdr_service import CDRService
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigurationError


logger = get_logger('SessionManager')


class SessionManager:
    """
    Session State 管理器
    
    統一管理所有 Streamlit session state 變數。
    所有 UI 模組都應該透過此管理器訪問服務。
    
    Example:
        >>> SessionManager.initialize()
        >>> gateway = SessionManager.get_gateway()
        >>> billing_service = SessionManager.get_billing_service()
    """
    
    @staticmethod
    def initialize() -> None:
        """
        初始化所有 session state 變數
        
        這個方法應該在 app.py 的 main() 開頭呼叫。
        會初始化服務工廠、repository、角色等。
        """
        logger.debug("Initializing session state")
        
        # 1. 初始化服務工廠
        SessionManager._initialize_service_factory()
        
        # 2. 初始化 Repository
        SessionManager._initialize_repository()
        
        # 3. 初始化用戶角色
        SessionManager._initialize_user_role()
        
        # 4. 初始化輪詢狀態
        SessionManager._initialize_polling_state()
        
        # 5. 初始化 Gateway（向後兼容）
        SessionManager._initialize_gateway_compat()
        
        logger.info("Session state initialized", 
                   role=st.session_state.current_role.value,
                   polling_enabled=st.session_state.polling_enabled)
    
    @staticmethod
    def _initialize_service_factory() -> None:
        """初始化服務工廠"""
        if 'service_factory' not in st.session_state:
            logger.info("Initializing ServiceFactory")
            
            factory = get_service_factory()
            
            if not factory.is_initialized:
                try:
                    factory.initialize_from_secrets(st.secrets)
                    logger.info("ServiceFactory initialized from secrets")
                except ConfigurationError as e:
                    logger.error("Failed to initialize ServiceFactory", exception=e)
                    st.error(f"❌ 服務初始化失敗：{e.message}")
                    st.stop()
            
            st.session_state.service_factory = factory
    
    @staticmethod
    def _initialize_repository() -> None:
        """初始化 Repository"""
        if 'request_store' not in st.session_state:
            logger.info("Initializing InMemoryRepository")
            st.session_state.request_store = InMemoryRepository()
    
    @staticmethod
    def _initialize_user_role() -> None:
        """初始化用戶角色"""
        if 'current_role' not in st.session_state:
            logger.info("Initializing user role", role="CUSTOMER")
            st.session_state.current_role = UserRole.CUSTOMER
    
    @staticmethod
    def _initialize_polling_state() -> None:
        """初始化輪詢狀態"""
        if 'polling_enabled' not in st.session_state:
            st.session_state.polling_enabled = False
    
    @staticmethod
    def _initialize_gateway_compat() -> None:
        """
        初始化 Gateway（向後兼容）
        
        為了向後兼容現有程式碼，同時在 session_state 中
        保存 gateway 的直接引用。
        """
        if 'gateway' not in st.session_state:
            st.session_state.gateway = SessionManager.get_gateway()
    
    # ==================== 服務訪問方法 ====================
    
    @staticmethod
    def get_service_factory() -> ServiceFactory:
        """
        取得服務工廠
        
        Returns:
            ServiceFactory 實例
            
        Raises:
            RuntimeError: 如果 session state 未初始化
        """
        if 'service_factory' not in st.session_state:
            raise RuntimeError(
                "SessionManager not initialized. "
                "Call SessionManager.initialize() first."
            )
        return st.session_state.service_factory
    
    @staticmethod
    def get_gateway() -> IWSGateway:
        """
        取得 IWS Gateway
        
        Returns:
            IWS Gateway 實例
        """
        factory = SessionManager.get_service_factory()
        return factory.gateway
    
    @staticmethod
    def get_billing_service() -> BillingService:
        """
        取得 Billing Service
        
        Returns:
            Billing Service 實例
        """
        factory = SessionManager.get_service_factory()
        return factory.billing_service
    
    @staticmethod
    def get_cdr_service() -> CDRService:
        """
        取得 CDR Service
        
        Returns:
            CDR Service 實例
        """
        factory = SessionManager.get_service_factory()
        return factory.cdr_service
    
    @staticmethod
    def get_repository() -> InMemoryRepository:
        """
        取得 Repository
        
        Returns:
            InMemoryRepository 實例
        """
        if 'request_store' not in st.session_state:
            raise RuntimeError("SessionManager not initialized")
        return st.session_state.request_store
    
    # ==================== 狀態訪問方法 ====================
    
    @staticmethod
    def get_current_role() -> UserRole:
        """
        取得當前用戶角色
        
        Returns:
            當前角色（CUSTOMER 或 ASSISTANT）
        """
        if 'current_role' not in st.session_state:
            return UserRole.CUSTOMER
        return st.session_state.current_role
    
    @staticmethod
    def set_current_role(role: UserRole) -> None:
        """
        設定當前用戶角色
        
        Args:
            role: 新角色
        """
        old_role = st.session_state.get('current_role')
        st.session_state.current_role = role
        
        logger.info("User role changed", 
                   old_role=old_role.value if old_role else None,
                   new_role=role.value)
    
    @staticmethod
    def is_polling_enabled() -> bool:
        """
        檢查輪詢是否啟用
        
        Returns:
            True 如果輪詢已啟用
        """
        return st.session_state.get('polling_enabled', False)
    
    @staticmethod
    def set_polling_enabled(enabled: bool) -> None:
        """
        設定輪詢狀態
        
        Args:
            enabled: True 啟用輪詢
        """
        st.session_state.polling_enabled = enabled
        logger.info("Polling state changed", enabled=enabled)
    
    # ==================== 工具方法 ====================
    
    @staticmethod
    def reset() -> None:
        """
        重置所有 session state
        
        Warning:
            這會清除所有狀態，僅用於開發/測試
        """
        logger.warning("Resetting all session state")
        
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        logger.info("Session state reset complete")
