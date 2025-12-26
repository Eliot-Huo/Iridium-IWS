"""
快速开始 - 服务请求追踪系统集成示例
演示如何在现有 Streamlit 应用中集成
"""
import streamlit as st
import sys
sys.path.insert(0, '/Users/eliothuo/Downloads/files (1)/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway
from service_tracking_with_polling import (
    RequestStore,
    BackgroundPoller,
    submit_service_request,
    render_assistant_page,
    get_current_taipei_time
)

# ========== 页面配置 ==========

st.set_page_config(
    page_title="SBD 管理系统 - 服务追踪演示",
    page_icon="📡",
    layout="wide"
)

# ========== 初始化 ==========

# IWS Gateway
if 'gateway' not in st.session_state:
    st.session_state.gateway = IWSGateway(
        username="IWSN3D",
        password="FvGr2({sE4V4TJ:",
        sp_account="200883",
        endpoint="https://iwstraining.iridium.com:8443/iws-current/iws"
    )

# 请求存储
if 'request_store' not in st.session_state:
    st.session_state.request_store = RequestStore('demo_requests.json')

# 后台轮询服务
if 'poller' not in st.session_state:
    st.session_state.poller = BackgroundPoller(
        gateway=st.session_state.gateway,
        store=st.session_state.request_store
    )
    st.session_state.poller.start()
    st.sidebar.success("✅ 后台轮询服务已启动")

# ========== 侧边栏导航 ==========

st.sidebar.title("📡 SBD 管理系统")

page = st.sidebar.radio(
    "选择页面",
    options=["客户页面", "助理页面", "系统说明"]
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**当前时间**\n{get_current_taipei_time()}")
st.sidebar.caption("(台湾时间)")

# ========== 页面路由 ==========

if page == "客户页面":
    # ========== 客户页面 ==========
    
    st.title("👤 客户服务页面")
    
    st.markdown("""
    在此页面提交服务请求后，系统会：
    1. ✅ 立即传递要求给 Iridium
    2. 🔄 后台每3分钟自动查询状态
    3. 📋 在助理页面显示实时状态
    """)
    
    st.markdown("---")
    
    # 输入表单
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
                value="测试客户",
                help="客户姓名"
            )
            
            imei = st.text_input(
                "IMEI",
                value="300534066711380",
                help="设备的 IMEI 号码"
            )
        
        with col2:
            operation = st.selectbox(
                "操作类型",
                options=['resume', 'suspend', 'deactivate', 'update_plan'],
                format_func=lambda x: {
                    'resume': '恢复设备',
                    'suspend': '暂停设备',
                    'deactivate': '注销设备',
                    'update_plan': '变更资费'
                }[x]
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
                    }[x]
                )
            
            reason = st.text_area(
                "原因说明",
                value="客户申请",
                help="操作的原因"
            )
        
        submitted = st.form_submit_button(
            "🚀 提交请求",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            # 验证输入
            if not customer_id or not customer_name or not imei:
                st.error("❌ 请填写所有必填字段")
            else:
                try:
                    with st.spinner("正在提交请求..."):
                        # 准备参数
                        kwargs = {'reason': reason}
                        if operation == 'update_plan' and new_plan_id:
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
                        
                        # 显示详情
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.info(f"**请求ID**: `{result['request_id']}`")
                        
                        with col2:
                            if result.get('transaction_id'):
                                st.info(f"**Transaction ID**: `{result['transaction_id']}`")
                        
                        # 状态说明
                        st.markdown("""
                        ### 📊 后续流程
                        
                        1. 🔄 **状态**: 正在等待 IWS 回馈中
                        2. ⏰ **预计时间**: 5-10 分钟
                        3. 🤖 **自动查询**: 后台每3分钟自动查询一次
                        4. 📋 **查看状态**: 请到"助理页面"查看实时状态
                        """)
                        
                        # 提供导航按钮
                        if st.button("📋 立即查看助理页面", use_container_width=True):
                            st.switch_page("assistant")
                
                except Exception as e:
                    st.error(f"❌ 提交失败: {str(e)}")
                    st.exception(e)

elif page == "助理页面":
    # ========== 助理页面 ==========
    
    render_assistant_page(st.session_state.request_store)

elif page == "系统说明":
    # ========== 系统说明 ==========
    
    st.title("📖 系统说明")
    
    st.markdown("""
    ## 🎯 服务请求追踪系统
    
    ### **核心功能**
    
    1. **自动轮询** 🔄
       - 后台服务每3分钟自动查询待处理请求
       - 无需手动刷新
       - 自动更新状态
    
    2. **实时显示** 📊
       - 客户编号
       - 需求名称（变更资费、暂停、注销等）
       - 目前状态
       - 生效时间（台湾时间）
    
    3. **批量管理** 📋
       - 支持多个并发请求
       - 统一追踪管理
       - 批量查询更新
    
    4. **时区转换** 🌏
       - IWS 返回 UTC 时间
       - 自动转换为台湾时间
       - 清晰显示
    
    ---
    
    ## 🔄 工作流程
    
    ### **1. 客户页面提交请求**
    
    ```
    提交表单
      ↓
    调用 IWS API
      ↓
    获取 Transaction ID
      ↓
    保存到数据库
      ↓
    显示确认消息
    ```
    
    ### **2. 后台自动轮询（每3分钟）**
    
    ```
    获取待处理请求
      ↓
    调用 getQueueEntry(TransactionID)
      ↓
    检查状态:
      - PENDING: 继续等待
      - WORKING: 处理中
      - DONE: 调用 getSubscriberAccount 验证
      - ERROR: 调用 getIwsRequest 获取错误
      ↓
    更新数据库
    ```
    
    ### **3. 助理页面显示**
    
    ```
    读取数据库
      ↓
    显示所有请求
      ↓
    实时状态更新
      ↓
    台湾时间显示
    ```
    
    ---
    
    ## 📊 状态说明
    
    | 状态 | 图标 | 说明 |
    |------|------|------|
    | 已提交 | 📤 | 请求已创建 |
    | 等待回馈中 | 🔄 | 已发送到 IWS，等待响应 |
    | 处理中 | ⚙️ | IWS 正在处理 |
    | 已确认 | ✅ | 处理完成，已生效 |
    | 失败 | ❌ | 处理失败 |
    | 超时 | ⏰ | 查询超时 |
    
    ---
    
    ## ⚙️ 技术实现
    
    ### **后台轮询服务**
    
    - 使用 Python threading
    - 独立线程运行
    - 每3分钟执行一次
    - 不影响主应用
    
    ### **数据持久化**
    
    - JSON 文件存储
    - 自动保存
    - 断电不丢失
    
    ### **IWS API**
    
    - `getQueueEntry`: 查询队列状态
    - `getSubscriberAccount`: 验证账户状态
    - `getIwsRequest`: 获取错误详情
    
    ---
    
    ## 🚨 重要提醒
    
    ### **IWS 不会主动推送**
    
    ❌ IWS **不会**发送 webhook 通知
    ✅ 需要**主动轮询**查询状态
    
    ### **轮询间隔**
    
    - 当前设置: **3分钟**
    - 可以调整: 1-5分钟
    - 不建议: 小于1分钟（避免限流）
    
    ### **处理时间**
    
    - 正常情况: **5-10 分钟**
    - 复杂操作: 可能更长
    - 失败情况: 立即返回错误
    
    ---
    
    ## 📞 技术支持
    
    如有问题，请查看：
    - 📋 助理页面的错误信息
    - 🔍 Transaction ID
    - 📧 联系 Iridium 技术支持
    """)
    
    # 系统状态
    st.markdown("---")
    st.subheader("🔧 系统状态")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "后台服务",
            "运行中 ✅" if st.session_state.poller.running else "已停止 ❌"
        )
    
    with col2:
        all_requests = st.session_state.request_store.get_all()
        st.metric("总请求数", len(all_requests))
    
    with col3:
        pending = st.session_state.request_store.get_pending()
        st.metric("待处理", len(pending))
    
    # 控制按钮
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 立即查询所有待处理请求", use_container_width=True):
            if pending:
                with st.spinner(f"正在查询 {len(pending)} 个请求..."):
                    st.session_state.poller._poll_pending_requests()
                st.success("查询完成！")
                st.rerun()
            else:
                st.info("没有待处理的请求")
    
    with col2:
        if st.button("🗑️ 清空所有数据", use_container_width=True, type="secondary"):
            st.session_state.request_store.requests = []
            st.session_state.request_store.save()
            st.success("数据已清空")
            st.rerun()

# ========== 页脚 ==========

st.markdown("---")
st.caption("SBD 管理系统 v6.12.0 - 服务请求追踪演示")
