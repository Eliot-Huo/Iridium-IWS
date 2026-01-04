# 🚀 快速部署指南
## Quick Deployment Guide

**⏱️ 預計時間：10-15 分鐘**

---

## 📋 部署步驟總覽

```
準備 → Git 初始化 → GitHub 創建 → 推送 → Streamlit Cloud → 完成！
  ↓         ↓           ↓          ↓          ↓            ↓
 2分鐘     1分鐘       2分鐘      1分鐘      5分鐘        ✓
```

---

## 步驟 1: 準備檢查 (2分鐘)

```bash
cd /home/claude/SBD-Project/SBD-Final-GitHub

# 運行準備檢查
./prepare_commit.sh

# 確認輸出都是 ✓
```

**檢查項目：**
- ✅ 所有核心檔案存在
- ✅ 沒有敏感資訊
- ✅ 測試通過
- ✅ 統計正常

---

## 步驟 2: Git 初始化 (1分鐘)

```bash
# 初始化 Git（如果尚未初始化）
git init

# 設定使用者資訊
git config user.name "Your Name"
git config user.email "your.email@example.com"

# 添加所有檔案
git add .

# 檢查將要提交的檔案
git status
```

**確認：**
- ✅ 看到綠色的新檔案列表
- ✅ 沒有看到 `secrets.toml` 或 `.json` 憑證檔案

---

## 步驟 3: 提交變更 (1分鐘)

```bash
# 提交（使用 prepare_commit.sh 建議的訊息）
git commit -m "feat: Add enhanced billing system v6.37.0

New Features:
- Device operations management page
- Enhanced billing calculator
- Complete billing logic implementation
- Device history tracking
- Administrative fee mechanism
- Prepayment recovery mechanism

Tests:
- test_extreme_scenarios.py (5 scenarios)
- test_system_integration.py (3 scenarios)
- quick_test.py (quick validation)
"
```

---

## 步驟 4: 創建 GitHub Repository (2分鐘)

### 方式 A: 網頁創建（推薦）

1. **前往 GitHub**
   - 訪問：https://github.com/new

2. **填寫資訊**
   - Repository name: `sbd-management-system`
   - Description: `Satellite Broadband Data Management System with Enhanced Billing`
   - 選擇 Public 或 Private
   - **不要** 勾選 "Add a README file"
   - **不要** 勾選 "Add .gitignore"
   - **不要** 選擇 "Choose a license"

3. **創建**
   - 點擊 "Create repository"

### 方式 B: GitHub CLI（如果已安裝）

```bash
gh repo create sbd-management-system --public --description "SBD Management System"
```

---

## 步驟 5: 連接並推送 (1分鐘)

```bash
# 添加遠端 repository（替換 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/sbd-management-system.git

# 檢查分支名稱
git branch

# 如果是 master，重命名為 main
git branch -M main

# 推送到 GitHub
git push -u origin main
```

**提示：** 如果要求登入，使用您的 GitHub 帳號和 Personal Access Token

---

## 步驟 6: 部署到 Streamlit Cloud (5分鐘)

### 6.1 前往 Streamlit Cloud

1. 訪問：https://share.streamlit.io
2. 使用 GitHub 帳號登入

### 6.2 創建新應用

1. 點擊 **"New app"**

2. 填寫資訊：
   - **Repository**: 選擇 `YOUR_USERNAME/sbd-management-system`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: 選擇一個名稱（例如 `sbd-system`）

### 6.3 設定 Secrets

1. 點擊 **"Advanced settings"**

2. 在 **"Secrets"** 欄位中貼上：

```toml
# IWS 憑證（替換成您的實際憑證）
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "your_password_here"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

# Google Drive（如果需要，否則可以先不設定）
# [gcp_service_account]
# type = "service_account"
# project_id = "your-project-id"
# ... 其他欄位
```

### 6.4 部署

1. 點擊 **"Deploy!"**
2. 等待部署完成（約 2-5 分鐘）
3. 部署成功後會顯示您的應用 URL

---

## 步驟 7: 驗證部署 (2分鐘)

### 7.1 訪問您的應用

打開 Streamlit 給您的 URL：`https://YOUR-APP-NAME.streamlit.app`

### 7.2 功能測試

**助理端測試：**
1. 切換到「助理 (Assistant)」模式
2. 選擇「🔧 設備操作管理（新）」
3. 嘗試記錄一個設備啟用：
   - IMEI: `300534066711380`
   - 方案: `SBD12`
   - 日期: 今天
4. 選擇「💰 帳單查詢（新）」
5. 查詢剛才設備的帳單

**客戶端測試：**
1. 切換到「客戶 (Customer)」模式
2. 選擇「💰 帳單查詢（新）」
3. 輸入 IMEI 查詢帳單

### 7.3 檢查清單

- [ ] 應用可以正常訪問
- [ ] 助理端頁面正常顯示
- [ ] 可以記錄設備操作
- [ ] 可以查詢帳單
- [ ] 費用計算正確
- [ ] 沒有錯誤訊息

---

## ✅ 完成！

**🎉 恭喜！您的 SBD 管理系統已成功部署！**

### 您的應用資訊：

- **GitHub Repository**: `https://github.com/YOUR_USERNAME/sbd-management-system`
- **Streamlit App**: `https://YOUR-APP-NAME.streamlit.app`
- **版本**: v6.37.0

### 下一步：

1. **分享給團隊**
   - 將 Streamlit URL 分享給需要使用的人

2. **設定使用者角色**
   - 助理：完整管理權限
   - 客戶：查詢權限

3. **開始使用**
   - 記錄設備操作
   - 查詢帳單
   - 管理 CDR

4. **持續改進**
   - 收集使用反饋
   - 添加新功能
   - 優化體驗

---

## 🔧 故障排除

### 問題 1: 推送失敗（403 錯誤）

**原因：** GitHub 認證失敗

**解決：**
```bash
# 使用 Personal Access Token
# 在 GitHub Settings → Developer settings → Personal access tokens 創建 token
# 推送時使用 token 作為密碼
```

### 問題 2: Streamlit 部署失敗

**原因：** 可能是 requirements.txt 問題

**解決：**
1. 檢查 Streamlit Cloud 的錯誤日誌
2. 確認 requirements.txt 格式正確
3. 檢查 Python 版本相容性

### 問題 3: 應用運行但功能異常

**原因：** Secrets 設定不正確

**解決：**
1. 檢查 Streamlit Cloud 的 Secrets 設定
2. 確認 IWS 憑證正確
3. 查看應用的錯誤訊息

### 問題 4: 數據不持久化

**原因：** Streamlit Cloud 會定期重啟

**解決：**
- 接受這個限制（適合測試）
- 或使用外部數據庫（生產環境）

---

## 📞 需要幫助？

- **GitHub Issues**: 在您的 repository 中創建 issue
- **Streamlit 文檔**: https://docs.streamlit.io
- **Streamlit 社群**: https://discuss.streamlit.io

---

**部署時間統計：**
```
✓ 準備檢查      2 分鐘
✓ Git 初始化    1 分鐘
✓ 提交變更      1 分鐘
✓ GitHub 創建   2 分鐘
✓ 推送         1 分鐘
✓ Streamlit    5 分鐘
✓ 驗證         2 分鐘
─────────────────────
總計：         14 分鐘
```

**🎊 享受您的新系統！**
