# 🔄 IWS 异步操作架构设计

## 💡 **业务现实**

### **实际操作流程**

根据用户反馈，通过 SPNet Pro 手动启动 IMEI 的实际流程：

```
1. 提交启动请求
   ↓
2. 系统接受请求（可能立即响应或超时）
   ↓
3. 后台处理：5-10 分钟
   ↓
4. 收到邮件：设定成功/失败
```

**关键发现**：
- ⏳ 操作需要 **5-10 分钟**
- 📧 通过**邮件**通知最终结果
- ✅ 这是**异步**操作，不是同步

---

## ❌ **当前架构的问题**

### **同步模式（不适合）**

```python
def resume_subscriber(self, imei: str) -> Dict:
    # 发送请求
    response = self._send_soap_request(...)
    # 期望立即得到最终结果
    return {'success': True}  # ← 实际上只是"已接受"
```

**问题**：
1. ❌ 30 秒超时太短（实际需要 5-10 分钟）
2. ❌ 超时被视为失败（实际上可能成功）
3. ❌ 无法追踪后台处理状态
4. ❌ 用户体验差（不知道是否完成）

---

## ✅ **正确的架构设计**

### **模式 1: 提交-轮询模式（推荐）**

#### **流程设计**

```
阶段 1: 提交请求
┌─────────────────────────────────────────┐
│ 1. 提交操作请求                          │
│    result = api.submit_resume(imei)     │
│                                         │
│ 2. 立即返回                             │
│    {'status': 'SUBMITTED',              │
│     'request_id': 'REQ-123',            │
│     'imei': '300434067857940'}          │
└─────────────────────────────────────────┘
          ↓
阶段 2: 状态轮询
┌─────────────────────────────────────────┐
│ while True:                             │
│   status = api.check_status(imei)       │
│   if status == 'ACTIVE':                │
│     break  # 成功                       │
│   elif status == 'ERROR':               │
│     raise Error  # 失败                 │
│   sleep(30)  # 等待 30 秒后重试         │
└─────────────────────────────────────────┘
          ↓
阶段 3: 完成
┌─────────────────────────────────────────┐
│ 返回最终结果                            │
│ {'status': 'COMPLETED',                 │
│  'final_status': 'ACTIVE'}              │
└─────────────────────────────────────────┘
```

#### **代码实现**

```python
def resume_subscriber_async(self, 
                           imei: str,
                           reason: str = "恢复设备",
                           wait_for_completion: bool = True,
                           max_wait_time: int = 600,  # 10 分钟
                           poll_interval: int = 30) -> Dict:
    """
    异步恢复设备（适合 5-10 分钟的后台处理）
    
    Args:
        imei: 设备 IMEI
        reason: 恢复原因
        wait_for_completion: 是否等待完成
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
        
    Returns:
        Dict: {
            'status': 'SUBMITTED'/'COMPLETED'/'TIMEOUT',
            'request_id': 请求ID,
            'final_status': 'ACTIVE'/'PENDING'/'ERROR',
            'message': 状态说明
        }
    """
    
    # 阶段 1: 提交请求（允许超时）
    print(f"[IWS] 提交恢复请求: {imei}")
    
    try:
        # 发送请求，不期望立即完成
        action_name, soap_body = self._build_set_subscriber_account_status_body(
            imei=imei,
            new_status="ACTIVE",
            reason=reason
        )
        
        # 使用较长的超时（或处理超时异常）
        try:
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body,
                timeout=60  # 增加到 60 秒
            )
            request_submitted = True
        except TimeoutError:
            # 超时不代表失败，可能是请求已被接受
            print("[IWS] 请求超时，但可能已被系统接受")
            request_submitted = True  # 假设已提交
        
        result = {
            'status': 'SUBMITTED',
            'imei': imei,
            'operation': 'resume',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # 如果不等待完成，立即返回
        if not wait_for_completion:
            result['message'] = "请求已提交，需要 5-10 分钟处理"
            return result
        
        # 阶段 2: 等待完成（轮询状态）
        print(f"[IWS] 等待操作完成（最多 {max_wait_time} 秒）...")
        
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < max_wait_time:
            # 检查当前状态
            try:
                status_info = self.check_account_status(imei)
                current_status = status_info.get('status')
                
                # 状态变化时输出
                if current_status != last_status:
                    print(f"[IWS] 当前状态: {current_status}")
                    last_status = current_status
                
                # 检查是否完成
                if current_status == 'ACTIVE':
                    result.update({
                        'status': 'COMPLETED',
                        'final_status': 'ACTIVE',
                        'message': '设备已成功恢复',
                        'elapsed_time': int(time.time() - start_time)
                    })
                    print(f"[IWS] ✅ 操作完成！耗时: {result['elapsed_time']} 秒")
                    return result
                
                elif current_status not in ['PENDING', 'SUSPENDED']:
                    # 意外状态
                    result.update({
                        'status': 'ERROR',
                        'final_status': current_status,
                        'message': f'意外状态: {current_status}'
                    })
                    return result
                
            except Exception as e:
                print(f"[IWS] 状态检查失败: {e}")
            
            # 等待后重试
            print(f"[IWS] 等待 {poll_interval} 秒后重试...")
            time.sleep(poll_interval)
        
        # 超时
        result.update({
            'status': 'TIMEOUT',
            'final_status': last_status or 'UNKNOWN',
            'message': f'操作超时（{max_wait_time} 秒），请稍后检查状态',
            'elapsed_time': max_wait_time
        })
        print(f"[IWS] ⏰ 操作超时，但可能仍在处理中")
        return result
        
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': str(e),
            'imei': imei
        }


def check_account_status(self, imei: str) -> Dict:
    """
    检查账号当前状态
    
    Returns:
        Dict: {
            'status': 'ACTIVE'/'PENDING'/'SUSPENDED'/'DEACTIVATED',
            'plan_name': 方案名称,
            'last_updated': 最后更新时间,
            'can_update': 是否可以更新
        }
    """
    try:
        # 使用 accountSearch 获取状态
        action_name, soap_body = self._build_account_search_body(imei)
        response_xml = self._send_soap_request(
            soap_action=action_name,
            soap_body=soap_body
        )
        
        # 解析响应
        root = ET.fromstring(response_xml)
        subscribers = root.findall('.//subscriber')
        
        for subscriber in subscribers:
            imei_elem = subscriber.find('.//imei')
            if imei_elem is not None and imei_elem.text == imei:
                status_elem = subscriber.find('.//accountStatus')
                plan_elem = subscriber.find('.//planName')
                updated_elem = subscriber.find('.//lastUpdated')
                
                status = status_elem.text if status_elem is not None else 'UNKNOWN'
                
                return {
                    'status': status,
                    'plan_name': plan_elem.text if plan_elem is not None else 'N/A',
                    'last_updated': updated_elem.text if updated_elem is not None else 'N/A',
                    'can_update': status not in ['PENDING', 'DEACTIVATED'],
                    'imei': imei
                }
        
        raise IWSException(f"Account not found for IMEI: {imei}")
        
    except Exception as e:
        raise IWSException(f"Failed to check account status: {e}")
```

---

### **模式 2: 任务队列模式（高级）**

#### **架构设计**

```
用户请求
    ↓
┌─────────────────────────────────────┐
│ Web API / Streamlit UI              │
│   - 创建任务                         │
│   - 返回任务 ID                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 任务队列（Celery / Redis）          │
│   - 异步执行                         │
│   - 状态追踪                         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ IWS Gateway                         │
│   - 调用 API                         │
│   - 轮询状态                         │
│   - 更新任务状态                     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 数据库                              │
│   - 任务记录                         │
│   - 状态历史                         │
└─────────────────────────────────────┘
    ↑
┌─────────────────────────────────────┐
│ 用户查询任务状态                     │
│   GET /tasks/{task_id}              │
└─────────────────────────────────────┘
```

#### **数据模型**

```python
class ServiceRequest(BaseModel):
    """服务请求记录"""
    request_id: str          # 请求 ID
    imei: str               # 设备 IMEI
    operation: str          # resume/suspend/update
    status: str             # SUBMITTED/PROCESSING/COMPLETED/FAILED
    created_at: datetime    # 创建时间
    updated_at: datetime    # 更新时间
    completed_at: Optional[datetime]  # 完成时间
    error_message: Optional[str]      # 错误信息
    
class StatusHistory(BaseModel):
    """状态历史"""
    request_id: str
    timestamp: datetime
    old_status: str
    new_status: str
    message: str
```

---

## 🎨 **Streamlit UI 设计**

### **用户体验流程**

#### **方案 A: 等待模式（推荐用于单个操作）**

```python
import streamlit as st
import time

def resume_device_ui():
    st.title("恢复设备")
    
    imei = st.text_input("IMEI")
    reason = st.text_area("恢复原因")
    
    if st.button("提交恢复请求"):
        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 提交请求
        status_text.text("⏳ 正在提交请求...")
        result = gateway.resume_subscriber_async(
            imei=imei,
            reason=reason,
            wait_for_completion=False  # 先提交
        )
        
        if result['status'] != 'SUBMITTED':
            st.error(f"提交失败: {result['message']}")
            return
        
        status_text.text("✅ 请求已提交，正在处理...")
        
        # 轮询状态
        max_iterations = 20  # 10 分钟（30秒 x 20）
        for i in range(max_iterations):
            progress = (i + 1) / max_iterations
            progress_bar.progress(progress)
            
            # 检查状态
            status_info = gateway.check_account_status(imei)
            current_status = status_info['status']
            
            status_text.text(f"当前状态: {current_status} ({i*30} 秒)")
            
            if current_status == 'ACTIVE':
                st.success("✅ 设备已成功恢复！")
                st.balloons()
                return
            elif current_status not in ['PENDING', 'SUSPENDED']:
                st.error(f"❌ 意外状态: {current_status}")
                return
            
            time.sleep(30)
        
        st.warning("⏰ 操作超时，但可能仍在处理中。请稍后检查设备状态。")
```

#### **方案 B: 任务追踪模式（推荐用于批量操作）**

```python
def batch_operations_ui():
    st.title("批量操作")
    
    # 上传 CSV 或输入多个 IMEI
    imeis = st.text_area("IMEI 列表（每行一个）").split('\n')
    operation = st.selectbox("操作", ["恢复", "暂停", "变更费率"])
    
    if st.button("提交批量操作"):
        # 创建任务
        tasks = []
        for imei in imeis:
            task_id = create_task(
                operation=operation,
                imei=imei
            )
            tasks.append(task_id)
        
        st.success(f"已创建 {len(tasks)} 个任务")
        st.info("任务将在后台处理，您可以在'任务状态'页面查看进度")
        
        # 存储任务 ID 到 session state
        st.session_state['current_tasks'] = tasks

def task_status_ui():
    st.title("任务状态")
    
    if 'current_tasks' in st.session_state:
        tasks = st.session_state['current_tasks']
        
        # 自动刷新
        if st.button("刷新状态"):
            st.rerun()
        
        # 显示任务状态
        for task_id in tasks:
            status = get_task_status(task_id)
            
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.text(f"任务 {task_id}")
            with col2:
                if status['status'] == 'COMPLETED':
                    st.success("✅ 完成")
                elif status['status'] == 'PROCESSING':
                    st.info("⏳ 处理中...")
                elif status['status'] == 'FAILED':
                    st.error("❌ 失败")
            with col3:
                st.text(f"{status['elapsed_time']}s")
```

---

## 📊 **最佳实践建议**

### **1. 超时设置**

```python
# 不同环境的超时配置
TIMEOUTS = {
    'training': {
        'submit': 60,      # 提交请求超时
        'poll': 30,        # 轮询间隔
        'max_wait': 600    # 最大等待时间（10分钟）
    },
    'production': {
        'submit': 30,
        'poll': 15,
        'max_wait': 300    # 可能更快
    }
}
```

### **2. 错误处理**

```python
def handle_timeout(imei: str, operation: str):
    """
    处理超时情况
    """
    return {
        'status': 'TIMEOUT',
        'message': (
            f"{operation} 操作已提交但响应超时。"
            f"这是正常的，操作可能仍在后台处理中。"
            f"请在 5-10 分钟后检查设备状态。"
        ),
        'next_steps': [
            "等待 5-10 分钟",
            f"运行: check_account_status('{imei}')",
            "如果长时间未完成，联系技术支持"
        ]
    }
```

### **3. 用户通知**

```python
def send_completion_notification(imei: str, status: str):
    """
    操作完成后通知用户
    （可以通过邮件、Slack、数据库等）
    """
    if status == 'ACTIVE':
        # 发送成功通知
        send_email(
            subject=f"设备 {imei} 已成功恢复",
            body=f"设备 {imei} 的恢复操作已完成"
        )
```

---

## 🎯 **推荐实施方案**

### **阶段 1: 基础异步支持（立即）**

1. 实现 `resume_subscriber_async()` 方法
2. 实现 `check_account_status()` 方法
3. 在 Streamlit 中使用进度条

### **阶段 2: 任务追踪（1-2 周）**

1. 添加数据库表（ServiceRequest, StatusHistory）
2. 实现任务创建和查询 API
3. 批量操作支持

### **阶段 3: 高级功能（1-3 个月）**

1. Celery 任务队列
2. 邮件/Slack 通知
3. 详细的操作日志

---

## 📝 **总结**

### **关键发现**

✅ IWS 操作是异步的，需要 **5-10 分钟**  
✅ 不应期望立即响应  
✅ 超时不等于失败  
✅ 需要轮询状态确认完成  

### **架构调整**

❌ 旧模式：同步等待（30秒超时）  
✅ 新模式：提交-轮询（5-10分钟）  

### **用户体验**

❌ 旧体验：超时 = 失败  
✅ 新体验：进度追踪 + 状态更新  

---

**这个发现对整个架构设计至关重要！感谢您分享实际业务经验！** 🙏
