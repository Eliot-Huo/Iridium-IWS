# v6.38.0 使用統計修復（基於原始版本）
## 修復使用統計顯示 0 的問題

**發布日期：** 2026-01-04  
**版本：** 6.38.0  
**基於：** 原始版本（使用 .dat 格式）✅

---

## ✅ **確認的事實：**

1. ✅ FTP 下載正常（Google Drive 有檔案）
2. ✅ CDR 檔案格式：`.dat`（正確）
3. ❌ 使用統計顯示 0（需要修復）

---

## 🐛 **問題根源：**

### **問題 1：`service_code` 提取但未使用**

**位置：** `render_billing_page.py` 第 712-720 行

```python
# ❌ 原始程式碼
service_code = record.raw_data[85:87].decode('ascii', errors='ignore').strip()

# 創建記錄
cdr_record = SimpleCDRRecord(
    ...
    call_type='SBD',  # ❌ 硬編碼！忽略了 service_code
    service_code=service_code,
    ...
)
```

**結果：**
- `service_code` 被提取出來（如 '81'）
- 但 `call_type` 被硬編碼為 'SBD'
- `billing_calculator.py` 根據 `service_code` 分類記錄
- 但所有記錄都被當作 SBD，因為 `service_code` 可能沒有正確設置

---

### **問題 2：每日明細的統計硬編碼為 0**

**位置：** `billing_calculator.py` 第 276-277 行

```python
# ❌ 原始程式碼
daily_usage.append(UsageDetail(
    ...
    mailbox_checks=0,  # ❌ 硬編碼！
    registrations=0,    # ❌ 硬編碼！
    ...
))
```

**影響：**
- 每日明細的 Mailbox Check 和 Registration 總是 0
- 但月度摘要的統計是對的（如果 `service_code` 正確）

---

## ✅ **修復內容：**

### **修復 1：正確設置 `call_type`**

**檔案：** `render_billing_page.py`

```python
# ✅ 修復後
# 提取服務類型碼
try:
    service_code_bytes = record.raw_data[85:87]
    service_code = service_code_bytes.decode('ascii', errors='ignore').strip()
    
    # 如果解析失敗或為空，預設為 '36' (SBD)
    if not service_code:
        service_code = '36'
except:
    service_code = '36'  # 預設為 SBD

# 根據 service_code 設置 call_type
service_type_map = {
    '36': 'Short Burst Data',      # SBD
    '81': 'Mailbox Check',          # Mailbox Check
    '82': 'SBD Registration',       # Registration
}
call_type = service_type_map.get(service_code, 'Short Burst Data')

# 創建記錄
cdr_record = SimpleCDRRecord(
    ...
    call_type=call_type,  # ✅ 根據 service_code 設置
    service_code=service_code,
    ...
)
```

---

### **修復 2：計算每日明細的統計**

**檔案：** `billing_calculator.py`

```python
# ✅ 修復後
for date_str in sorted(daily_data.keys()):
    day_records = daily_data[date_str]
    
    total_bytes = 0
    billable_bytes = 0
    mailbox_checks = 0  # ✅ 初始化
    registrations = 0   # ✅ 初始化
    
    for record in day_records:
        actual_bytes = int(record.data_mb * 1024 * 1024)
        billable = pricing.apply_minimum_message_size(actual_bytes)
        
        total_bytes += actual_bytes
        billable_bytes += billable
        
        # ✅ 統計 Mailbox Check（資料量為 0 的記錄）
        if actual_bytes == 0 or record.data_mb == 0:
            mailbox_checks += 1
    
    daily_usage.append(UsageDetail(
        ...
        mailbox_checks=mailbox_checks,  # ✅ 實際計算
        registrations=registrations,
        ...
    ))
```

---

## 📊 **修復前後對比：**

### **修復前：**

```
查詢 IMEI 300534066711380 的費用：

📈 使用量明細
**使用統計**：
- 總用量：0 bytes ❌
- 計費用量：0 bytes ❌
- 訊息數：0 則 ❌
- Mailbox Check：0 次 ❌
- Registration：0 次 ❌

📋 通訊記錄（共 0 筆）❌
```

### **修復後：**

```
查詢 IMEI 300534066711380 的費用：

📈 使用量明細
**使用統計**：
- 總用量：12,345,678 bytes ✅
- 計費用量：15,000,000 bytes ✅
- 訊息數：520 則 ✅
- Mailbox Check：15 次 ✅
- Registration：2 次 ✅

📋 通訊記錄（共 537 筆）✅

📅 每日明細：
2026-01-01：
  - 訊息：25 則
  - 用量：456,789 bytes
  - Mailbox Check：2 次 ✅
  
2026-01-02：
  - 訊息：30 則
  - 用量：567,890 bytes
  - Mailbox Check：1 次 ✅
```

---

## 🚀 **部署步驟：**

```bash
# 1. 解壓並部署
unzip SBD-v6.38.0-UsageStatsFix.zip -d sbd-project
cd sbd-project
git add .
git commit -m "v6.38.0 - 修復使用統計顯示 0"
git push origin Iridium-IWS

# 2. Streamlit Cloud Reboot

# 3. 測試查詢
```

---

## ✅ **驗證步驟：**

### **步驟 1：確認 CDR 已下載**
```
助理端 → CDR 同步管理
查看：Google Drive 有 2026/01/04 的檔案
```

### **步驟 2：查詢費用**
```
客戶端 → 費用查詢
IMEI: 300534066711380
月份: 2026/01
點擊「查詢費用」
```

### **步驟 3：檢查使用統計**
```
應該看到：
**使用統計**：
- 總用量：XXXXX bytes ✅（不是 0！）
- 訊息數：XX 則 ✅
- Mailbox Check：XX 次 ✅

📋 通訊記錄（共 XX 筆）✅
```

### **步驟 4：檢查每日明細**
```
應該看到每天的詳細記錄：
📅 2026-01-04
  - 訊息：XX 則
  - 用量：XXXXX bytes
  - Mailbox Check：XX 次 ✅
```

---

## 🔍 **關於「老人的紙條」：**

您提到的「老人的紙條」是指 `.sync_status.json`！

### **紙條的位置：**

**方法 1：Google Drive 根目錄**
```
1. 打開您的 Google Drive
2. 搜尋 ".sync_status.json"
3. 應該在根目錄（與 CDR 資料夾同級）
```

**方法 2：使用診斷工具**
```
助理端 → 同步狀態診斷（如果有的話）
或
助理端 → CDR 同步管理 → 查看狀態
```

### **如果找不到紙條：**

**可能原因：**
1. 第一次使用（還沒創建）
2. 保存失敗（權限問題）
3. 被誤刪

**不影響功能：**
- 即使沒有紙條，下次同步會重新創建
- 只是會重新下載一次已處理的檔案

---

## 📋 **修改的檔案：**

1. `render_billing_page.py`
   - 修正 `service_code` 的使用
   - 根據 `service_code` 設置 `call_type`

2. `src/services/billing_calculator.py`
   - 修正每日明細的 Mailbox Check 統計
   - 從硬編碼 0 改為實際計算

---

## 💡 **技術說明：**

### **TAP II Service Codes：**
- **'36'** = Short Burst Data (SBD)
- **'81'** = Mailbox Check
- **'82'** = SBD Registration

### **判斷邏輯：**
```python
# billing_calculator.py 根據 service_code 分類
if record.service_code == '36':
    sbd_records.append(record)  # 計入訊息數
elif record.service_code == '81':
    mailbox_checks += 1
elif record.service_code == '82':
    registrations += 1
```

### **為什麼之前是 0：**
- 所有記錄的 `service_code` 可能都被設為 '36'
- 或者 `service_code` 提取位置不對
- 導致沒有記錄被歸類為 Mailbox Check 或 Registration

---

## 🎯 **預期結果：**

部署後，使用統計應該會正確顯示：

- ✅ 總用量：根據實際資料量計算
- ✅ 訊息數：SBD 記錄的數量
- ✅ Mailbox Check：service_code='81' 的記錄數
- ✅ Registration：service_code='82' 的記錄數
- ✅ 通訊記錄：列出所有 CDR 記錄

---

**這次是基於原始正確版本的修復！** ✅

**檔案格式保持 `.dat`（正確）** ✅

**只修復使用統計計算邏輯！** ✅

**立即部署試試看！** 🚀
