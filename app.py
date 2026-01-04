"""
SBD 衛星設備管理系統 - 主程式

企業級架構重構版本，包含：
- 依賴注入
- 異常處理體系
- 結構化日誌
- 模組化設計

Author: Senior Python Software Architect
Date: 2026-01-04
Version: 6.36.0
"""
import streamlit as st

from src.ui import (
    SessionManager,
    render_sidebar,
    render_customer_billing_page
)
from src.models.models import UserRole
from src.utils.logger import LoggerFactory, get_logger


# ==================== 應用配置 ====================

# 配置日誌系統
LoggerFactory.configure(
    level='INFO',
    log_dir='logs'
)

logger = get_logger('app')

# Streamlit 頁面配置
st.set_page_config(
    page_title="SBD 管理系統",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== 主程式 ====================

def main() -> None:
    """
    主程式入口
    
    流程：
    1. 初始化 Session State
    2. 渲染側邊欄
    3. 根據角色渲染對應頁面
    """
    try:
        # 1. 初始化 Session State
        SessionManager.initialize()
        
        # 2. 渲染側邊欄
        render_sidebar()
        
        # 3. 根據角色渲染頁面
        current_role = SessionManager.get_current_role()
        
        if current_role == UserRole.CUSTOMER:
            # 客戶視圖
            render_customer_billing_page()
        else:
            # 助理視圖
            st.header("🔧 助理管理頁面")
            st.info("助理功能開發中...")
            
            st.caption("""
            計劃功能：
            - 設備管理
            - 方案管理  
            - 請求審批
            - 系統監控
            """)
        
        logger.debug("Page rendered successfully", role=current_role.value)
        
    except Exception as e:
        logger.critical("Application error", exception=e)
        st.error(f"❌ 應用程式錯誤：{str(e)}")
        
        with st.expander("錯誤詳情"):
            st.exception(e)


# ==================== 程式入口 ====================

if __name__ == "__main__":
    main()
