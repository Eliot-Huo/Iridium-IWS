"""
SBD 服務業務邏輯（已整合 IWS Gateway）
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from ..models.models import ServiceRequest, ActionType, RequestStatus
from ..repositories.repo import InMemoryRepository
from ..config.constants import RATE_PLANS, ACTIVATION_FEE
from ..infrastructure.iws_gateway import IWSGateway, IWSException


class SBDService:
    """SBD 服務類別"""
    
    def __init__(self, repository: InMemoryRepository, iws_gateway: Optional[IWSGateway] = None):
        """
        初始化 SBD 服務
        
        Args:
            repository: 資料儲存庫（依賴注入）
            iws_gateway: IWS 閘道器（可選，用於測試時注入 mock）
        """
        self._repository = repository
        self._iws_gateway = iws_gateway
    
    def _get_iws_gateway(self) -> Optional[IWSGateway]:
        """
        取得 IWS Gateway 實例
        
        Returns:
            Optional[IWSGateway]: IWS Gateway 或 None（如果未配置）
        """
        if self._iws_gateway is not None:
            return self._iws_gateway
        
        try:
            return IWSGateway()
        except ValueError:
            # IWS 未配置，返回 None
            return None
    
    def create_activation_request(
        self, 
        imei: str, 
        plan_id: str, 
        requester: str
    ) -> ServiceRequest:
        """
        建立啟用請求
        
        Args:
            imei: IMEI 號碼
            plan_id: 資費方案 ID (必須存在於 RATE_PLANS 中)
            requester: 請求者名稱
            
        Returns:
            ServiceRequest: 建立的服務請求
            
        Raises:
            ValueError: 當 plan_id 不存在時
        """
        # 驗證資費方案
        if plan_id not in RATE_PLANS:
            raise ValueError(f"Invalid plan_id: {plan_id}. Available plans: {list(RATE_PLANS.keys())}")
        
        # 計算總金額：啟用費 + 月租費
        plan_fee = RATE_PLANS[plan_id]
        total_amount = ACTIVATION_FEE + plan_fee
        
        # 生成請求 ID
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        request_id = f"ACT-{imei[-6:]}-{timestamp}"
        
        # 建立服務請求
        request = ServiceRequest(
            request_id=request_id,
            imei=imei,
            action_type=ActionType.ACTIVATE,
            plan_id=plan_id,
            amount_due=total_amount,
            status=RequestStatus.PENDING_FINANCE,
            notes=f"Requested by {requester}"
        )
        
        # 儲存至 Repository
        self._repository.save_request(request)
        
        return request
    
    def create_suspend_request(
        self, 
        imei: str, 
        requester: str
    ) -> ServiceRequest:
        """
        建立暫停服務請求
        
        Args:
            imei: IMEI 號碼
            requester: 請求者名稱
            
        Returns:
            ServiceRequest: 建立的服務請求
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        request_id = f"SUS-{imei[-6:]}-{timestamp}"
        
        request = ServiceRequest(
            request_id=request_id,
            imei=imei,
            action_type=ActionType.SUSPEND,
            plan_id="N/A",
            amount_due=MONTHLY_SUSPENDED_FEE,
            status=RequestStatus.PENDING_FINANCE,
            notes=f"Requested by {requester}"
        )
        
        self._repository.save_request(request)
        return request
    
    def create_resume_request(
        self, 
        imei: str, 
        plan_id: str,
        requester: str
    ) -> ServiceRequest:
        """
        建立恢復服務請求
        
        Args:
            imei: IMEI 號碼
            plan_id: 資費方案 ID
            requester: 請求者名稱
            
        Returns:
            ServiceRequest: 建立的服務請求
        """
        if plan_id not in RATE_PLANS:
            raise ValueError(f"Invalid plan_id: {plan_id}")
        
        plan_fee = RATE_PLANS[plan_id]
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        request_id = f"RES-{imei[-6:]}-{timestamp}"
        
        request = ServiceRequest(
            request_id=request_id,
            imei=imei,
            action_type=ActionType.RESUME,
            plan_id=plan_id,
            amount_due=plan_fee,
            status=RequestStatus.PENDING_FINANCE,
            notes=f"Requested by {requester}"
        )
        
        self._repository.save_request(request)
        return request
    
    def process_finance_approval(
        self, 
        request_id: str, 
        assistant_name: str,
        execute_iws: bool = True
    ) -> Optional[ServiceRequest]:
        """
        處理財務核准並自動觸發 IWS 執行
        
        工作流程：
        1. 驗證請求狀態 (必須為 PENDING_FINANCE)
        2. 核准請求 → 狀態變更為 APPROVED
        3. 初始化 IWSGateway
        4. 根據請求類型呼叫對應的 IWS 方法
        5. 成功：寫入 TransactionID，狀態變更為 EXECUTED
        6. 失敗：記錄錯誤，保持 APPROVED 狀態供人工介入
        
        Args:
            request_id: 請求 ID
            assistant_name: 助理名稱
            execute_iws: 是否自動執行 IWS（預設 True）
            
        Returns:
            ServiceRequest: 更新後的服務請求，若請求不存在則回傳 None
            
        Raises:
            ValueError: 當請求狀態不是 PENDING_FINANCE 時
            IWSException: 當 IWS 執行失敗時（已記錄錯誤，保持 APPROVED 狀態）
        """
        # ========== 步驟 1: 驗證請求 ==========
        request = self._repository.get_request(request_id)
        
        if request is None:
            return None
        
        if request.status != RequestStatus.PENDING_FINANCE:
            raise ValueError(
                f"Request {request_id} cannot be approved. "
                f"Current status: {request.status.value}, expected: pending_finance"
            )
        
        # ========== 步驟 2: 核准請求 (狀態 → APPROVED) ==========
        request.approve(assistant_name)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        request.notes = (request.notes or '') + f" | Approved by {assistant_name} at {timestamp}"
        
        # 如果不需要執行 IWS，直接儲存並返回
        if not execute_iws:
            self._repository.save_request(request)
            return request
        
        # ========== 步驟 3: 初始化 IWSGateway ==========
        try:
            iws_gateway = self._get_iws_gateway()
            
            if iws_gateway is None:
                # IWS 未配置，僅更新狀態為 APPROVED，需要人工執行
                request.notes += " | ⚠️ IWS not configured - Manual execution required"
                self._repository.save_request(request)
                return request
            
            # ========== 步驟 4: 根據請求類型呼叫對應的 IWS 方法 ==========
            result = None
            
            if request.action_type == ActionType.ACTIVATE:
                result = iws_gateway.activate_device(request.imei, request.plan_id)
                
            elif request.action_type == ActionType.SUSPEND:
                result = iws_gateway.suspend_device(request.imei)
                
            elif request.action_type == ActionType.RESUME:
                result = iws_gateway.resume_device(request.imei)
                
            else:
                raise ValueError(f"Unknown action type: {request.action_type}")
            
            # ========== 步驟 5: IWS 成功 - 更新狀態為 EXECUTED ==========
            if result:
                # 提取 TransactionID
                transaction_id = result.get('transaction_id')
                execution_timestamp = result.get('timestamp', datetime.now())
                
                # 執行請求（狀態 → EXECUTED）
                request.execute()
                
                # 記錄 TransactionID 和執行資訊
                request.notes += (
                    f" | ✅ IWS Executed Successfully"
                    f" | TransactionID: {transaction_id}"
                    f" | Action: {request.action_type.value}"
                    f" | IMEI: {request.imei}"
                    f" | Timestamp: {execution_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # 儲存成功執行的請求
                self._repository.save_request(request)
                return request
            
        except IWSException as e:
            # ========== 步驟 6: IWS 失敗 - 保持 APPROVED 狀態 ==========
            error_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'UNKNOWN')
            response_text = getattr(e, 'response_text', None)
            
            # 記錄詳細的錯誤資訊（包含完整 response_text）
            request.notes += (
                f" | ❌ IWS Execution Failed"
                f" | Error Code: {error_code}"
                f" | Error: {error_msg}"
                f" | Timestamp: {error_timestamp}"
                f" | Status: APPROVED (requires manual intervention)"
            )
            
            # 如果有 response_text，記錄完整內容（用於除錯）
            if response_text:
                # 截斷過長的 response（保留前 1000 字元）
                truncated_response = response_text[:1000] if len(response_text) > 1000 else response_text
                request.notes += f" | 📝 Full Response: {truncated_response}"
                
                if len(response_text) > 1000:
                    request.notes += " ... (truncated)"
            
            # 儲存失敗狀態（保持 APPROVED）
            self._repository.save_request(request)
            
            # 重新拋出異常，讓呼叫者知道 IWS 執行失敗
            raise IWSException(
                f"IWS execution failed for request {request_id}. "
                f"Request remains in APPROVED status for manual intervention. "
                f"Error: {error_msg}",
                error_code=error_code
            )
            
        except ValueError as e:
            # 未知的操作類型
            error_msg = str(e)
            request.notes += f" | ❌ Invalid Action Type: {error_msg}"
            self._repository.save_request(request)
            raise
            
        except Exception as e:
            # 其他未預期的錯誤
            error_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_msg = str(e)
            
            request.notes += (
                f" | ❌ Unexpected Error"
                f" | Error: {error_msg}"
                f" | Timestamp: {error_timestamp}"
                f" | Status: APPROVED (requires manual intervention)"
            )
            
            # 儲存錯誤狀態
            self._repository.save_request(request)
            
            # 包裝為 IWSException
            raise IWSException(
                f"Unexpected error during IWS execution for request {request_id}: {error_msg}"
            )
        
        # 正常情況下不應該到達這裡
        self._repository.save_request(request)
        return request
    
    def get_request(self, request_id: str) -> Optional[ServiceRequest]:
        """取得請求"""
        return self._repository.get_request(request_id)
    
    def get_requests_by_imei(self, imei: str) -> list:
        """依 IMEI 取得所有請求"""
        return self._repository.get_requests_by_imei(imei)
    
    def list_pending_requests(self) -> list:
        """列出所有待核准請求"""
        return [
            req for req in self._repository.list_all_requests()
            if req.status == RequestStatus.PENDING_FINANCE
        ]
