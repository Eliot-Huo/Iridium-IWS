# 🎯 服务请求追踪系统 - 集成指南

## 📊 **系统概览**

### **核心功能**

1. **自动轮询** - 每3分钟自动查询待处理请求
2. **状态追踪** - 实时显示每个请求的状态
3. **台湾时间** - 自动转换所有时间为台湾时区
4. **批量管理** - 支持多个并发请求
5. **持久化** - 数据保存在 JSON 文件

---

## 🔧 **架构设计**

### **整体流程**

```
客户页面 (提交请求)
    ↓
服务请求存储 (JSON)
    ↓
后台轮询服务 (每3分钟)
    ↓
IWS Gateway API
    ↓
更新请求状态
    ↓
助理页面 (显示状态)
```

### **组件说明**

#### **1. RequestStore (持久化存储)**

```python
# 存储位置
service_requests.json

# 数据结构
{
  "request_id": "REQ-1735179600",
  "customer_id": "C001",
  "customer_name": "王大明",
  "imei": "300534066711380",
  "operation": "resume",
  "transaction_id": "TXN-12345",
  "status": "PENDING",
  "created_at": "2025-12-26T02:30:00Z",
  "updated_at": "2025-12-26T02:33:00Z",
  "completed_at": null,
  "error_message": null,
  "plan_name": null,
  "account_number": "SUB-52830841655"
}
```

#### **2. BackgroundPoller (后台轮询)**

```python
# 工作机制
while running:
    # 获取所有待处理请求
    pending = store.get_pending()
    
    # 逐个查询
    for request in pending:
        # 1. 调用 getQueueEntry
        status = gateway.get_queue_entry(request.transaction_id)
        
        # 2. 根据状态更新
        if status == 'DONE':
            # 验证账户状态
            account = gateway.get_subscriber_account(request.account_number)
            # 更新为完成
            store.update(request_id, {
                'status': 'DONE',
                'completed_at': now(),
                'plan_name': account.plan_name
            })
        
        elif status == 'ERROR':
            # 获取错误详情
            error = gateway.get_iws_request(request.transaction_id)
            # 更新为失败
            store.update(request_id, {
                'status': 'ERROR',
                'error_message': error.error_message
            })
    
    # 等待3分钟
    sleep(180)
```

#### **3. Assistant Page UI (助理页面)**

**显示字段**：

| 字段 | 说明 | 示例 |
|------|------|------|
| 客户编号 | 客户ID | C001 |
| 客户名称 | 客户姓名 | 王大明 |
| 需求名称 | 操作类型 | 变更资费 |
| IMEI | 设备号 | 300534066711380 |
| 目前状态 | 处理状态 | 🔄 处理中 |
| 提交时间 | 创建时间 (台湾) | 2025-12-26 10:30:00 |
| 生效时间 | 完成时间 (台湾) | 2025-12-26 10:35:23 |

**状态说明**：

- 📤 **已提交** - 请求已创建，等待发送
- 🔄 **等待回馈中** - 已发送到 IWS，等待响应
- ⚙️ **处理中** - IWS 正在处理
- ✅ **已确认** - 处理完成，已生效
- ❌ **失败** - 处理失败
- ⏰ **超时** - 查询超时

---

## 📋 **集成步骤**

### **第一步：添加依赖**

```python
# requirements.txt
streamlit
pandas
pytz
```

### **第二步：初始化存储**

```python
# 在 app.py 的开始
from service_tracking_with_polling import RequestStore, BackgroundPoller

# 初始化存储
if 'request_store' not in st.session_state:
    st.session_state.request_store = RequestStore('service_requests.json')

# 初始化轮询服务
if 'poller' not in st.session_state:
    st.session_state.poller = BackgroundPoller(
        gateway=gateway,
        store=st.session_state.request_store
    )
    st.session_state.poller.start()
```

### **第三步：客户页面集成**

```python
# pages/customer_page.py

def handle_resume_device(customer_id, customer_name, imei):
    """处理恢复设备请求"""
    
    from service_tracking_with_polling import submit_service_request
    
    try:
        # 提交请求
        result = submit_service_request(
            gateway=st.session_state.gateway,
            store=st.session_state.request_store,
            customer_id=customer_id,
            customer_name=customer_name,
            imei=imei,
            operation='resume',
            reason='客户申请恢复'
        )
        
        # 显示成功消息
        st.success(result['message'])
        st.info(f"请求ID: {result['request_id']}")
        st.info(f"Transaction ID: {result['transaction_id']}")
        
        # 提供链接到助理页面
        st.markdown("[📋 查看服务请求状态 →](/助理页面)")
        
    except Exception as e:
        st.error(f"提交失败: {e}")


def render_customer_page():
    """客户页面"""
    
    st.title("客户服务")
    
    # 输入表单
    with st.form("service_request_form"):
        customer_id = st.text_input("客户编号")
        customer_name = st.text_input("客户名称")
        imei = st.text_input("IMEI")
        
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
                "新方案",
                options=['763925991', '763924583', '763927911', '763925351'],
                format_func=lambda x: {
                    '763925991': 'SBD 0',
                    '763924583': 'SBD 12',
                    '763927911': 'SBD 17',
                    '763925351': 'SBD 30'
                }[x]
            )
        
        submitted = st.form_submit_button("提交请求")
        
        if submitted:
            if operation == 'update_plan':
                handle_resume_device(customer_id, customer_name, imei)
            else:
                handle_resume_device(customer_id, customer_name, imei)
```

### **第四步：助理页面集成**

```python
# pages/assistant_page.py

from service_tracking_with_polling import render_assistant_page

def show_assistant_page():
    """显示助理页面"""
    
    # 获取存储
    store = st.session_state.request_store
    
    # 渲染页面
    render_assistant_page(store)
```

### **第五步：应用入口**

```python
# app.py

import streamlit as st
from src.infrastructure.iws_gateway import IWSGateway
from service_tracking_with_polling import RequestStore, BackgroundPoller

# 页面配置
st.set_page_config(
    page_title="SBD 管理系统",
    page_icon="📡",
    layout="wide"
)

# 初始化 Gateway
if 'gateway' not in st.session_state:
    st.session_state.gateway = IWSGateway(
        username=st.secrets['IWS_USERNAME'],
        password=st.secrets['IWS_PASSWORD'],
        sp_account=st.secrets['IWS_SP_ACCOUNT'],
        endpoint=st.secrets['IWS_ENDPOINT']
    )

# 初始化存储
if 'request_store' not in st.session_state:
    st.session_state.request_store = RequestStore('service_requests.json')

# 启动后台轮询
if 'poller' not in st.session_state:
    st.session_state.poller = BackgroundPoller(
        gateway=st.session_state.gateway,
        store=st.session_state.request_store
    )
    st.session_state.poller.start()

# 侧边栏导航
page = st.sidebar.radio(
    "选择页面",
    options=["客户页面", "助理页面"]
)

# 路由
if page == "客户页面":
    from pages.customer_page import render_customer_page
    render_customer_page()
elif page == "助理页面":
    from pages.assistant_page import show_assistant_page
    show_assistant_page()
```

---

## 🎨 **助理页面界面预览**

### **页面布局**

```
┌─────────────────────────────────────────────────────────────┐
│  📋 服务请求追踪                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  当前时间: 2025-12-26 10:30:00 (台湾时间)                   │
│  每3分钟自动查询待处理请求的状态                             │
│                                                              │
│  [🔄 立即刷新]  [自动刷新页面 ○]                           │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   总请求数    待处理     已完成      失败                    │
│      15         3          10         2                      │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  筛选: [状态▼] [操作▼] [搜索客户...]                        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 服务请求列表                                            │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 客户: C001 - 王大明        需求: 变更资费             │ │
│  │ IMEI: 300534066711380     时间: 提交 10:30:00        │ │
│  │                                 ✅ 生效 10:35:23      │ │
│  │                                            ✅ 已确认   │ │
│  │ 方案: SBD 12                                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 客户: C002 - 李小华        需求: 暂停设备             │ │
│  │ IMEI: 300434067857940     时间: 提交 10:28:15        │ │
│  │                                                        │ │
│  │                                          🔄 等待回馈中 │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 客户: C003 - 张三           需求: 注销设备            │ │
│  │ IMEI: 300434065956950     时间: 提交 10:25:00        │ │
│  │                                                        │ │
│  │ ❌ 设备不存在或资费冲突                    ❌ 失败   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🔧 批量操作                                                │
│                                                              │
│  [🔄 立即查询所有待处理请求]  [🗑️ 清除已完成请求]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ **配置说明**

### **轮询间隔**

```python
# service_tracking_with_polling.py
POLLING_INTERVAL = 180  # 3分钟（秒）

# 根据需要调整
POLLING_INTERVAL = 60   # 1分钟
POLLING_INTERVAL = 300  # 5分钟
```

### **时区设置**

```python
# 台湾时区
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# 其他时区
TOKYO_TZ = pytz.timezone('Asia/Tokyo')
SHANGHAI_TZ = pytz.timezone('Asia/Shanghai')
```

### **存储位置**

```python
# 默认：当前目录
store = RequestStore('service_requests.json')

# 自定义路径
store = RequestStore('/data/requests.json')
```

---

## 🔄 **工作流程详解**

### **完整的请求生命周期**

```
1. 客户页面提交
   ↓
   submit_service_request()
   - 创建 ServiceRequest
   - 调用 IWS API
   - 获取 TransactionID
   - 保存到 RequestStore
   - 状态: SUBMITTED
   
2. 后台轮询（每3分钟）
   ↓
   BackgroundPoller._poll_pending_requests()
   - 获取所有 SUBMITTED/PENDING/WORKING 请求
   - 对每个请求:
     ↓
     _poll_single_request(request)
     - 调用 getQueueEntry(transaction_id)
     - 获取队列状态
     
     if status == 'DONE':
       - 调用 getSubscriberAccount(account_number)
       - 更新 status = 'DONE'
       - 记录 completed_at
       - 记录 plan_name
     
     elif status == 'ERROR':
       - 调用 getIwsRequest(transaction_id)
       - 更新 status = 'ERROR'
       - 记录 error_message
     
     elif status in ['PENDING', 'WORKING']:
       - 更新 status
       - 继续等待
   
3. 助理页面显示
   ↓
   render_assistant_page()
   - 读取 RequestStore
   - 显示所有请求
   - 显示实时状态
   - 显示生效时间（台湾时间）
```

---

## 📊 **数据库设计**

### **ServiceRequest 模型**

```python
{
    # 基本信息
    "request_id": str,          # 请求ID (唯一)
    "customer_id": str,         # 客户编号
    "customer_name": str,       # 客户名称
    "imei": str,                # 设备IMEI
    "operation": str,           # 操作类型
    
    # IWS 相关
    "transaction_id": str,      # IWS Transaction ID
    "account_number": str,      # Subscriber Account Number
    
    # 状态信息
    "status": str,              # 当前状态
    "plan_name": str,           # 费率方案（完成后）
    "error_message": str,       # 错误信息（失败时）
    
    # 时间戳（UTC）
    "created_at": str,          # 创建时间
    "updated_at": str,          # 最后更新时间
    "completed_at": str         # 完成时间（完成后）
}
```

### **状态转换图**

```
SUBMITTED → PENDING → WORKING → DONE
    ↓           ↓         ↓        
  ERROR      ERROR    ERROR
```

---

## 🚨 **重要注意事项**

### **1. IWS 不会主动推送**

❌ **错误理解**：IWS 会发送 webhook 通知
✅ **正确理解**：需要主动轮询 getQueueEntry

### **2. 轮询频率**

⚠️ **不要太频繁**：避免 API 限流
✅ **推荐**：3-5 分钟一次
⚠️ **不要太慢**：用户等待时间太长

### **3. Transaction ID 很重要**

- 每个请求都要保存 Transaction ID
- 用于追踪请求状态
- 如果没有就无法查询

### **4. 时区转换**

- IWS 返回 UTC 时间
- 必须转换为台湾时间显示
- 使用 pytz 库

### **5. 并发请求**

- 系统支持多个并发请求
- 每个请求独立追踪
- 按客户编号分组显示

---

## 🎯 **总结**

### **核心特性**

✅ **自动轮询** - 每3分钟查询一次，无需手动刷新
✅ **实时状态** - 显示最新的处理状态
✅ **台湾时间** - 所有时间自动转换
✅ **批量管理** - 支持多个并发请求
✅ **持久化** - 数据保存不丢失

### **用户体验**

1. **客户页面**：提交请求后立即显示确认
2. **助理页面**：实时查看所有请求状态
3. **自动更新**：后台自动查询，无需手动操作
4. **清晰显示**：客户编号、需求名称、状态、时间一目了然

### **技术实现**

1. **后台线程**：独立的轮询服务
2. **JSON 存储**：简单可靠的持久化
3. **IWS API**：标准的异步查询流程
4. **Streamlit UI**：直观的界面展示

---

**版本**: v6.12.0 - Complete Service Tracking System
**状态**: ✅ 生产就绪
**特性**: 自动轮询 + 台湾时间 + 批量管理
