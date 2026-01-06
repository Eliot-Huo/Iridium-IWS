"""
Device Management Page (Assistant)
設備管理頁面 - 助理端
"""

import streamlit as st
import logging
from typing import Optional

from src.services.subscriber_service import SubscriberService
from src.utils.exceptions import (
    SubscriberNotFoundError,
    InvalidSubscriberStateError,
    PlanChangeError,
    ServiceError
)


logger = logging.getLogger(__name__)


def render_device_management_page(
    subscriber_service: SubscriberService
) -> None:
    """
    渲染設備管理頁面
    
    職責：
    - 渲染 UI
    - 處理使用者輸入
    - 呼叫 Service
    - 顯示結果
    
    不包含：
    - 業務邏輯
    - API 呼叫
    - 資料驗證（除了 UI 層級的基本驗證）
    
    Args:
        subscriber_service: 訂戶服務（透過依賴注入）
    """
    st.header("🛰️ 設備管理")
    
    # 建立標籤
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 查詢設備",
        "✅ 啟用設備",
        "⏸️ 暫停設備",
        "❌ 註銷設備",
        "🔄 變更方案"
    ])
    
    # ========== Tab 1: 查詢設備 ==========
    with tab1:
        st.subheader("查詢設備資訊")
        
        with st.form("query_form"):
            imei = st.text_input(
                "IMEI",
                max_chars=15,
                placeholder="請輸入 15 位數字"
            )
            
            submitted = st.form_submit_button("🔍 查詢")
            
            if submitted:
                if not imei or len(imei) != 15 or not imei.isdigit():
                    st.error("❌ 請輸入有效的 15 位數字 IMEI")
                else:
                    _handle_query_subscriber(subscriber_service, imei)
    
    # ========== Tab 2: 啟用設備 ==========
    with tab2:
        st.subheader("啟用設備")
        
        with st.form("activate_form"):
            imei = st.text_input(
                "IMEI",
                max_chars=15,
                key="activate_imei"
            )
            
            plan_id = st.selectbox(
                "資費方案",
                ["SBD0", "SBD12", "SBD17", "SBD30", "SBD12P", "SBD17P", "SBD30P"]
            )
            
            reason = st.text_area(
                "啟用原因",
                placeholder="請輸入啟用原因..."
            )
            
            submitted = st.form_submit_button("✅ 啟用")
            
            if submitted:
                if not imei or len(imei) != 15 or not imei.isdigit():
                    st.error("❌ 請輸入有效的 15 位數字 IMEI")
                else:
                    _handle_activate_subscriber(
                        subscriber_service,
                        imei,
                        plan_id,
                        reason
                    )
    
    # ========== Tab 3: 暫停設備 ==========
    with tab3:
        st.subheader("暫停設備")
        
        with st.form("suspend_form"):
            imei = st.text_input(
                "IMEI",
                max_chars=15,
                key="suspend_imei"
            )
            
            reason = st.text_area(
                "暫停原因",
                placeholder="請輸入暫停原因..."
            )
            
            submitted = st.form_submit_button("⏸️ 暫停")
            
            if submitted:
                if not imei or len(imei) != 15 or not imei.isdigit():
                    st.error("❌ 請輸入有效的 15 位數字 IMEI")
                else:
                    _handle_suspend_subscriber(
                        subscriber_service,
                        imei,
                        reason
                    )
    
    # ========== Tab 4: 註銷設備 ==========
    with tab4:
        st.subheader("註銷設備")
        
        st.warning("⚠️ 註銷後設備將無法使用，此操作不可逆！")
        
        with st.form("deactivate_form"):
            imei = st.text_input(
                "IMEI",
                max_chars=15,
                key="deactivate_imei"
            )
            
            reason = st.text_area(
                "註銷原因",
                placeholder="請輸入註銷原因..."
            )
            
            confirm = st.checkbox("我確認要註銷此設備")
            
            submitted = st.form_submit_button("❌ 註銷")
            
            if submitted:
                if not confirm:
                    st.error("❌ 請勾選確認框")
                elif not imei or len(imei) != 15 or not imei.isdigit():
                    st.error("❌ 請輸入有效的 15 位數字 IMEI")
                else:
                    _handle_deactivate_subscriber(
                        subscriber_service,
                        imei,
                        reason
                    )
    
    # ========== Tab 5: 變更方案 ==========
    with tab5:
        st.subheader("變更資費方案")
        
        with st.form("change_plan_form"):
            imei = st.text_input(
                "IMEI",
                max_chars=15,
                key="change_plan_imei"
            )
            
            new_plan_id = st.selectbox(
                "新資費方案",
                ["SBD0", "SBD12", "SBD17", "SBD30", "SBD12P", "SBD17P", "SBD30P"]
            )
            
            reason = st.text_area(
                "變更原因",
                placeholder="請輸入變更原因..."
            )
            
            submitted = st.form_submit_button("🔄 變更")
            
            if submitted:
                if not imei or len(imei) != 15 or not imei.isdigit():
                    st.error("❌ 請輸入有效的 15 位數字 IMEI")
                else:
                    _handle_change_plan(
                        subscriber_service,
                        imei,
                        new_plan_id,
                        reason
                    )


# ========== Handler Functions ==========

def _handle_query_subscriber(
    service: SubscriberService,
    imei: str
) -> None:
    """處理查詢訂戶"""
    try:
        with st.spinner("查詢中..."):
            subscriber = service.get_subscriber(imei)
        
        st.success("✅ 查詢成功")
        
        # 顯示訂戶資訊
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("IMEI", subscriber.imei)
            st.metric("狀態", subscriber.status.value)
            st.metric("方案", subscriber.plan_id)
        
        with col2:
            if subscriber.account_number:
                st.metric("帳號", subscriber.account_number)
            if subscriber.activation_date:
                st.metric("啟用日期", subscriber.activation_date.strftime("%Y-%m-%d"))
            if subscriber.customer_name:
                st.metric("客戶", subscriber.customer_name)
        
        if subscriber.notes:
            st.info(f"📝 備註: {subscriber.notes}")
        
    except SubscriberNotFoundError as e:
        st.error(f"❌ {e.message}")
    except Exception as e:
        st.error(f"❌ 查詢失敗: {str(e)}")
        logger.error(f"Query error: {e}", exc_info=True)


def _handle_activate_subscriber(
    service: SubscriberService,
    imei: str,
    plan_id: str,
    reason: Optional[str]
) -> None:
    """處理啟用訂戶"""
    try:
        with st.spinner("啟用中..."):
            subscriber = service.activate_subscriber(imei, plan_id, reason)
        
        st.success(f"✅ 訂戶 {imei} 已成功啟用")
        st.info(f"📋 方案: {subscriber.plan_id}")
        
    except SubscriberNotFoundError as e:
        st.error(f"❌ {e.message}")
    except InvalidSubscriberStateError as e:
        st.warning(f"⚠️ {e.message}")
    except Exception as e:
        st.error(f"❌ 啟用失敗: {str(e)}")
        logger.error(f"Activate error: {e}", exc_info=True)


def _handle_suspend_subscriber(
    service: SubscriberService,
    imei: str,
    reason: Optional[str]
) -> None:
    """處理暫停訂戶"""
    try:
        with st.spinner("暫停中..."):
            subscriber = service.suspend_subscriber(imei, reason)
        
        st.success(f"✅ 訂戶 {imei} 已成功暫停")
        
    except SubscriberNotFoundError as e:
        st.error(f"❌ {e.message}")
    except InvalidSubscriberStateError as e:
        st.warning(f"⚠️ {e.message}")
    except Exception as e:
        st.error(f"❌ 暫停失敗: {str(e)}")
        logger.error(f"Suspend error: {e}", exc_info=True)


def _handle_deactivate_subscriber(
    service: SubscriberService,
    imei: str,
    reason: Optional[str]
) -> None:
    """處理註銷訂戶"""
    try:
        with st.spinner("註銷中..."):
            subscriber = service.deactivate_subscriber(imei, reason)
        
        st.success(f"✅ 訂戶 {imei} 已成功註銷")
        
    except SubscriberNotFoundError as e:
        st.error(f"❌ {e.message}")
    except InvalidSubscriberStateError as e:
        st.warning(f"⚠️ {e.message}")
    except Exception as e:
        st.error(f"❌ 註銷失敗: {str(e)}")
        logger.error(f"Deactivate error: {e}", exc_info=True)


def _handle_change_plan(
    service: SubscriberService,
    imei: str,
    new_plan_id: str,
    reason: Optional[str]
) -> None:
    """處理變更方案"""
    try:
        with st.spinner("變更中..."):
            subscriber = service.change_subscriber_plan(imei, new_plan_id, reason)
        
        st.success(f"✅ 訂戶 {imei} 已成功變更方案")
        st.info(f"📋 新方案: {subscriber.plan_id}")
        
    except SubscriberNotFoundError as e:
        st.error(f"❌ {e.message}")
    except PlanChangeError as e:
        st.warning(f"⚠️ {e.message}")
    except Exception as e:
        st.error(f"❌ 變更失敗: {str(e)}")
        logger.error(f"Change plan error: {e}", exc_info=True)
