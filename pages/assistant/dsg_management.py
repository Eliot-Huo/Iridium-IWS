"""
DSG 管理頁面 - 助理端
提供完整的 DSG 流量追蹤管理功能
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# 添加專案路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.dsg_tracker_service import DSGTrackerService


def render_dsg_management_page(gateway):
    """渲染 DSG 管理頁面"""
    
    st.header("🛰️ DSG 流量管理")
    
    # 重要提示
    st.warning("""
    ⚠️ **重要說明**：
    - 此功能建立的是**監控群組（Resource Group）**，用於追蹤流量
    - **實際的 DSG（Dynamic Shared Group）**必須透過 **SPNet Pro** 或 **Email Support** 創建
    - Resource Group 可以監控任何設備群組，不限於 DSG
    """)
    
    # 初始化服務
    dsg_service = DSGTrackerService(gateway)
    
    # 標籤頁
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 查看 DSG 流量",
        "➕ 建立監控群組",
        "👥 管理群組成員",
        "⚙️ 設定 Tracker"
    ])
    
    # ========== Tab 1: 查看流量 ==========
    with tab1:
        render_view_dsg_tab(dsg_service)
    
    # ========== Tab 2: 建立群組 ==========
    with tab2:
        render_create_group_tab(dsg_service)
    
    # ========== Tab 3: 管理成員 ==========
    with tab3:
        render_manage_members_tab(dsg_service)
    
    # ========== Tab 4: 設定 Tracker ==========
    with tab4:
        render_setup_tracker_tab(dsg_service)


def render_view_dsg_tab(dsg_service):
    """渲染查看 DSG 流量標籤"""
    
    st.subheader("📊 DSG 流量查詢")
    
    # 查詢群組
    st.markdown("### 1️⃣ 選擇監控群組")
    
    if st.button("🔄 重新載入群組列表"):
        st.rerun()
    
    # 取得所有群組
    groups_result = dsg_service.get_resource_groups()
    
    if not groups_result['success']:
        st.error(f"❌ 查詢群組失敗: {groups_result.get('error', '未知錯誤')}")
        return
    
    if groups_result['total_count'] == 0:
        st.info("📝 尚未建立任何監控群組，請到「建立監控群組」標籤建立")
        return
    
    # 顯示群組列表
    group_options = {
        f"{g['group_name']} (ID: {g['group_id']})": g['group_id']
        for g in groups_result['groups']
    }
    
    selected_group_display = st.selectbox(
        "選擇群組",
        options=list(group_options.keys())
    )
    
    if selected_group_display:
        selected_group_id = group_options[selected_group_display]
        
        # 顯示群組詳情
        st.markdown("### 2️⃣ 群組資訊")
        
        # 查詢成員
        members_result = dsg_service.get_group_members(selected_group_id)
        
        if members_result['success']:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("群組 ID", selected_group_id)
            with col2:
                st.metric("成員數量", members_result['total_count'])
            
            if members_result['total_count'] > 0:
                with st.expander("📋 查看所有成員 IMEI"):
                    for i, imei in enumerate(members_result['members'], 1):
                        st.text(f"{i}. {imei}")
        
        # 流量資訊（需要先設定 Tracker）
        st.markdown("### 3️⃣ 流量使用情況")
        st.info("""
        💡 **提示**：需要先在「設定 Tracker」標籤建立 Tracker 和 Rule，才能查詢流量
        
        完整設定流程：
        1. 建立監控群組（Resource Group）
        2. 加入 IMEI 到群組
        3. 建立 Tracker
        4. 建立 Tracker Profile
        5. 建立 Tracker Rule
        6. 關聯群組到 Tracker
        7. 即可查詢流量！
        """)


def render_create_group_tab(dsg_service):
    """渲染建立監控群組標籤"""
    
    st.subheader("➕ 建立監控群組")
    
    st.info("""
    **建立監控群組**：用於追蹤一組設備的流量使用
    
    注意：
    - 群組名稱必須在您的 SP 帳號內唯一
    - 最多 40 個字元
    - 建議命名：DSG_客戶名稱_方案名稱
    """)
    
    with st.form("create_group_form"):
        group_name = st.text_input(
            "群組名稱",
            max_chars=40,
            placeholder="例如：DSG_客戶A_SBD12P",
            help="必須唯一，建議包含客戶名稱和方案"
        )
        
        description = st.text_area(
            "群組描述（選填）",
            max_chars=100,
            placeholder="例如：客戶A的DSG群組，SBD-12P方案，10個IMEI"
        )
        
        submitted = st.form_submit_button("✅ 建立群組", type="primary")
        
        if submitted:
            if not group_name:
                st.error("❌ 請輸入群組名稱")
            else:
                with st.spinner("正在建立群組..."):
                    result = dsg_service.create_resource_group(
                        group_name=group_name,
                        description=description
                    )
                
                if result['success']:
                    st.success(f"✅ {result['message']}")
                    st.info(f"**群組 ID**: {result['group_id']}")
                    st.balloons()
                else:
                    st.error(f"❌ {result.get('error', '建立失敗')}")


def render_manage_members_tab(dsg_service):
    """渲染管理群組成員標籤"""
    
    st.subheader("👥 管理群組成員")
    
    # 選擇群組
    groups_result = dsg_service.get_resource_groups()
    
    if not groups_result['success'] or groups_result['total_count'] == 0:
        st.warning("📝 請先建立監控群組")
        return
    
    group_options = {
        f"{g['group_name']} (ID: {g['group_id']})": g['group_id']
        for g in groups_result['groups']
    }
    
    selected_group_display = st.selectbox(
        "選擇群組",
        options=list(group_options.keys()),
        key="manage_group"
    )
    
    if selected_group_display:
        selected_group_id = group_options[selected_group_display]
        
        # 顯示當前成員
        members_result = dsg_service.get_group_members(selected_group_id)
        
        if members_result['success']:
            st.metric("當前成員數量", members_result['total_count'])
            
            if members_result['total_count'] > 0:
                with st.expander("📋 當前成員列表"):
                    for i, imei in enumerate(members_result['members'], 1):
                        st.text(f"{i}. {imei}")
        
        st.markdown("---")
        
        # 加入成員
        st.markdown("### ➕ 加入 IMEI")
        
        with st.form("add_members_form"):
            st.info("""
            **批次加入 IMEI**：一次可以加入多個 IMEI
            
            格式：每行一個 IMEI，15位數字
            範例：
            ```
            300534066711380
            300534066716260
            300534066722345
            ```
            """)
            
            imeis_input = st.text_area(
                "IMEI 列表（每行一個）",
                height=150,
                placeholder="300534066711380\n300534066716260\n300534066722345"
            )
            
            add_submitted = st.form_submit_button("✅ 批次加入", type="primary")
            
            if add_submitted:
                # 解析 IMEI
                imeis = [
                    line.strip()
                    for line in imeis_input.strip().split('\n')
                    if line.strip()
                ]
                
                # 驗證 IMEI
                invalid_imeis = [
                    imei for imei in imeis
                    if len(imei) != 15 or not imei.isdigit()
                ]
                
                if invalid_imeis:
                    st.error(f"❌ 以下 IMEI 格式錯誤（必須是15位數字）：")
                    for imei in invalid_imeis:
                        st.text(f"  - {imei}")
                elif not imeis:
                    st.error("❌ 請輸入至少一個 IMEI")
                else:
                    with st.spinner(f"正在加入 {len(imeis)} 個 IMEI..."):
                        result = dsg_service.add_imeis_to_group(
                            group_id=selected_group_id,
                            imeis=imeis,
                            bulk=True
                        )
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', '加入失敗')}")
        
        st.markdown("---")
        
        # 移除成員
        st.markdown("### ➖ 移除 IMEI")
        
        with st.form("remove_members_form"):
            remove_imeis_input = st.text_area(
                "要移除的 IMEI 列表（每行一個）",
                height=100
            )
            
            remove_submitted = st.form_submit_button("🗑️ 批次移除", type="secondary")
            
            if remove_submitted:
                imeis = [
                    line.strip()
                    for line in remove_imeis_input.strip().split('\n')
                    if line.strip()
                ]
                
                if not imeis:
                    st.error("❌ 請輸入至少一個 IMEI")
                else:
                    with st.spinner(f"正在移除 {len(imeis)} 個 IMEI..."):
                        result = dsg_service.remove_imeis_from_group(
                            group_id=selected_group_id,
                            imeis=imeis
                        )
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', '移除失敗')}")


def render_setup_tracker_tab(dsg_service):
    """渲染設定 Tracker 標籤"""
    
    st.subheader("⚙️ 設定 Tracker")
    
    st.info("""
    **Tracker 設定流程**：
    
    1. 建立 Tracker（監控器）
    2. 建立 Tracker Profile（定義閾值）
    3. 建立 Tracker Rule（定義重置週期）
    4. 關聯 Resource Group 到 Tracker
    
    完成後即可查詢流量使用情況！
    """)
    
    st.warning("⚠️ 此功能較為進階，建議先完成前面的步驟")
    
    # 步驟 1: 建立 Tracker
    with st.expander("1️⃣ 建立 Tracker"):
        with st.form("create_tracker_form"):
            tracker_name = st.text_input(
                "Tracker 名稱",
                max_chars=40,
                placeholder="例如：Tracker_客戶A_DSG"
            )
            
            email_addresses = st.text_input(
                "通知 Email（多個用逗號分隔）",
                placeholder="admin@n3d.com,support@n3d.com"
            )
            
            tracker_desc = st.text_area(
                "描述（選填）",
                max_chars=100
            )
            
            create_tracker_submit = st.form_submit_button("✅ 建立 Tracker")
            
            if create_tracker_submit:
                if not tracker_name or not email_addresses:
                    st.error("❌ 請填寫所有必填欄位")
                else:
                    result = dsg_service.create_tracker(
                        name=tracker_name,
                        email_addresses=email_addresses,
                        description=tracker_desc
                    )
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        st.info(f"**Tracker ID**: {result['tracker_id']}")
                    else:
                        st.error(f"❌ {result.get('error')}")
    
    # 步驟 2: 建立 Tracker Profile
    with st.expander("2️⃣ 建立 Tracker Profile"):
        with st.form("create_profile_form"):
            st.info("定義流量閾值（總配額）")
            
            profile_name = st.text_input(
                "Profile 名稱",
                max_chars=40,
                placeholder="例如：Profile_120KB_Monthly"
            )
            
            threshold_kb = st.number_input(
                "閾值（KB）",
                min_value=1,
                value=120,
                help="例如：10個IMEI × 12KB = 120KB"
            )
            
            create_profile_submit = st.form_submit_button("✅ 建立 Profile")
            
            if create_profile_submit:
                if not profile_name:
                    st.error("❌ 請輸入 Profile 名稱")
                else:
                    threshold_bytes = int(threshold_kb * 1024)
                    result = dsg_service.create_tracker_profile(
                        name=profile_name,
                        threshold_bytes=threshold_bytes
                    )
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        st.info(f"**Profile ID**: {result['profile_id']}")
                    else:
                        st.error(f"❌ {result.get('error')}")
    
    # 步驟 3: 建立 Tracker Rule
    with st.expander("3️⃣ 建立 Tracker Rule"):
        with st.form("create_rule_form"):
            st.info("定義重置週期和關聯 Tracker & Profile")
            
            rule_tracker_id = st.text_input(
                "Tracker ID",
                help="從步驟1取得"
            )
            
            rule_profile_id = st.text_input(
                "Profile ID",
                help="從步驟2取得"
            )
            
            rule_name = st.text_input(
                "Rule 名稱",
                placeholder="例如：Rule_Monthly_Reset"
            )
            
            reset_cycle = st.selectbox(
                "重置週期",
                options=["MONTHLY", "BILLCYCLE"],
                help="MONTHLY=每月重置, BILLCYCLE=按帳單週期"
            )
            
            if reset_cycle == "MONTHLY":
                cycle_day = st.number_input(
                    "每月重置日期",
                    min_value=1,
                    max_value=31,
                    value=1,
                    help="1-31號"
                )
            else:
                cycle_day = 0
            
            create_rule_submit = st.form_submit_button("✅ 建立 Rule")
            
            if create_rule_submit:
                if not all([rule_tracker_id, rule_profile_id, rule_name]):
                    st.error("❌ 請填寫所有必填欄位")
                else:
                    result = dsg_service.add_tracker_rule(
                        tracker_id=rule_tracker_id,
                        profile_id=rule_profile_id,
                        rule_name=rule_name,
                        reset_cycle=reset_cycle,
                        cycle_setting=cycle_day
                    )
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        st.info(f"**Rule ID**: {result['rule_id']}")
                    else:
                        st.error(f"❌ {result.get('error')}")
    
    # 步驟 4: 關聯群組到 Tracker
    with st.expander("4️⃣ 關聯 Resource Group 到 Tracker"):
        with st.form("link_group_form"):
            link_tracker_id = st.text_input(
                "Tracker ID",
                help="從步驟1取得",
                key="link_tracker"
            )
            
            link_group_id = st.text_input(
                "Resource Group ID",
                help="從「建立監控群組」取得"
            )
            
            link_submit = st.form_submit_button("✅ 關聯群組")
            
            if link_submit:
                if not all([link_tracker_id, link_group_id]):
                    st.error("❌ 請填寫所有必填欄位")
                else:
                    result = dsg_service.add_tracker_member(
                        tracker_id=link_tracker_id,
                        group_id=link_group_id
                    )
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        st.balloons()
                        st.info("🎉 設定完成！現在可以到「查看 DSG 流量」標籤查詢流量了！")
                    else:
                        st.error(f"❌ {result.get('error')}")
