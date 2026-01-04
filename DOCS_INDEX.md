# 📚 文檔索引
## Documentation Index

---

## 🚀 開始使用

| 文檔 | 說明 | 適合對象 |
|------|------|----------|
| [README.md](README.md) | 專案總覽、功能介紹 | 所有人 |
| [QUICK_DEPLOY.md](QUICK_DEPLOY.md) | 10分鐘快速部署指南 | 新手 ⭐ |
| [requirements.txt](requirements.txt) | Python 依賴列表 | 開發者 |

---

## 📦 部署文檔

| 文檔 | 說明 | 用途 |
|------|------|------|
| [GITHUB_DEPLOYMENT_CHECKLIST.md](GITHUB_DEPLOYMENT_CHECKLIST.md) | GitHub 部署完整檢查清單 | 部署前檢查 |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | 詳細部署指南 | 完整部署流程 |
| [prepare_commit.sh](prepare_commit.sh) | 自動化檢查腳本 | 提交前驗證 |
| [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example) | Secrets 設定範例 | 配置參考 |

---

## 💰 計費系統文檔

| 文檔 | 說明 | 目標讀者 |
|------|------|----------|
| [CONTRACT_BILLING_RULES.md](CONTRACT_BILLING_RULES.md) | 工業IoT計費規則合約 | 客戶、業務 |
| [HIKING_RENTAL_CONTRACT.md](HIKING_RENTAL_CONTRACT.md) | 登山租用服務合約 | 客戶、業務 |
| [IoT_Billing_Logic_Rules.pdf](IoT_Billing_Logic_Rules.pdf) | 計費邏輯PDF文檔 | 客戶、業務 |

---

## 🧪 測試文檔

| 檔案 | 說明 | 測試內容 |
|------|------|----------|
| [quick_test.py](quick_test.py) | 快速功能測試 | 基本功能驗證 |
| [test_system_integration.py](test_system_integration.py) | 系統整合測試 | 3個整合場景 |
| [test_extreme_scenarios.py](test_extreme_scenarios.py) | 極端情況測試 | 5個極端場景 |

---

## 🔧 技術文檔

### 核心模組

| 模組 | 位置 | 功能 |
|------|------|------|
| DeviceHistoryManager | `src/services/device_history.py` | 設備歷史記錄管理 |
| EnhancedBillingCalculator | `src/services/enhanced_billing_calculator.py` | 增強版計費計算器 |
| IWSGateway | `src/infrastructure/iws_gateway.py` | IWS API 閘道 |
| PriceManager | `src/config/price_rules.py` | 價格規則管理 |

### 頁面模組

| 頁面 | 檔案 | 用戶角色 |
|------|------|----------|
| 設備操作管理 | `render_device_operations_page.py` | 助理 |
| 增強版帳單查詢 | `render_enhanced_billing_page.py` | 客戶/助理 |
| CDR 管理 | `render_cdr_management_page.py` | 助理 |
| 價格管理 | `render_price_management_page.py` | 助理 |

---

## 📖 使用指南

### 助理端操作

1. **記錄設備啟用**
   - 頁面：設備操作管理 → 記錄操作
   - 選擇：啟用設備
   - 填寫：IMEI、方案、日期

2. **記錄方案變更**
   - 頁面：設備操作管理 → 記錄操作
   - 選擇：變更方案
   - 系統自動判斷升降級

3. **記錄狀態變更**
   - 頁面：設備操作管理 → 記錄操作
   - 選擇：變更狀態
   - 系統自動檢查暫停次數

4. **查詢帳單**
   - 頁面：帳單查詢（新）
   - 輸入：IMEI、年份、月份
   - 查看：費用明細、操作記錄

### 客戶端操作

1. **查詢帳單**
   - 頁面：帳單查詢（新）
   - 輸入：IMEI、年份、月份
   - 查看：費用明細、計費規則

2. **下載帳單**
   - 在帳單頁面底部
   - 點擊：下載帳單（JSON）

---

## 🔍 計費規則快速參考

### 方案變更

```
升級（SBD12 → SBD30）：當月立即生效，收 $50
降級（SBD30 → SBD12）：次月才生效，當月仍收 $50
```

### 狀態變更

```
暫停：原月租 + $4
恢復：$4 + 新月租
暫停又恢復：原月租 + $4 + 新月租
```

### 行政手續費

```
第 1-2 次暫停：正常收費
第 3 次起：每次加收 $20
```

---

## 💡 常見問題

### Q: 如何開始使用？

**A:** 閱讀 [QUICK_DEPLOY.md](QUICK_DEPLOY.md)，10分鐘完成部署。

### Q: 如何修改計費規則？

**A:** 編輯 `src/services/enhanced_billing_calculator.py` 中的 `_calculate_fees` 方法。

### Q: 如何添加新方案？

**A:** 在 `src/config/price_rules.py` 中註冊新的價格規則。

### Q: 資料存儲在哪裡？

**A:** `data/device_history.json`（本地）或外部數據庫（生產環境）。

### Q: 如何運行測試？

**A:** 
```bash
python3 quick_test.py
python3 test_system_integration.py
python3 test_extreme_scenarios.py
```

---

## 📞 支援資源

### 外部資源

- **Streamlit 文檔**: https://docs.streamlit.io
- **GitHub 文檔**: https://docs.github.com
- **Python 文檔**: https://docs.python.org

### 專案資源

- **GitHub Repository**: https://github.com/YOUR_USERNAME/sbd-management-system
- **Issues**: https://github.com/YOUR_USERNAME/sbd-management-system/issues
- **Discussions**: https://github.com/YOUR_USERNAME/sbd-management-system/discussions

---

## 🗂️ 檔案結構

```
SBD-Management-System/
├── 📄 README.md                    ← 從這裡開始
├── 🚀 QUICK_DEPLOY.md              ← 快速部署
├── 📋 GITHUB_DEPLOYMENT_CHECKLIST.md
├── 📖 DEPLOYMENT_GUIDE.md
├── 📚 DOCS_INDEX.md                ← 你在這裡
│
├── 💰 CONTRACT_BILLING_RULES.md
├── 💰 HIKING_RENTAL_CONTRACT.md
├── 📊 IoT_Billing_Logic_Rules.pdf
│
├── 🧪 quick_test.py
├── 🧪 test_system_integration.py
├── 🧪 test_extreme_scenarios.py
│
├── ⚙️ app.py                       ← 主程式
├── 📦 requirements.txt
├── 🔒 .gitignore
│
├── src/                           ← 核心程式碼
│   ├── services/
│   │   ├── device_history.py      ⭐ NEW
│   │   └── enhanced_billing_calculator.py  ⭐ NEW
│   ├── infrastructure/
│   ├── models/
│   └── config/
│
├── render_device_operations_page.py  ⭐ NEW
├── render_enhanced_billing_page.py   ⭐ NEW
└── data/                          ← 數據存儲
    └── device_history.json
```

---

## 🎯 文檔導航建議

### 如果您是...

**新手用戶：**
1. 閱讀 [README.md](README.md)
2. 跟隨 [QUICK_DEPLOY.md](QUICK_DEPLOY.md)
3. 運行 `quick_test.py`

**業務人員：**
1. 閱讀 [CONTRACT_BILLING_RULES.md](CONTRACT_BILLING_RULES.md)
2. 查看 [IoT_Billing_Logic_Rules.pdf](IoT_Billing_Logic_Rules.pdf)

**開發人員：**
1. 閱讀 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. 運行所有測試
3. 查看核心模組原始碼

**系統管理員：**
1. 閱讀 [GITHUB_DEPLOYMENT_CHECKLIST.md](GITHUB_DEPLOYMENT_CHECKLIST.md)
2. 運行 `prepare_commit.sh`
3. 設定 Streamlit Cloud

---

**最後更新：** 2026-01-04  
**版本：** v6.37.0
