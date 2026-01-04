# GitHub 部署檢查清單
## Deployment Checklist for GitHub

---

## ✅ 部署前檢查

### 1. 檔案完整性檢查

```bash
# 檢查核心檔案是否存在
ls -la src/services/device_history.py
ls -la src/services/enhanced_billing_calculator.py
ls -la render_device_operations_page.py
ls -la render_enhanced_billing_page.py
ls -la app.py
ls -la README.md
ls -la requirements.txt
ls -la .gitignore
```

### 2. 敏感資訊清理

```bash
# 確認這些檔案不會被提交
cat .gitignore | grep -E "(secrets.toml|*.json|*.key)"

# 確認 secrets.toml 不存在於版本控制中
git status | grep secrets.toml
# 應該要沒有輸出
```

### 3. 測試運行

```bash
# 運行所有測試
python3 quick_test.py
python3 test_system_integration.py
python3 test_extreme_scenarios.py

# 檢查是否全部通過
```

---

## 📦 準備提交到 GitHub

### 步驟 1：初始化 Git（如果尚未初始化）

```bash
cd /home/claude/SBD-Project/SBD-Final-GitHub

# 初始化（如果需要）
git init

# 檢查狀態
git status
```

### 步驟 2：添加檔案

```bash
# 添加所有檔案
git add .

# 檢查將要提交的檔案
git status

# 確認沒有敏感資訊
git diff --cached | grep -i "password\|secret\|key" || echo "✅ 沒有發現敏感資訊"
```

### 步驟 3：提交變更

```bash
# 提交
git commit -m "feat: Add enhanced billing system v6.37.0

New Features:
- Device operations management page
- Enhanced billing calculator
- Complete billing logic implementation
- Device history tracking
- Administrative fee mechanism
- Prepayment recovery mechanism

Improvements:
- Optimized UI design
- Added detailed billing notes
- Complete test suite

Tests:
- test_extreme_scenarios.py (5 scenarios)
- test_system_integration.py (3 scenarios)
- quick_test.py (quick validation)
"
```

### 步驟 4：創建 GitHub Repository

1. **在 GitHub 上創建新 repository**
   - 前往 https://github.com/new
   - Repository 名稱：`sbd-management-system`
   - 描述：`Satellite Broadband Data (SBD) Management System with Enhanced Billing`
   - 選擇 Public 或 Private
   - 不要初始化 README（我們已經有了）

2. **連接本地到遠端**

```bash
# 添加遠端 repository（替換成您的 username）
git remote add origin https://github.com/YOUR_USERNAME/sbd-management-system.git

# 檢查遠端
git remote -v
```

3. **推送到 GitHub**

```bash
# 首次推送（設定 upstream）
git push -u origin main

# 或如果分支名稱是 master
git push -u origin master
```

---

## 🚀 部署到 Streamlit Cloud

### 步驟 1：前往 Streamlit Cloud

1. 訪問 [share.streamlit.io](https://share.streamlit.io)
2. 使用 GitHub 帳號登入

### 步驟 2：創建新應用

1. 點擊 "New app"
2. 選擇您的 GitHub repository
3. 設定：
   - **Repository**: `YOUR_USERNAME/sbd-management-system`
   - **Branch**: `main` (或 `master`)
   - **Main file path**: `app.py`
   - **App URL**: 選擇一個喜歡的名稱

### 步驟 3：設定 Secrets

1. 點擊 "Advanced settings"
2. 在 "Secrets" 欄位中貼上：

```toml
# IWS 憑證
IWS_USERNAME = "your_iws_username"
IWS_PASSWORD = "your_iws_password"
IWS_SP_ACCOUNT = "your_sp_account"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

# Google Drive（如果需要）
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

### 步驟 4：部署

1. 點擊 "Deploy!"
2. 等待部署完成（通常 2-5 分鐘）
3. 部署成功後會獲得一個 URL：`https://your-app-name.streamlit.app`

---

## 📋 部署後驗證

### 1. 功能測試

訪問您的 Streamlit 應用並測試：

- [ ] 切換到助理模式
- [ ] 進入「設備操作管理」頁面
- [ ] 記錄一個設備啟用
- [ ] 記錄一個方案變更
- [ ] 進入「帳單查詢」頁面
- [ ] 查詢一個月帳單
- [ ] 檢查費用是否正確計算

### 2. 檢查數據持久化

```bash
# 在 Streamlit Cloud 中，數據會在每次重啟時重置
# 如果需要持久化，考慮使用外部數據庫
```

---

## 🔄 更新部署

### 本地修改後推送

```bash
# 1. 修改程式碼
# 2. 測試
python3 quick_test.py

# 3. 提交
git add .
git commit -m "fix: your fix description"

# 4. 推送
git push origin main

# Streamlit Cloud 會自動重新部署
```

---

## 📊 版本管理

### 創建新版本

```bash
# 打標籤
git tag -a v6.37.0 -m "Release v6.37.0: Enhanced Billing System"

# 推送標籤
git push origin v6.37.0

# 在 GitHub 上創建 Release
# 訪問 https://github.com/YOUR_USERNAME/sbd-management-system/releases/new
```

---

## ⚠️ 注意事項

### 安全性

1. **絕對不要提交敏感資訊**
   - secrets.toml
   - JSON 憑證檔案
   - API 金鑰
   - 密碼

2. **使用環境變數**
   - 在 Streamlit Cloud 中使用 Secrets
   - 在本地使用 `.streamlit/secrets.toml`

3. **定期更新憑證**
   - IWS 密碼
   - Service Account 金鑰

### 性能

1. **數據持久化**
   - Streamlit Cloud 不保證檔案系統持久化
   - 考慮使用 Streamlit Cloud 的 Secrets 存儲小量數據
   - 或使用外部數據庫（PostgreSQL, MongoDB 等）

2. **CDR 檔案**
   - 大量 CDR 檔案應存儲在 Google Drive
   - 不要存儲在 Git repository 中

---

## ✅ 最終檢查清單

部署前確認：

- [ ] 所有測試通過
- [ ] README.md 更新
- [ ] requirements.txt 包含所有依賴
- [ ] .gitignore 正確設定
- [ ] secrets.toml.example 已創建
- [ ] 沒有敏感資訊在 Git 中
- [ ] 程式碼已提交到 GitHub
- [ ] Streamlit Cloud 已設定 Secrets
- [ ] 應用已成功部署
- [ ] 功能測試通過

---

**🎉 恭喜！您的 SBD 管理系統已成功部署到 GitHub 和 Streamlit Cloud！**
