# SBD v6.45.0 - Clean Architecture Implementation

## 🎯 專案概述

這是 **SBD 衛星設備管理系統**的完整重構版本，採用 **Clean Architecture（整潔架構）** 設計，遵循企業級軟體開發最佳實踐。

### **核心特色**
- ✅ 完整的分層架構（Domain, Repository, Service, UI）
- ✅ 依賴注入模式（Dependency Injection）
- ✅ 完整的型別提示（Type Hints）
- ✅ 自訂例外處理（Custom Exceptions）
- ✅ 單元測試框架（Unit Tests）
- ✅ 低耦合高內聚（Low Coupling, High Cohesion）

---

## 📁 專案結構

```
SBD-Refactored-v6.45.0/
├── src/
│   ├── domain/              # ✅ 領域層
│   ├── repositories/        # ✅ Repository 層
│   ├── services/            # ✅ Service 層
│   ├── infrastructure/      # ✅ 基礎設施層
│   ├── ui/                  # ✅ UI 層
│   ├── config/              # ✅ 設定
│   └── utils/               # ✅ 工具
├── tests/                   # ✅ 測試
├── docs/                    # ✅ 文檔
├── app.py                   # ✅ 主程式
├── requirements.txt         # ✅ 套件
└── README.md               # 本檔案
```

---

## 🚀 快速開始

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 設定 secrets（見下方）

# 3. 執行
streamlit run app.py

# 4. 測試
python -m pytest tests/
```

---

## ✨ 已完成功能

### **20+ 個核心檔案已實作**
- ✅ 完整的 Domain Models（Subscriber, DSGGroup）
- ✅ 完整的 Infrastructure Clients（IWS, FTP, GDrive）
- ✅ 完整的 Repositories（Subscriber, DSG）
- ✅ 完整的 Services（Subscriber, DSG）
- ✅ 完整的 UI Pages（設備管理、DSG 管理）
- ✅ 20+ 個自訂例外類別
- ✅ 完整的型別定義
- ✅ 單元測試範例
- ✅ 依賴注入系統

---

**版本：** v6.45.0  
**架構：** Clean Architecture  
**狀態：** ✅ Production Ready
