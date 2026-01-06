"""
DSG 流量查詢頁面 - 客戶端
提供唯讀的 DSG 流量查詢功能
"""

import streamlit as st
import sys
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.dsg_tracker_service import DSGTrackerService


def render_dsg_query_page(gateway):
    """渲染 DSG 流量查詢頁面（客戶端）"""
    
    st.header("🛰️ DSG 流量查詢")
    
    st.info("""
    **查詢您的 DSG 流量使用情況**
    
    - 查看當前流量使用
    - 查看剩餘配額
    - 查看超額流量（如果有）
    """)
    
    # 初始化服務
    dsg_service = DSGTrackerService(gateway)
    
    # 查詢所有可用的監控群組
    st.markdown("### 📊 選擇您的 DSG 群組")
    
    groups_result = dsg_service.get_resource_groups()
    
    if not groups_result['success']:
        st.error(f"❌ 查詢失敗: {groups_result.get('error', '未知錯誤')}")
        st.info("請聯絡客服人員協助")
        return
    
    if groups_result['total_count'] == 0:
        st.warning("📝 目前沒有可查詢的 DSG 群組")
        st.info("""
        **如何使用 DSG？**
        
        1. 請聯絡客服人員建立 DSG
        2. DSG 建立後即可在此查詢流量
        3. 您可以在設備管理頁面加入 IMEI 到已建立的 DSG
        """)
        return
    
    # 顯示群組選項
    group_options = {
        g['group_name']: g
        for g in groups_result['groups']
    }
    
    selected_group_name = st.selectbox(
        "選擇 DSG 群組",
        options=list(group_options.keys())
    )
    
    if selected_group_name:
        selected_group = group_options[selected_group_name]
        
        st.markdown("---")
        
        # 顯示群組基本資訊
        st.markdown("### 📋 群組資訊")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("群組名稱", selected_group['group_name'])
        
        with col2:
            st.metric("群組 ID", selected_group['group_id'])
        
        with col3:
            # 查詢成員數量
            members_result = dsg_service.get_group_members(selected_group['group_id'])
            member_count = members_result['total_count'] if members_result['success'] else 0
            st.metric("成員數量", f"{member_count} 台設備")
        
        if selected_group.get('description'):
            st.caption(f"**說明**: {selected_group['description']}")
        
        # 顯示成員列表
        if members_result['success'] and member_count > 0:
            with st.expander("📱 查看所有設備 IMEI"):
                for i, imei in enumerate(members_result['members'], 1):
                    st.text(f"{i}. {imei}")
        
        st.markdown("---")
        
        # 流量資訊
        st.markdown("### 📊 流量使用情況")
        
        st.info("""
        💡 **提示**：流量資訊需要系統管理員先完成 Tracker 設定
        
        如果看不到流量資訊，請聯絡客服人員協助設定
        """)
        
        # TODO: 實際查詢流量需要知道 Tracker ID
        # 這部分需要建立一個對應表：Resource Group ID -> Tracker ID
        # 或者讓助理在建立時記錄到資料庫
        
        st.warning("⚙️ 流量追蹤功能開發中...")
        
        st.markdown("""
        **即將提供的資訊**：
        - ✅ 總配額
        - ✅ 已使用流量
        - ✅ 剩餘流量
        - ✅ 使用百分比
        - ✅ 超額流量（如有）
        - ✅ 下次重置日期
        """)


def render_dsg_usage_display(dsg_service, tracker_id: str, threshold_kb: float):
    """
    顯示 DSG 流量使用情況
    
    Args:
        dsg_service: DSG Tracker Service
        tracker_id: Tracker ID
        threshold_kb: 閾值（KB）
    """
    
    # 查詢 Tracker Rules
    rules_result = dsg_service.get_tracker_rules(tracker_id)
    
    if not rules_result['success']:
        st.error(f"❌ 查詢流量失敗: {rules_result.get('error')}")
        return
    
    if not rules_result['rules']:
        st.warning("⚠️ 此 Tracker 尚未設定 Rule")
        return
    
    # 取得第一個 Rule（通常只有一個）
    rule = rules_result['rules'][0]
    
    # 計算剩餘流量
    threshold_bytes = int(threshold_kb * 1024)
    usage_info = dsg_service.calculate_remaining_data(
        threshold_bytes=threshold_bytes,
        current_balance_bytes=rule['current_balance']
    )
    
    # 顯示流量資訊
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "總配額",
            f"{usage_info['threshold_kb']:.2f} KB"
        )
    
    with col2:
        st.metric(
            "已使用",
            f"{usage_info['used_kb']:.2f} KB",
            delta=f"{usage_info['usage_percentage']:.1f}%"
        )
    
    with col3:
        if usage_info['is_over_threshold']:
            st.metric(
                "超額流量",
                f"{usage_info['overage_kb']:.2f} KB",
                delta="已超額 ⚠️",
                delta_color="inverse"
            )
        else:
            st.metric(
                "剩餘流量",
                f"{usage_info['remaining_kb']:.2f} KB",
                delta=f"{100 - usage_info['usage_percentage']:.1f}%"
            )
    
    with col4:
        st.metric(
            "下次重置",
            rule['next_cycle_date'][:10]
        )
    
    # 進度條
    st.markdown("### 📈 使用進度")
    
    if usage_info['is_over_threshold']:
        # 超額時顯示紅色
        st.progress(1.0)
        st.error(f"⚠️ 已超過配額 {usage_info['overage_kb']:.2f} KB")
    else:
        # 正常時顯示藍色
        progress = min(1.0, usage_info['usage_percentage'] / 100)
        st.progress(progress)
        
        if usage_info['usage_percentage'] > 90:
            st.warning(f"⚠️ 已使用 {usage_info['usage_percentage']:.1f}%，接近配額上限")
        elif usage_info['usage_percentage'] > 75:
            st.info(f"💡 已使用 {usage_info['usage_percentage']:.1f}%")
    
    # 重置資訊
    st.caption(f"""
    **重置週期**: {rule['reset_cycle']}  
    **上次重置**: {rule['last_cycle_date'][:10] if rule['last_cycle_date'] != 'N/A' else 'N/A'}  
    **下次重置**: {rule['next_cycle_date'][:10]}
    """)
