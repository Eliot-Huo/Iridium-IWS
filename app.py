"""
SBD Management System - Main Application
SBD 管理系統主程式
"""

import streamlit as st
import logging
from typing import Dict, Any

# Infrastructure
from src.infrastructure.iws_client import IWSClient
from src.infrastructure.ftp_client import FTPClient
from src.infrastructure.gdrive_client import GoogleDriveClient

# Repositories
from src.repositories.subscriber_repository import SubscriberRepository
from src.repositories.dsg_repository import DSGRepository

# Services
from src.services.subscriber_service import SubscriberService
from src.services.dsg_service import DSGService

# UI Pages
from src.ui.pages.assistant.device_management import render_device_management_page
from src.ui.pages.assistant.dsg_management import render_dsg_management_page

# Utils
from src.utils.types import IWSConfig, FTPConfig, GoogleDriveConfig
from src.utils.exceptions import SBDBaseException


# 設定 Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========== Configuration ==========

def load_config_from_secrets() -> Dict[str, Any]:
    """
    從 Streamlit Secrets 載入設定
    
    Returns:
        設定字典
    """
    return {
        'iws': IWSConfig(
            endpoint=st.secrets.get('IWS_ENDPOINT', ''),
            username=st.secrets.get('IWS_USERNAME', ''),
            password=st.secrets.get('IWS_PASSWORD', ''),
            sp_account=st.secrets.get('IWS_SP_ACCOUNT', ''),
            timeout=30
        ),
        'ftp': FTPConfig(
            host=st.secrets.get('FTP_HOST', ''),
            port=21,
            username=st.secrets.get('FTP_USER', ''),
            password=st.secrets.get('FTP_PASS', ''),
            passive_mode=True
        ),
        'gdrive': GoogleDriveConfig(
            service_account_json=st.secrets.get('GOOGLE_SERVICE_ACCOUNT_JSON', ''),
            root_folder_id=st.secrets.get('GOOGLE_DRIVE_ROOT_FOLDER_ID', '')
        )
    }


# ========== Dependency Injection ==========

@st.cache_resource
def init_dependencies() -> Dict[str, Any]:
    """
    初始化依賴注入容器
    
    使用 Streamlit cache_resource 確保單例模式。
    
    Returns:
        依賴字典
    """
    logger.info("Initializing dependencies...")
    
    try:
        # 載入設定
        config = load_config_from_secrets()
        
        # 1. Infrastructure Layer
        iws_client = IWSClient(config['iws'])
        ftp_client = FTPClient(config['ftp'])
        gdrive_client = GoogleDriveClient(config['gdrive'])
        
        # 建立連線（IWS 必須成功，GDrive 可選）
        iws_client.connect()
        gdrive_client.connect()  # 失敗時只記錄警告，不中斷
        
        # 2. Repository Layer
        subscriber_repo = SubscriberRepository(iws_client)
        dsg_repo = DSGRepository(iws_client)
        
        # 3. Service Layer
        subscriber_service = SubscriberService(subscriber_repo)
        dsg_service = DSGService(dsg_repo)
        
        logger.info("✅ Dependencies initialized successfully")
        
        return {
            # Clients
            'iws_client': iws_client,
            'ftp_client': ftp_client,
            'gdrive_client': gdrive_client,
            
            # Services
            'subscriber_service': subscriber_service,
            'dsg_service': dsg_service
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize dependencies: {e}")
        raise


# ========== Page Configuration ==========

def setup_page_config() -> None:
    """設定頁面"""
    st.set_page_config(
        page_title="SBD 管理系統",
        page_icon="🛰️",
        layout="wide",
        initial_sidebar_state="expanded"
    )


# ========== Sidebar Navigation ==========

def render_sidebar(deps: Dict[str, Any]) -> tuple[str, str]:
    """
    渲染側邊欄導航
    
    Args:
        deps: 依賴字典
        
    Returns:
        (角色, 頁面) 元組
    """
    with st.sidebar:
        st.title("🛰️ SBD 管理系統")
        st.markdown("---")
        
        # 角色選擇
        role = st.radio(
            "選擇角色",
            ["助理", "客戶"],
            key="role_selector"
        )
        
        st.markdown("---")
        
        # 根據角色顯示不同選單
        if role == "助理":
            page = st.radio(
                "選擇功能",
                [
                    "設備管理",
                    "DSG 流量管理",
                    "費用查詢",
                    "CDR 管理",
                    "Profile 管理"
                ]
            )
        else:  # 客戶
            page = st.radio(
                "選擇功能",
                [
                    "設備查詢",
                    "DSG 流量查詢",
                    "費用查詢"
                ]
            )
        
        st.markdown("---")
        
        # 系統資訊
        with st.expander("ℹ️ 系統資訊"):
            st.text(f"版本: v6.45.0")
            st.text(f"架構: Clean Architecture")
            
            # 連線狀態
            if deps.get('iws_client'):
                iws_status = "🟢 已連線" if deps['iws_client'].is_connected() else "🔴 未連線"
                st.text(f"IWS API: {iws_status}")
            
            if deps.get('gdrive_client'):
                gdrive_status = "🟢 已連線" if deps['gdrive_client'].is_connected() else "⚪ 未設定"
                st.text(f"Google Drive: {gdrive_status}")
        
        return role, page


# ========== Main Application ==========

def main() -> None:
    """主程式入口"""
    # 設定頁面
    setup_page_config()
    
    try:
        # 初始化依賴
        deps = init_dependencies()
        
        # 渲染側邊欄並取得選擇
        role, page = render_sidebar(deps)
        
        # 根據角色和頁面渲染對應內容
        if role == "助理":
            if page == "設備管理":
                render_device_management_page(deps['subscriber_service'])
            
            elif page == "DSG 流量管理":
                render_dsg_management_page(deps['dsg_service'])
            
            elif page == "費用查詢":
                st.header("💰 費用查詢")
                st.info("功能開發中...")
            
            elif page == "CDR 管理":
                st.header("📊 CDR 管理")
                st.info("功能開發中...")
            
            elif page == "Profile 管理":
                st.header("📋 Profile 管理")
                st.info("功能開發中...")
        
        else:  # 客戶
            if page == "設備查詢":
                st.header("🛰️ 設備查詢")
                st.info("功能開發中...")
            
            elif page == "DSG 流量查詢":
                st.header("📊 DSG 流量查詢")
                st.info("功能開發中...")
            
            elif page == "費用查詢":
                st.header("💰 費用查詢")
                st.info("功能開發中...")
    
    except SBDBaseException as e:
        st.error(f"❌ 系統錯誤: {e.message}")
        if e.details:
            st.json(e.details)
        logger.error(f"Application error: {e}", exc_info=True)
    
    except Exception as e:
        st.error(f"❌ 未預期的錯誤: {str(e)}")
        logger.error(f"Unexpected error: {e}", exc_info=True)


# ========== Entry Point ==========

if __name__ == '__main__':
    main()
