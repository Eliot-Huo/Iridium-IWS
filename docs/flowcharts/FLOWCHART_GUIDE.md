# 📊 IWS 操作流程圖說明

本文檔包含 IWS Gateway v6.9 的三個核心操作流程：
1. **變更費率** (update_subscriber_plan)
2. **暫停設備** (suspend_subscriber)
3. **註銷設備** (deactivate_subscriber)

---

## 📁 流程圖檔案

### **1. 完整流程圖** - `iws_operations_flowchart.mermaid`
詳細的流程圖，包含：
- 所有驗證步驟
- 錯誤處理路徑
- 狀態檢查
- 成功和失敗終點

**使用場景**：完整理解操作流程，包括所有可能的錯誤情況

---

### **2. 簡化流程圖** - `iws_operations_simple.mermaid`
簡化的成功路徑流程圖，只顯示：
- 主要步驟
- 成功路徑
- 關鍵 API 調用

**使用場景**：快速了解操作的主要步驟

---

### **3. 狀態轉換圖** - `device_state_diagram.mermaid`
設備狀態生命週期圖，顯示：
- RESERVED → ACTIVE → SUSPENDED
- 各狀態可執行的操作
- 狀態轉換條件

**使用場景**：理解設備狀態和允許的操作

---

## 🔄 流程詳解

### **1. 變更費率流程** 💱

```mermaid
變更費率
    ↓
驗證 IMEI 格式
    ↓
validateDeviceString (檢查歸屬權)
    ↓
accountSearch (查詢訂閱者帳號)
    ↓
accountUpdate (更新費率)
    ↓
成功 ✅
```

**關鍵步驟**：

| 步驟 | API/方法 | 目的 | 可能錯誤 |
|------|---------|------|----------|
| 1 | 格式驗證 | 確認 IMEI 15位數字 | IMEI 格式錯誤 |
| 2 | validateDeviceString | 確認設備屬於 SP 帳戶 | 設備不屬於帳戶 |
| 3 | accountSearch | 查詢 subscriberAccountNumber | 設備未啟動 (RESERVED) |
| 4 | accountUpdate | 更新費率方案 | HTTP 500 |

**必要條件**：
- ✅ 設備必須屬於您的 Device Pool
- ✅ 設備狀態必須是 **ACTIVE**
- ✅ 必須有 subscriberAccountNumber

**常見錯誤**：
```
❌ "Account not found for IMEI"
   → 設備處於 RESERVED 狀態（未啟動）
   → 需要先啟動設備

❌ "Device does not belong to account"
   → 設備不在您的 Device Pool
   → 使用其他設備
```

---

### **2. 暫停設備流程** ⏸️

```mermaid
暫停設備
    ↓
驗證 IMEI 格式
    ↓
validateDeviceString (檢查歸屬權)
    ↓
檢查設備狀態 (必須是 ACTIVE)
    ↓
setSubscriberAccountStatus (SUSPENDED)
    ↓
成功 ✅
```

**關鍵步驟**：

| 步驟 | API/方法 | 目的 | 可能錯誤 |
|------|---------|------|----------|
| 1 | 格式驗證 | 確認 IMEI 15位數字 | IMEI 格式錯誤 |
| 2 | validateDeviceString | 確認設備屬於 SP 帳戶 | 設備不屬於帳戶 |
| 3 | 狀態檢查 | 確認設備是 ACTIVE | 設備未啟動/已暫停 |
| 4 | setSubscriberAccountStatus | 設定為 SUSPENDED | HTTP 500 |

**必要條件**：
- ✅ 設備必須屬於您的 Device Pool
- ✅ 設備狀態必須是 **ACTIVE**
- ❌ RESERVED 狀態無法暫停
- ❌ 已經 SUSPENDED 的設備無需重複操作

**狀態變化**：
```
ACTIVE → SUSPENDED
```

**常見錯誤**：
```
❌ "Invalid state for device"
   → 設備不是 ACTIVE 狀態
   → 檢查設備當前狀態
```

---

### **3. 註銷設備流程** 🗑️

```mermaid
註銷設備
    ↓
驗證 IMEI 格式
    ↓
validateDeviceString (檢查歸屬權)
    ↓
檢查設備狀態 (ACTIVE 或 SUSPENDED)
    ↓
setSubscriberAccountStatus (DEACTIVATED)
    ↓
IMEI 立即釋放，恢復 RESERVED ✅
```

**關鍵步驟**：

| 步驟 | API/方法 | 目的 | 可能錯誤 |
|------|---------|------|----------|
| 1 | 格式驗證 | 確認 IMEI 15位數字 | IMEI 格式錯誤 |
| 2 | validateDeviceString | 確認設備屬於 SP 帳戶 | 設備不屬於帳戶 |
| 3 | 狀態檢查 | 確認設備是 ACTIVE/SUSPENDED | 設備未啟動 |
| 4 | setSubscriberAccountStatus | 設定為 DEACTIVATED | HTTP 500 |

**必要條件**：
- ✅ 設備必須屬於您的 Device Pool
- ✅ 設備狀態必須是 **ACTIVE** 或 **SUSPENDED**
- ❌ RESERVED 狀態無需註銷

**狀態變化**：
```
ACTIVE/SUSPENDED → RESERVED (立即釋放)
```

**重要特性**：
- ✅ **IMEI 立即釋放**
- ✅ 可以**重新啟動**同一設備
- ✅ 適合測試啟動功能

**用途**：
```python
# 準備測試設備
gateway.deactivate_subscriber(imei, "準備測試")
# → 設備變為 RESERVED 狀態

# 現在可以測試啟動
gateway.activate_subscriber(imei, plan_id, ...)
```

---

## 📊 設備狀態生命週期

```
┌─────────────────────────────────────────────────┐
│           設備狀態轉換                            │
└─────────────────────────────────────────────────┘

RESERVED (預留)
    │
    │ activateSubscriber
    ↓
ACTIVE (已啟動)
    │
    ├─→ update_subscriber_plan → ACTIVE (費率已變更)
    │
    ├─→ suspend_subscriber → SUSPENDED
    │
    └─→ deactivate_subscriber → RESERVED
    
SUSPENDED (暫停)
    │
    ├─→ resume_subscriber → ACTIVE
    │
    └─→ deactivate_subscriber → RESERVED
```

### **各狀態允許的操作**

| 狀態 | 允許操作 | 不允許操作 |
|------|---------|-----------|
| **RESERVED** | • activateSubscriber<br>• validateDeviceString | • update_subscriber_plan<br>• suspend_subscriber<br>• resume_subscriber<br>• deactivate_subscriber |
| **ACTIVE** | • update_subscriber_plan<br>• suspend_subscriber<br>• deactivate_subscriber<br>• accountSearch<br>• validateDeviceString | • activateSubscriber<br>• resume_subscriber |
| **SUSPENDED** | • resume_subscriber<br>• deactivate_subscriber<br>• validateDeviceString | • activateSubscriber<br>• update_subscriber_plan<br>• suspend_subscriber |

---

## 🔍 錯誤處理策略

### **v6.9 的智能錯誤處理**

**原則**：
- ✅ **IWS 成功** → 自動更新狀態為 EXECUTED
- ❌ **IWS 失敗** → 保持 APPROVED 狀態，需人工介入

**實現**：
```python
try:
    # 執行 IWS 操作
    result = iws_gateway.update_subscriber_plan(...)
    
    # 成功 → 自動更新為 EXECUTED
    request.execute()
    request.notes += f" | ✅ TransactionID: {result['transaction_id']}"
    
except IWSException as e:
    # 失敗 → 保持 APPROVED，記錄錯誤
    request.notes += f" | ❌ Error: {str(e)}"
    # 狀態仍為 APPROVED，等待人工處理
```

**好處**：
1. 成功的操作自動完成
2. 失敗的操作不會丟失
3. 人工可以查看錯誤原因並重試

---

## 💡 最佳實踐

### **1. 操作前驗證**

```python
# 始終先驗證設備
validation = gateway.validate_device_string(imei, "IMEI", True)

if not validation['valid']:
    print(f"❌ {validation['reason']}")
    return

# 然後執行操作
gateway.update_subscriber_plan(imei, new_plan_id)
```

### **2. 狀態檢查**

```python
# 檢查設備當前狀態
search_result = gateway.search_account(imei)

if search_result['found']:
    print("設備是 ACTIVE 狀態")
    # 可以變更費率或暫停
else:
    print("設備是 RESERVED 狀態")
    # 只能啟動
```

### **3. 測試設備準備**

```python
# 準備測試設備的完整流程
def prepare_test_device(imei: str):
    """準備設備用於測試啟動"""
    gateway = IWSGateway()
    
    # 1. 驗證歸屬權
    validation = gateway.validate_device_string(imei, "IMEI", True)
    if not validation['valid']:
        raise Exception(f"設備不可用: {validation['reason']}")
    
    # 2. 檢查狀態
    search_result = gateway.search_account(imei)
    
    # 3. 如果已啟動，先註銷
    if search_result['found']:
        gateway.deactivate_subscriber(imei, "準備測試")
    
    # 4. 確認 RESERVED 狀態
    print("✅ 設備已準備好測試啟動")
    return True
```

---

## 📝 流程圖使用指南

### **如何查看 Mermaid 流程圖**

**方法 1：GitHub**
- 直接上傳 .mermaid 文件到 GitHub
- GitHub 會自動渲染流程圖

**方法 2：Mermaid Live Editor**
- 訪問 https://mermaid.live/
- 貼上流程圖代碼
- 即時預覽和導出

**方法 3：VSCode**
- 安裝 "Markdown Preview Mermaid Support" 擴展
- 在 Markdown 文件中嵌入流程圖
- 預覽即可看到渲染結果

**方法 4：本地渲染**
```bash
# 安裝 mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# 渲染為 PNG
mmdc -i iws_operations_flowchart.mermaid -o flowchart.png

# 渲染為 SVG
mmdc -i iws_operations_flowchart.mermaid -o flowchart.svg
```

---

## 📦 檔案清單

本次交付包含 3 個 Mermaid 流程圖：

1. **iws_operations_flowchart.mermaid** - 完整流程（含錯誤處理）
2. **iws_operations_simple.mermaid** - 簡化流程（成功路徑）
3. **device_state_diagram.mermaid** - 狀態轉換圖

---

## 🔗 相關文檔

- **IMEI_OWNERSHIP_GUIDE.md** - IMEI 歸屬權完整指南
- **v6.9_RELEASE_NOTES.md** - v6.9 版本說明
- **iws_gateway.py** - 實際實現代碼

---

**文檔版本**: v1.0  
**更新時間**: 2025-12-25  
**對應版本**: IWS Gateway v6.9
