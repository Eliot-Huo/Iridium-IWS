# 🔍 SITEST 環境診斷指南 - v5.1

## 🎯 架構師深度分析完成

根據 SITEST 環境的 HTTP 500 錯誤分析，v5.1 進行了 5 大深度優化。

---

## 🔧 關鍵優化（5 大項）

### 1. 修正命名空間歧義

**問題**：伺服器使用帶斜線的命名空間

**修正前**：
```python
IWS_NS = 'http://www.iridium.com'  # ❌ 無斜線
```

**修正後**：
```python
IWS_NS = 'http://www.iridium.com/'  # ✅ 有斜線
```

**為什麼**：
- SITEST 環境的錯誤訊息顯示伺服器使用 `http://www.iridium.com/`
- 命名空間不匹配會導致 HTTP 500 或 SOAP Fault

---

### 2. 強制完整標籤閉合

**問題**：空欄位使用 self-closing tag 可能導致解析錯誤

**修正前**：
```xml
<lritFlagstate/>  <!-- ❌ Self-closing tag -->
<serviceProviderAccountNumber/>  <!-- ❌ Self-closing tag -->
```

**修正後**：
```xml
<lritFlagstate></lritFlagstate>  <!-- ✅ 完整閉合 -->
<serviceProviderAccountNumber></serviceProviderAccountNumber>  <!-- ✅ 完整閉合 -->
```

**實作方法**：
```python
def _safe_xml_value(self, value: Optional[str]) -> str:
    """
    強制完整標籤閉合
    - 空值/None 返回空字串
    - 確保所有欄位使用 <tag></tag> 格式
    """
    if value is None or value == '':
        return ''  # 空字串，將生成 <tag></tag>
    return str(value)
```

---

### 3. 實作基礎診斷方法

**新增**：`check_connection()` 方法

**目的**：
- 使用最簡單的 `getSystemStatus` 操作
- 僅包含認證欄位，無業務資料
- 診斷「認證/標頭/命名空間」問題

**診斷邏輯**：
```
如果 check_connection() 失敗（HTTP 500）
  → 問題在「認證/標頭/命名空間」
  → 檢查：IWS_USER, IWS_PASS, IWS_SP_ACCOUNT, 命名空間

如果 check_connection() 成功但 activate_subscriber() 失敗
  → 問題在「SBD 資料結構」
  → 檢查：IMEI, plan_id, deliveryDetails
```

**使用方法**：
```python
from src.infrastructure.iws_gateway import check_iws_connection

try:
    result = check_iws_connection()
    print("✅ Connection OK:", result)
except Exception as e:
    print("❌ Connection Failed:", e)
```

---

### 4. 優化錯誤回應捕捉

**新增功能**：記錄 `response.headers`

**為什麼**：
- Web 伺服器可能在 Header 中給出提示
- 常見的錯誤 headers：
  - `X-Error-Info`
  - `X-Error-Code`
  - `X-SOAP-Fault`

**實作**：
```python
print(f"\n[IWS] Response Headers:")
for key, value in response.headers.items():
    print(f"  {key}: {value}")

# 檢查特殊的錯誤 headers
if 'X-Error-Info' in response.headers:
    error_details.append(f"X-Error-Info: {response.headers['X-Error-Info']}")
```

**詳細日誌輸出**：
```
============================================================
[IWS] SOAP Request Details:
============================================================
Endpoint: https://ws.iridium.com/services/information.asmx
Action: getSystemStatus
Namespace: http://www.iridium.com/
Username: your_username
SP Account: SP12345

[IWS] Request Headers:
  Content-Type: application/soap+xml; charset=utf-8; action="getSystemStatus"
  Accept: application/soap+xml, text/xml

[IWS] SOAP Envelope (first 500 chars):
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
...
============================================================

============================================================
[IWS] SOAP Response Details:
============================================================
Status Code: 200
Reason: OK

[IWS] Response Headers:
  Content-Type: application/soap+xml; charset=utf-8
  Content-Length: 1234
  ...

[IWS] Response Body (first 1000 chars):
<?xml version="1.0" encoding="UTF-8"?>
...
============================================================
```

---

### 5. 簽章大小寫校正

**問題**：action 名稱大小寫不一致可能導致簽章驗證失敗

**修正**：
```python
# 所有 action 名稱完全符合 WSDL
soap_action='getSystemStatus'        # ✅ 小寫 g, 大寫 S
soap_action='activateSubscriber'     # ✅ 小寫 a, 大寫 S
soap_action='setSubscriberAccountStatus'  # ✅ 小寫 s, 大寫 S, A, S
```

**一致性檢查**：
- WSDL 定義：`activateSubscriber`
- HTTP Header：`action="activateSubscriber"`
- XML 元素：`<tns:activateSubscriber>`

---

## 📋 完整的診斷流程

### 步驟 1: 基礎連線測試 ⭐⭐⭐

```python
from src.infrastructure.iws_gateway import check_iws_connection

# 測試最簡單的操作
try:
    result = check_iws_connection()
    print("\n✅ [STEP 1] Connection test PASSED!")
    print("Authentication/headers/namespace are correct.")
    print("Proceed to Step 2: Activation test.")
except Exception as e:
    print("\n❌ [STEP 1] Connection test FAILED!")
    print(f"Error: {e}")
    print("\n🔍 DIAGNOSIS:")
    print("Problem in authentication/headers/namespace")
    print("\n📝 ACTION:")
    print("1. Check IWS_USER, IWS_PASS, IWS_SP_ACCOUNT in secrets")
    print("2. Verify endpoint URL")
    print("3. Check network connectivity")
```

### 步驟 2: 啟用測試

```python
from src.infrastructure.iws_gateway import IWSGateway

gateway = IWSGateway()

try:
    result = gateway.activate_subscriber(
        imei='300534066711380',
        plan_id='SBD12'
    )
    print("\n✅ [STEP 2] Activation test PASSED!")
    print(f"Transaction ID: {result['transaction_id']}")
except Exception as e:
    print("\n❌ [STEP 2] Activation test FAILED!")
    print(f"Error: {e}")
    print("\n🔍 DIAGNOSIS:")
    print("Step 1 passed but Step 2 failed")
    print("Problem in SBD data structure")
    print("\n📝 ACTION:")
    print("1. Verify IMEI format (15 digits, starts with 30)")
    print("2. Check plan_id (SBD12, SBDO, SBD17, etc.)")
    print("3. Verify deliveryDetails structure")
```

---

## 🧪 完整的測試腳本

### test_iws_connection.py

```python
"""
IWS Connection Diagnostic Test
SITEST 環境診斷腳本
"""
from src.infrastructure.iws_gateway import IWSGateway, check_iws_connection

def test_basic_connection():
    """測試 1: 基礎連線（getSystemStatus）"""
    print("\n" + "="*60)
    print("TEST 1: Basic Connection Test")
    print("="*60)
    
    try:
        result = check_iws_connection()
        print("\n✅ PASSED: Basic connection successful")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print("\n❌ FAILED: Basic connection failed")
        print(f"Error: {e}")
        return False

def test_activation():
    """測試 2: 設備啟用（activateSubscriber）"""
    print("\n" + "="*60)
    print("TEST 2: Device Activation Test")
    print("="*60)
    
    gateway = IWSGateway()
    
    try:
        result = gateway.activate_subscriber(
            imei='300534066711380',
            plan_id='SBD12'
        )
        print("\n✅ PASSED: Device activation successful")
        print(f"Transaction ID: {result['transaction_id']}")
        return True
    except Exception as e:
        print("\n❌ FAILED: Device activation failed")
        print(f"Error: {e}")
        return False

def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("IWS SITEST Diagnostic Suite")
    print("="*60)
    
    # 測試 1: 基礎連線
    test1_passed = test_basic_connection()
    
    if not test1_passed:
        print("\n" + "="*60)
        print("DIAGNOSIS: Basic connection failed")
        print("="*60)
        print("Problem: Authentication/headers/namespace")
        print("Action: Check credentials and configuration")
        return
    
    # 測試 2: 啟用
    test2_passed = test_activation()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"Test 1 (Basic Connection): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Device Activation): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and not test2_passed:
        print("\n🔍 DIAGNOSIS:")
        print("Basic connection OK but activation failed")
        print("Problem: SBD data structure")
        print("Action: Check IMEI, plan_id, deliveryDetails")
    elif test1_passed and test2_passed:
        print("\n✅ ALL TESTS PASSED!")
        print("IWS integration is working correctly.")
    
    print("="*60)

if __name__ == "__main__":
    main()
```

---

## 📊 診斷決策樹

```
開始診斷
    │
    ├─ check_connection() 測試
    │   │
    │   ├─ ✅ 成功
    │   │   │
    │   │   └─ activate_subscriber() 測試
    │   │       │
    │   │       ├─ ✅ 成功 → 🎉 完全正常
    │   │       │
    │   │       └─ ❌ 失敗
    │   │           │
    │   │           └─ 🔍 診斷：SBD 資料結構問題
    │   │               ├─ 檢查 IMEI 格式
    │   │               ├─ 檢查 plan_id
    │   │               └─ 檢查 deliveryDetails
    │   │
    │   └─ ❌ 失敗
    │       │
    │       └─ 🔍 診斷：認證/標頭/命名空間問題
    │           ├─ 檢查 IWS_USER
    │           ├─ 檢查 IWS_PASS
    │           ├─ 檢查 IWS_SP_ACCOUNT
    │           ├─ 檢查命名空間（是否有斜線）
    │           └─ 檢查 Content-Type
```

---

## ✅ v5.1 優化總結

| 優化項目 | 修正內容 | 狀態 |
|---------|---------|------|
| 命名空間 | 結尾加斜線 | ✅ |
| 標籤閉合 | 強制 `<tag></tag>` | ✅ |
| 診斷方法 | `check_connection()` | ✅ |
| 錯誤日誌 | 記錄 `response.headers` | ✅ |
| 大小寫 | action 名稱一致 | ✅ |

---

## 🚀 部署步驟

### 1. 更新 iws_gateway.py

將 `src/infrastructure/iws_gateway.py` 替換為 v5.1 版本。

### 2. 執行診斷測試

```bash
# 在 Streamlit 應用程式中添加診斷按鈕
# 或在 Python console 中執行
python test_iws_connection.py
```

### 3. 分析結果

根據診斷決策樹分析測試結果。

---

## 📝 預期輸出範例

### 成功案例

```
============================================================
🔍 [DIAGNOSTIC] Starting connection test...
============================================================
This is the simplest IWS operation (getSystemStatus)
Purpose: Verify authentication/headers/namespace
============================================================

============================================================
[IWS] SOAP Request Details:
============================================================
Endpoint: https://ws.iridium.com/services/information.asmx
Action: getSystemStatus
Namespace: http://www.iridium.com/
Username: your_username
SP Account: SP12345
...

============================================================
[IWS] SOAP Response Details:
============================================================
Status Code: 200
Reason: OK
...

============================================================
✅ [DIAGNOSTIC] Connection test PASSED!
============================================================
Authentication/headers/namespace are correct.
If activateSubscriber fails, check SBD data structure.
============================================================
```

### 失敗案例（認證問題）

```
============================================================
❌ [DIAGNOSTIC] Connection test FAILED!
============================================================
Error Code: 500
Error Message: HTTP 500: Internal Server Error
============================================================
DIAGNOSIS: Problem in authentication/headers/namespace
ACTION: Check IWS_USER, IWS_PASS, IWS_SP_ACCOUNT
============================================================
```

---

**v5.1 深度優化完成！請先執行 check_connection() 診斷基礎協議層。** 🔍

**更新日期**: 2025-12-25  
**版本**: v5.0 → v5.1  
**優化重點**: SITEST 環境 HTTP 500 深度診斷  
**狀態**: ✅ **準備測試**
