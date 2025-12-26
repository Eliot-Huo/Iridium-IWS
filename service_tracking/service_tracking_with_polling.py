"""
服务请求追踪系统 - 完整版
包含后台轮询机制和助理页面UI
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
from typing import Dict, List, Optional
import time
import threading
import json
import os

# ========== 配置 ==========

POLLING_INTERVAL = 180  # 3分钟轮询一次
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# ========== 时间转换工具 ==========

def utc_to_taipei(utc_time_str: str) -> str:
    """
    将 UTC 时间转换为台湾时间
    
    Args:
        utc_time_str: UTC 时间字符串 (ISO 8601 格式)
        
    Returns:
        台湾时间字符串 (YYYY-MM-DD HH:MM:SS)
    """
    if not utc_time_str:
        return ""
    
    try:
        # 解析 UTC 时间
        if utc_time_str.endswith('Z'):
            utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        else:
            utc_time = datetime.fromisoformat(utc_time_str)
        
        # 确保是 UTC 时区
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        
        # 转换为台湾时间
        taipei_time = utc_time.astimezone(TAIPEI_TZ)
        
        # 格式化输出
        return taipei_time.strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        return f"转换失败: {e}"


def get_current_taipei_time() -> str:
    """获取当前台湾时间"""
    taipei_time = datetime.now(TAIPEI_TZ)
    return taipei_time.strftime('%Y-%m-%d %H:%M:%S')


# ========== 数据模型 ==========

class ServiceRequest:
    """服务请求记录"""
    
    def __init__(self,
                 request_id: str,
                 customer_id: str,
                 customer_name: str,
                 imei: str,
                 operation: str,
                 transaction_id: Optional[str] = None,
                 status: str = 'SUBMITTED',
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None,
                 completed_at: Optional[datetime] = None,
                 error_message: Optional[str] = None,
                 plan_name: Optional[str] = None,
                 account_number: Optional[str] = None):
        
        self.request_id = request_id
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.imei = imei
        self.operation = operation
        self.transaction_id = transaction_id
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.completed_at = completed_at
        self.error_message = error_message
        self.plan_name = plan_name
        self.account_number = account_number
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'request_id': self.request_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'imei': self.imei,
            'operation': self.operation,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'plan_name': self.plan_name,
            'account_number': self.account_number
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServiceRequest':
        """从字典创建"""
        return cls(
            request_id=data['request_id'],
            customer_id=data['customer_id'],
            customer_name=data['customer_name'],
            imei=data['imei'],
            operation=data['operation'],
            transaction_id=data.get('transaction_id'),
            status=data.get('status', 'SUBMITTED'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error_message=data.get('error_message'),
            plan_name=data.get('plan_name'),
            account_number=data.get('account_number')
        )


# ========== 持久化存储 ==========

class RequestStore:
    """服务请求持久化存储"""
    
    def __init__(self, db_path: str = 'service_requests.json'):
        self.db_path = db_path
        self.requests: List[Dict] = []
        self.load()
    
    def load(self):
        """从文件加载"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.requests = json.load(f)
            except Exception as e:
                print(f"加载失败: {e}")
                self.requests = []
        else:
            self.requests = []
    
    def save(self):
        """保存到文件"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.requests, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存失败: {e}")
    
    def add(self, request: ServiceRequest):
        """添加请求"""
        self.requests.append(request.to_dict())
        self.save()
    
    def update(self, request_id: str, updates: Dict):
        """更新请求"""
        for i, req in enumerate(self.requests):
            if req['request_id'] == request_id:
                req.update(updates)
                req['updated_at'] = datetime.now(timezone.utc).isoformat()
                self.requests[i] = req
                self.save()
                break
    
    def get(self, request_id: str) -> Optional[Dict]:
        """获取单个请求"""
        for req in self.requests:
            if req['request_id'] == request_id:
                return req
        return None
    
    def get_all(self) -> List[Dict]:
        """获取所有请求"""
        return self.requests
    
    def get_pending(self) -> List[Dict]:
        """获取待处理的请求"""
        return [
            req for req in self.requests
            if req['status'] in ['SUBMITTED', 'PENDING', 'WORKING']
        ]


# ========== 后台轮询服务 ==========

class BackgroundPoller:
    """后台轮询服务（每3分钟查询一次）"""
    
    def __init__(self, gateway, store: RequestStore):
        self.gateway = gateway
        self.store = store
        self.running = False
        self.thread = None
    
    def start(self):
        """启动后台轮询"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.thread.start()
            print("✅ 后台轮询服务已启动")
    
    def stop(self):
        """停止后台轮询"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("⏹️ 后台轮询服务已停止")
    
    def _poll_loop(self):
        """轮询循环"""
        while self.running:
            try:
                self._poll_pending_requests()
            except Exception as e:
                print(f"轮询错误: {e}")
            
            # 等待3分钟
            time.sleep(POLLING_INTERVAL)
    
    def _poll_pending_requests(self):
        """查询所有待处理的请求"""
        pending = self.store.get_pending()
        
        if not pending:
            return
        
        print(f"\n[轮询] 检查 {len(pending)} 个待处理请求...")
        
        for request in pending:
            try:
                self._poll_single_request(request)
            except Exception as e:
                print(f"查询请求 {request['request_id']} 失败: {e}")
        
        print("[轮询] 本轮查询完成\n")
    
    def _poll_single_request(self, request: Dict):
        """查询单个请求的状态"""
        transaction_id = request.get('transaction_id')
        
        if not transaction_id:
            print(f"请求 {request['request_id']} 没有 TransactionID")
            return
        
        print(f"[轮询] 查询 {request['request_id']} (TXN: {transaction_id})")
        
        try:
            # 查询队列状态
            queue_info = self.gateway.get_queue_entry(transaction_id)
            queue_status = queue_info.get('status')
            
            print(f"  状态: {request['status']} → {queue_status}")
            
            # 更新状态
            if queue_status == 'DONE':
                # 验证最终账户状态
                account_info = self.gateway.get_subscriber_account(
                    request['account_number']
                )
                
                self.store.update(request['request_id'], {
                    'status': 'DONE',
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'plan_name': account_info.get('plan_name', '')
                })
                
                print(f"  ✅ 已完成！")
            
            elif queue_status == 'ERROR':
                # 获取错误详情
                error_info = self.gateway.get_iws_request(transaction_id)
                
                self.store.update(request['request_id'], {
                    'status': 'ERROR',
                    'error_message': error_info.get('error_message', '未知错误')
                })
                
                print(f"  ❌ 失败: {error_info.get('error_message')}")
            
            elif queue_status in ['PENDING', 'WORKING']:
                # 更新为处理中
                self.store.update(request['request_id'], {
                    'status': queue_status
                })
                
                print(f"  ⏳ 仍在处理中...")
        
        except Exception as e:
            print(f"  ⚠️  查询失败: {e}")


# ========== 助理页面 UI ==========

def get_operation_text(operation: str) -> str:
    """获取操作类型的中文文字"""
    operation_map = {
        'resume': '恢复设备',
        'suspend': '暂停设备',
        'deactivate': '注销设备',
        'update_plan': '变更资费',
        'activate': '启动设备'
    }
    return operation_map.get(operation, operation)


def get_status_badge(status: str) -> str:
    """获取状态徽章 HTML"""
    badge_map = {
        'SUBMITTED': ('📤 已提交', '#6c757d'),
        'PENDING': ('🔄 等待回馈中', '#ffc107'),
        'WORKING': ('⚙️ 处理中', '#17a2b8'),
        'DONE': ('✅ 已确认', '#28a745'),
        'ERROR': ('❌ 失败', '#dc3545'),
        'TIMEOUT': ('⏰ 超时', '#fd7e14')
    }
    
    text, color = badge_map.get(status, ('❓ 未知', '#6c757d'))
    
    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
    ">{text}</span>
    """


def render_assistant_page(store: RequestStore):
    """渲染助理页面"""
    
    st.title("📋 服务请求追踪")
    
    # 顶部信息栏
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"**当前时间**: {get_current_taipei_time()} (台湾时间)")
        st.caption("每3分钟自动查询待处理请求的状态")
    
    with col2:
        if st.button("🔄 立即刷新"):
            st.rerun()
    
    with col3:
        auto_refresh = st.toggle("自动刷新页面", value=False)
        if auto_refresh:
            time.sleep(30)
            st.rerun()
    
    st.markdown("---")
    
    # 统计卡片
    all_requests = store.get_all()
    pending_requests = store.get_pending()
    completed = [r for r in all_requests if r['status'] == 'DONE']
    failed = [r for r in all_requests if r['status'] == 'ERROR']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总请求数", len(all_requests))
    
    with col2:
        st.metric("待处理", len(pending_requests), 
                 delta=f"{len(pending_requests)} 个正在查询中" if pending_requests else None)
    
    with col3:
        st.metric("已完成", len(completed))
    
    with col4:
        st.metric("失败", len(failed))
    
    st.markdown("---")
    
    # 筛选器
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_status = st.multiselect(
            "筛选状态",
            options=['SUBMITTED', 'PENDING', 'WORKING', 'DONE', 'ERROR'],
            default=['PENDING', 'WORKING']
        )
    
    with col2:
        filter_operation = st.multiselect(
            "筛选操作",
            options=['resume', 'suspend', 'deactivate', 'update_plan', 'activate'],
            format_func=get_operation_text
        )
    
    with col3:
        search_customer = st.text_input("搜索客户编号或名称")
    
    # 显示请求列表（表格形式）
    st.markdown("### 📊 服务请求列表")
    
    if not all_requests:
        st.info("📭 暂无服务请求")
        return
    
    # 筛选
    filtered = all_requests
    
    if filter_status:
        filtered = [r for r in filtered if r['status'] in filter_status]
    
    if filter_operation:
        filtered = [r for r in filtered if r['operation'] in filter_operation]
    
    if search_customer:
        filtered = [
            r for r in filtered
            if search_customer.lower() in r['customer_id'].lower() or
               search_customer.lower() in r['customer_name'].lower()
        ]
    
    if not filtered:
        st.info("🔍 没有符合筛选条件的请求")
        return
    
    # 按更新时间倒序
    filtered = sorted(filtered, key=lambda x: x.get('updated_at', ''), reverse=True)
    
    # 构建表格数据
    table_data = []
    for req in filtered:
        table_data.append({
            '客户编号': req['customer_id'],
            '客户名称': req['customer_name'],
            '需求名称': get_operation_text(req['operation']),
            'IMEI': req['imei'],
            '目前状态': req['status'],
            '提交时间': utc_to_taipei(req.get('created_at', '')),
            '生效时间': utc_to_taipei(req.get('completed_at', '')) if req['status'] == 'DONE' else '',
            'Transaction ID': req.get('transaction_id', 'N/A'),
            '费率方案': req.get('plan_name', '') if req['status'] == 'DONE' else '',
            '错误信息': req.get('error_message', '') if req['status'] == 'ERROR' else ''
        })
    
    # 显示表格
    df = pd.DataFrame(table_data)
    
    # 使用自定义样式显示表格
    for i, row in df.iterrows():
        with st.container():
            # 状态徽章
            status_html = get_status_badge(filtered[i]['status'])
            
            # 卡片布局
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.markdown(f"**客户**: {row['客户编号']} - {row['客户名称']}")
                st.caption(f"IMEI: {row['IMEI']}")
            
            with col2:
                st.markdown(f"**需求**: {row['需求名称']}")
                if row['费率方案']:
                    st.caption(f"方案: {row['费率方案']}")
            
            with col3:
                st.markdown("**时间**")
                st.caption(f"提交: {row['提交时间']}")
                if row['生效时间']:
                    st.caption(f"✅ 生效: {row['生效时间']}")
            
            with col4:
                st.markdown(status_html, unsafe_allow_html=True)
            
            # 显示错误信息
            if row['错误信息']:
                st.error(f"❌ {row['错误信息']}")
            
            # Transaction ID（可展开）
            with st.expander("查看详情"):
                st.code(f"Transaction ID: {row['Transaction ID']}")
                st.text(f"请求ID: {filtered[i]['request_id']}")
            
            st.markdown("---")
    
    # 批量操作
    st.markdown("### 🔧 批量操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 立即查询所有待处理请求", use_container_width=True):
            pending = store.get_pending()
            if pending:
                with st.spinner(f"正在查询 {len(pending)} 个待处理请求..."):
                    # 这里调用 poller._poll_pending_requests()
                    st.success("查询完成！")
                    st.rerun()
            else:
                st.info("没有待处理的请求")
    
    with col2:
        if st.button("🗑️ 清除已完成请求", use_container_width=True):
            # 只保留未完成的
            store.requests = [r for r in store.requests if r['status'] != 'DONE']
            store.save()
            st.success("已清除所有已完成的请求")
            st.rerun()
    
    with col3:
        if st.button("📥 导出为 CSV", use_container_width=True):
            df.to_csv('service_requests.csv', index=False, encoding='utf-8-sig')
            st.success("已导出到 service_requests.csv")


# ========== 提交请求工具函数 ==========

def submit_service_request(gateway,
                          store: RequestStore,
                          customer_id: str,
                          customer_name: str,
                          imei: str,
                          operation: str,
                          **kwargs) -> Dict:
    """
    提交服务请求
    
    Args:
        gateway: IWS Gateway 实例
        store: 请求存储
        customer_id: 客户编号
        customer_name: 客户名称
        imei: IMEI
        operation: 操作类型 (resume/suspend/deactivate/update_plan)
        **kwargs: 其他参数
    
    Returns:
        Dict: 请求结果
    """
    
    # 生成请求ID
    request_id = f"REQ-{int(time.time())}"
    
    # 先查找账号
    search_result = gateway.search_account(imei)
    if not search_result['found']:
        raise Exception(f"未找到 IMEI {imei} 对应的账号")
    
    account_number = search_result['subscriber_account_number']
    
    # 根据操作类型调用不同的 API
    if operation == 'resume':
        api_result = gateway.resume_subscriber(imei=imei, reason=kwargs.get('reason', '恢复设备'))
    elif operation == 'suspend':
        api_result = gateway.suspend_subscriber(imei=imei, reason=kwargs.get('reason', '暂停设备'))
    elif operation == 'deactivate':
        api_result = gateway.deactivate_subscriber(imei=imei, reason=kwargs.get('reason', '注销设备'))
    elif operation == 'update_plan':
        api_result = gateway.update_subscriber_plan(
            imei=imei,
            new_plan_id=kwargs.get('new_plan_id')
        )
    else:
        raise ValueError(f"不支持的操作类型: {operation}")
    
    # 创建请求记录
    request = ServiceRequest(
        request_id=request_id,
        customer_id=customer_id,
        customer_name=customer_name,
        imei=imei,
        operation=operation,
        transaction_id=api_result.get('transaction_id'),
        status='SUBMITTED',
        account_number=account_number
    )
    
    # 保存到存储
    store.add(request)
    
    return {
        'success': True,
        'request_id': request_id,
        'transaction_id': api_result.get('transaction_id'),
        'message': f'✅ 已正确传递要求给 Iridium\n状态: 🔄 正在等待回馈中'
    }


# ========== 主程序示例 ==========

if __name__ == "__main__":
    # 设置页面
    st.set_page_config(
        page_title="服务请求追踪",
        page_icon="📋",
        layout="wide"
    )
    
    # 初始化存储
    store = RequestStore('service_requests.json')
    
    # 渲染页面
    render_assistant_page(store)
    
    # 侧边栏：测试工具
    with st.sidebar:
        st.markdown("### 🧪 测试工具")
        
        if st.button("➕ 添加测试请求"):
            test_req = ServiceRequest(
                request_id=f"REQ-{int(time.time())}",
                customer_id=f"C{int(time.time()) % 1000:03d}",
                customer_name="测试客户",
                imei="300534066711380",
                operation="resume",
                transaction_id=f"TXN-{int(time.time())}",
                status="PENDING",
                account_number="SUB-52830841655"
            )
            store.add(test_req)
            st.success("已添加")
            st.rerun()
        
        if st.button("✅ 模拟完成"):
            pending = store.get_pending()
            if pending:
                store.update(pending[0]['request_id'], {
                    'status': 'DONE',
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'plan_name': 'SBD 12'
                })
                st.success("已完成")
                st.rerun()
        
        if st.button("❌ 模拟失败"):
            pending = store.get_pending()
            if pending:
                store.update(pending[0]['request_id'], {
                    'status': 'ERROR',
                    'error_message': '设备不存在'
                })
                st.success("已失败")
                st.rerun()
