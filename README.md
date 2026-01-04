# 🛰️ SBD 衛星設備管理系統
## Satellite Broadband Data (SBD) Management System

[![Version](https://img.shields.io/badge/version-6.37.0-blue.svg)](https://github.com/yourusername/sbd-management-system)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28%2B-red.svg)](https://streamlit.io/)

一個完整的 Iridium SBD 設備管理與計費系統，支持設備操作追蹤、智能計費、CDR 管理等功能。

---

## ✨ 功能特色

### 🔧 設備管理
- ✅ 設備啟用/停用
- ✅ 服務暫停/恢復
- ✅ 方案升級/降級
- ✅ 完整操作歷史追蹤

### 💰 智能計費系統 ⭐ NEW
- ✅ **升級當月生效** - 立即按高費率計費
- ✅ **降級次月生效** - 當月仍享原方案
- ✅ **狀態變更雙重收費** - 暫停/恢復費用管理
- ✅ **行政手續費** - 防止頻繁暫停濫用（第3次起 $20/次）
- ✅ **預付款機制** - 第3次暫停後需預付才能恢復

### 📊 CDR 管理
- ✅ 自動 FTP 同步
- ✅ Google Drive 整合
- ✅ 帳單查詢

---

## 🚀 快速開始

```bash
# 1. 克隆專案
git clone https://github.com/yourusername/sbd-management-system.git
cd sbd-management-system

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 創建數據目錄
mkdir -p data

# 4. 設定憑證（複製並編輯）
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 5. 運行系統
streamlit run app.py
```

---

## 💵 計費規則

### 方案變更

**升級（當月生效）：**
- 1/31 升級 SBD12→SBD30
- 1月帳單：$50 ✓

**降級（次月生效）：**
- 2/15 降級 SBD30→SBD12  
- 2月帳單：$50（仍收原費率）
- 3月帳單：$28（降級生效）✓

### 狀態變更（雙重收費）

| 變更 | 費用 |
|-----|------|
| 暫停 | 原月租 + $4 |
| 恢復 | $4 + 新月租 |
| 暫停又恢復 | 原月租 + $4 + 新月租 |

### 行政手續費

- 第 1-2 次暫停：正常收費
- **第 3 次起：每次加收 $20**

---

## 📦 部署到 Streamlit Cloud

1. Fork 此專案
2. 前往 [share.streamlit.io](https://share.streamlit.io)
3. 連接 GitHub 並選擇 repository
4. 主文件：`app.py`
5. 在 Secrets 中添加憑證
6. Deploy！

---

## 🧪 測試

```bash
# 快速測試
python3 quick_test.py

# 完整測試
python3 test_system_integration.py
python3 test_extreme_scenarios.py
```

---

## 📚 文檔

- [部署指南](DEPLOYMENT_GUIDE.md)
- [計費規則合約](CONTRACT_BILLING_RULES.md)

---

## 📝 版本歷史

### v6.37.0 (2026-01-04) ⭐

- ✨ 新增設備操作管理
- ✨ 新增增強版計費系統
- ✨ 實作完整計費邏輯
- 🧪 新增完整測試套件

---

**⭐ 如果這個專案對您有幫助，請給我們一個 Star！**
