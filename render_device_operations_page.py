"""
設備操作管理頁面
Device Operations Management Page

功能：
1. 記錄設備啟用
2. 記錄方案變更
3. 記錄狀態變更（暫停/恢復）
4. 查看設備操作歷史
5. 查看設備當前狀態
"""

import streamlit as st
from datetime import datetime, date
from typing import Optional

from src.services.device_history import get_device_history_manager, DeviceOperation
from src.models.models import UserRole


def render_device_operations_page():
    """渲染設備操作管理頁面"""
    
    st.title("🔧 設備操作管理")
    
    # 權限檢查
    if st.session_state.current_role != UserRole.ASSISTANT:
        st.error("⚠️ 此頁面僅限助理使用")
        return
    
    # 獲取設備歷史管理器
    history_mgr = get_device_history_manager(data_dir="data")
    
    # 標籤頁
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 記錄操作",
        "📜 操作歷史",
        "📊 設備狀態",
        "⚙️ 管理"
    ])
    
    # ==================== Tab 1: 記錄操作 ====================
    with tab1:
        render_operation_recording(history_mgr)
    
    # ==================== Tab 2: 操作歷史 ====================
    with tab2:
        render_operation_history(history_mgr)
    
    # ==================== Tab 3: 設備狀態 ====================
    with tab3:
        render_device_status(history_mgr)
    
    # ==================== Tab 4: 管理 ====================
    with tab4:
        render_management_tools(history_mgr)


def render_operation_recording(history_mgr):
    """渲染操作記錄界面"""
    
    st.subheader("記錄新操作")
    
    # 選擇操作類型
    operation_type = st.selectbox(
        "操作類型",
        ["啟用設備 (ACTIVATE)", "變更方案 (PLAN_CHANGE)", "變更狀態 (STATUS_CHANGE)"],
        help="選擇要記錄的操作類型"
    )
    
    # 基本資訊
    col1, col2 = st.columns(2)
    
    with col1:
        imei = st.text_input(
            "設備 IMEI",
            placeholder="300534066711380",
            help="15 位數字的設備識別碼"
        )
    
    with col2:
        operation_date = st.date_input(
            "操作日期",
            value=date.today(),
            help="操作執行的日期"
        )
    
    operator = st.text_input(
        "操作人員",
        value=st.session_state.current_username,
        help="執行此操作的人員名稱"
    )
    
    st.markdown("---")
    
    # 根據操作類型顯示不同的表單
    if operation_type == "啟用設備 (ACTIVATE)":
        render_activate_form(history_mgr, imei, operation_date, operator)
    
    elif operation_type == "變更方案 (PLAN_CHANGE)":
        render_plan_change_form(history_mgr, imei, operation_date, operator)
    
    elif operation_type == "變更狀態 (STATUS_CHANGE)":
        render_status_change_form(history_mgr, imei, operation_date, operator)


def render_activate_form(history_mgr, imei: str, operation_date: date, operator: str):
    """渲染啟用設備表單"""
    
    st.markdown("### 啟用設備")
    
    plan = st.selectbox(
        "選擇方案",
        ["SBD0", "SBD12", "SBD17", "SBD30"],
        index=1,
        help="選擇初始服務方案"
    )
    
    notes = st.text_area(
        "備註",
        placeholder="例如：新客戶啟用、測試設備等",
        help="記錄此次啟用的相關資訊"
    )
    
    if st.button("✅ 記錄啟用", type="primary", use_container_width=True):
        if not imei or len(imei) != 15:
            st.error("❌ 請輸入有效的 15 位 IMEI")
            return
        
        try:
            history_mgr.record_activation(
                imei=imei,
                plan=plan,
                date_str=operation_date.strftime('%Y-%m-%d'),
                operator=operator,
                notes=notes if notes else None
            )
            st.success(f"✅ 已記錄設備啟用：{imei} - {plan}")
            st.balloons()
        except Exception as e:
            st.error(f"❌ 記錄失敗：{e}")


def render_plan_change_form(history_mgr, imei: str, operation_date: date, operator: str):
    """渲染方案變更表單"""
    
    st.markdown("### 變更方案")
    
    # 先查詢當前方案
    if imei and len(imei) == 15:
        current_plan, current_status = history_mgr.get_state_at_date(
            imei,
            operation_date.strftime('%Y-%m-%d')
        )
        
        if current_plan:
            st.info(f"📌 當前方案：{current_plan} ({current_status})")
        else:
            st.warning("⚠️ 此設備尚未啟用")
            return
    else:
        current_plan = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        old_plan = st.selectbox(
            "原方案",
            ["SBD0", "SBD12", "SBD17", "SBD30"],
            index=["SBD0", "SBD12", "SBD17", "SBD30"].index(current_plan) if current_plan else 0,
            help="當前使用的方案"
        )
    
    with col2:
        new_plan = st.selectbox(
            "新方案",
            ["SBD0", "SBD12", "SBD17", "SBD30"],
            index=1,
            help="要變更到的新方案"
        )
    
    # 顯示升降級提示
    if old_plan and new_plan:
        is_upgrade = history_mgr.is_upgrade(old_plan, new_plan)
        if is_upgrade:
            st.success("✓ 升級 - 當月立即生效")
        elif old_plan != new_plan:
            st.warning("✗ 降級 - 次月才生效")
        else:
            st.info("→ 方案相同")
    
    notes = st.text_area(
        "備註",
        placeholder="例如：客戶要求升級、流量不足等",
        help="記錄此次變更的原因"
    )
    
    if st.button("✅ 記錄方案變更", type="primary", use_container_width=True):
        if not imei or len(imei) != 15:
            st.error("❌ 請輸入有效的 15 位 IMEI")
            return
        
        if old_plan == new_plan:
            st.error("❌ 新舊方案相同，無需變更")
            return
        
        try:
            history_mgr.record_plan_change(
                imei=imei,
                old_plan=old_plan,
                new_plan=new_plan,
                date_str=operation_date.strftime('%Y-%m-%d'),
                operator=operator,
                notes=notes if notes else None
            )
            
            if history_mgr.is_upgrade(old_plan, new_plan):
                st.success(f"✅ 已記錄方案升級：{old_plan} → {new_plan}（當月生效）")
            else:
                st.success(f"✅ 已記錄方案降級：{old_plan} → {new_plan}（次月生效）")
            
            st.balloons()
        except Exception as e:
            st.error(f"❌ 記錄失敗：{e}")


def render_status_change_form(history_mgr, imei: str, operation_date: date, operator: str):
    """渲染狀態變更表單"""
    
    st.markdown("### 變更狀態")
    
    # 先查詢當前狀態
    if imei and len(imei) == 15:
        current_plan, current_status = history_mgr.get_state_at_date(
            imei,
            operation_date.strftime('%Y-%m-%d')
        )
        
        if current_plan:
            st.info(f"📌 當前狀態：{current_status} ({current_plan})")
        else:
            st.warning("⚠️ 此設備尚未啟用")
            return
    else:
        current_status = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        old_status = st.selectbox(
            "原狀態",
            ["ACTIVE", "SUSPENDED"],
            index=0 if current_status == "ACTIVE" else 1 if current_status else 0,
            help="當前的服務狀態"
        )
    
    with col2:
        new_status = st.selectbox(
            "新狀態",
            ["ACTIVE", "SUSPENDED"],
            index=1 if old_status == "ACTIVE" else 0,
            help="要變更到的新狀態"
        )
    
    # 顯示費用提示
    if old_status and new_status and old_status != new_status:
        st.warning("⚠️ 狀態變更將產生雙重收費（原月租 + 暫停費 或 暫停費 + 新月租）")
        
        # 檢查是否為第3次暫停
        if new_status == "SUSPENDED":
            current_month = operation_date.month
            current_year = operation_date.year
            suspend_count = history_mgr.count_suspend_actions(imei, current_year, current_month)
            
            if suspend_count >= 2:
                st.error(f"⚠️ 本月已暫停 {suspend_count} 次，第 3 次起將加收行政手續費 $20/次")
    
    notes = st.text_area(
        "備註",
        placeholder="例如：客戶要求暫停、出國期間等",
        help="記錄此次變更的原因"
    )
    
    if st.button("✅ 記錄狀態變更", type="primary", use_container_width=True):
        if not imei or len(imei) != 15:
            st.error("❌ 請輸入有效的 15 位 IMEI")
            return
        
        if old_status == new_status:
            st.error("❌ 新舊狀態相同，無需變更")
            return
        
        try:
            history_mgr.record_status_change(
                imei=imei,
                old_status=old_status,
                new_status=new_status,
                date_str=operation_date.strftime('%Y-%m-%d'),
                operator=operator,
                notes=notes if notes else None
            )
            
            if new_status == "SUSPENDED":
                st.success(f"✅ 已記錄服務暫停：{old_status} → {new_status}")
            else:
                st.success(f"✅ 已記錄服務恢復：{old_status} → {new_status}")
            
            st.balloons()
        except Exception as e:
            st.error(f"❌ 記錄失敗：{e}")


def render_operation_history(history_mgr):
    """渲染操作歷史"""
    
    st.subheader("操作歷史查詢")
    
    # 查詢選項
    col1, col2 = st.columns(2)
    
    with col1:
        query_imei = st.text_input(
            "查詢 IMEI",
            placeholder="輸入 IMEI 查詢該設備的操作歷史",
            help="留空顯示所有設備"
        )
    
    with col2:
        show_limit = st.number_input(
            "顯示筆數",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            help="限制顯示的記錄數量"
        )
    
    # 獲取歷史記錄
    if query_imei:
        history = history_mgr.get_device_history(query_imei)
        st.info(f"📌 設備 {query_imei} 的操作記錄")
    else:
        history = history_mgr.history
        st.info(f"📌 所有設備的操作記錄")
    
    if not history:
        st.warning("⚠️ 沒有找到操作記錄")
        return
    
    # 顯示記錄
    st.markdown(f"**共 {len(history)} 筆記錄**")
    
    # 倒序顯示（最新的在前）
    display_history = list(reversed(history[-show_limit:]))
    
    for i, op in enumerate(display_history, 1):
        with st.expander(f"{op.date} - {op.imei} - {get_operation_label(op)}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**日期：** {op.date}")
                st.markdown(f"**IMEI：** {op.imei}")
            
            with col2:
                st.markdown(f"**操作：** {op.action}")
                if op.operator:
                    st.markdown(f"**操作人員：** {op.operator}")
            
            with col3:
                if op.action == 'ACTIVATE':
                    st.markdown(f"**方案：** {op.plan}")
                    st.markdown(f"**狀態：** {op.status}")
                
                elif op.action == 'PLAN_CHANGE':
                    is_upgrade = history_mgr.is_upgrade(op.old_plan, op.new_plan)
                    mark = "✓ 升級" if is_upgrade else "✗ 降級"
                    st.markdown(f"**變更：** {op.old_plan} → {op.new_plan} {mark}")
                
                elif op.action == 'STATUS_CHANGE':
                    st.markdown(f"**變更：** {op.old_status} → {op.new_status}")
            
            if op.notes:
                st.markdown(f"**備註：** {op.notes}")


def render_device_status(history_mgr):
    """渲染設備狀態查詢"""
    
    st.subheader("設備當前狀態")
    
    query_imei = st.text_input(
        "查詢 IMEI",
        placeholder="輸入 IMEI 查詢當前狀態",
        help="15 位數字的設備識別碼"
    )
    
    if not query_imei:
        st.info("💡 請輸入 IMEI 查詢設備狀態")
        return
    
    if len(query_imei) != 15:
        st.error("❌ IMEI 應為 15 位數字")
        return
    
    # 查詢當前狀態
    current_plan, current_status = history_mgr.get_state_at_date(
        query_imei,
        datetime.now().strftime('%Y-%m-%d')
    )
    
    if not current_plan:
        st.warning(f"⚠️ 設備 {query_imei} 尚未啟用")
        return
    
    # 顯示狀態
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("當前方案", current_plan)
    
    with col2:
        status_color = "🟢" if current_status == "ACTIVE" else "🔴"
        st.metric("當前狀態", f"{status_color} {current_status}")
    
    with col3:
        history = history_mgr.get_device_history(query_imei)
        st.metric("操作次數", len(history))
    
    # 顯示本月操作統計
    st.markdown("---")
    st.markdown("### 📊 本月操作統計")
    
    now = datetime.now()
    month_operations = history_mgr.get_operations_in_month(query_imei, now.year, now.month)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        plan_changes = [op for op in month_operations if op.action == 'PLAN_CHANGE']
        st.metric("方案變更", len(plan_changes))
    
    with col2:
        suspend_count = history_mgr.count_suspend_actions(query_imei, now.year, now.month)
        st.metric("暫停次數", suspend_count)
        
        if suspend_count >= 3:
            st.error(f"⚠️ 已達 {suspend_count} 次，將加收行政手續費")
    
    with col3:
        status_changes = history_mgr.get_status_changes(query_imei, now.year, now.month)
        st.metric("狀態變更", len(status_changes))
    
    # 顯示本月操作詳情
    if month_operations:
        st.markdown("### 本月操作詳情")
        for op in month_operations:
            st.text(f"{op.date}: {get_operation_label(op)}")


def render_management_tools(history_mgr):
    """渲染管理工具"""
    
    st.subheader("管理工具")
    
    # 導出功能
    st.markdown("### 📤 導出歷史記錄")
    
    if st.button("導出為 JSON", use_container_width=True):
        import json
        from datetime import datetime
        
        filename = f"device_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = f"/tmp/{filename}"
        
        try:
            history_mgr.export_to_json(filepath)
            
            with open(filepath, 'r') as f:
                data = f.read()
            
            st.download_button(
                label="下載 JSON 檔案",
                data=data,
                file_name=filename,
                mime="application/json",
                use_container_width=True
            )
            
            st.success(f"✅ 已準備 {len(history_mgr.history)} 筆記錄")
        except Exception as e:
            st.error(f"❌ 導出失敗：{e}")
    
    # 統計資訊
    st.markdown("---")
    st.markdown("### 📊 系統統計")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_records = len(history_mgr.history)
        st.metric("總記錄數", total_records)
    
    with col2:
        unique_devices = len(set(op.imei for op in history_mgr.history))
        st.metric("設備數量", unique_devices)
    
    with col3:
        activations = len([op for op in history_mgr.history if op.action == 'ACTIVATE'])
        st.metric("啟用次數", activations)
    
    with col4:
        plan_changes = len([op for op in history_mgr.history if op.action == 'PLAN_CHANGE'])
        st.metric("方案變更", plan_changes)


def get_operation_label(op: DeviceOperation) -> str:
    """獲取操作標籤"""
    if op.action == 'ACTIVATE':
        return f"啟用 - {op.plan}"
    elif op.action == 'PLAN_CHANGE':
        return f"方案變更 - {op.old_plan} → {op.new_plan}"
    elif op.action == 'STATUS_CHANGE':
        return f"狀態變更 - {op.old_status} → {op.new_status}"
    return op.action
