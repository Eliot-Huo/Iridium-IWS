"""
DSG Management Page (Assistant)
DSG 管理頁面 - 助理端
"""

import streamlit as st
import logging
from typing import Optional

from src.services.dsg_service import DSGService
from src.utils.exceptions import (
    RecordNotFoundError,
    ValidationError,
    DSGSetupError,
    ServiceError
)


logger = logging.getLogger(__name__)


def render_dsg_management_page(
    dsg_service: DSGService
) -> None:
    """
    渲染 DSG 管理頁面
    
    Args:
        dsg_service: DSG 服務（透過依賴注入）
    """
    st.header("🛰️ DSG 流量管理")
    
    # 建立標籤
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 查看 DSG 流量",
        "➕ 建立監控群組",
        "👥 管理群組成員",
        "⚡ 一鍵設定"
    ])
    
    # ========== Tab 1: 查看 DSG 流量 ==========
    with tab1:
        st.subheader("查看 DSG 流量")
        
        try:
            groups = dsg_service.get_all_groups()
            
            if not groups:
                st.info("📋 目前沒有 DSG 群組")
            else:
                # 選擇群組
                group_names = {g.group_name: g.group_id for g in groups}
                selected_name = st.selectbox(
                    "選擇群組",
                    options=list(group_names.keys())
                )
                
                if selected_name:
                    group_id = group_names[selected_name]
                    _display_group_info(dsg_service, group_id)
        
        except Exception as e:
            st.error(f"❌ 載入群組失敗: {str(e)}")
            logger.error(f"Load groups error: {e}", exc_info=True)
    
    # ========== Tab 2: 建立監控群組 ==========
    with tab2:
        st.subheader("建立監控群組")
        
        st.info("💡 建議命名: DSG_客戶名稱_方案名稱")
        
        with st.form("create_group_form"):
            group_name = st.text_input(
                "群組名稱",
                max_chars=40,
                placeholder="例如: DSG_客戶A_SBD12P"
            )
            
            description = st.text_area(
                "群組描述",
                max_chars=100,
                placeholder="選填，最多 100 字元"
            )
            
            submitted = st.form_submit_button("➕ 建立群組")
            
            if submitted:
                if not group_name:
                    st.error("❌ 請輸入群組名稱")
                else:
                    _handle_create_group(
                        dsg_service,
                        group_name,
                        description
                    )
    
    # ========== Tab 3: 管理群組成員 ==========
    with tab3:
        st.subheader("管理群組成員")
        
        try:
            groups = dsg_service.get_all_groups()
            
            if not groups:
                st.warning("⚠️ 請先建立群組")
            else:
                # 選擇群組
                group_names = {g.group_name: g.group_id for g in groups}
                selected_name = st.selectbox(
                    "選擇群組",
                    options=list(group_names.keys()),
                    key="manage_group_select"
                )
                
                if selected_name:
                    group_id = group_names[selected_name]
                    
                    # 顯示當前成員
                    _display_current_members(dsg_service, group_id)
                    
                    # 加入成員
                    st.markdown("---")
                    st.markdown("### ➕ 批次加入 IMEI")
                    
                    with st.form("add_members_form"):
                        imeis_text = st.text_area(
                            "IMEI 列表",
                            placeholder="每行一個 IMEI（15 位數字）",
                            height=150
                        )
                        
                        submitted = st.form_submit_button("➕ 加入")
                        
                        if submitted:
                            _handle_add_members(
                                dsg_service,
                                group_id,
                                imeis_text
                            )
                    
                    # 移除成員
                    st.markdown("---")
                    st.markdown("### ➖ 批次移除 IMEI")
                    
                    with st.form("remove_members_form"):
                        imeis_text = st.text_area(
                            "IMEI 列表",
                            placeholder="每行一個 IMEI（15 位數字）",
                            height=150,
                            key="remove_imeis"
                        )
                        
                        submitted = st.form_submit_button("➖ 移除")
                        
                        if submitted:
                            _handle_remove_members(
                                dsg_service,
                                group_id,
                                imeis_text
                            )
        
        except Exception as e:
            st.error(f"❌ 載入群組失敗: {str(e)}")
            logger.error(f"Load groups error: {e}", exc_info=True)
    
    # ========== Tab 4: 一鍵設定 ==========
    with tab4:
        st.subheader("⚡ 一鍵完成 DSG 設定")
        
        st.info("💡 自動完成：建立群組 → 加入成員 → 設定 Tracker")
        
        with st.form("quick_setup_form"):
            group_name = st.text_input(
                "群組名稱",
                max_chars=40,
                key="quick_group_name"
            )
            
            imeis_text = st.text_area(
                "IMEI 列表",
                placeholder="每行一個 IMEI（15 位數字）\n至少需要 2 個 IMEI",
                height=150
            )
            
            threshold_kb = st.number_input(
                "流量閾值 (KB)",
                min_value=1,
                value=120,
                help="例如：10 個 IMEI × 12 KB = 120 KB"
            )
            
            description = st.text_area(
                "群組描述",
                max_chars=100,
                key="quick_description"
            )
            
            email = st.text_input(
                "通知 Email（選填）",
                placeholder="email@example.com"
            )
            
            submitted = st.form_submit_button("⚡ 一鍵設定")
            
            if submitted:
                _handle_quick_setup(
                    dsg_service,
                    group_name,
                    imeis_text,
                    threshold_kb,
                    description,
                    email
                )


# ========== Helper Functions ==========

def _display_group_info(service: DSGService, group_id: str) -> None:
    """顯示群組資訊"""
    try:
        group = service.get_group(group_id)
        
        # 基本資訊
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("群組 ID", group.group_id)
        with col2:
            st.metric("成員數量", len(group.member_imeis))
        with col3:
            st.metric("狀態", group.status)
        
        if group.description:
            st.info(f"📝 {group.description}")
        
        # 成員列表
        if group.member_imeis:
            with st.expander("查看成員 IMEI", expanded=False):
                for i, imei in enumerate(group.member_imeis, 1):
                    st.text(f"{i}. {imei}")
        
    except RecordNotFoundError as e:
        st.error(f"❌ {e.message}")
    except Exception as e:
        st.error(f"❌ 載入群組資訊失敗: {str(e)}")
        logger.error(f"Display group error: {e}", exc_info=True)


def _display_current_members(service: DSGService, group_id: str) -> None:
    """顯示當前成員"""
    try:
        members = service.get_group_members(group_id)
        
        st.markdown(f"**當前成員數量: {len(members)}**")
        
        if members:
            with st.expander("查看成員列表", expanded=False):
                for i, imei in enumerate(members, 1):
                    st.text(f"{i}. {imei}")
        else:
            st.info("📋 群組目前沒有成員")
    
    except Exception as e:
        st.error(f"❌ 載入成員失敗: {str(e)}")


def _handle_create_group(
    service: DSGService,
    group_name: str,
    description: str
) -> None:
    """處理建立群組"""
    try:
        with st.spinner("建立中..."):
            group = service.create_group(
                group_name=group_name,
                description=description
            )
        
        st.success(f"✅ 群組建立成功")
        st.info(f"📋 群組 ID: {group.group_id}")
        st.info("💡 下一步：前往「管理群組成員」加入 IMEI")
        
    except ValidationError as e:
        st.error(f"❌ {e.message}")
    except DSGSetupError as e:
        st.error(f"❌ {e.message}")
    except Exception as e:
        st.error(f"❌ 建立失敗: {str(e)}")
        logger.error(f"Create group error: {e}", exc_info=True)


def _handle_add_members(
    service: DSGService,
    group_id: str,
    imeis_text: str
) -> None:
    """處理加入成員"""
    if not imeis_text.strip():
        st.error("❌ 請輸入 IMEI")
        return
    
    # 解析 IMEI
    imeis = [line.strip() for line in imeis_text.strip().split('\n') if line.strip()]
    
    if not imeis:
        st.error("❌ 沒有有效的 IMEI")
        return
    
    try:
        with st.spinner(f"加入 {len(imeis)} 個成員..."):
            group = service.add_members_to_group(group_id, imeis)
        
        st.success(f"✅ 成功加入成員")
        st.info(f"📋 群組目前共有 {len(group.member_imeis)} 個成員")
        st.rerun()
        
    except ValidationError as e:
        st.error(f"❌ {e.message}")
    except Exception as e:
        st.error(f"❌ 加入失敗: {str(e)}")
        logger.error(f"Add members error: {e}", exc_info=True)


def _handle_remove_members(
    service: DSGService,
    group_id: str,
    imeis_text: str
) -> None:
    """處理移除成員"""
    if not imeis_text.strip():
        st.error("❌ 請輸入 IMEI")
        return
    
    # 解析 IMEI
    imeis = [line.strip() for line in imeis_text.strip().split('\n') if line.strip()]
    
    if not imeis:
        st.error("❌ 沒有有效的 IMEI")
        return
    
    try:
        with st.spinner(f"移除 {len(imeis)} 個成員..."):
            group = service.remove_members_from_group(group_id, imeis)
        
        st.success(f"✅ 成功移除成員")
        st.info(f"📋 群組目前共有 {len(group.member_imeis)} 個成員")
        st.rerun()
        
    except ValidationError as e:
        st.error(f"❌ {e.message}")
    except Exception as e:
        st.error(f"❌ 移除失敗: {str(e)}")
        logger.error(f"Remove members error: {e}", exc_info=True)


def _handle_quick_setup(
    service: DSGService,
    group_name: str,
    imeis_text: str,
    threshold_kb: float,
    description: str,
    email: str
) -> None:
    """處理一鍵設定"""
    # 驗證輸入
    if not group_name:
        st.error("❌ 請輸入群組名稱")
        return
    
    if not imeis_text.strip():
        st.error("❌ 請輸入 IMEI")
        return
    
    # 解析 IMEI
    imeis = [line.strip() for line in imeis_text.strip().split('\n') if line.strip()]
    
    if len(imeis) < 2:
        st.error("❌ DSG 至少需要 2 個 IMEI")
        return
    
    try:
        with st.spinner("⚡ 設定中..."):
            result = service.setup_complete_dsg_tracking(
                group_name=group_name,
                imeis=imeis,
                threshold_kb=threshold_kb,
                description=description,
                email_addresses=email if email else None
            )
        
        st.success("✅ DSG 設定完成！")
        st.balloons()
        
        st.info(f"""
        📋 設定結果：
        - 群組 ID: {result['group_id']}
        - 群組名稱: {result['group_name']}
        - 成員數量: {result['member_count']}
        """)
        
    except ValidationError as e:
        st.error(f"❌ {e.message}")
    except DSGSetupError as e:
        st.error(f"❌ {e.message}")
    except Exception as e:
        st.error(f"❌ 設定失敗: {str(e)}")
        logger.error(f"Quick setup error: {e}", exc_info=True)
