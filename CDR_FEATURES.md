# 📊 CDR 完整功能說明

## 🎯 功能概述

本系統已完整整合 CDR（Call Detail Record）管理功能，包括：

1. ✅ **CDR 自動同步** - FTP 下載 → 解析 → Google Drive 上傳
2. ✅ **CDR 帳單查詢** - IMEI + 年月 → 完整計費明細
3. ✅ **增量同步** - 智慧斷點續傳，只處理新檔案
4. ✅ **年月分類** - Google Drive 自動建立 年/月 資料夾結構

---

## 🔄 功能 1: CDR 同步管理

### **位置：** 助理端 → 「CDR 同步管理」

### **功能：**

- 📥 **手動同步** - 從 FTP 下載最新 CDR 檔案
- 🔄 **增量同步** - 只下載未處理的新檔案
- 📊 **同步狀態** - 顯示已同步檔案數、最後同步時間
- 🗂️ **智慧分類** - 自動建立 Google Drive 資料夾結構

### **資料夾結構：**

```
Google Drive/
└── CDR_Files/
    ├── 2024/
    │   ├── 11/
    │   │   ├── CD00USA77DDATA0020766.dat
    │   │   └── CD00USA77DDATA0020767.dat
    │   └── 12/
    │       └── CD00USA77DDATA0020800.dat
    └── 2025/
        └── 01/
            ├── CD00USA77DDATA0020801.dat
            └── CD00USA77DDATA0020802.dat
```

### **跨月檔案處理：**

如果一個 CDR 檔案包含多個月份的記錄，系統會自動複製到所有相關月份的資料夾。

例如：`CD00USA77DDATA0020800.dat` 包含 2024/12 和 2025/01 的記錄
- 會同時上傳到 `2024/12/` 和 `2025/01/`

---

## 📊 功能 2: CDR 帳單查詢

### **位置：** 助理端 → 「CDR 帳單查詢」

### **查詢流程：**

1. **輸入查詢條件**
   - IMEI（15 位數字）
   - 年份（2020-2030）
   - 月份（1-12）

2. **系統處理**
   - 從 Google Drive 下載對應月份的所有 CDR 檔案
   - 解析 TAP II 格式，提取通訊記錄
   - 過濾該 IMEI 的所有記錄
   - 查詢 IWS 取得資費方案
   - 計算月帳單

3. **顯示結果**
   - 📊 **帳單總覽** - 資費方案、總費用、記錄數
   - 📈 **用量統計** - 上傳/下載流量、方案使用率
   - 📋 **明細記錄** - 每筆通訊的時間、流量、來源檔案

### **範例輸出：**

```
📊 帳單總覽
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
資費方案：SBD12
記錄數量：150 筆
月租費用：$20.00
超量費用：$5.50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
總計費用：$25.50

📈 用量統計
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
上傳流量：15,000 bytes (14.6 KB)
下載流量：5,000 bytes (4.9 KB)
總流量：20,000 bytes (19.5 KB)
方案用量：75.0%

📋 通訊記錄
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
時間                    | 上傳  | 下載  | 服務     | 來源檔案
2025-01-01 08:30:15    | 100 B | 50 B  | Location | CD00...0801.dat
2025-01-01 09:15:22    | 150 B | 75 B  | Message  | CD00...0801.dat
...
```

---

## ⚙️ 配置需求

### **FTP 設定（必須）**

在 `.streamlit/secrets.toml` 中設定：

```toml
FTP_HOST = "cdr.iridium.com"
FTP_USER = "你的FTP帳號"
FTP_PASS = "你的FTP密碼"
```

### **Google Drive 設定（必須）**

在 `.streamlit/secrets.toml` 中設定：

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

---

## 🔧 技術細節

### **TAP II 格式解析**

系統支援 TAP II v9.2 格式：

- **記錄長度**: 160 bytes（固定）
- **IMEI 位置**: Byte 10-24 或 25-40
- **日期位置**: Byte 115-120（YYMMDD）
- **時間位置**: Byte 121-126（HHMMSS）
- **流量位置**: Byte 134-139（6位數，bytes）

### **增量同步機制**

使用 `.sync_status.json` 追蹤已處理檔案：

```json
{
  "last_sync": "2025-01-02T10:30:00",
  "processed_files": [
    "CD00USA77DDATA0020766.dat",
    "CD00USA77DDATA0020767.dat"
  ],
  "total_synced": 2
}
```

### **錯誤處理**

- FTP 連線失敗 → 顯示錯誤，保持手動介入能力
- Google Drive 上傳失敗 → 記錄日誌，繼續處理其他檔案
- TAP II 解析錯誤 → 跳過該記錄，記錄警告

---

## 📚 相關文件

- `CDR_IMPLEMENTATION_GUIDE.md` - 完整實作細節
- `CHANGELOG.md` - 修改歷程
- `TEST_EXECUTION_GUIDE.md` - 測試指南

---

## 🎉 使用建議

### **首次使用：**

1. 設定 FTP 和 Google Drive 憑證
2. 執行「CDR 同步管理」→ 手動同步
3. 等待同步完成（約 5-10 分鐘）
4. 使用「CDR 帳單查詢」查看結果

### **日常使用：**

1. 定期執行增量同步（建議每天或每週）
2. 需要查詢時使用「CDR 帳單查詢」
3. 系統會自動處理跨月檔案

### **故障排除：**

- 同步失敗 → 檢查 FTP 憑證和網路連線
- 查詢無結果 → 確認該 IMEI 在該月份有通訊記錄
- IMEI 提取錯誤 → 檢查 CDR 檔案格式，可能需要調整位元組位置

---

**系統版本：v6.36.0**  
**更新日期：2025-01-02**
