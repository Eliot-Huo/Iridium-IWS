"""
側邊欄元件

顯示應用標題、角色選擇和系統狀態。

Author: Senior Python Software Architect
Date: 2026-01-04
"""
import streamlit as st

from src.ui.state.session_manager import SessionManager
from src.models.models import UserRole
from src.utils.logger import get_logger


logger = get_logger('Sidebar')


def render_sidebar() -> None:
    """
    渲染側邊欄
    
    包含：
    1. 應用標題和版本
    2. 角色選擇器
    3. Gateway 連線狀態
    4. 系統資訊
    """
    with st.sidebar:
        # 標題
        st.title("🛰️ SBD 管理系統")
        st.caption("v6.36.0 - 企業級重構版")
        
        st.divider()
        
        # 角色選擇
        _render_role_selector()
        
        st.divider()
        
        # 系統狀態
        _render_system_status()
        
        st.divider()
        
        # 關於資訊
        _render_about_info()


def _render_role_selector() -> None:
    """渲染角色選擇器"""
    st.subheader("👤 用戶角色")
    
    current_role = SessionManager.get_current_role()
    
    # 角色選項
    role_options = {
        UserRole.CUSTOMER: "👤 客戶",
        UserRole.ASSISTANT: "🔧 助理"
    }
    
    # 當前索引
    current_index = 0 if current_role == UserRole.CUSTOMER else 1
    
    # 選擇器
    selected_label = st.radio(
        "選擇角色",
        options=list(role_options.values()),
        index=current_index,
        label_visibility="collapsed"
    )
    
    # 轉換回 UserRole
    new_role = UserRole.CUSTOMER if "客戶" in selected_label else UserRole.ASSISTANT
    
    # 更新角色（如果改變）
    if new_role != current_role:
        SessionManager.set_current_role(new_role)
        logger.info("User switched role", 
                   old_role=current_role.value,
                   new_role=new_role.value)
        st.rerun()


def _render_system_status() -> None:
    """渲染系統狀態"""
    st.subheader("📡 系統狀態")
    
    try:
        # Gateway 狀態
        gateway = SessionManager.get_gateway()
        
        st.success("✅ Gateway 已連接")
        
        # 詳細資訊
        with st.expander("連線資訊"):
            st.text(f"Username: {gateway.username}")
            st.text(f"SP Account: {gateway.sp_account}")
            st.text(f"Endpoint: {gateway.endpoint[:50]}...")
        
        # Repository 狀態
        repo = SessionManager.get_repository()
        pending_count = len([r for r in repo.get_all() if r.status == "PENDING"])
        
        if pending_count > 0:
            st.warning(f"⏳ {pending_count} 個待處理請求")
        
    except Exception as e:
        st.error("❌ 系統未就緒")
        logger.error("Failed to render system status", exception=e)


def _render_about_info() -> None:
    """渲染關於資訊"""
    st.subheader("ℹ️ 關於")
    
    st.caption("""
    **SBD 衛星設備管理系統**
    
    企業級架構重構版，包含：
    - 🛡️ 異常處理體系
    - 📝 結構化日誌
    - 💉 依賴注入
    - 🎨 模組化設計
    
    © 2026 N3D
    """)
