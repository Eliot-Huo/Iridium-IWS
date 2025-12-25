"""
SBD 管理系統 - Streamlit 主程式 v6.5
Asset Management Edition - 資產管理專用版
"""
import streamlit as st
from datetime import datetime
from src.repositories.repo import InMemoryRepository
from src.services.sbd_service import SBDService
from src.services.cdr_service import CDRService
from src.models.models import UserRole, RequestStatus, ActionType
from src.config.constants import RATE_PLANS


# 頁面配置
st.set_page_config(
    page_title="SBD 資產管理系統",
    page_icon="📡",
    layout="wide"
)


def init_session_state():
    """初始化 Session State"""
    if 'repository' not in st.session_state:
        st.session_state.repository = InMemoryRepository()
    
    if 'sbd_service' not in st.session_state:
        st.session_state.sbd_service = SBDService(st.session_state.repository)
    
    if 'current_role' not in st.session_state:
        st.session_state.current_role = UserRole.CUSTOMER
    
    if 'current_username' not in st.session_state:
        st.session_state.current_username = 'customer001'
    
    if 'sample_cdr_data' not in st.session_state:
        # 模擬 CDR 資料
        st.session_state.sample_cdr_data = [
            '123456789012345,2025-01-15 10:30:00,120,0.0,voice,+886912345678,1.5',
            '123456789012345,2025-01-15 14:20:00,60,2.5,data,,0.8',
            '987654321098765,2025-01-15 16:45:00,90,0.0,sms,+886987654321,0.3'
        ]


def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        st.title("📡 SBD 資產管理系統")
        st.markdown("---")
        
        # 身份驗證模擬
        st.subheader("🔐 身份切換")
        
        role_option = st.radio(
            "選擇角色",
            options=["客戶 (Customer)", "助理 (Assistant)"],
            index=0 if st.session_state.current_role == UserRole.CUSTOMER else 1
        )
        
        if role_option == "客戶 (Customer)":
            st.session_state.current_role = UserRole.CUSTOMER
            st.session_state.current_username = 'customer001'
        else:
            st.session_state.current_role = UserRole.ASSISTANT
            st.session_state.current_username = 'assistant001'
        
        st.info(f"當前身份: **{st.session_state.current_username}**")
        
        st.markdown("---")
        
        # 系統資訊
        st.subheader("📊 系統狀態")
        total_requests = st.session_state.repository.count()
        pending_count = len([r for r in st.session_state.repository.list_all_requests() 
                            if r.status == RequestStatus.PENDING_FINANCE])
        
        st.metric("總請求數", total_requests)
        st.metric("待核准", pending_count)


def render_cdr_monitor():
    """渲染流量監視器"""
    st.subheader("📈 通訊紀錄監視器")
    
    if st.session_state.sample_cdr_data:
        records = CDRService.parse_multiple_lines(st.session_state.sample_cdr_data)
        
        if records:
            # 建立顯示用的資料
            display_data = []
            for record in records:
                display_data.append({
                    'IMEI': record.imei,
                    '時間 (台北)': record.get_formatted_time('%Y-%m-%d %H:%M:%S'),
                    '類型': record.call_type,
                    '時長 (秒)': record.duration_seconds,
                    '數據 (MB)': record.data_mb,
                    '目的地': record.destination or 'N/A',
                    '費用 ($)': f'${record.cost:.2f}'
                })
            
            st.dataframe(display_data, width='stretch')
            
            # 統計資訊
            total_cost = CDRService.calculate_total_cost(records)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("總筆數", len(records))
            with col2:
                st.metric("總費用", f"${total_cost:.2f}")
            with col3:
                st.metric("平均費用", f"${total_cost/len(records):.2f}" if records else "$0.00")
        else:
            st.info("無有效的通訊紀錄")
    else:
        st.info("暫無通訊紀錄")


def render_customer_view():
    """渲染客戶介面 - 資產管理專用版"""
    st.header("👤 設備資產管理")
    
    # IMEI 輸入（共用）
    imei_input = st.text_input(
        "IMEI 號碼",
        placeholder="請輸入 15 位數字",
        max_chars=15,
        help="設備的唯一識別碼"
    )
    
    # 功能選擇 Tabs
    tab1, tab2, tab3 = st.tabs(["💱 變更費率", "⏸️ 暫停設備", "🔴 註銷設備"])
    
    # Tab 1: 變更費率
    with tab1:
        st.subheader("變更資費方案")
        
        # 獲取可用方案
        available_plans = st.session_state.sbd_service.get_available_plans()
        plan_options = list(available_plans.keys())
        
        selected_plan = st.selectbox(
            "選擇新的資費方案",
            options=plan_options,
            help="選擇要變更的資費方案"
        )
        
        # 顯示方案費用
        if selected_plan:
            plan_fee = available_plans[selected_plan]
            st.info(f"💰 新方案月租費: **${plan_fee:.2f}**")
        
        st.markdown("---")
        
        if st.button("🚀 提交變更費率申請", type="primary", key="submit_plan_change"):
            if not imei_input or len(imei_input) != 15:
                st.error("❌ 請輸入有效的 15 位數 IMEI 號碼")
            elif not imei_input.isdigit():
                st.error("❌ IMEI 只能包含數字")
            else:
                try:
                    request = st.session_state.sbd_service.create_plan_change_request(
                        imei=imei_input,
                        new_plan_id=selected_plan,
                        requester=st.session_state.current_username
                    )
                    st.success(f"✅ 費率變更申請已提交！")
                    st.info(f"📋 請求編號: **{request.request_id}**")
                    st.info(f"📋 新方案: **{selected_plan}** (${plan_fee:.2f}/月)")
                    st.info(f"📋 目前狀態: **{request.status.value}** (等待財務確認)")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ 申請失敗: {str(e)}")
    
    # Tab 2: 暫停設備
    with tab2:
        st.subheader("暫停設備服務")
        
        suspend_reason = st.text_area(
            "暫停原因",
            placeholder="請輸入暫停原因（例如：臨時停用、設備維修等）",
            help="說明為何需要暫停此設備"
        )
        
        st.warning("⚠️ 暫停後設備將無法使用 SBD 服務，直到恢復為止。")
        
        st.markdown("---")
        
        if st.button("⏸️ 提交暫停申請", type="primary", key="submit_suspend"):
            if not imei_input or len(imei_input) != 15:
                st.error("❌ 請輸入有效的 15 位數 IMEI 號碼")
            elif not imei_input.isdigit():
                st.error("❌ IMEI 只能包含數字")
            elif not suspend_reason:
                st.error("❌ 請輸入暫停原因")
            else:
                try:
                    request = st.session_state.sbd_service.create_suspend_request(
                        imei=imei_input,
                        reason=suspend_reason,
                        requester=st.session_state.current_username
                    )
                    st.success(f"✅ 暫停申請已提交！")
                    st.info(f"📋 請求編號: **{request.request_id}**")
                    st.info(f"📋 暫停原因: **{suspend_reason}**")
                    st.info(f"📋 目前狀態: **{request.status.value}** (等待財務確認)")
                except Exception as e:
                    st.error(f"❌ 申請失敗: {str(e)}")
    
    # Tab 3: 註銷設備
    with tab3:
        st.subheader("註銷設備服務")
        
        deactivate_reason = st.text_area(
            "註銷原因",
            placeholder="請輸入註銷原因（例如：設備報廢、不再使用等）",
            help="說明為何需要註銷此設備"
        )
        
        st.error("🚨 **注意**: 註銷後設備將永久停用，無法恢復！")
        
        confirm_deactivate = st.checkbox("我確認要註銷此設備")
        
        st.markdown("---")
        
        if st.button("🔴 提交註銷申請", type="primary", key="submit_deactivate", disabled=not confirm_deactivate):
            if not imei_input or len(imei_input) != 15:
                st.error("❌ 請輸入有效的 15 位數 IMEI 號碼")
            elif not imei_input.isdigit():
                st.error("❌ IMEI 只能包含數字")
            elif not deactivate_reason:
                st.error("❌ 請輸入註銷原因")
            else:
                try:
                    request = st.session_state.sbd_service.create_deactivate_request(
                        imei=imei_input,
                        reason=deactivate_reason,
                        requester=st.session_state.current_username
                    )
                    st.success(f"✅ 註銷申請已提交！")
                    st.info(f"📋 請求編號: **{request.request_id}**")
                    st.info(f"📋 註銷原因: **{deactivate_reason}**")
                    st.info(f"📋 目前狀態: **{request.status.value}** (等待財務確認)")
                except Exception as e:
                    st.error(f"❌ 申請失敗: {str(e)}")
    
    # 查詢我的申請
    st.markdown("---")
    st.subheader("📋 我的申請記錄")
    
    if imei_input:
        my_requests = st.session_state.sbd_service.get_requests_by_imei(imei_input)
        
        if my_requests:
            for req in my_requests:
                # 根據操作類型顯示不同圖標
                action_icons = {
                    ActionType.CHANGE_PLAN: "💱",
                    ActionType.SUSPEND: "⏸️",
                    ActionType.RESUME: "▶️",
                    ActionType.DEACTIVATE: "🔴",
                    ActionType.ACTIVATE: "🚀",
                }
                icon = action_icons.get(req.action_type, "📄")
                
                with st.expander(f"{icon} {req.request_id} - {req.status.value.upper()}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**操作類型:** {req.action_type.value}")
                        if req.action_type == ActionType.CHANGE_PLAN:
                            st.write(f"**新資費方案:** {req.plan_id}")
                        st.write(f"**應付金額:** ${req.amount_due:.2f}")
                    with col2:
                        st.write(f"**建立時間:** {req.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**狀態:** {req.status.value}")
                        if req.approved_by:
                            st.write(f"**核准者:** {req.approved_by}")
                    
                    # 顯示備註
                    if req.notes:
                        st.markdown("**備註:**")
                        st.text(req.notes)
        else:
            st.info("此 IMEI 尚無申請記錄")


def render_assistant_view():
    """渲染助理介面"""
    st.header("👨‍💼 財務核准工作台")
    
    # 功能 B: 財務核准工作台
    pending_requests = st.session_state.sbd_service.list_pending_requests()
    
    if not pending_requests:
        st.info("✅ 目前沒有待核准的請求")
        return
    
    st.markdown(f"### 📝 待處理請求 ({len(pending_requests)} 筆)")
    
    for idx, request in enumerate(pending_requests):
        with st.container():
            # 根據操作類型顯示不同顏色標題
            action_colors = {
                ActionType.CHANGE_PLAN: "blue",
                ActionType.SUSPEND: "orange",
                ActionType.RESUME: "green",
                ActionType.DEACTIVATE: "red",
                ActionType.ACTIVATE: "violet",
            }
            color = action_colors.get(request.action_type, "gray")
            
            st.markdown(f"#### :{color}[請求 #{idx + 1}: {request.request_id}]")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**IMEI:** {request.imei}")
                st.write(f"**操作:** {request.action_type.value.upper()}")
                if request.action_type == ActionType.CHANGE_PLAN:
                    st.write(f"**新方案:** {request.plan_id}")
            
            with col2:
                st.write(f"**應收金額:** ${request.amount_due:.2f}")
                st.write(f"**申請時間:** {request.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**備註:** {request.notes[:50]}..." if len(request.notes) > 50 else f"**備註:** {request.notes}")
            
            with col3:
                # 確認執行按鈕
                if st.button(
                    "✅ 確認並執行 IWS",
                    key=f"approve_{request.request_id}",
                    type="primary"
                ):
                    try:
                        approved_request = st.session_state.sbd_service.process_finance_approval(
                            request_id=request.request_id,
                            assistant_name=st.session_state.current_username
                        )
                        st.success(f"✅ 已核准並執行！狀態: {approved_request.status.value}")
                        st.info(f"核准者: {approved_request.approved_by}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 執行失敗: {str(e)}")
            
            st.markdown("---")


def main():
    """主程式"""
    init_session_state()
    render_sidebar()
    
    # 根據角色顯示對應介面
    if st.session_state.current_role == UserRole.CUSTOMER:
        render_customer_view()
    else:
        render_assistant_view()
    
    # 通訊紀錄監視器（兩種角色都可見）
    st.markdown("---")
    render_cdr_monitor()


if __name__ == "__main__":
    main()
