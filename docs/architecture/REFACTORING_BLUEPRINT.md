# SBD v6.45.0 - Clean Architecture 重構藍圖

## 📐 架構設計原則

### **分層架構（Layered Architecture）**
```
┌─────────────────────────────────────┐
│     Presentation Layer (UI)         │  ← Streamlit Pages/Components
├─────────────────────────────────────┤
│     Service Layer (Business Logic)  │  ← 業務邏輯協調
├─────────────────────────────────────┤
│     Repository Layer (Data Access)  │  ← 資料存取抽象
├─────────────────────────────────────┤
│     Infrastructure Layer (External) │  ← IWS API, FTP, GDrive
├─────────────────────────────────────┤
│     Domain Layer (Core Business)    │  ← 領域模型與規則
└─────────────────────────────────────┘
```

---

## 📁 新目錄結構

```
SBD-Refactored-v6.45.0/
├── src/
│   ├── domain/                    # 領域層（核心業務）
│   │   ├── __init__.py
│   │   ├── subscriber.py          # ✅ 已實作
│   │   ├── dsg_group.py           # 待實作
│   │   ├── tracker.py             # 待實作
│   │   └── billing.py             # 待實作
│   │
│   ├── repositories/              # Repository 層（資料存取）
│   │   ├── __init__.py
│   │   ├── base_repository.py    # ✅ 已實作
│   │   ├── subscriber_repository.py
│   │   ├── dsg_repository.py
│   │   ├── cdr_repository.py
│   │   └── profile_repository.py
│   │
│   ├── services/                  # Service 層（業務邏輯）
│   │   ├── __init__.py
│   │   ├── subscriber_service.py
│   │   ├── dsg_service.py
│   │   ├── billing_service.py
│   │   └── cdr_service.py
│   │
│   ├── infrastructure/            # 基礎設施層（外部系統）
│   │   ├── __init__.py
│   │   ├── iws_client.py         # IWS API 客戶端
│   │   ├── ftp_client.py
│   │   └── gdrive_client.py
│   │
│   ├── ui/                        # UI 層（展示）
│   │   ├── pages/
│   │   │   ├── assistant/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dsg_management.py
│   │   │   │   ├── device_management.py
│   │   │   │   └── billing_query.py
│   │   │   ├── customer/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── device_request.py
│   │   │   │   └── dsg_query.py
│   │   │   └── shared/
│   │   │       └── billing_query.py
│   │   └── components/           # UI 元件
│   │       ├── forms.py
│   │       ├── tables.py
│   │       └── charts.py
│   │
│   ├── config/                    # 設定
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── constants.py
│   │   └── price_profile.py
│   │
│   ├── models/                    # 資料傳輸物件（DTO）
│   │   ├── __init__.py
│   │   ├── requests.py
│   │   └── responses.py
│   │
│   └── utils/                     # 工具
│       ├── __init__.py
│       ├── exceptions.py         # ✅ 已實作
│       ├── types.py              # ✅ 已實作
│       ├── validators.py
│       └── helpers.py
│
├── tests/                         # 測試
│   ├── unit/
│   │   ├── domain/
│   │   ├── repositories/
│   │   └── services/
│   └── integration/
│       ├── api/
│       └── database/
│
├── docs/                          # 文檔
│   ├── architecture/
│   │   ├── CLEAN_ARCHITECTURE.md
│   │   └── LAYER_DESIGN.md
│   ├── api/
│   │   └── IWS_API_GUIDE.md
│   └── guides/
│       ├── DEVELOPMENT.md
│       └── TESTING.md
│
├── app.py                         # 主入口
├── requirements.txt
└── README.md
```

---

## 🔄 重構步驟

### **Phase 1: 基礎設施（已完成 ✅）**
- [x] 建立目錄結構
- [x] 定義自訂例外 (`src/utils/exceptions.py`)
- [x] 定義型別 (`src/utils/types.py`)
- [x] 建立 BaseRepository (`src/repositories/base_repository.py`)
- [x] 建立 Subscriber Domain Model (`src/domain/subscriber.py`)

### **Phase 2: Infrastructure Layer**
```python
# src/infrastructure/iws_client.py
class IWSClient:
    """
    IWS API 客戶端
    
    職責：
    - 管理 SOAP 連線
    - 處理認證
    - 執行 API 呼叫
    - 處理錯誤和重試
    
    不包含：
    - 業務邏輯
    - 資料轉換
    - 快取管理
    """
    
    def __init__(self, config: IWSConfig):
        self._config = config
        self._client = None
    
    def connect(self) -> None:
        """建立連線"""
        ...
    
    def call_api(self, method: str, **params) -> Dict[str, Any]:
        """呼叫 API"""
        ...
```

### **Phase 3: Repository Layer**
```python
# src/repositories/subscriber_repository.py
class SubscriberRepository(BaseRepository[Subscriber, IMEI]):
    """
    訂戶 Repository
    
    職責：
    - 透過 IWS API 查詢訂戶
    - 將 API 回應轉換為 Domain Model
    - 管理快取
    
    不包含：
    - 業務邏輯
    - 狀態轉換邏輯
    """
    
    def __init__(self, iws_client: IWSClient):
        super().__init__()
        self._client = iws_client
    
    def find_by_id(self, imei: IMEI) -> Optional[Subscriber]:
        """查詢訂戶"""
        # 1. 檢查快取
        # 2. 呼叫 API
        # 3. 轉換為 Domain Model
        # 4. 加入快取
        ...
    
    def save(self, subscriber: Subscriber) -> Subscriber:
        """儲存訂戶（更新狀態）"""
        # 1. 驗證
        # 2. 呼叫對應的 IWS API
        # 3. 更新快取
        ...
```

### **Phase 4: Service Layer**
```python
# src/services/subscriber_service.py
class SubscriberService:
    """
    訂戶服務
    
    職責：
    - 協調業務流程
    - 執行業務規則
    - 管理交易
    
    不包含：
    - API 呼叫細節
    - UI 邏輯
    """
    
    def __init__(self, repository: SubscriberRepository):
        self._repo = repository
    
    def activate_subscriber(
        self, 
        imei: IMEI, 
        plan_id: PlanID,
        reason: str
    ) -> Subscriber:
        """
        啟用訂戶
        
        業務流程：
        1. 查詢訂戶
        2. 檢查是否可啟用
        3. 執行啟用
        4. 記錄操作
        5. 儲存變更
        """
        # 1. 查詢
        subscriber = self._repo.find_by_id(imei)
        if not subscriber:
            raise SubscriberNotFoundError(f"找不到 IMEI: {imei}")
        
        # 2. 業務規則檢查
        if not subscriber.can_activate():
            raise InvalidSubscriberStateError(
                f"訂戶狀態 {subscriber.status} 無法啟用"
            )
        
        # 3. 執行業務邏輯（在 Domain Model 中）
        subscriber.activate()
        
        # 4. 儲存
        return self._repo.save(subscriber)
```

### **Phase 5: UI Layer**
```python
# src/ui/pages/assistant/device_management.py
def render_device_management_page(
    subscriber_service: SubscriberService
) -> None:
    """
    設備管理頁面
    
    職責：
    - 渲染 UI
    - 處理使用者輸入
    - 呼叫 Service
    - 顯示結果
    
    不包含：
    - 業務邏輯
    - API 呼叫
    - 資料驗證（除了 UI 層級的基本驗證）
    """
    st.header("設備管理")
    
    with st.form("activate_form"):
        imei = st.text_input("IMEI")
        plan = st.selectbox("方案", ["SBD-12", "SBD-17"])
        reason = st.text_area("原因")
        
        if st.form_submit_button("啟用"):
            try:
                # 只呼叫 Service，不包含業務邏輯
                subscriber = subscriber_service.activate_subscriber(
                    imei=imei,
                    plan_id=plan,
                    reason=reason
                )
                st.success(f"✅ 訂戶 {imei} 已啟用")
            
            except SubscriberNotFoundError as e:
                st.error(f"❌ {e.message}")
            
            except InvalidSubscriberStateError as e:
                st.warning(f"⚠️ {e.message}")
            
            except Exception as e:
                st.error(f"❌ 系統錯誤: {e}")
```

---

## 🎯 依賴注入模式

### **app.py - 主入口**
```python
# app.py
import streamlit as st
from src.infrastructure.iws_client import IWSClient
from src.repositories.subscriber_repository import SubscriberRepository
from src.services.subscriber_service import SubscriberService
from src.ui.pages.assistant.device_management import render_device_management_page

def init_dependencies():
    """初始化依賴"""
    # 1. Infrastructure
    iws_client = IWSClient(
        config=IWSConfig(
            endpoint=st.secrets['IWS_ENDPOINT'],
            username=st.secrets['IWS_USERNAME'],
            password=st.secrets['IWS_PASSWORD'],
            sp_account=st.secrets['IWS_SP_ACCOUNT']
        )
    )
    
    # 2. Repositories
    subscriber_repo = SubscriberRepository(iws_client)
    
    # 3. Services
    subscriber_service = SubscriberService(subscriber_repo)
    
    return {
        'subscriber_service': subscriber_service
    }

def main():
    st.set_page_config(page_title="SBD 管理系統")
    
    # 初始化依賴
    deps = init_dependencies()
    
    # 路由
    page = st.sidebar.selectbox("選擇功能", ["設備管理", "費用查詢"])
    
    if page == "設備管理":
        render_device_management_page(deps['subscriber_service'])
```

---

## ✅ 重構完成的好處

### **1. 可測試性**
```python
# tests/unit/services/test_subscriber_service.py
def test_activate_subscriber():
    # Mock Repository
    mock_repo = Mock(spec=SubscriberRepository)
    mock_repo.find_by_id.return_value = Subscriber(...)
    
    # 建立 Service（注入 Mock）
    service = SubscriberService(mock_repo)
    
    # 測試
    result = service.activate_subscriber("123456789012345", "SBD-12", "測試")
    
    assert result.is_active()
    mock_repo.save.assert_called_once()
```

### **2. 可維護性**
- 每個層級職責清晰
- 修改不影響其他層級
- 易於理解和修改

### **3. 可擴展性**
- 新增功能只需實作對應層級
- 可輕易替換底層實作（例如改用 REST API）
- 支援多種資料源

### **4. 程式碼品質**
- 完整型別提示
- 清晰的錯誤處理
- 統一的命名規範
- 完整的文檔

---

## 📝 遷移計劃

### **優先順序**
1. **High Priority**: Subscriber 管理
2. **Medium Priority**: DSG 管理
3. **Low Priority**: CDR 處理

### **漸進式遷移**
```
Week 1: 建立新架構骨架
Week 2: 遷移 Subscriber 模組
Week 3: 遷移 DSG 模組
Week 4: 遷移 Billing 模組
Week 5: 遷移 CDR 模組
Week 6: 測試與優化
```

---

## 🎓 學習資源

### **Clean Architecture**
- Uncle Bob's Clean Architecture
- Domain-Driven Design (DDD)
- SOLID Principles

### **Python 最佳實踐**
- PEP 8 Style Guide
- Type Hints (PEP 484)
- Dataclasses (PEP 557)

---

**版本：** v6.45.0  
**日期：** 2026-01-06  
**狀態：** 架構設計階段
