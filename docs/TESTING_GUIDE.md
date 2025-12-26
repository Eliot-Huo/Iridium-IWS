# 🧪 IWS Gateway v6.9 測試指南

## 📋 測試環境資訊

### **確認的測試 IMEI**
```
IMEI: 300534066716260
Service Account: 200883
狀態: ACTIVE
確認: 在您的 Device Pool 中
```

### **WSDL 合規性**
- ✅ **100% 符合官方 WSDL 規範**
- ✅ 所有 API 方法已通過文檔對照
- ✅ 詳細檢查報告：`WSDL_COMPLIANCE_REPORT.md`

---

## 🚀 快速開始

### **1. 執行完整測試套件**

```bash
cd /home/claude/SBD-Final
python tests/test_real_imei.py
```

**測試項目**：
1. ✅ 連線測試 (getSystemStatus)
2. ✅ 設備驗證 (validateDeviceString)
3. ✅ 帳號搜尋 (accountSearch)
4. ✅ 變更費率 (accountUpdate)
5. ✅ 暫停設備 (setSubscriberAccountStatus - SUSPEND)
6. ✅ 恢復設備 (setSubscriberAccountStatus - RESUME)
7. ✅ 查詢方案 (getSBDBundles)

---

### **2. 單獨測試特定功能**

```python
from src.infrastructure.iws_gateway import IWSGateway

gateway = IWSGateway()
TEST_IMEI = "300534066716260"

# 測試 1: 驗證設備
result = gateway.validate_device_string(TEST_IMEI, "IMEI", True)
print(f"設備有效: {result['valid']}")

# 測試 2: 搜尋帳號
result = gateway.search_account(TEST_IMEI)
print(f"訂閱者帳號: {result['subscriber_account_number']}")

# 測試 3: 變更費率
result = gateway.update_subscriber_plan(
    imei=TEST_IMEI,
    new_plan_id="17",
    lrit_flagstate="",
    ring_alerts_flag=False
)
print(f"Transaction ID: {result['transaction_id']}")

# 測試 4: 暫停設備
result = gateway.suspend_subscriber(TEST_IMEI, "測試暫停")
print(f"暫停成功")

# 測試 5: 恢復設備
result = gateway.resume_subscriber(TEST_IMEI, "測試恢復")
print(f"恢復成功")
```

---

## 📊 預期結果

### **成功的測試輸出**

```
================================================================================
🧪 IWS Gateway v6.9 完整測試
================================================================================
測試 IMEI: 300534066716260
Service Account: 200883
當前狀態: ACTIVE
================================================================================

================================================================================
測試 1: getSystemStatus (連線測試)
================================================================================
✅ 連線測試成功
   系統狀態: OK

================================================================================
測試 2: validateDeviceString (設備驗證)
================================================================================
✅ 設備驗證成功
   屬於 SP 帳戶: 是
   可用於操作: 是

================================================================================
測試 3: accountSearch (帳號搜尋)
================================================================================
✅ 帳號搜尋成功
   訂閱者帳號: SUB1234567
   設備狀態: ACTIVE

================================================================================
測試 4: accountUpdate (變更費率)
================================================================================
✅ 變更費率成功
   Transaction ID: 12345678
   訂閱者帳號: SUB1234567
   新費率 ID: 17

================================================================================
測試 5: setSubscriberAccountStatus - SUSPEND (暫停設備)
================================================================================
✅ 暫停設備成功
   Transaction ID: 12345679
   設備狀態: SUSPENDED

================================================================================
測試 6: setSubscriberAccountStatus - RESUME (恢復設備)
================================================================================
✅ 恢復設備成功
   Transaction ID: 12345680
   設備狀態: ACTIVE

================================================================================
測試 7: getSBDBundles (查詢方案)
================================================================================
✅ 查詢成功，找到 25 個方案

   方案列表（前 5 個）:
   1. Bundle ID: 1, Name: Basic Plan
   2. Bundle ID: 17, Name: Standard Plan
   3. Bundle ID: 25, Name: Premium Plan
   ...

================================================================================
📊 測試結果摘要
================================================================================
連線測試 (getSystemStatus): ✅ PASS
設備驗證 (validateDeviceString): ✅ PASS
帳號搜尋 (accountSearch): ✅ PASS
變更費率 (accountUpdate): ✅ PASS
暫停設備 (setSubscriberAccountStatus): ✅ PASS
恢復設備 (setSubscriberAccountStatus): ✅ PASS
查詢方案 (getSBDBundles): ✅ PASS

總計: 7/7 測試通過

🎉 所有測試通過！
```

---

## 🔍 故障排除

### **問題 1: "Account not found for IMEI"**

**原因**：
- IMEI 處於 RESERVED 狀態（未啟動）
- IMEI 不在您的 Device Pool

**解決方案**：
```python
# 1. 驗證設備歸屬權
result = gateway.validate_device_string("300534066716260", "IMEI", True)
if not result['valid']:
    print(f"設備不可用: {result['reason']}")

# 2. 確認設備狀態
result = gateway.search_account("300534066716260")
if not result['found']:
    print("設備處於 RESERVED 狀態（未啟動）")
```

---

### **問題 2: HTTP 500 錯誤**

**可能原因**：
1. IMEI 不存在
2. 設備狀態不允許此操作
3. SOAP 格式問題

**診斷步驟**：
```bash
# 使用診斷腳本
python tests/diagnose_imei.py 300534066716260
```

---

### **問題 3: "Invalid state for device"**

**原因**：設備狀態不符合操作要求

**狀態要求**：
- **暫停**：需要 ACTIVE 狀態
- **恢復**：需要 SUSPENDED 狀態
- **變更費率**：需要 ACTIVE 狀態

**解決方案**：
```python
# 檢查當前狀態
result = gateway.search_account(imei)

if result['found']:
    print("設備是 ACTIVE 或 SUSPENDED")
else:
    print("設備是 RESERVED（未啟動）")
```

---

## 📁 相關文檔

### **核心文檔**
1. **WSDL_COMPLIANCE_REPORT.md** - 完整的 WSDL 合規性檢查報告
2. **IMEI_OWNERSHIP_GUIDE.md** - IMEI 歸屬權和狀態管理指南
3. **FLOWCHART_GUIDE.md** - 操作流程圖說明

### **流程圖**
1. **iws_operations_simple.mermaid** - 簡化流程圖
2. **iws_operations_flowchart.mermaid** - 完整流程圖
3. **device_state_diagram.mermaid** - 狀態轉換圖
4. **flowchart_preview.html** - HTML 預覽頁面

### **測試工具**
1. **test_real_imei.py** - 完整測試套件
2. **diagnose_imei.py** - IMEI 診斷工具

---

## 🎯 測試檢查清單

在開始測試前，確認以下項目：

- [ ] IMEI 已確認屬於您的 Service Account
- [ ] IMEI 格式正確（15 位，30 開頭，0 結尾）
- [ ] 已配置 IWS 憑證（在 Streamlit secrets 或環境變數）
- [ ] 網路可以訪問 SITEST 環境
- [ ] 了解設備當前狀態（RESERVED/ACTIVE/SUSPENDED）

---

## 💡 最佳實踐

### **1. 測試前驗證**
```python
# 始終先驗證設備
validation = gateway.validate_device_string(imei, "IMEI", True)

if not validation['valid']:
    print(f"❌ {validation['reason']}")
    exit()

# 然後檢查狀態
search_result = gateway.search_account(imei)
print(f"設備狀態: {'ACTIVE/SUSPENDED' if search_result['found'] else 'RESERVED'}")
```

### **2. 錯誤處理**
```python
try:
    result = gateway.update_subscriber_plan(imei, plan_id)
    print(f"✅ 成功: {result['transaction_id']}")
except IWSException as e:
    print(f"❌ 失敗: {e.error_code} - {str(e)}")
    # 記錄詳細錯誤供分析
```

### **3. 測試順序**
```
1. 驗證設備 (validateDeviceString)
2. 檢查狀態 (accountSearch)
3. 執行操作 (update/suspend/resume)
4. 確認結果
```

---

## 🔗 API 方法對照表

| 功能 | Python 方法 | WSDL API | 必要條件 |
|------|------------|----------|----------|
| 驗證設備 | validate_device_string() | validateDeviceString | 無 |
| 搜尋帳號 | search_account() | accountSearch | 設備已啟動 |
| 變更費率 | update_subscriber_plan() | accountUpdate | ACTIVE |
| 暫停設備 | suspend_subscriber() | setSubscriberAccountStatus | ACTIVE |
| 恢復設備 | resume_subscriber() | setSubscriberAccountStatus | SUSPENDED |
| 註銷設備 | deactivate_subscriber() | setSubscriberAccountStatus | ACTIVE/SUSPENDED |
| 查詢方案 | get_sbd_bundles() | getSBDBundles | 無 |
| 連線測試 | check_connection() | getSystemStatus | 無 |

---

## 📞 支援

如遇到問題：
1. 查看 `WSDL_COMPLIANCE_REPORT.md` 確認實現正確性
2. 使用 `diagnose_imei.py` 診斷 IMEI 問題
3. 檢查日誌輸出的詳細 SOAP 請求/回應
4. 參考流程圖理解操作順序

---

**測試環境**: SITEST  
**文檔版本**: v1.0  
**更新時間**: 2025-12-25  
**IWS Gateway**: v6.9  
**狀態**: ✅ **準備測試**

---

**🎊 使用確認的 IMEI 300534066716260 開始測試吧！**
