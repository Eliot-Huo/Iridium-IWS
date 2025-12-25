# 🔐 IWS IMEI 歸屬權與狀態管理完整指南

## 🎯 核心概念：IMEI 的「歸屬權」與「狀態」

### **重要澄清** ⭐

**Iridium 不會「隨機指定」測試 IMEI 給您！**

就像門禁系統一樣：
- ✅ 您可以用**公司現有的員工卡**（您帳戶下的 IMEI）
- ✅ 但必須先**註銷這張卡**（DEACTIVATE → RESERVED 狀態）
- ❌ 您**不能用別家公司的卡**（不屬於您的 Device Pool）

---

## 📋 使用 IMEI 的 4 個必要條件

### **條件 1: 歸屬權 - 必須在您的設備池 (Device Pool)** 🔑

**什麼是 Device Pool？**
- 每個服務供應商 (SP) 帳戶都有自己的設備池
- 只有池內的 IMEI 才能被該 SP 使用

**兩種 IMEI 類型**：

| 類型 | 說明 | 特性 |
|------|------|------|
| **Reserved IMEI** | 預留給特定 SP | ✅ 只有該 SP 可以啟動<br>✅ 最常見的情況 |
| **Global IMEI** | 存在中央資料庫 | ⚠️ 任何 SP 都可嘗試啟動<br>⚠️ 先啟動者獲得歸屬權 |

**錯誤範例**：
```
❌ Device does not belong to account
```
**原因**：嘗試使用不屬於您 SP 帳戶的 IMEI

---

### **條件 2: 狀態 - 必須處於 RESERVED 狀態** 📊

**設備狀態生命週期**：

```
RESERVED (預留)
    ↓ activateSubscriber
ACTIVE (已啟動)
    ↓ suspend
SUSPENDED (暫停)
    ↓ resume
ACTIVE (已啟動)
    ↓ deactivate
RESERVED (預留) ← 可以重新啟動！
```

**關鍵規則**：
- ✅ **只有 RESERVED 狀態才能執行 activateSubscriber**
- ❌ ACTIVE 狀態的設備無法重新啟動
- ❌ SUSPENDED 狀態的設備無法重新啟動
- ✅ **DEACTIVATE 後立即釋放**，恢復到 RESERVED

**錯誤範例**：
```
❌ Invalid state for device
```
**原因**：嘗試啟動已處於 ACTIVE 或 SUSPENDED 狀態的設備

---

### **條件 3: 環境同步 - SITEST 數據刷新** 🔄

**SITEST 環境特性**：
- 定期從**生產環境 (Production)** 刷新數據
- 只有生產環境存在的設備會同步到 SITEST
- 測試環境不會憑空產生新的 IMEI

**建議做法**：
1. ✅ **使用公司名下的真實設備 IMEI**
2. ✅ 確認該設備在生產環境中存在
3. ✅ 等待 SITEST 環境數據刷新
4. ❌ 不要使用隨機編造的 IMEI

---

### **條件 4: 格式驗證** ✓

**SBD 設備 IMEI 格式**：
- 長度：15 位數字
- 前綴：通常以 `3` 開頭
- 後綴：通常以 `0` 結尾

**範例**：
```
✅ 300434067857940  (正確格式)
❌ 12345678901234   (錯誤格式)
❌ 30043406785794   (長度錯誤，只有 14 位)
```

**主動驗證 API**：
```python
# 建議：啟動前先驗證
result = gateway.validate_device_string(
    imei="300434067857940",
    device_type="IMEI"
)

if result['valid']:
    # 可以啟動
    gateway.activate_subscriber(...)
else:
    # IMEI 無效或不可用
    print(result['error_message'])
```

---

## 🚀 如何獲取可用的測試 IMEI

### **方法 1: 從現有設備中選擇（推薦）** ⭐

**步驟**：
1. 列出您帳戶下所有設備
2. 選擇一個已啟動的設備
3. 執行 DEACTIVATE
4. 該 IMEI 立即變為 RESERVED 狀態
5. 可以用於測試啟動

**程式碼範例**：
```python
from src.infrastructure.iws_gateway import IWSGateway

gateway = IWSGateway()

# 步驟 1: 選擇一個已啟動的測試設備
TEST_IMEI = "300434067857940"  # 您帳戶下的設備

# 步驟 2: 註銷設備（恢復到 RESERVED 狀態）
gateway.deactivate_subscriber(
    imei=TEST_IMEI,
    reason="準備測試啟動功能"
)

# 步驟 3: 確認設備已變為 RESERVED
# （此時 accountSearch 應該找不到帳號）
result = gateway.search_account(TEST_IMEI)
if not result['found']:
    print("✅ 設備已註銷，處於 RESERVED 狀態")
    print("✅ 可以用於測試 activateSubscriber")

# 步驟 4: 測試啟動
gateway.activate_subscriber(
    imei=TEST_IMEI,
    plan_id="17",
    # ... 其他必要參數
)
```

---

### **方法 2: 使用 validateDeviceString 檢查** 🔍

**在啟動前驗證**：
```python
# 檢查 IMEI 是否可用
validation = gateway.validate_device_string(
    imei="300434067857940",
    device_type="IMEI"
)

print(f"有效: {validation['valid']}")
print(f"歸屬於您的帳戶: {validation['belongs_to_account']}")
print(f"當前狀態: {validation['current_state']}")
print(f"可以啟動: {validation['can_activate']}")
```

---

### **方法 3: 聯絡您的帳戶管理員** 📞

如果您需要更多測試設備：
1. 聯絡 Iridium 帳戶管理員
2. 要求分配更多 IMEI 到您的 Device Pool
3. 等待配置完成和 SITEST 數據刷新

---

## 🔍 常見問題診斷

### **問題 1: "Account not found for IMEI"**

**可能原因**：
1. ❌ IMEI 不屬於您的 SP 帳戶
2. ❌ IMEI 處於 RESERVED 狀態（尚未啟動）
3. ❌ IMEI 在 SITEST 環境中不存在

**解決方法**：
```python
# 檢查 IMEI 歸屬權和狀態
validation = gateway.validate_device_string(imei="...")

if not validation['belongs_to_account']:
    print("❌ 此 IMEI 不屬於您的帳戶")
    print("→ 使用您公司名下的 IMEI")
    
elif validation['current_state'] == 'RESERVED':
    print("✅ 設備處於 RESERVED 狀態")
    print("✅ 可以執行 activateSubscriber")
    
elif validation['current_state'] == 'ACTIVE':
    print("⚠️ 設備已啟動")
    print("→ 先執行 deactivate 再測試啟動")
```

---

### **問題 2: "Invalid state for device"**

**原因**：嘗試啟動已處於 ACTIVE 或 SUSPENDED 狀態的設備

**解決方法**：
```python
# 先註銷設備
gateway.deactivate_subscriber(imei="...")

# 確認狀態變為 RESERVED
validation = gateway.validate_device_string(imei="...")

if validation['current_state'] == 'RESERVED':
    # 現在可以啟動
    gateway.activate_subscriber(...)
```

---

### **問題 3: "Device does not belong to account"**

**原因**：IMEI 不在您的 Device Pool

**解決方法**：
1. ✅ 使用您公司名下的設備
2. ✅ 聯絡帳戶管理員分配 IMEI
3. ❌ 不要使用隨機編造的 IMEI
4. ❌ 不要使用其他公司的 IMEI

---

## 📊 IMEI 狀態檢查流程圖

```
開始測試
    ↓
選擇 IMEI
    ↓
validateDeviceString ──→ 不屬於帳戶? → 使用其他 IMEI
    ↓ 屬於帳戶
檢查狀態
    ↓
RESERVED? ─────→ 是 → 可以啟動測試 ✅
    ↓ 否
ACTIVE/SUSPENDED
    ↓
執行 deactivate
    ↓
確認變為 RESERVED
    ↓
可以啟動測試 ✅
```

---

## 🎯 最佳實踐

### **1. 建立測試設備清單**

```python
# 在您的測試配置中維護可用的測試 IMEI
TEST_DEVICES = {
    'imei_1': {
        'imei': '300434067857940',
        'status': 'RESERVED',  # 定期更新
        'belongs_to_account': True,
        'notes': '用於啟動測試'
    },
    'imei_2': {
        'imei': '301434061231580',
        'status': 'ACTIVE',
        'belongs_to_account': True,
        'notes': '用於變更費率測試'
    }
}
```

---

### **2. 測試前驗證**

```python
def prepare_test_device(imei: str) -> bool:
    """
    準備測試設備
    
    Returns:
        bool: True 如果設備已準備好測試
    """
    gateway = IWSGateway()
    
    # 步驟 1: 驗證設備
    validation = gateway.validate_device_string(
        imei=imei,
        device_type="IMEI"
    )
    
    if not validation['belongs_to_account']:
        print(f"❌ {imei} 不屬於您的帳戶")
        return False
    
    # 步驟 2: 檢查狀態
    if validation['current_state'] == 'ACTIVE':
        print(f"⚠️ {imei} 已啟動，正在註銷...")
        gateway.deactivate_subscriber(imei, "準備測試")
        
    elif validation['current_state'] == 'SUSPENDED':
        print(f"⚠️ {imei} 已暫停，正在註銷...")
        gateway.deactivate_subscriber(imei, "準備測試")
    
    # 步驟 3: 確認 RESERVED
    validation = gateway.validate_device_string(imei, "IMEI")
    
    if validation['current_state'] == 'RESERVED':
        print(f"✅ {imei} 已準備好測試")
        return True
    
    return False
```

---

### **3. 測試後清理**

```python
def cleanup_test_device(imei: str):
    """測試後註銷設備，恢復到 RESERVED 狀態"""
    gateway = IWSGateway()
    
    try:
        gateway.deactivate_subscriber(
            imei=imei,
            reason="測試完成，清理設備"
        )
        print(f"✅ {imei} 已恢復到 RESERVED 狀態，可供下次測試")
    except Exception as e:
        print(f"⚠️ 清理失敗: {e}")
```

---

## ✅ 檢查清單

在開始測試前，確認以下項目：

- [ ] IMEI 屬於您的 SP 帳戶（Device Pool）
- [ ] IMEI 格式正確（15 位，3 開頭，0 結尾）
- [ ] 使用 validateDeviceString 驗證設備
- [ ] 確認設備狀態為 RESERVED
- [ ] 如果是 ACTIVE，先執行 deactivate
- [ ] 在 SITEST 環境中測試
- [ ] 測試完成後清理設備

---

## 🔗 相關 API 方法

| 方法 | 用途 | WSDL 頁碼 |
|------|------|----------|
| validateDeviceString | 驗證設備歸屬權和狀態 | p.236 |
| activateSubscriber | 啟動設備 | p.76 |
| deactivate (setSubscriberAccountStatus) | 註銷設備，恢復 RESERVED | p.224 |
| accountSearch | 搜尋已啟動的設備 | p.62 |

---

## 📚 總結

### **門禁系統比喻** 🏢

```
您的公司門禁系統：
├─ 員工卡片庫（Device Pool）
│  ├─ 已分配的卡（ACTIVE）
│  ├─ 已停用的卡（SUSPENDED）
│  └─ 待分配的卡（RESERVED）← 可以用來測試發卡
│
├─ 測試發卡功能
│  └─ 拿一張「待分配」的卡
│     └─ 執行發卡 API (activateSubscriber)
│
└─ ❌ 不能用
   ├─ 別家公司的卡（不屬於您的 Pool）
   ├─ 已在使用的卡（ACTIVE 狀態）
   └─ 憑空編造的卡號（不在系統中）
```

---

**關鍵要點**：
1. 使用**您公司名下**的真實設備 IMEI
2. 確保設備處於 **RESERVED 狀態**
3. 使用 **validateDeviceString** 驗證
4. 測試後執行 **deactivate** 恢復 RESERVED

---

**文件版本**: v1.0  
**更新時間**: 2025-12-25  
**參考**: Iridium WSDL v25.1.0.1
