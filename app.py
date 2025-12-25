"""
SBD 管理系統 - Streamlit 主程式
"""
import streamlit as st
from datetime import datetime
from src.repositories.repo import InMemoryRepository
from src.services.sbd_service import SBDService
from src.services.cdr_service import CDRService
from src.models.models import UserRole, RequestStatus
from src.config.constants import RATE_PLANS, ACTIVATION_FEE


# 頁面配置
st.set_page_config(
    page_title="SBD 管理系統",
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
        st.title("📡 SBD 管理系統")
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
            
            st.dataframe(display_data, use_container_width=True)
            
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
    """渲染客戶介面"""
    st.header("👤 客戶服務申請")
    
    # 功能 A: 發起 SBD 啟用申請
    with st.container():
        st.subheader("📱 申請 SBD 啟用服務")
        
        col1, col2 = st.columns(2)
        
        with col1:
            imei_input = st.text_input(
                "IMEI 號碼",
                placeholder="請輸入 15 位數字",
                max_chars=15,
                help="設備的唯一識別碼"
            )
        
        with col2:
            plan_options = list(RATE_PLANS.keys())
            selected_plan = st.selectbox(
                "資費方案",
                options=plan_options,
                help="選擇適合的資費方案"
            )
        
        # 即時費用計算
        if selected_plan:
            plan_fee = RATE_PLANS[selected_plan]
            total_amount = ACTIVATION_FEE + plan_fee
            
            st.markdown("### 💰 費用明細")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("啟用費", f"${ACTIVATION_FEE:.2f}")
            with col2:
                st.metric("月租費", f"${plan_fee:.2f}")
            with col3:
                st.metric("應付總額", f"${total_amount:.2f}", delta=None)
        
        # 提交申請
        st.markdown("---")
        if st.button("🚀 提交申請", type="primary", use_container_width=True):
            if not imei_input or len(imei_input) != 15:
                st.error("❌ 請輸入有效的 15 位數 IMEI 號碼")
            elif not imei_input.isdigit():
                st.error("❌ IMEI 只能包含數字")
            else:
                try:
                    request = st.session_state.sbd_service.create_activation_request(
                        imei=imei_input,
                        plan_id=selected_plan,
                        requester=st.session_state.current_username
                    )
                    st.success(f"✅ 申請已提交！請求編號: **{request.request_id}**")
                    st.info(f"💵 應付金額: **${request.amount_due:.2f}**")
                    st.info(f"📋 目前狀態: **{request.status.value}** (等待財務確認)")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ 申請失敗: {str(e)}")
    
    # 查詢我的申請
    st.markdown("---")
    st.subheader("📋 我的申請記錄")
    
    if imei_input:
        my_requests = st.session_state.sbd_service.get_requests_by_imei(imei_input)
        
        if my_requests:
            for req in my_requests:
                with st.expander(f"📄 {req.request_id} - {req.status.value.upper()}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**操作類型:** {req.action_type.value}")
                        st.write(f"**資費方案:** {req.plan_id}")
                        st.write(f"**應付金額:** ${req.amount_due:.2f}")
                    with col2:
                        st.write(f"**建立時間:** {req.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**狀態:** {req.status.value}")
                        if req.approved_by:
                            st.write(f"**核准者:** {req.approved_by}")
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
            st.markdown(f"#### 請求 #{idx + 1}: {request.request_id}")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**IMEI:** {request.imei}")
                st.write(f"**操作:** {request.action_type.value.upper()}")
                st.write(f"**方案:** {request.plan_id}")
            
            with col2:
                st.write(f"**應收金額:** ${request.amount_due:.2f}")
                st.write(f"**申請時間:** {request.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**申請人:** {request.notes}")
            
            with col3:
                # 確認執行按鈕
                if st.button(
                    "✅ 確認收款並執行 IWS",
                    key=f"approve_{request.request_id}",
                    type="primary"
                ):
                    try:
                        approved_request = st.session_state.sbd_service.process_finance_approval(
                            request_id=request.request_id,
                            assistant_name=st.session_state.current_username
                        )
                        st.success(f"✅ 已核准！狀態更新為: {approved_request.status.value}")
                        st.info(f"核准者: {approved_request.approved_by}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 核准失敗: {str(e)}")
            
            st.markdown("---")
    
    # 已處理的請求
    st.markdown("### 📊 已處理請求")
    all_requests = st.session_state.repository.list_all_requests()
    processed_requests = [r for r in all_requests if r.status != RequestStatus.PENDING_FINANCE]
    
    if processed_requests:
        display_data = []
        for req in processed_requests:
            display_data.append({
                '請求編號': req.request_id,
                'IMEI': req.imei,
                '操作': req.action_type.value,
                '方案': req.plan_id,
                '金額 ($)': f'${req.amount_due:.2f}',
                '狀態': req.status.value,
                '核准者': req.approved_by or 'N/A',
                '更新時間': req.updated_at.strftime('%Y-%m-%d %H:%M:%S') if req.updated_at else 'N/A'
            })
        
        st.dataframe(display_data, use_container_width=True)
    else:
        st.info("尚無已處理的請求")


def main():
    """主程式"""
    # 初始化
    init_session_state()
    
    # 渲染側邊欄
    render_sidebar()
    
    # 主要內容區
    st.title("📡 衛星寬頻數據 (SBD) 管理系統")
    
    # 流量監視器（共通組件）
    with st.expander("📈 通訊紀錄監視器", expanded=False):
        render_cdr_monitor()
    
    st.markdown("---")
    
    # 根據角色顯示對應介面
    if st.session_state.current_role == UserRole.CUSTOMER:
        render_customer_view()
    else:
        render_assistant_view()


if __name__ == '__main__':
    main()
