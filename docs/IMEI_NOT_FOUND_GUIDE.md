# 🔍 IMEI 不存在問題診斷

## 🎯 問題摘要

**IMEI**: 300434065956950  
**錯誤**: Account not found for IMEI

**所有操作失敗**：
- ❌ 變更費率：帳號不存在
- ❌ 暫停設備：HTTP 500（因為帳號不存在）
- ❌ 註銷設備：HTTP 500（因為帳號不存在）

---

## 🔍 根本原因

**IMEI 300434065956950 在 IWS SITEST 環境中不存在**

這表示：
1. 設備尚未在 IWS 系統中啟用（activated）
2. IMEI 可能輸入錯誤
3. 設備可能在其他環境（非 SITEST）

---

## ✅ 解決方案

### **方案 1: 使用已啟用的測試 IMEI**

**建議使用之前成功的 IMEI**：
- 300434067857940（之前測試成功）
- 301434061231580（之前測試成功）

### **方案 2: 啟用新設備**

如果需要啟用 300434065956950，需要：
1. 使用 `activateSubscriber` 方法
2. 提供完整的啟用資訊（plan, delivery details, etc.）
3. 由具有啟用權限的帳號執行

**注意**：SITEST 環境可能對啟用有限制。

### **方案 3: 驗證 IMEI**

使用診斷腳本確認：
```bash
python tests/diagnose_imei.py 300434065956950
```

這會顯示：
- IMEI 格式是否正確
- 帳號是否存在
- 如果不存在，提供解決建議

---

## 🧪 診斷步驟

### **步驟 1: 檢查 IMEI 格式**

```python
IMEI: 300434065956950
✅ 長度: 15 位數字
✅ 前綴: 30 (正確)
✅ 後綴: 0 (正確)
```

格式正確 ✅

### **步驟 2: 搜尋帳號**

```python
result = gateway.search_account("300434065956950")

# 預期結果
{
    'found': False,
    'message': 'Account not found - device may not be activated'
}
```

帳號不存在 ❌

### **步驟 3: 使用已知的測試 IMEI**

```python
# 測試 IMEI 1
result = gateway.search_account("300434067857940")
# 預期：found = True, subscriber_account_number = "SUB..."

# 測試 IMEI 2
result = gateway.search_account("301434061231580")
# 預期：found = True, subscriber_account_number = "SUB..."
```

---

## 📊 HTTP 500 錯誤說明

### **為什麼 setSubscriberAccountStatus 返回 500？**

當 IMEI 不存在時：
- `accountSearch` 返回空結果
- `setSubscriberAccountStatus` 嘗試操作不存在的設備
- IWS 伺服器返回 HTTP 500 Internal Server Error

**這是預期行為**：無法對不存在的設備執行狀態變更。

---

## 🚀 立即行動

### **選項 A: 使用已啟用的 IMEI（推薦）**

```python
# 使用已知可用的 IMEI
TEST_IMEI = "300434067857940"

# 測試所有功能
gateway = IWSGateway()

# 1. 搜尋帳號
result = gateway.search_account(TEST_IMEI)
print(f"帳號: {result['subscriber_account_number']}")

# 2. 變更費率
gateway.update_subscriber_plan(TEST_IMEI, "17")

# 3. 暫停設備
gateway.suspend_subscriber(TEST_IMEI, "測試暫停")

# 4. 恢復設備
gateway.resume_subscriber(TEST_IMEI, "測試恢復")
```

### **選項 B: 診斷並找到可用的 IMEI**

```bash
# 運行診斷腳本
python tests/diagnose_imei.py

# 測試多個 IMEI，找到可用的
```

---

## 📋 v6.8.2 新增功能

### **search_account() 方法**

```python
def search_account(imei: str) -> Dict:
    """
    搜尋帳號
    
    Returns:
        {
            'success': True,
            'found': True/False,
            'subscriber_account_number': 'SUB...' or None,
            'imei': '...',
            'message': '...'  (如果未找到)
        }
    """
```

**使用範例**：
```python
from src.infrastructure.iws_gateway import IWSGateway

gateway = IWSGateway()

# 檢查 IMEI 是否存在
result = gateway.search_account("300434065956950")

if result['found']:
    print(f"設備已啟用，帳號: {result['subscriber_account_number']}")
    # 可以執行變更費率、暫停等操作
else:
    print("設備未啟用，無法執行操作")
    # 需要先啟用設備或使用其他 IMEI
```

---

## 🎯 常見問答

### **Q: 為什麼我的 IMEI 不存在？**
A: SITEST 是測試環境，只有預先啟用的設備可用。使用已知的測試 IMEI 即可。

### **Q: 如何啟用新設備？**
A: 需要使用 `activateSubscriber` 方法，但 SITEST 可能有限制。建議使用現有測試設備。

### **Q: 500 錯誤一定是程式問題嗎？**
A: 不一定。當操作不存在的設備時，伺服器返回 500 是正常的。

### **Q: 如何找到可用的測試 IMEI？**
A: 使用 `diagnose_imei.py` 腳本測試多個 IMEI，找到 `found=True` 的即可使用。

---

## ✅ 檢查清單

使用此清單確認問題：

- [ ] IMEI 格式正確（15 位，30 開頭，0 結尾）
- [ ] 使用 search_account() 確認帳號是否存在
- [ ] 如果不存在，使用已知的測試 IMEI
- [ ] 如果存在，檢查具體的錯誤訊息
- [ ] 執行 diagnose_imei.py 獲取詳細診斷

---

## 📦 更新檔案

**v6.8.2 新增**：
1. `search_account()` 公開方法
2. `diagnose_imei.py` 診斷腳本
3. 改善的錯誤訊息

**部署**：
```
更新 iws_gateway.py → v6.8.2
添加 diagnose_imei.py → tests/
```

---

**結論**: IMEI 300434065956950 不存在於 SITEST 環境。  
**建議**: 使用已知的測試 IMEI（如 300434067857940）。  
**工具**: 使用 `search_account()` 和 `diagnose_imei.py` 診斷。

---

**更新時間**: 2025-12-25 16:23  
**版本**: v6.8.2  
**狀態**: ✅ 問題已診斷，解決方案已提供
