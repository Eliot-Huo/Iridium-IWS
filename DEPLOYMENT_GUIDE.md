# 🚀 GitHub 上傳與 Streamlit 部署指南

## 📋 目錄

1. [準備工作](#準備工作)
2. [上傳到 GitHub](#上傳到-github)
3. [Streamlit Cloud 部署](#streamlit-cloud-部署)
4. [配置 Secrets](#配置-secrets)
5. [驗證部署](#驗證部署)

---

## 🛠️ 準備工作

### **1. 確認檔案結構**

```
SBD-Final-Integrated/
├── app.py                              # 主程式
├── requirements.txt                    # 依賴套件
├── .gitignore                          # Git 忽略清單
├── README.md                           # 專案說明
├── CDR_FEATURES.md                     # CDR 功能說明
│
├── src/                                # 核心模組
│   ├── config/
│   ├── infrastructure/
│   │   ├── ftp_client.py              # FTP 客戶端
│   │   ├── gdrive_client.py           # Google Drive 客戶端
│   │   └── iws_gateway.py             # IWS Gateway
│   ├── models/
│   ├── parsers/
│   │   └── tapii_parser.py            # TAP II 解析器
│   ├── repositories/
│   └── services/
│       ├── incremental_sync.py        # 增量同步管理
│       ├── billing_service.py         # 計費服務
│       └── ...
│
├── service_tracking/                   # 服務追蹤系統
├── render_*.py                         # UI 頁面
└── test_*.py                          # 測試程式（不需上傳）
```

### **2. 創建 .gitignore**

```bash
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/

# Streamlit
.streamlit/secrets.toml

# IDE
.vscode/
.idea/

# 測試檔案
test_*.py
temp_*.dat
*.dat

# 日誌
*.log

# 同步狀態（本地）
.sync_status.json
service_requests.json
```

### **3. 創建 requirements.txt**

```txt
streamlit>=1.28.0
requests>=2.31.0
zeep>=4.2.1
google-api-python-client>=2.100.0
google-auth>=2.23.0
pytz>=2023.3
```

---

## 📤 上傳到 GitHub

### **方法 1: 使用 GitHub Desktop（推薦新手）**

1. **下載並安裝 GitHub Desktop**
   - https://desktop.github.com/

2. **創建新儲存庫**
   - File → New Repository
   - Name: `SBD-Management-System`
   - Local Path: 選擇 `SBD-Final-Integrated` 資料夾
   - 勾選 "Initialize this repository with a README"
   - 點擊 "Create Repository"

3. **提交變更**
   - 在 Changes 標籤中查看所有檔案
   - 輸入 Commit message: "Initial commit - v6.36.0 with CDR features"
   - 點擊 "Commit to main"

4. **發布到 GitHub**
   - 點擊 "Publish repository"
   - 取消勾選 "Keep this code private"（如果要公開）
   - 點擊 "Publish Repository"

---

### **方法 2: 使用命令列**

```bash
cd SBD-Final-Integrated

# 初始化 Git
git init

# 添加所有檔案
git add .

# 提交
git commit -m "Initial commit - v6.36.0 with CDR features"

# 創建 GitHub 儲存庫後，連結遠端
git remote add origin https://github.com/你的帳號/SBD-Management-System.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

---

## ☁️ Streamlit Cloud 部署

### **步驟 1: 登入 Streamlit Cloud**

1. 前往 https://share.streamlit.io/
2. 使用 GitHub 帳號登入

### **步驟 2: 新增應用**

1. 點擊 "New app"
2. 選擇儲存庫：`你的帳號/SBD-Management-System`
3. 選擇分支：`main`
4. 主檔案路徑：`app.py`
5. App URL: 自訂網址（例如：`sbd-management`）
6. 點擊 "Deploy!"

### **步驟 3: 等待部署**

- 首次部署約需 5-10 分鐘
- 可在 "Logs" 查看部署進度
- 看到 "Your app is live!" 表示成功

---

## 🔐 配置 Secrets

### **在 Streamlit Cloud 設定 Secrets：**

1. **進入應用設定**
   - 在應用頁面點擊右上角 "⋮"
   - 選擇 "Settings"
   - 點擊 "Secrets"

2. **新增 Secrets**

```toml
# IWS 設定
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "你的密碼"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

# FTP 設定
FTP_HOST = "cdr.iridium.com"
FTP_USER = "DDATA"
FTP_PASS = "4x5oQLppej"

# Google Drive 設定
[gcp_service_account]
type = "service_account"
project_id = "iridium-billing-system"
private_key_id = "你的 private_key_id"
private_key = "-----BEGIN PRIVATE KEY-----\n你的私鑰\n-----END PRIVATE KEY-----\n"
client_email = "你的服務帳號email"
client_id = "你的 client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "你的 cert URL"
```

3. **儲存設定**
   - 點擊 "Save"
   - Streamlit 會自動重新部署應用

---

## ✅ 驗證部署

### **1. 檢查基本功能**

- [ ] 應用成功啟動
- [ ] 側邊欄正常顯示
- [ ] 可以切換客戶/助理角色

### **2. 測試 IWS 連線**

- [ ] 進入「設備管理」
- [ ] 輸入測試 IMEI 查詢
- [ ] 確認可以取得設備資訊

### **3. 測試 CDR 功能**

#### **CDR 同步管理：**

- [ ] 進入助理端 → 「CDR 同步管理」
- [ ] 查看同步狀態
- [ ] 點擊「手動同步」
- [ ] 確認 FTP 連線成功
- [ ] 確認 Google Drive 上傳成功

#### **CDR 帳單查詢：**

- [ ] 進入助理端 → 「CDR 帳單查詢」
- [ ] 輸入 IMEI、年份、月份
- [ ] 點擊查詢
- [ ] 確認顯示帳單結果

---

## 🐛 常見問題

### **問題 1: 部署失敗**

**錯誤：** `ModuleNotFoundError`

**解決：** 檢查 `requirements.txt` 是否包含所有依賴

```bash
# 在本地生成完整依賴清單
pip freeze > requirements.txt
```

---

### **問題 2: Secrets 設定錯誤**

**錯誤：** `KeyError: 'FTP_USER'`

**解決：** 
1. 檢查 Secrets 格式（注意大小寫）
2. 確認沒有多餘的空格
3. GCP JSON 格式必須正確（特別是換行符 `\n`）

---

### **問題 3: FTP 連線逾時**

**錯誤：** `FTP connection timeout`

**解決：**
- Streamlit Cloud 可能有防火牆限制
- 嘗試使用被動模式（已預設開啟）
- 檢查 FTP 伺服器是否允許 Streamlit Cloud IP

---

### **問題 4: Google Drive 權限錯誤**

**錯誤：** `403 Forbidden`

**解決：**
1. 確認服務帳號有 Google Drive API 權限
2. 確認服務帳號有存取目標資料夾權限
3. 在 Google Cloud Console 啟用 Google Drive API

---

## 📊 監控與維護

### **查看日誌**

在 Streamlit Cloud 應用頁面：
- 點擊 "Manage app"
- 選擇 "Logs"
- 可以看到即時日誌輸出

### **應用重啟**

如果應用異常：
- 點擊 "⋮" → "Reboot app"
- 或修改任何檔案並推送到 GitHub，會自動重新部署

### **更新應用**

```bash
# 本地修改後
git add .
git commit -m "更新說明"
git push

# Streamlit Cloud 會自動偵測並重新部署
```

---

## 🎉 完成！

您的 SBD 管理系統現已成功部署到 Streamlit Cloud！

**應用網址：** `https://你的網址.streamlit.app`

---

## 📞 支援

如有問題，請檢查：

1. **Streamlit 文件：** https://docs.streamlit.io/
2. **GitHub 文件：** https://docs.github.com/
3. **應用日誌：** Streamlit Cloud 管理介面

---

**文件版本：v1.0**  
**更新日期：2025-01-02**
