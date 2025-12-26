"""
SBD 管理系統 - Streamlit 主程式 v6.12
完整整合 IWS Gateway + 服務請求追蹤系統
"""
import streamlit as st
import sys
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 匯入核心模組
from src.infrastructure.iws_gateway import IWSGateway
from src.models.models import UserRole

# 匯入服務追蹤模組
from service_tracking.service_tracking_with_polling import (
    RequestStore,
    BackgroundPoller,
    submit_service_request,
    render_assistant_page,
    get_current_taipei_time,
    get_operation_text
)

# ========== 頁面設定 ==========

st.set_page_config(
    page_title="SBD 管理系統",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 初始化 ==========

def init_session_state():
    """初始化 Session State"""
    
    # 使用者角色
    if 'current_role' not in st.session_state:
        st.session_state.current_role = UserRole.CUSTOMER
    
    if 'current_username' not in st.session_state:
        st.session_state.current_username = 'customer001'
    
    # IWS Gateway
    if 'gateway' not in st.session_state:
        try:
            # 優先從 secrets 讀取，否則使用預設值
            username = st.secrets.get('IWS_USERNAME', 'IWSN3D')
            password = st.secrets.get('IWS_PASSWORD', 'FvGr2({sE4V4TJ:')
            sp_account = st.secrets.get('IWS_SP_ACCOUNT', '200883')
            endpoint = st.secrets.get('IWS_ENDPOINT', 'https://iwstraining.iridium.com:8443/iws-current/iws')
            
            st.session_state.gateway = IWSGateway(
                username=username,
                password=password,
                sp_account=sp_account,
                endpoint=endpoint
            )
            st.session_state.gateway_initialized = True
        except Exception as e:
            st.session_state.gateway_initialized = False
            st.session_state.gateway_error = str(e)
    
    # 服務追蹤系統
    if 'request_store' not in st.session_state:
        st.session_state.request_store = RequestStore('service_requests.json')
    
    if 'poller' not in st.session_state and st.session_state.gateway_initialized:
        try:
            st.session_state.poller = BackgroundPoller(
                gateway=st.session_state.gateway,
                store=st.session_state.request_store
            )
            st.session_state.poller.start()
            st.session_state.poller_running = True
        except Exception as e:
            st.session_state.poller_running = False
            st.session_state.poller_error = str(e)


# ========== 側邊欄 ==========

def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        st.title("📡 SBD 管理系統")
        st.caption("v6.12 - 服務追蹤版")
        
        st.markdown("---")
        
        # 角色切換
        st.subheader("🔐 身份切換")
        
        role_option = st.radio(
            "選擇角色",
            options=["客戶 (Customer)", "助理 (Assistant)"],
            index=0 if st.session_state.current_role == UserRole.CUSTOMER else 1,
            help="切換不同的使用者視角"
        )
        
        if role_option == "客戶 (Customer)":
            st.session_state.current_role = UserRole.CUSTOMER
            st.session_state.current_username = 'customer001'
        else:
            st.session_state.current_role = UserRole.ASSISTANT
            st.session_state.current_username = 'assistant001'
        
        st.info(f"當前身份: **{st.session_state.current_username}**")
        
        st.markdown("---")
        
        # 系統狀態
        st.subheader("📊 系統狀態")
        
        # IWS Gateway 狀態
        if st.session_state.gateway_initialized:
            st.success("✅ IWS Gateway")
        else:
            st.error("❌ IWS Gateway")
            if 'gateway_error' in st.session_state:
                with st.expander("查看錯誤"):
                    st.code(st.session_state.gateway_error)
        
        # 後台輪詢服務狀態
        if st.session_state.get('poller_running', False):
            st.success("✅ 後台輪詢 (3分鐘)")
        else:
            st.warning("⏸️ 後台輪詢未執行")
            if 'poller_error' in st.session_state:
                with st.expander("查看錯誤"):
                    st.code(st.session_state.poller_error)
        
        # 請求統計
        if 'request_store' in st.session_state:
            all_requests = st.session_state.request_store.get_all()
            pending = st.session_state.request_store.get_pending()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("總請求", len(all_requests))
            with col2:
                st.metric("待處理", len(pending))
        
        st.markdown("---")
        
        # 當前時間
        st.caption("**台灣時間**")
        st.caption(get_current_taipei_time())


# ========== 客戶頁面 ==========

def render_customer_view():
    """渲染客戶頁面"""
    st.header("👤 客戶服務頁面")
    
    # 檢查系統狀態
    if not st.session_state.gateway_initialized:
        st.error("❌ IWS Gateway 未初始化，無法提交請求")
        st.info("請檢查設定或聯絡管理員")
        return
    
    st.info("""
    **提交流程說明**：  
    ✅ 提交後立即傳遞要求給 Iridium  
    🔄 後台每3分鐘自動查詢狀態  
    📋 到助理頁面查看即時狀態  
    ⏰ 通常 5-10 分鐘內完成
    """)
    
    st.markdown("---")
    
    # 服務請求表單
    with st.form("service_request_form"):
        st.subheader("📝 提交服務請求")
        
        col1, col2 = st.columns(2)
        
        with col1:
            customer_id = st.text_input(
                "客戶編號",
                value="C001",
                help="客戶的唯一編號"
            )
            
            customer_name = st.text_input(
                "客戶名稱",
                placeholder="請輸入客戶姓名",
                help="客戶姓名"
            )
            
            imei = st.text_input(
                "IMEI",
                placeholder="請輸入15位IMEI號碼",
                max_chars=15,
                help="設備的 IMEI 號碼"
            )
        
        with col2:
            operation = st.selectbox(
                "操作類型",
                options=['resume', 'suspend', 'deactivate', 'update_plan'],
                format_func=get_operation_text,
                help="選擇要執行的操作"
            )
            
            # 如果是變更資費，顯示方案選擇
            new_plan_id = None
            if operation == 'update_plan':
                new_plan_id = st.selectbox(
                    "新資費方案",
                    options=['763925991', '763924583', '763927911', '763925351'],
                    format_func=lambda x: {
                        '763925991': 'SBD 0',
                        '763924583': 'SBD 12',
                        '763927911': 'SBD 17',
                        '763925351': 'SBD 30'
                    }[x],
                    help="選擇新的資費方案"
                )
            
            reason = st.text_area(
                "操作原因",
                placeholder="請輸入操作原因",
                help="說明為什麼需要執行此操作"
            )
        
        submitted = st.form_submit_button(
            "🚀 提交請求",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            # 驗證輸入
            if not customer_id:
                st.error("❌ 請輸入客戶編號")
            elif not customer_name:
                st.error("❌ 請輸入客戶名稱")
            elif not imei or len(imei) != 15 or not imei.isdigit():
                st.error("❌ 請輸入有效的 15 位數字 IMEI")
            elif operation == 'update_plan' and not new_plan_id:
                st.error("❌ 請選擇新的資費方案")
            elif not reason:
                st.error("❌ 請輸入操作原因")
            else:
                try:
                    with st.spinner("正在提交請求..."):
                        # 準備參數
                        kwargs = {'reason': reason}
                        if operation == 'update_plan':
                            kwargs['new_plan_id'] = new_plan_id
                        
                        # 提交請求
                        result = submit_service_request(
                            gateway=st.session_state.gateway,
                            store=st.session_state.request_store,
                            customer_id=customer_id,
                            customer_name=customer_name,
                            imei=imei,
                            operation=operation,
                            **kwargs
                        )
                        
                        # 顯示成功訊息
                        st.success("✅ 已正確傳遞要求給 Iridium")
                        st.balloons()
                        
                        # 顯示詳情
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.info(f"**請求ID**\n`{result['request_id']}`")
                        
                        with col2:
                            if result.get('transaction_id'):
                                st.info(f"**Transaction ID**\n`{result['transaction_id']}`")
                            else:
                                st.warning("未獲取到 Transaction ID")
                        
                        with col3:
                            st.info(f"**狀態**\n🔄 正在等待回饋中")
                        
                        # 後續說明
                        st.markdown("---")
                        st.markdown("""
                        ### 📊 後續流程
                        
                        - **自動查詢** - 後台每3分鐘自動查詢一次狀態
                        - **預計時間** - 通常 5-10 分鐘內完成
                        - **查看狀態** - 請到"助理頁面"查看即時狀態
                        """)
                
                except Exception as e:
                    st.error(f"❌ 提交失敗: {str(e)}")
                    with st.expander("查看詳細錯誤"):
                        st.exception(e)


# ========== 主程式 ==========

def main():
    """主程式"""
    # 初始化
    init_session_state()
    
    # 渲染側邊欄
    render_sidebar()
    
    # 根據角色顯示對應頁面
    if st.session_state.current_role == UserRole.CUSTOMER:
        render_customer_view()
    else:
        # 助理頁面 - 使用服務追蹤系統的完整 UI
        # 傳遞 gateway 以便助理確認後提交給 IWS
        render_assistant_page(st.session_state.request_store, st.session_state.gateway)


if __name__ == "__main__":
    main()
