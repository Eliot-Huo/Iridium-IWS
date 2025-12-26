"""
服務請求追蹤系統 - 完整版
包含後台輪詢機制和助理頁面UI
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

# ========== 設定 ==========

POLLING_INTERVAL = 180  # 3分钟輪詢一次
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# ========== 時間轉換工具 ==========

def utc_to_taipei(utc_time_str: str) -> str:
    """
    將 UTC 時間轉換為台灣時間
    
    Args:
        utc_time_str: UTC 時間字串 (ISO 8601 格式)
        
    Returns:
        台灣時間字串 (YYYY-MM-DD HH:MM:SS)
    """
    if not utc_time_str:
        return ""
    
    try:
        # 解析 UTC 時間
        if utc_time_str.endswith('Z'):
            utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        else:
            utc_time = datetime.fromisoformat(utc_time_str)
        
        # 確保是 UTC 時區
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        
        # 轉換為台灣時間
        taipei_time = utc_time.astimezone(TAIPEI_TZ)
        
        # 格式化輸出
        return taipei_time.strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        return f"轉換失敗: {e}"


def get_current_taipei_time() -> str:
    """取得目前台灣時間"""
    taipei_time = datetime.now(TAIPEI_TZ)
    return taipei_time.strftime('%Y-%m-%d %H:%M:%S')


# ========== 資料模型 ==========

class ServiceRequest:
    """服務請求記錄"""
    
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
                 account_number: Optional[str] = None,
                 reason: Optional[str] = None,
                 new_plan_id: Optional[str] = None):
        
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
        self.reason = reason
        self.new_plan_id = new_plan_id
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
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
            'account_number': self.account_number,
            'reason': self.reason,
            'new_plan_id': self.new_plan_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServiceRequest':
        """從字典創建"""
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
            account_number=data.get('account_number'),
            reason=data.get('reason'),
            new_plan_id=data.get('new_plan_id')
        )


# ========== 持久化儲存 ==========

class RequestStore:
    """服務請求持久化儲存"""
    
    def __init__(self, db_path: str = 'service_requests.json'):
        self.db_path = db_path
        self.requests: List[Dict] = []
        self.load()
    
    def load(self):
        """从文件加載"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.requests = json.load(f)
            except Exception as e:
                print(f"加載失敗: {e}")
                self.requests = []
        else:
            self.requests = []
    
    def save(self):
        """保存到文件"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.requests, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存失敗: {e}")
    
    def add(self, request: ServiceRequest):
        """新增請求"""
        self.requests.append(request.to_dict())
        self.save()
    
    def update(self, request_id: str, updates: Dict):
        """更新請求"""
        for i, req in enumerate(self.requests):
            if req['request_id'] == request_id:
                req.update(updates)
                req['updated_at'] = datetime.now(timezone.utc).isoformat()
                self.requests[i] = req
                self.save()
                break
    
    def get(self, request_id: str) -> Optional[Dict]:
        """取得單個請求"""
        for req in self.requests:
            if req['request_id'] == request_id:
                return req
        return None
    
    def get_all(self) -> List[Dict]:
        """取得所有請求"""
        return self.requests
    
    def get_pending(self) -> List[Dict]:
        """取得待處理的請求"""
        return [
            req for req in self.requests
            if req['status'] in ['SUBMITTED', 'PENDING', 'WORKING']
        ]


# ========== 後台輪詢服務 ==========

class BackgroundPoller:
    """後台輪詢服務（每3分钟查詢一次）"""
    
    def __init__(self, gateway, store: RequestStore):
        self.gateway = gateway
        self.store = store
        self.running = False
        self.thread = None
    
    def start(self):
        """啟動後台輪詢"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.thread.start()
            print("✅ 後台輪詢服務已啟動")
    
    def stop(self):
        """停止後台輪詢"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("⏹️ 後台輪詢服務已停止")
    
    def _poll_loop(self):
        """輪詢循环"""
        while self.running:
            try:
                self._poll_pending_requests()
            except Exception as e:
                print(f"輪詢錯誤: {e}")
            
            # 等待3分钟
            time.sleep(POLLING_INTERVAL)
    
    def _poll_pending_requests(self):
        """查詢所有待處理的請求"""
        pending = self.store.get_pending()
        
        if not pending:
            return
        
        print(f"\n[輪詢] 檢查 {len(pending)} 個待處理請求...")
        
        for request in pending:
            try:
                self._poll_single_request(request)
            except Exception as e:
                print(f"查詢請求 {request['request_id']} 失敗: {e}")
        
        print("[輪詢] 本轮查詢完成\n")
    
    def _poll_single_request(self, request: Dict):
        """查詢單個請求的狀態"""
        transaction_id = request.get('transaction_id')
        
        if not transaction_id:
            print(f"請求 {request['request_id']} 没有 TransactionID")
            return
        
        print(f"[輪詢] 查詢 {request['request_id']} (TXN: {transaction_id})")
        
        try:
            # 查詢佇列狀態
            queue_info = self.gateway.get_queue_entry(transaction_id)
            queue_status = queue_info.get('status')
            
            print(f"  狀態: {request['status']} → {queue_status}")
            
            # 更新狀態
            if queue_status == 'DONE':
                # 驗證最終帳户狀態
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
                # 取得錯誤详情
                error_info = self.gateway.get_iws_request(transaction_id)
                
                self.store.update(request['request_id'], {
                    'status': 'ERROR',
                    'error_message': error_info.get('error_message', '未知錯誤')
                })
                
                print(f"  ❌ 失敗: {error_info.get('error_message')}")
            
            elif queue_status in ['PENDING', 'WORKING']:
                # 更新為處理中
                self.store.update(request['request_id'], {
                    'status': queue_status
                })
                
                print(f"  ⏳ 仍在處理中...")
        
        except Exception as e:
            print(f"  ⚠️  查詢失敗: {e}")


# ========== 助理頁面 UI ==========

def get_operation_text(operation: str) -> str:
    """取得操作类型的中文文字"""
    operation_map = {
        'resume': '恢复設备',
        'suspend': '暂停設备',
        'deactivate': '注销設备',
        'update_plan': '變更资费',
        'activate': '啟動設备'
    }
    return operation_map.get(operation, operation)


def get_status_badge(status: str) -> str:
    """取得狀態徽章 HTML"""
    badge_map = {
        'SUBMITTED': ('📤 已提交', '#6c757d'),
        'PENDING': ('🔄 等待回馈中', '#ffc107'),
        'WORKING': ('⚙️ 處理中', '#17a2b8'),
        'DONE': ('✅ 已确认', '#28a745'),
        'ERROR': ('❌ 失敗', '#dc3545'),
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


def render_assistant_page(store: RequestStore, gateway=None):
    """
    渲染助理頁面（包含財務核准流程）
    
    Args:
        store: 請求儲存
        gateway: IWS Gateway 實例（用於核准後提交）
    """
    
    st.title("👨‍💼 助理工作台")
    
    # 標籤頁
    tab1, tab2 = st.tabs(["📋 待核准請求", "🔍 已提交請求追蹤"])
    
    # ========== 標籤1：待核准請求 ==========
    with tab1:
        st.subheader("📋 待核准的服務請求")
        st.info("客戶提交的請求會顯示在此處，請確認後提交給 Iridium")
        
        # 獲取待核准請求
        all_requests = store.get_all()
        pending_approval = [r for r in all_requests if r['status'] == 'PENDING_APPROVAL']
        
        if not pending_approval:
            st.success("✅ 目前沒有待核准的請求")
        else:
            st.warning(f"⚠️ 有 {len(pending_approval)} 個請求等待核准")
            
            # 顯示每個待核准請求
            for idx, req_dict in enumerate(pending_approval):
                with st.container():
                    st.markdown(f"### 請求 #{idx + 1}")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**客戶編號**: {req_dict['customer_id']}")
                        st.write(f"**客戶名稱**: {req_dict['customer_name']}")
                        st.write(f"**IMEI**: {req_dict['imei']}")
                    
                    with col2:
                        operation_text = get_operation_text(req_dict['operation'])
                        st.write(f"**需求類型**: {operation_text}")
                        
                        if req_dict['operation'] == 'update_plan' and req_dict.get('new_plan_id'):
                            plan_text = {
                                '763925991': 'SBD 0',
                                '763924583': 'SBD 12',
                                '763927911': 'SBD 17',
                                '763925351': 'SBD 30'
                            }.get(req_dict['new_plan_id'], req_dict['new_plan_id'])
                            st.write(f"**新資費方案**: {plan_text}")
                        
                        if req_dict.get('reason'):
                            st.write(f"**原因**: {req_dict['reason']}")
                        
                        submit_time = utc_to_taipei(req_dict['created_at'])
                        st.write(f"**提交時間**: {submit_time}")
                    
                    with col3:
                        # 確認提交按鈕
                        if gateway and st.button(
                            "✅ 確認提交給 IWS",
                            key=f"approve_{req_dict['request_id']}",
                            type="primary",
                            use_container_width=True
                        ):
                            try:
                                with st.spinner("正在提交給 Iridium..."):
                                    result = approve_and_submit_to_iws(
                                        gateway=gateway,
                                        store=store,
                                        request_id=req_dict['request_id'],
                                        assistant_name='assistant001'
                                    )
                                
                                st.success(result['message'])
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"❌ 提交失敗: {str(e)}")
                        
                        if not gateway:
                            st.warning("⚠️ IWS Gateway 未初始化")
                    
                    st.markdown("---")
    
    # ========== 標籤2：已提交請求追蹤 ==========
    with tab2:
        st.subheader("🔍 已提交請求狀態追蹤")
        st.caption("顯示已提交給 Iridium 的請求及其狀態")
        
        # 獲取已提交的請求（排除 PENDING_APPROVAL）
        submitted_requests = [r for r in all_requests if r['status'] != 'PENDING_APPROVAL']
        pending_requests = [r for r in submitted_requests if r['status'] in ['SUBMITTED', 'PENDING', 'WORKING']]
        completed = [r for r in submitted_requests if r['status'] == 'DONE']
        failed = [r for r in submitted_requests if r['status'] == 'ERROR']
        
        # 統計卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("總已提交", len(submitted_requests))
        
        with col2:
            st.metric("處理中", len(pending_requests))
        
        with col3:
            st.metric("已完成", len(completed))
        
        with col4:
            st.metric("失敗", len(failed))
        
        st.markdown("---")
        
        # 篩選器
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            filter_status = st.multiselect(
                "篩選狀態",
                options=['SUBMITTED', 'PENDING', 'WORKING', 'DONE', 'ERROR'],
                default=['SUBMITTED', 'PENDING', 'WORKING']
            )
        
        with col2:
            filter_operation = st.multiselect(
                "篩選操作",
                options=['resume', 'suspend', 'deactivate', 'update_plan'],
                format_func=get_operation_text
            )
        
        with col3:
            search_customer = st.text_input("搜尋客戶編號或名稱")
        
        # 應用篩選
        filtered = submitted_requests
        
        if filter_status:
            filtered = [r for r in filtered if r['status'] in filter_status]
        
        if filter_operation:
            filtered = [r for r in filtered if r['operation'] in filter_operation]
        
        if search_customer:
            filtered = [r for r in filtered if 
                       search_customer.lower() in r['customer_id'].lower() or
                       search_customer.lower() in r['customer_name'].lower()]
    
    # 顯示請求列表（保留原有的顯示邏輯）
    st.markdown("### 📊 服務請求列表")
    
    if not all_requests:
        st.info("📭 暫無服務請求")
        return
    
    # 篩選（此變數已在上面定義，這裡是為了相容）
    # filtered = all_requests
    
    if not filtered:
        st.info("🔍 没有符合篩選条件的請求")
        return
    
    # 按更新時間倒序
    filtered = sorted(filtered, key=lambda x: x.get('updated_at', ''), reverse=True)
    
    # 构建表格資料
    table_data = []
    for req in filtered:
        table_data.append({
            '客户编号': req['customer_id'],
            '客户名称': req['customer_name'],
            '需求名称': get_operation_text(req['operation']),
            'IMEI': req['imei'],
            '目前狀態': req['status'],
            '提交時間': utc_to_taipei(req.get('created_at', '')),
            '生效時間': utc_to_taipei(req.get('completed_at', '')) if req['status'] == 'DONE' else '',
            'Transaction ID': req.get('transaction_id', 'N/A'),
            '資費方案': req.get('plan_name', '') if req['status'] == 'DONE' else '',
            '錯誤信息': req.get('error_message', '') if req['status'] == 'ERROR' else ''
        })
    
    # 顯示表格
    df = pd.DataFrame(table_data)
    
    # 使用自定义样式顯示表格
    for i, row in df.iterrows():
        with st.container():
            # 狀態徽章
            status_html = get_status_badge(filtered[i]['status'])
            
            # 卡片布局
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.markdown(f"**客户**: {row['客户编号']} - {row['客户名称']}")
                st.caption(f"IMEI: {row['IMEI']}")
            
            with col2:
                st.markdown(f"**需求**: {row['需求名称']}")
                if row['資費方案']:
                    st.caption(f"方案: {row['資費方案']}")
            
            with col3:
                st.markdown("**時間**")
                st.caption(f"提交: {row['提交時間']}")
                if row['生效時間']:
                    st.caption(f"✅ 生效: {row['生效時間']}")
            
            with col4:
                st.markdown(status_html, unsafe_allow_html=True)
            
            # 顯示錯誤信息
            if row['錯誤信息']:
                st.error(f"❌ {row['錯誤信息']}")
            
            # Transaction ID（可展开）
            with st.expander("查看详情"):
                st.code(f"Transaction ID: {row['Transaction ID']}")
                st.text(f"請求ID: {filtered[i]['request_id']}")
            
            st.markdown("---")
    
    # 批量操作
    st.markdown("### 🔧 批量操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 立即查詢所有待處理請求", use_container_width=True):
            pending = store.get_pending()
            if pending:
                with st.spinner(f"正在查詢 {len(pending)} 個待處理請求..."):
                    # 這里调用 poller._poll_pending_requests()
                    st.success("查詢完成！")
                    st.rerun()
            else:
                st.info("没有待處理的請求")
    
    with col2:
        if st.button("🗑️ 清除已完成請求", use_container_width=True):
            # 只保留未完成的
            store.requests = [r for r in store.requests if r['status'] != 'DONE']
            store.save()
            st.success("已清除所有已完成的請求")
            st.rerun()
    
    with col3:
        if st.button("📥 導出為 CSV", use_container_width=True):
            df.to_csv('service_requests.csv', index=False, encoding='utf-8-sig')
            st.success("已導出到 service_requests.csv")


# ========== 提交請求工具函数 ==========

def submit_service_request(gateway,
                          store: RequestStore,
                          customer_id: str,
                          customer_name: str,
                          imei: str,
                          operation: str,
                          **kwargs) -> Dict:
    """
    提交服務請求（客戶頁面）
    
    重要：此方法只創建請求記錄，不呼叫 IWS API
    需要由助理在助理頁面確認後才會呼叫 IWS API
    
    Args:
        gateway: IWS Gateway 實例（不在此使用）
        store: 請求儲存
        customer_id: 客戶編號
        customer_name: 客戶名稱
        imei: IMEI
        operation: 操作類型 (resume/suspend/deactivate/update_plan)
        **kwargs: 其他參數
    
    Returns:
        Dict: 請求結果
    """
    
    # 生成請求ID
    request_id = f"REQ-{int(time.time())}"
    
    # 創建請求記錄（狀態：PENDING_APPROVAL）
    request = ServiceRequest(
        request_id=request_id,
        customer_id=customer_id,
        customer_name=customer_name,
        imei=imei,
        operation=operation,
        transaction_id=None,  # 尚未提交給 IWS
        status='PENDING_APPROVAL',  # 等待助理核准
        account_number=None,  # 暫時未知
        plan_name=kwargs.get('new_plan_id') if operation == 'update_plan' else None
    )
    
    # 儲存操作原因和其他參數
    request.reason = kwargs.get('reason', '')
    if operation == 'update_plan':
        request.new_plan_id = kwargs.get('new_plan_id')
    
    # 保存到儲存
    store.add(request)
    
    return {
        'success': True,
        'request_id': request_id,
        'transaction_id': None,  # 尚未提交
        'message': f'✅ 請求已提交\n📋 狀態: 等待助理確認\n🔔 請通知助理在助理頁面確認此請求'
    }


def approve_and_submit_to_iws(gateway,
                               store: RequestStore,
                               request_id: str,
                               assistant_name: str) -> Dict:
    """
    核准請求並提交給 IWS（助理頁面）
    
    此方法由助理在助理頁面呼叫，負責：
    1. 查找帳號
    2. 呼叫對應的 IWS API
    3. 更新請求狀態
    4. 返回結果
    
    Args:
        gateway: IWS Gateway 實例
        store: 請求儲存
        request_id: 請求ID
        assistant_name: 助理名稱
    
    Returns:
        Dict: 提交結果
    """
    
    # 獲取請求（返回 Dict）
    request = store.get(request_id)
    if not request:
        raise Exception(f"未找到請求: {request_id}")
    
    # 檢查狀態
    if request['status'] != 'PENDING_APPROVAL':
        raise Exception(f"請求狀態不正確: {request['status']}，應為 PENDING_APPROVAL")
    
    try:
        # 步驟 1：查找帳號
        print(f"\n[助理確認] 正在查找帳號...")
        search_result = gateway.search_account(request['imei'])
        if not search_result['found']:
            raise Exception(f"未找到 IMEI {request['imei']} 對應的帳號")
        
        account_number = search_result['subscriber_account_number']
        current_status = search_result.get('status', 'UNKNOWN')
        
        # 更新帳號資訊
        request['account_number'] = account_number
        
        # 步驟 2：根據操作類型呼叫 IWS API
        print(f"[助理確認] 正在提交給 IWS...")
        print(f"  操作: {request['operation']}")
        print(f"  IMEI: {request['imei']}")
        print(f"  帳號: {account_number}")
        print(f"  目前狀態: {current_status}")
        
        if request['operation'] == 'resume':
            api_result = gateway.resume_subscriber(
                imei=request['imei'],
                reason=request.get('reason') or '恢復設備'
            )
        
        elif request['operation'] == 'suspend':
            # 檢查是否已經是 SUSPENDED
            if current_status == 'SUSPENDED':
                raise Exception(f"帳號已經是暫停狀態，無需再次暫停")
            api_result = gateway.suspend_subscriber(
                imei=request['imei'],
                reason=request.get('reason') or '暫停設備'
            )
        
        elif request['operation'] == 'deactivate':
            # 檢查是否已經是 DEACTIVATED
            if current_status == 'DEACTIVATED':
                raise Exception(f"帳號已經是註銷狀態，無需再次註銷")
            api_result = gateway.deactivate_subscriber(
                imei=request['imei'],
                reason=request.get('reason') or '註銷設備'
            )
        
        elif request['operation'] == 'update_plan':
            # 智慧處理：如果帳號是 SUSPENDED，先恢復
            if current_status == 'SUSPENDED':
                print(f"[提示] 帳號目前是暫停狀態，將先恢復再更新資費")
                gateway.resume_subscriber(
                    imei=request['imei'],
                    reason='變更資費前自動恢復'
                )
                time.sleep(2)  # 等待恢復生效
            
            # 更新資費
            api_result = gateway.update_subscriber_plan(
                imei=request['imei'],
                new_plan_id=request.get('new_plan_id')
            )
        
        else:
            raise ValueError(f"不支援的操作類型: {request['operation']}")
        
        # 步驟 3：更新請求狀態
        request['transaction_id'] = api_result.get('transaction_id')
        request['status'] = 'SUBMITTED'  # 已提交給 IWS
        request['updated_at'] = datetime.now(timezone.utc).isoformat()
        store.update(request_id, request)
        
        print(f"[助理確認] ✅ 已成功提交給 IWS")
        print(f"  Transaction ID: {request['transaction_id']}")
        
        return {
            'success': True,
            'request_id': request_id,
            'transaction_id': request['transaction_id'],
            'message': (
                f'✅ Iridium 已成功接收請求\n\n'
                f'📋 Transaction ID: {request["transaction_id"]}\n\n'
                f'⏳ **請注意**：Iridium 需要數分鐘處理此請求\n'
                f'🔄 系統會自動每 3 分鐘查詢一次處理狀態\n'
                f'📊 請在「已提交請求追蹤」標籤查看最新狀態'
            )
        }
    
    except Exception as e:
        # 更新為錯誤狀態
        request['status'] = 'ERROR'
        request['error_message'] = str(e)
        request['updated_at'] = datetime.now(timezone.utc).isoformat()
        store.update(request_id, request)
        
        raise Exception(f"提交失敗: {str(e)}")


# ========== 主程序示例 ==========

if __name__ == "__main__":
    # 設置頁面
    st.set_page_config(
        page_title="服務請求追蹤",
        page_icon="📋",
        layout="wide"
    )
    
    # 初始化儲存
    store = RequestStore('service_requests.json')
    
    # 渲染頁面
    render_assistant_page(store)
    
    # 侧边栏：测试工具
    with st.sidebar:
        st.markdown("### 🧪 测试工具")
        
        if st.button("➕ 新增测试請求"):
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
            st.success("已新增")
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
        
        if st.button("❌ 模拟失敗"):
            pending = store.get_pending()
            if pending:
                store.update(pending[0]['request_id'], {
                    'status': 'ERROR',
                    'error_message': '設备不存在'
                })
                st.success("已失敗")
                st.rerun()
