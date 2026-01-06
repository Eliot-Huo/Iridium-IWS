# DSG 流量管理功能實作總結
**版本：** v6.44.0  
**日期：** 2026-01-06  
**功能：** DSG 流量追蹤與管理系統

---

## 📋 實作內容

### **階段一：修正現有問題** ✅

#### 1. 移除價格管理頁面
- ❌ 刪除選單中的「價格管理」選項
- ✅ 所有價格統一在「Profile 管理」中管理
- 📁 保留檔案：`pages/assistant/price_management.py`（未來可刪除）

#### 2. 新增 DSG 選單
- ✅ 助理端：新增「DSG 流量管理」選項
- ✅ 客戶端：新增「DSG 流量查詢」選項

#### 3. 修復 Profile 初始化警告
- ✅ 當沒有可複製的 Profile 時，顯示「一鍵初始化」按鈕
- ✅ 點擊按鈕自動執行 `scripts/initialize_profiles.py`
- ✅ 初始化成功後自動重新載入頁面

---

## 🛠️ 新增檔案

### **1. DSG Tracker Service**
**路徑：** `src/services/dsg_tracker_service.py`

**功能：**
```python
class DSGTrackerService:
    # Resource Group 管理
    - create_resource_group()           # 建立監控群組
    - add_imeis_to_group()             # 批次加入 IMEI
    - remove_imeis_from_group()        # 批次移除 IMEI
    - get_resource_groups()            # 查詢所有群組
    - get_group_members()              # 查詢群組成員
    
    # Tracker 管理
    - create_tracker()                 # 建立 Tracker
    - create_tracker_profile()         # 建立 Tracker Profile
    - add_tracker_rule()               # 建立 Tracker Rule
    - add_tracker_member()             # 關聯群組到 Tracker
    
    # 流量查詢
    - get_tracker_rules()              # 查詢 Tracker Rules（含用量）
    - calculate_remaining_data()       # 計算剩餘流量
    - get_tracker_usage_log()          # 查詢用量記錄
```

**API 對應：**
- IWS Report API - Resource Group
- IWS Report API - Tracker
- IWS Report API - Tracker Rules
- IWS Report API - Tracker Usage Log

---

### **2. 助理端 DSG 管理頁面**
**路徑：** `pages/assistant/dsg_management.py`

**功能標籤：**

#### Tab 1️⃣: 查看 DSG 流量
```
- 選擇監控群組
- 顯示群組資訊（ID、成員數量）
- 顯示成員列表
- 顯示流量使用情況（開發中）
```

#### Tab 2️⃣: 建立監控群組
```
- 輸入群組名稱（最多40字元）
- 輸入群組描述（最多100字元）
- 建議命名：DSG_客戶名稱_方案名稱
```

#### Tab 3️⃣: 管理群組成員
```
- 選擇群組
- 顯示當前成員列表
- 批次加入 IMEI（支援多行輸入）
- 批次移除 IMEI
- IMEI 格式驗證（15位數字）
```

#### Tab 4️⃣: 設定 Tracker
```
步驟1: 建立 Tracker
  - 輸入 Tracker 名稱
  - 輸入通知 Email
  - 輸入描述

步驟2: 建立 Tracker Profile
  - 輸入 Profile 名稱
  - 設定閾值（KB）

步驟3: 建立 Tracker Rule
  - 輸入 Tracker ID
  - 輸入 Profile ID
  - 設定重置週期（MONTHLY/BILLCYCLE）
  - 設定重置日期

步驟4: 關聯群組到 Tracker
  - 輸入 Tracker ID
  - 輸入 Resource Group ID
```

---

### **3. 客戶端 DSG 查詢頁面**
**路徑：** `pages/customer/dsg_query.py`

**功能：**
```
- 查詢所有可用的 DSG 群組
- 選擇群組查看資訊
- 顯示群組成員數量
- 顯示成員 IMEI 列表
- 流量查詢功能（待完成）
```

**待實作：**
```python
def render_dsg_usage_display():
    """
    顯示流量使用情況（已定義，待整合）
    
    顯示內容：
    - 總配額
    - 已使用流量
    - 剩餘流量 / 超額流量
    - 使用百分比
    - 進度條
    - 下次重置日期
    """
```

---

## 📊 完整流程

### **助理端操作流程**

```
1. 建立監控群組
   ├─ DSG 流量管理 → Tab 2
   ├─ 輸入群組名稱：DSG_客戶A_SBD12P
   ├─ 輸入描述：客戶A的DSG群組，10個IMEI
   └─ ✅ 得到 Group ID: 12345

2. 加入 IMEI
   ├─ DSG 流量管理 → Tab 3
   ├─ 選擇群組：DSG_客戶A_SBD12P
   ├─ 批次加入 IMEI（每行一個）：
   │   300534066711380
   │   300534066716260
   │   ...（共10個）
   └─ ✅ 成功加入 10 個 IMEI

3. 建立 Tracker（一次性設定）
   ├─ DSG 流量管理 → Tab 4
   ├─ 步驟1: 建立 Tracker
   │   ├─ 名稱：Tracker_客戶A_DSG
   │   ├─ Email：admin@n3d.com
   │   └─ ✅ 得到 Tracker ID: 54321
   │
   ├─ 步驟2: 建立 Profile
   │   ├─ 名稱：Profile_120KB_Monthly
   │   ├─ 閾值：120 KB (10個IMEI × 12KB)
   │   └─ ✅ 得到 Profile ID: 67890
   │
   ├─ 步驟3: 建立 Rule
   │   ├─ Tracker ID：54321
   │   ├─ Profile ID：67890
   │   ├─ 重置週期：MONTHLY
   │   ├─ 重置日期：1號
   │   └─ ✅ 得到 Rule ID: 99999
   │
   └─ 步驟4: 關聯群組
       ├─ Tracker ID：54321
       ├─ Group ID：12345
       └─ ✅ 設定完成！

4. 查看流量
   ├─ DSG 流量管理 → Tab 1
   ├─ 選擇群組：DSG_客戶A_SBD12P
   └─ 查看流量使用情況
```

### **客戶端查詢流程**

```
1. 進入 DSG 流量查詢
   └─ 選單：DSG 流量查詢

2. 選擇 DSG 群組
   └─ 看到助理建立的：DSG_客戶A_SBD12P

3. 查看資訊
   ├─ 群組 ID
   ├─ 成員數量
   ├─ IMEI 列表
   └─ 流量使用情況（待完成）
```

---

## ⚠️ 重要提醒

### **Resource Group ≠ 實際 DSG**

```
Resource Group：
  - IWS Report API 的監控工具
  - 用於追蹤流量使用
  - 可以透過 API 建立

實際 DSG：
  - Iridium 計費系統中的共享流量池
  - 必須透過 SPNet Pro 或 Email Support 創建
  - 客戶才能真正共享流量
```

### **DSG 限制**

```
1. 第一次建立 DSG 必須由助理操作
   - 需要至少 2 個 IMEI
   - 透過 SPNet Pro 或 Email Support

2. DSG 成員必須使用相同方案
   - 所有成員繼承群組設定
   - 不能混用 SBD-12P 和 SBD-17P

3. resetCycle 建議
   - 使用 MONTHLY（每月重置）
   - 或 BILLCYCLE（帳單週期）
   - 不要使用 THRESHOLD（會無限重置）
```

---

## 🎯 後續開發

### **優先級 1：整合流量查詢**
```
問題：目前缺少 Resource Group → Tracker 的對應關係

解決方案：
1. 建立對應表（JSON 或 SQLite）
   {
     "group_id": "12345",
     "tracker_id": "54321",
     "threshold_kb": 120
   }

2. 在建立 Tracker 時記錄對應關係

3. 查詢時根據 Group ID 找到 Tracker ID
```

### **優先級 2：自動化設定**
```
一鍵建立完整 DSG 監控：
  
  輸入：
  - 群組名稱
  - IMEI 列表
  - 閾值（KB）
  
  自動執行：
  1. 建立 Resource Group
  2. 加入 IMEI
  3. 建立 Tracker
  4. 建立 Profile
  5. 建立 Rule
  6. 關聯群組
  
  輸出：
  - 完成設定
  - 立即可查詢流量
```

### **優先級 3：視覺化報表**
```
- 流量使用趨勢圖
- 每日用量統計
- 預測超額時間
- 成員用量排行
```

---

## 📁 檔案結構

```
SBD-Project/SBD-Restored/
├── app.py                              (已修改)
│   ├─ 移除「價格管理」選單
│   ├─ 新增「DSG 流量管理」選單（助理）
│   └─ 新增「DSG 流量查詢」選單（客戶）
│
├── src/services/
│   └── dsg_tracker_service.py          (新增)
│       └─ DSG Tracker Service 類別
│
├── pages/
│   ├── assistant/
│   │   ├── dsg_management.py           (新增)
│   │   │   └─ 助理端 DSG 管理頁面
│   │   │
│   │   ├── profile_management.py       (已修改)
│   │   │   └─ 新增一鍵初始化按鈕
│   │   │
│   │   └── price_management.py         (保留，建議刪除)
│   │
│   └── customer/
│       ├── __init__.py                 (新增)
│       └── dsg_query.py                (新增)
│           └─ 客戶端 DSG 查詢頁面
│
└── docs/
    └── DSG_IMPLEMENTATION.md           (本文檔)
```

---

## 🚀 部署步驟

```bash
# 1. 更新程式碼
cd /home/claude/SBD-Project/SBD-Restored

# 2. 初始化 Profiles（如果還沒初始化）
python scripts/initialize_profiles.py

# 3. 測試功能
streamlit run app.py

# 4. Git 提交
git add .
git commit -m "v6.44.0 - Add DSG tracking system"
git push origin Iridium-IWS
```

---

## ✅ 完成清單

- [x] 移除價格管理頁面
- [x] 新增 DSG 選單（助理 + 客戶）
- [x] 修復 Profile 初始化警告
- [x] 實作 DSG Tracker Service
- [x] 實作助理端 DSG 管理頁面
- [x] 實作客戶端 DSG 查詢頁面
- [x] 創建文檔
- [ ] 整合流量查詢（待完成）
- [ ] 自動化設定（待完成）
- [ ] 視覺化報表（待完成）

---

## 📞 聯絡資訊

**如有問題請聯絡：**
- 開發者：Claude
- 日期：2026-01-06
- 版本：v6.44.0
