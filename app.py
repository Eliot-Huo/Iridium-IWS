"""
衛星設備管理系統 - Streamlit 主程式 v6.44.0
完整整合 IWS Gateway + 服務請求追蹤系統 + 費用查詢 + 價格管理 + CDR 完整管理 + DSG 流量管理

支援設備類型：
- SBD (Short Burst Data) - 當前主要功能
- 衛星電話 (Voice) - 預留
- Iridium Go! Exec - 預留

版本更新：
- v6.44.0: 新增 DSG 流量管理 - Resource Group + Tracker 完整功能
- v6.43.1: 實際價格初始化 - 使用 Exhibit B 價格
- v6.43.0: 檔案結構重構 - 清晰的資料夾組織
- v6.42.0: Profile 管理 Web UI - 完整的價格 Profile 管理
- v6.41.0: Profile 系統實作 - 支援多版本價格管理
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

# 匯入頁面
from pages.shared.billing_query import render_billing_query_page

# ========== 頁面設定 ==========

st.set_page_config(
    page_title="衛星設備管理系統",
    page_icon="🛰️",
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
            password = st.secrets.get('IWS_PASSWORD', '')  # 不提供預設密碼
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
    
    # 🍎 Safari 兼容性：完全停用後台轮询
    # 改为手动重新整理模式，避免後台執行緒导致的性能问题
    if 'poller' not in st.session_state and st.session_state.gateway_initialized:
        try:
            st.session_state.poller = BackgroundPoller(
                gateway=st.session_state.gateway,
                store=st.session_state.request_store
            )
            
            # 預設停用後台轮询（Safari 兼容性）
            if 'polling_enabled' not in st.session_state:
                st.session_state.polling_enabled = False  # 改为預設停用
            
            # 只有用户明确啟用时才啟動
            if st.session_state.polling_enabled:
                st.session_state.poller.start()
                st.session_state.poller_running = True
            else:
                st.session_state.poller_running = False
                
        except Exception as e:
            st.session_state.poller_running = False
            st.session_state.poller_error = str(e)


# ========== 側邊欄 ==========

def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        st.title("🛰️ 衛星設備管理")
        st.caption("v6.35.6 - 穩定版")
        
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
        poller_status_placeholder = st.empty()
        
        with poller_status_placeholder:
            if st.session_state.get('poller_running', False):
                st.success("✅ 後台輪詢 (3分鐘)")
            else:
                st.warning("⏸️ 後台輪詢未執行")
                if 'poller_error' in st.session_state:
                    with st.expander("查看錯誤"):
                        st.code(st.session_state.poller_error)
        
        # 🍎 Safari 兼容性：轮询控制
        st.markdown("##### ⚙️ 性能設定")
        
        polling_enabled = st.checkbox(
            "啟用後台自動輪詢",
            value=st.session_state.get('polling_enabled', False),  # 預設停用
            help="預設關閉以提升所有浏览器性能。啟用后每3分鐘自动查詢一次狀態。",
            key="polling_toggle"
        )
        
        # 處理轮询狀態变化
        if 'polling_enabled' not in st.session_state:
            st.session_state.polling_enabled = False  # 預設停用
        
        if polling_enabled != st.session_state.polling_enabled:
            st.session_state.polling_enabled = polling_enabled
            
            if 'poller' in st.session_state:
                if polling_enabled:
                    # 啟動轮询
                    try:
                        st.session_state.poller.start()
                        st.session_state.poller_running = True
                        st.success("✅ 已啟動後台轮询")
                        time.sleep(0.5)
                    except Exception as e:
                        st.error(f"啟動失敗: {e}")
                else:
                    # 停止轮询
                    try:
                        st.session_state.poller.stop()
                        st.session_state.poller_running = False
                        st.info("⏸️ 已停止後台轮询")
                        time.sleep(0.5)
                    except Exception as e:
                        st.error(f"停止失敗: {e}")
                
                st.rerun()
        
        # 狀態提示
        if st.session_state.get('poller_running', False):
            st.success("🟢 自动轮询: 執行中（每3分鐘）")
        else:
            st.info("🔵 手动重新整理模式（推荐）")
        
        st.caption("💡 **建议**: 使用手動重新整理模式以获得最佳性能")

        
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
    
    # ========== IMEI 查詢區域（獨立於表單） ==========
    st.subheader("🔍 設備狀態查詢")
    st.info("先查詢設備狀態，確認無誤後再提交服務請求")
    
    # IMEI 輸入與查詢按鈕
    query_col1, query_col2, query_col3 = st.columns([3, 1, 1])
    
    with query_col1:
        query_imei = st.text_input(
            "IMEI",
            placeholder="請輸入15位IMEI號碼",
            max_chars=15,
            help="設備的 IMEI 號碼",
            key="query_imei"
        )
    
    with query_col2:
        query_basic_button = st.button(
            "📋 快速查詢",
            use_container_width=True,
            disabled=(not query_imei or len(query_imei) != 15),
            help="快速查看基本狀態"
        )
    
    with query_col3:
        query_detail_button = st.button(
            "🔍 完整查詢",
            use_container_width=True,
            type="secondary",
            disabled=(not query_imei or len(query_imei) != 15),
            help="查詢完整的 7 個欄位資訊"
        )
    
    # 快速查詢 - 基本狀態
    if query_basic_button and query_imei and len(query_imei) == 15 and query_imei.isdigit():
        try:
            with st.spinner("正在查詢 IMEI 狀態..."):
                search_result = st.session_state.gateway.search_account(query_imei)
            
            if search_result['found']:
                # 顯示狀態資訊
                status = search_result.get('status', 'UNKNOWN')
                plan_name = search_result.get('plan_name', '未知')
                account_number = search_result.get('subscriber_account_number', 'N/A')
                activation_date = search_result.get('activation_date', 'N/A')
                
                # 根據狀態選擇顏色和圖示
                status_config = {
                    'ACTIVE': {'emoji': '✅', 'color': 'green', 'text': '正常運作'},
                    'SUSPENDED': {'emoji': '⏸️', 'color': 'orange', 'text': '已暫停'},
                    'DEACTIVATED': {'emoji': '🔴', 'color': 'red', 'text': '已註銷'}
                }
                
                config = status_config.get(status, {'emoji': '❓', 'color': 'gray', 'text': '未知狀態'})
                
                # 使用 container 顯示基本狀態
                st.markdown("---")
                st.markdown("#### 📋 設備基本狀態")
                
                # 使用 columns 顯示基本資訊
                info_col1, info_col2, info_col3 = st.columns(3)
                
                with info_col1:
                    st.metric(
                        label="狀態",
                        value=f"{config['emoji']} {config['text']}"
                    )
                
                with info_col2:
                    st.metric(
                        label="資費方案",
                        value=plan_name
                    )
                
                with info_col3:
                    st.metric(
                        label="開通日期",
                        value=activation_date if activation_date != 'N/A' else '未知'
                    )
                
                st.caption(f"合約號碼: {account_number}")
                
                # 根據狀態顯示提示
                if status == 'SUSPENDED':
                    st.info(
                        "💡 **SITEST 環境提示**：此設備在測試環境中為暫停狀態。\n\n"
                        "• 生產環境可能是正常狀態\n"
                        "• 變更資費時系統會自動恢復\n"
                        "• 也可以選擇「恢復設備」操作"
                    )
                elif status == 'DEACTIVATED':
                    st.warning(
                        "⚠️  此設備已註銷，建議執行「恢復設備」操作後再進行其他操作。"
                    )
                elif status == 'ACTIVE':
                    st.success(
                        "✅ 設備運作正常，可以執行所有操作。點擊「🔍 完整查詢」查看詳細資訊。"
                    )
                
                st.markdown("---")
            else:
                st.error(
                    f"❌ 找不到 IMEI: {query_imei}\n\n"
                    "可能原因：\n"
                    "• IMEI 輸入錯誤\n"
                    "• 設備未在 IWS 系統中註冊"
                )
                
        except Exception as e:
            st.warning(
                f"⚠️  無法查詢 IMEI 狀態\n\n"
                f"錯誤: {str(e)}\n\n"
                "您仍可繼續提交請求，系統會在助理確認時再次查詢。"
            )
    
    # 完整查詢 - 顯示完整的 7 個字段
    if query_detail_button and query_imei and len(query_imei) == 15 and query_imei.isdigit():
        with st.spinner("正在查詢完整資訊..."):
            try:
                detailed_result = st.session_state.gateway.get_detailed_account_info(query_imei)
                
                if detailed_result.get('found'):
                    st.markdown("---")
                    st.markdown("### 📊 設備完整資訊")
                    
                    # 分成三欄顯示
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.metric("狀態", detailed_result.get('status', 'N/A'))
                        st.metric("現行資費", detailed_result.get('plan_name', 'N/A'))
                        st.metric("開通日期", detailed_result.get('activation_date', 'N/A'))
                    
                    with col_b:
                        destinations = detailed_result.get('destinations', [])
                        if destinations:
                            first_dest = destinations[0]
                            st.metric("Destination", first_dest.get('destination', 'N/A'))
                            st.metric("Geo", first_dest.get('geo_data', 'N/A'))
                            st.metric("MO ACK", first_dest.get('mo_ack', 'N/A'))
                        else:
                            st.metric("Destination", 'N/A')
                            st.metric("Geo", 'N/A')
                            st.metric("MO ACK", 'N/A')
                    
                    with col_c:
                        st.metric("Ring Alert", detailed_result.get('ring_alert', 'N/A'))
                        st.metric("合約代碼", detailed_result.get('account_number', 'N/A'))
                        st.metric("Home Gateway", detailed_result.get('home_gateway', 'N/A'))
                    
                    # 如果有多個 destinations，顯示所有
                    if len(destinations) > 1:
                        st.markdown("#### 📡 所有 Destinations")
                        for i, dest in enumerate(destinations, 1):
                            with st.expander(f"Destination {i}: {dest.get('destination', 'N/A')}"):
                                st.write(f"**投遞方法**: {dest.get('method', 'N/A')}")
                                st.write(f"**Geo Data**: {dest.get('geo_data', 'N/A')}")
                                st.write(f"**MO ACK**: {dest.get('mo_ack', 'N/A')}")
                    
                    # 額外資訊
                    with st.expander("📋 其他資訊"):
                        st.write(f"**ICCID**: {detailed_result.get('iccid', 'N/A')}")
                        st.write(f"**SP Reference**: {detailed_result.get('sp_reference', 'N/A')}")
                        st.write(f"**Account Type**: {detailed_result.get('account_type', 'N/A')}")
                        st.write(f"**Last Updated**: {detailed_result.get('last_updated', 'N/A')}")
                    
                    st.markdown("---")
                    st.success("✅ 完整資訊查詢成功！")
                else:
                    st.error(f"❌ 無法獲取詳細資訊: {detailed_result.get('message', '未知錯誤')}")
            
            except Exception as e:
                st.error(f"❌ 查詢失敗: {str(e)}")
    
    st.markdown("---")
    st.markdown("---")
    
    # ========== 服務請求表單 ==========
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
                help="設備的 IMEI 號碼（可從上方查詢結果複製）",
                key="imei_input",
                value=query_imei if query_imei and len(query_imei) == 15 else ""
            )
        
        with col2:
            operation = st.selectbox(
                "操作類型",
                options=['resume', 'suspend', 'deactivate', 'update_plan'],
                format_func=get_operation_text,
                help="選擇要執行的操作"
            )
        
        # ========== 資費方案選擇（始終顯示，避免 Form 內條件渲染問題） ==========
        st.markdown("---")
        st.markdown("### 📋 資費方案選擇")
        
        # 定義方案資訊（使用與 IWS getSBDBundles 返回一致的名称）
        # 注意：IWS 返回的名称带空格，如 "SBD 0", "SBD 12" 等
        plan_options = {
            'SBD 0': {  # ✅ 与 IWS 返回一致（带空格）
                'name': 'SBD 0',
                'description': '基礎方案 - 0 則訊息/月',
                'monthly_fee': '$0',
                'messages': 0,
                'bundle_id': '763925991'
            },
            'SBD 12': {
                'name': 'SBD 12',
                'description': '標準方案 - 12 則訊息/月',
                'monthly_fee': '$30',
                'messages': 12,
                'bundle_id': '763924583'
            },
            'SBD 17': {
                'name': 'SBD 17',
                'description': '進階方案 - 17 則訊息/月',
                'monthly_fee': '$45',
                'messages': 17,
                'bundle_id': '763927911'
            },
            'SBD 30': {
                'name': 'SBD 30',
                'description': '專業方案 - 30 則訊息/月',
                'monthly_fee': '$60',
                'messages': 30,
                'bundle_id': '763925351'
            }
        }
        
        # 顯示提示
        if operation == 'update_plan':
            st.info("💡 請選擇要變更的資費方案（符合 IWS 開發規範）")
        else:
            st.warning("⚠️ 只有選擇「變更資費方案」操作時才需要選擇資費")
        
        # 资费選擇（始终顯示）
        new_plan_id = st.selectbox(
            "選擇新資費方案" + (" *" if operation == 'update_plan' else " (當前操作不需要)"),
            options=list(plan_options.keys()),
            format_func=lambda x: f"{plan_options[x]['name']} - {plan_options[x]['description']} ({plan_options[x]['monthly_fee']})",
            help="選擇要變更的資費方案。系統會先查詢可用方案，再執行變更。",
            disabled=(operation != 'update_plan')  # 非變更資費時停用
        )
        
        # 顯示選擇的資費詳情
        if operation == 'update_plan' and new_plan_id:
            selected_plan = plan_options[new_plan_id]
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("方案代碼", selected_plan['name'])
            
            with col_b:
                st.metric("訊息數量", f"{selected_plan['messages']} 則/月")
            
            with col_c:
                st.metric("月費", selected_plan['monthly_fee'])

        
        reason = st.text_area(
            "操作原因 *",
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
                        
                        # 顯示成功訊息（客戶只是提交請求，尚未傳給 IWS）
                        st.success("✅ 請求已提交成功")
                        st.info("📋 **請求狀態：等待助理確認**\n\n您的請求已記錄，需要助理在助理頁面確認後才會提交給 Iridium")
                        
                        # 顯示詳情
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("請求ID", result['request_id'])
                        
                        with col2:
                            st.metric("狀態", "等待助理確認")
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
        # 客戶端頁面選單
        page = st.sidebar.selectbox(
            "📌 功能選單",
            options=["設備管理", "費用查詢", "DSG 流量查詢"],
            key="customer_page"
        )
        
        if page == "設備管理":
            render_customer_view()
        elif page == "費用查詢":
            render_billing_query_page(st.session_state.gateway)
        elif page == "DSG 流量查詢":
            from pages.customer.dsg_query import render_dsg_query_page
            render_dsg_query_page(st.session_state.gateway)
    else:
        # 助理端頁面選單
        page = st.sidebar.selectbox(
            "📌 功能選單",
            options=["設備管理", "費用查詢", "Profile 管理", "DSG 流量管理", "CDR 同步管理", "CDR 帳單查詢", "📁 建立服務帳號資料夾"],
            key="assistant_page"
        )
        
        if page == "設備管理":
            # 助理頁面 - 使用服務追蹤系統的完整 UI
            # 傳遞 gateway 以便助理確認後提交給 IWS
            render_assistant_page(
                gateway=st.session_state.gateway,
                store=st.session_state.request_store
            )
        elif page == "費用查詢":
            render_billing_query_page(st.session_state.gateway)
        elif page == "Profile 管理":
            # Profile 管理頁面
            from pages.assistant.profile_management import render_profile_management_page
            render_profile_management_page()
        elif page == "DSG 流量管理":
            # DSG 流量管理頁面
            from pages.assistant.dsg_management import render_dsg_management_page
            render_dsg_management_page(st.session_state.gateway)
        elif page == "CDR 同步管理":
            # CDR 同步管理頁面
            from pages.assistant.cdr_sync import render_sync_management_page
            render_sync_management_page()
        elif page == "CDR 帳單查詢":
            # CDR 帳單查詢頁面
            from pages.assistant.cdr_billing_query import render_cdr_billing_query_page
            render_cdr_billing_query_page()
        elif page == "📁 建立服務帳號資料夾":
            # 建立服務帳號資料夾頁面
            from pages.assistant.create_sa_folder import create_sa_folder
            create_sa_folder()


if __name__ == "__main__":
    main()
