# 🛰️ SBD 衛星設備管理系統

完整的 Iridium SBD（Short Burst Data）設備管理與計費系統

---

## 🎯 系統功能

### ✅ **設備管理**
- IMEI 查詢與狀態監控
- 服務請求提交（啟用/停用/暫停/恢復）
- 自動狀態追蹤與更新
- IWS API 完整整合

### 💰 **計費管理**
- 月費用查詢
- 資費方案管理
- 價格規則設定
- CDR 帳單明細查詢

### 📊 **CDR 完整管理** ⭐ 新功能
- **自動同步** - FTP 下載 → TAP II 解析 → Google Drive 上傳
- **智慧分類** - 年/月資料夾自動建立
- **增量同步** - 斷點續傳，只處理新檔案
- **帳單查詢** - IMEI + 年月 → 完整計費明細

---

## 🚀 快速開始

### **本地運行**

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定 Secrets
mkdir -p .streamlit
# 編輯 .streamlit/secrets.toml 填入憑證

# 啟動應用
streamlit run app.py
```

---

## 📋 系統需求

- Python 3.8+
- Streamlit >= 1.28.0
- Iridium IWS API 帳號
- FTP 伺服器存取
- Google Cloud Platform 服務帳號

---

## ⚙️ 配置說明

在 `.streamlit/secrets.toml` 中設定：

```toml
IWS_USERNAME = "你的帳號"
IWS_PASSWORD = "你的密碼"
FTP_HOST = "cdr.iridium.com"
FTP_USER = "你的FTP帳號"
FTP_PASS = "你的FTP密碼"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
# ... 其他 GCP 設定
```

詳細說明請參考 [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)

---

## 📚 文件

- 📖 **[部署指南](DEPLOYMENT_GUIDE.md)** - GitHub 與 Streamlit Cloud 部署
- 📊 **[CDR 功能說明](CDR_FEATURES.md)** - CDR 同步與查詢指南

---

## 📝 版本歷程

### v6.36.0 (2025-01-02) - 最新版本 ⭐
- ✨ 新增 CDR 帳單查詢功能
- ✨ 完整 CDR 下載、分類、上傳流程
- 🔧 優化增量同步機制

---

**系統版本：v6.36.0**  
**最後更新：2025-01-02**
