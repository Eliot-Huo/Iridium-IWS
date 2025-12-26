"""
SBD 管理系统 - Streamlit 主程式 v6.12
完整集成 IWS Gateway + 服务请求追踪系统
"""
import streamlit as st
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入核心模块
from src.infrastructure.iws_gateway import IWSGateway
from src.models.models import UserRole

# 导入服务追踪模块
from service_tracking.service_tracking_with_polling import (
    RequestStore,
    BackgroundPoller,
    submit_service_request,
    render_assistant_page,
    get_current_taipei_time,
    get_operation_text
)

# ========== 页面配置 ==========

st.set_page_config(
    page_title="SBD 管理系统",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 初始化 ==========

def init_session_state():
    """初始化 Session State"""
    
    # 用户角色
    if 'current_role' not in st.session_state:
        st.session_state.current_role = UserRole.CUSTOMER
    
    if 'current_username' not in st.session_state:
        st.session_state.current_username = 'customer001'
    
    # IWS Gateway
    if 'gateway' not in st.session_state:
        try:
            # 优先从 secrets 读取，否则使用默认值
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
    
    # 服务追踪系统
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


# ========== 侧边栏 ==========

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("📡 SBD 管理系统")
        st.caption("v6.12 - 服务追踪版")
        
        st.markdown("---")
        
        # 角色切换
        st.subheader("🔐 身份切换")
        
        role_option = st.radio(
            "选择角色",
            options=["客户 (Customer)", "助理 (Assistant)"],
            index=0 if st.session_state.current_role == UserRole.CUSTOMER else 1,
            help="切换不同的用户视角"
        )
        
        if role_option == "客户 (Customer)":
            st.session_state.current_role = UserRole.CUSTOMER
            st.session_state.current_username = 'customer001'
        else:
            st.session_state.current_role = UserRole.ASSISTANT
            st.session_state.current_username = 'assistant001'
        
        st.info(f"当前身份: **{st.session_state.current_username}**")
        
        st.markdown("---")
        
        # 系统状态
        st.subheader("📊 系统状态")
        
        # IWS Gateway 状态
        if st.session_state.gateway_initialized:
            st.success("✅ IWS Gateway")
        else:
            st.error("❌ IWS Gateway")
            if 'gateway_error' in st.session_state:
                with st.expander("查看错误"):
                    st.code(st.session_state.gateway_error)
        
        # 后台轮询服务状态
        if st.session_state.get('poller_running', False):
            st.success("✅ 后台轮询 (3分钟)")
        else:
            st.warning("⏸️ 后台轮询未运行")
            if 'poller_error' in st.session_state:
                with st.expander("查看错误"):
                    st.code(st.session_state.poller_error)
        
        # 请求统计
        if 'request_store' in st.session_state:
            all_requests = st.session_state.request_store.get_all()
            pending = st.session_state.request_store.get_pending()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总请求", len(all_requests))
            with col2:
                st.metric("待处理", len(pending))
        
        st.markdown("---")
        
        # 当前时间
        st.caption("**台湾时间**")
        st.caption(get_current_taipei_time())


# ========== 客户页面 ==========

def render_customer_view():
    """渲染客户页面"""
    st.header("👤 客户服务页面")
    
    # 检查系统状态
    if not st.session_state.gateway_initialized:
        st.error("❌ IWS Gateway 未初始化，无法提交请求")
        st.info("请检查配置或联系管理员")
        return
    
    st.info("""
    **提交流程说明**：  
    ✅ 提交后立即传递要求给 Iridium  
    🔄 后台每3分钟自动查询状态  
    📋 到助理页面查看实时状态  
    ⏰ 通常 5-10 分钟内完成
    """)
    
    st.markdown("---")
    
    # 服务请求表单
    with st.form("service_request_form"):
        st.subheader("📝 提交服务请求")
        
        col1, col2 = st.columns(2)
        
        with col1:
            customer_id = st.text_input(
                "客户编号",
                value="C001",
                help="客户的唯一编号"
            )
            
            customer_name = st.text_input(
                "客户名称",
                placeholder="请输入客户姓名",
                help="客户姓名"
            )
            
            imei = st.text_input(
                "IMEI",
                placeholder="请输入15位IMEI号码",
                max_chars=15,
                help="设备的 IMEI 号码"
            )
        
        with col2:
            operation = st.selectbox(
                "操作类型",
                options=['resume', 'suspend', 'deactivate', 'update_plan'],
                format_func=get_operation_text,
                help="选择要执行的操作"
            )
            
            # 如果是变更资费，显示方案选择
            new_plan_id = None
            if operation == 'update_plan':
                new_plan_id = st.selectbox(
                    "新费率方案",
                    options=['763925991', '763924583', '763927911', '763925351'],
                    format_func=lambda x: {
                        '763925991': 'SBD 0',
                        '763924583': 'SBD 12',
                        '763927911': 'SBD 17',
                        '763925351': 'SBD 30'
                    }[x],
                    help="选择新的费率方案"
                )
            
            reason = st.text_area(
                "操作原因",
                placeholder="请输入操作原因",
                help="说明为什么需要执行此操作"
            )
        
        submitted = st.form_submit_button(
            "🚀 提交请求",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            # 验证输入
            if not customer_id:
                st.error("❌ 请输入客户编号")
            elif not customer_name:
                st.error("❌ 请输入客户名称")
            elif not imei or len(imei) != 15 or not imei.isdigit():
                st.error("❌ 请输入有效的 15 位数字 IMEI")
            elif operation == 'update_plan' and not new_plan_id:
                st.error("❌ 请选择新的费率方案")
            elif not reason:
                st.error("❌ 请输入操作原因")
            else:
                try:
                    with st.spinner("正在提交请求..."):
                        # 准备参数
                        kwargs = {'reason': reason}
                        if operation == 'update_plan':
                            kwargs['new_plan_id'] = new_plan_id
                        
                        # 提交请求
                        result = submit_service_request(
                            gateway=st.session_state.gateway,
                            store=st.session_state.request_store,
                            customer_id=customer_id,
                            customer_name=customer_name,
                            imei=imei,
                            operation=operation,
                            **kwargs
                        )
                        
                        # 显示成功消息
                        st.success("✅ 已正确传递要求给 Iridium")
                        st.balloons()
                        
                        # 显示详情
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.info(f"**请求ID**\n`{result['request_id']}`")
                        
                        with col2:
                            if result.get('transaction_id'):
                                st.info(f"**Transaction ID**\n`{result['transaction_id']}`")
                            else:
                                st.warning("未获取到 Transaction ID")
                        
                        with col3:
                            st.info(f"**状态**\n🔄 正在等待回馈中")
                        
                        # 后续说明
                        st.markdown("---")
                        st.markdown("""
                        ### 📊 后续流程
                        
                        - **自动查询** - 后台每3分钟自动查询一次状态
                        - **预计时间** - 通常 5-10 分钟内完成
                        - **查看状态** - 请到"助理页面"查看实时状态
                        """)
                
                except Exception as e:
                    st.error(f"❌ 提交失败: {str(e)}")
                    with st.expander("查看详细错误"):
                        st.exception(e)


# ========== 主程序 ==========

def main():
    """主程序"""
    # 初始化
    init_session_state()
    
    # 渲染侧边栏
    render_sidebar()
    
    # 根据角色显示对应页面
    if st.session_state.current_role == UserRole.CUSTOMER:
        render_customer_view()
    else:
        # 助理页面 - 使用服务追踪系统的完整 UI
        render_assistant_page(st.session_state.request_store)


if __name__ == "__main__":
    main()
