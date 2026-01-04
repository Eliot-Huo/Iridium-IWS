"""
增強版帳單查詢頁面
Enhanced Billing Query Page

功能：
1. 查詢月帳單（整合新的計費邏輯）
2. 顯示費用明細
3. 顯示操作歷史
4. 顯示計費備註
"""

import streamlit as st
from datetime import datetime, date
from typing import Optional

from src.services.enhanced_billing_calculator import get_enhanced_billing_calculator
from src.services.device_history import get_device_history_manager
from src.models.models import UserRole


def render_enhanced_billing_page():
    """渲染增強版帳單查詢頁面"""
    
    st.title("💰 帳單查詢")
    
    # 獲取服務
    calculator = get_enhanced_billing_calculator()
    history_mgr = get_device_history_manager(data_dir="data")
    
    # 查詢表單
    st.markdown("### 查詢條件")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        query_imei = st.text_input(
            "設備 IMEI",
            placeholder="300534066711380",
            help="15 位數字的設備識別碼"
        )
    
    with col2:
        query_year = st.number_input(
            "年份",
            min_value=2020,
            max_value=2030,
            value=datetime.now().year,
            step=1
        )
    
    with col3:
        query_month = st.number_input(
            "月份",
            min_value=1,
            max_value=12,
            value=datetime.now().month,
            step=1
        )
    
    # 查詢按鈕
    if st.button("🔍 查詢帳單", type="primary", use_container_width=True):
        if not query_imei or len(query_imei) != 15:
            st.error("❌ 請輸入有效的 15 位 IMEI")
            return
        
        try:
            # 計算帳單
            bill = calculator.calculate_monthly_bill(
                imei=query_imei,
                year=query_year,
                month=query_month
            )
            
            # 顯示帳單
            display_enhanced_bill(bill, history_mgr)
            
        except ValueError as e:
            st.error(f"❌ {str(e)}")
        except Exception as e:
            st.error(f"❌ 查詢失敗：{e}")
            import traceback
            with st.expander("詳細錯誤訊息"):
                st.code(traceback.format_exc())


def display_enhanced_bill(bill, history_mgr):
    """顯示增強版帳單"""
    
    # 標題
    st.markdown("---")
    st.markdown(f"## 📅 {bill.year} 年 {bill.month} 月帳單")
    st.markdown(f"**設備 IMEI：** {bill.imei}")
    
    # 狀態摘要
    st.markdown("### 📊 帳單摘要")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("月初方案", bill.month_start_plan)
    
    with col2:
        status_color = "🟢" if bill.month_start_status == "ACTIVE" else "🔴"
        st.metric("月初狀態", f"{status_color} {bill.month_start_status}")
    
    with col3:
        plan_color = "🔵" if bill.billing_plan != bill.month_start_plan else "⚪"
        st.metric("計費方案", f"{plan_color} {bill.billing_plan}")
    
    with col4:
        st.metric("總費用", f"${bill.total_cost:.2f}", 
                 delta=None if bill.total_cost == bill.billing_plan_rate else f"${bill.total_cost - bill.billing_plan_rate:+.2f}")
    
    # 費用明細
    st.markdown("---")
    st.markdown("### 💰 費用明細")
    
    # 創建費用表格
    fee_data = []
    
    if bill.monthly_fee > 0:
        fee_data.append({
            "項目": f"{bill.billing_plan} 月租費",
            "金額": f"${bill.monthly_fee:.2f}",
            "說明": "基本月租費用"
        })
    
    if bill.suspend_fee > 0:
        fee_data.append({
            "項目": "暫停管理費",
            "金額": f"${bill.suspend_fee:.2f}",
            "說明": "服務暫停管理費用"
        })
    
    if bill.admin_fee > 0:
        fee_data.append({
            "項目": f"行政手續費",
            "金額": f"${bill.admin_fee:.2f}",
            "說明": f"頻繁暫停手續費 (第3次起，共{bill.suspend_count}次)"
        })
    
    if bill.overage_fee > 0:
        fee_data.append({
            "項目": "超量費用",
            "金額": f"${bill.overage_fee:.2f}",
            "說明": f"超過方案流量的費用 ({bill.total_bytes:,} bytes)"
        })
    
    if bill.other_fees > 0:
        fee_data.append({
            "項目": "其他費用",
            "金額": f"${bill.other_fees:.2f}",
            "說明": "Mailbox Check、Registration 等"
        })
    
    # 總計
    fee_data.append({
        "項目": "**總計**",
        "金額": f"**${bill.total_cost:.2f}**",
        "說明": "本月應付金額"
    })
    
    st.table(fee_data)
    
    # 使用量統計
    if bill.total_bytes > 0 or bill.message_count > 0:
        st.markdown("---")
        st.markdown("### 📈 使用量統計")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("總數據量", f"{bill.total_bytes:,} bytes")
        
        with col2:
            st.metric("訊息數量", f"{bill.message_count:,} 則")
        
        with col3:
            if bill.total_bytes > 0:
                avg_per_msg = bill.total_bytes / bill.message_count
                st.metric("平均訊息大小", f"{avg_per_msg:.0f} bytes")
    
    # 操作記錄
    if bill.plan_changes or bill.status_changes:
        st.markdown("---")
        st.markdown("### 📝 本月操作記錄")
        
        # 方案變更
        if bill.plan_changes:
            st.markdown("#### 方案變更")
            for change in bill.plan_changes:
                st.text(f"📅 {change['date']}: {change['details']}")
        
        # 狀態變更
        if bill.status_changes:
            st.markdown("#### 狀態變更")
            for change in bill.status_changes:
                st.text(f"📅 {change['date']}: {change['details']}")
        
        # 暫停次數警告
        if bill.suspend_count > 0:
            if bill.suspend_count >= 3:
                st.error(f"⚠️ 本月暫停 {bill.suspend_count} 次，已產生行政手續費 ${bill.admin_fee:.2f}")
            elif bill.suspend_count == 2:
                st.warning(f"⚠️ 本月已暫停 {bill.suspend_count} 次，第 3 次起將加收手續費 $20/次")
            else:
                st.info(f"ℹ️ 本月暫停 {bill.suspend_count} 次")
    
    # 計費備註
    if bill.notes:
        st.markdown("---")
        st.markdown("### 📋 計費備註")
        for note in bill.notes:
            st.info(f"💡 {note}")
    
    # 計費規則說明
    with st.expander("ℹ️ 計費規則說明"):
        st.markdown("""
        #### 方案變更規則
        - **升級（往高費率）**：當月立即生效，收取升級後的高費率
        - **降級（往低費率）**：次月才生效，當月仍收原費率
        
        #### 狀態變更規則
        - **暫停（ACTIVE → SUSPENDED）**：收取原月租 + 暫停管理費 $4
        - **恢復（SUSPENDED → ACTIVE）**：收取暫停管理費 $4 + 新月租
        - **同月暫停又恢復**：收取原月租 + 暫停管理費 + 新月租
        
        #### 行政手續費
        - 同月內前 2 次暫停：正常收費
        - 第 3 次暫停起：每次加收 $20 行政手續費
        - 目的：防止頻繁暫停/恢復行為
        
        #### 預付款機制（第3次暫停後恢復）
        當月暫停達 3 次以上後，若要恢復服務需先付清：
        1. 當月月租費
        2. 當月通訊費
        3. 行政手續費
        4. 欲恢復方案的月租費
        
        付款後由助理手動恢復（1-2 個工作日）
        """)
    
    # 下載帳單
    st.markdown("---")
    if st.button("📥 下載帳單（JSON）", use_container_width=True):
        import json
        
        bill_dict = {
            "imei": bill.imei,
            "year": bill.year,
            "month": bill.month,
            "month_start_plan": bill.month_start_plan,
            "month_start_status": bill.month_start_status,
            "billing_plan": bill.billing_plan,
            "fees": {
                "monthly_fee": bill.monthly_fee,
                "suspend_fee": bill.suspend_fee,
                "admin_fee": bill.admin_fee,
                "overage_fee": bill.overage_fee,
                "other_fees": bill.other_fees,
                "total": bill.total_cost
            },
            "usage": {
                "total_bytes": bill.total_bytes,
                "message_count": bill.message_count
            },
            "operations": {
                "plan_changes": bill.plan_changes,
                "status_changes": bill.status_changes,
                "suspend_count": bill.suspend_count
            },
            "notes": bill.notes
        }
        
        filename = f"bill_{bill.imei}_{bill.year}{bill.month:02d}.json"
        
        st.download_button(
            label="下載 JSON 檔案",
            data=json.dumps(bill_dict, ensure_ascii=False, indent=2),
            file_name=filename,
            mime="application/json",
            use_container_width=True
        )
