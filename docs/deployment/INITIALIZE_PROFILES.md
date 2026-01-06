# 初始化 Price Profiles 使用說明

## 📋 **功能說明**

`scripts/initialize_profiles.py` 會創建兩個預設 Price Profiles：

1. **客戶售價 Profile** (customer_2025H1)
2. **Iridium 成本 Profile** (iridium_cost_2025H1)

---

## 🚀 **執行方式**

### **方法 1：從專案根目錄執行**
```bash
python scripts/initialize_profiles.py
```

### **方法 2：作為模組執行**
```bash
python -m scripts.initialize_profiles
```

---

## 📊 **創建的 Profiles**

### **1. 客戶售價 Profile**

**檔案位置：** `price_profiles/customer/customer_2025H1.json`

**基本資訊：**
- Profile ID: `customer_2025H1`
- Profile 名稱: `2025年上半年客戶售價`
- 生效日期: `2025-01-07`
- 備註: `N3D 客戶售價（根據 SBD_Airtime_STD.pdf, 2025/1/7）`

**Standard Plans：**
```
SBD0:
  月租費: $20.00
  包含流量: 0 bytes
  超量費: $2.10/KB
  啟用費: $0.00
  
SBD12:
  月租費: $28.00
  包含流量: 12,000 bytes
  超量費: $2.00/KB
  啟用費: $50.00
  
SBD17:
  月租費: $30.00
  包含流量: 17,000 bytes
  超量費: $1.60/KB
  啟用費: $50.00
  
SBD30:
  月租費: $50.00
  包含流量: 30,000 bytes
  超量費: $1.50/KB
  啟用費: $50.00
```

**DSG Plans：**
```
SBD-12P:
  月租費: $37.80  (= $28.00 × 1.35)
  包含流量: 12,000 bytes
  超量費: $2.70/KB  (= $2.00 × 1.35)
  啟用費: $50.00
  DSG 限制: 2-10,000 ISUs
  
SBD-17P:
  月租費: $40.50  (= $30.00 × 1.35)
  包含流量: 17,000 bytes
  超量費: $2.16/KB  (= $1.60 × 1.35)
  啟用費: $50.00
  DSG 限制: 2-10,000 ISUs
  
SBD-30P:
  月租費: $67.50  (= $50.00 × 1.35)
  包含流量: 30,000 bytes
  超量費: $2.03/KB  (≈ $1.50 × 1.35, 四捨五入)
  啟用費: $50.00
  DSG 限制: 2-10,000 ISUs
```

---

### **2. Iridium 成本 Profile**

**檔案位置：** `price_profiles/iridium_cost/iridium_cost_2025H1.json`

**基本資訊：**
- Profile ID: `iridium_cost_2025H1`
- Profile 名稱: `2025年上半年 Iridium 成本價`
- 生效日期: `2025-06-23`
- 備註: `Iridium 官方成本價（Exhibit B-3.1 & B-3.3, Ver 23 June 2025）`

**Standard Plans：**
```
SBD0:
  月租費: $10.00
  包含流量: 0 bytes
  超量費: $0.75/KB
  啟用費: $0.00
  
SBD12:
  月租費: $14.00
  包含流量: 12,000 bytes
  超量費: $0.80/KB
  啟用費: $30.00
  
SBD17:
  月租費: $15.00
  包含流量: 17,000 bytes
  超量費: $1.00/KB
  啟用費: $30.00
  
SBD30:
  月租費: $25.00
  包含流量: 30,000 bytes
  超量費: $0.75/KB
  啟用費: $30.00
```

**DSG Plans：**
```
SBD-12P:
  月租費: $15.00
  包含流量: 12,000 bytes
  超量費: $1.25/KB
  啟用費: $15.00
  DSG 限制: 2-10,000 ISUs
  
SBD-17P:
  月租費: $17.00
  包含流量: 17,000 bytes
  超量費: $1.00/KB
  啟用費: $15.00
  DSG 限制: 2-10,000 ISUs
  
SBD-30P:
  月租費: $27.00
  包含流量: 30,000 bytes
  超量費: $0.75/KB
  啟用費: $15.00
  DSG 限制: 2-10,000 ISUs
```

---

## 💰 **利潤分析（範例）**

### **SBD12 利潤：**
```
月租利潤:
  客戶: $28.00
  成本: $14.00
  利潤: $14.00 (50.0%)

超量利潤:
  客戶: $2.00/KB
  成本: $0.80/KB
  利潤: $1.20/KB (60.0%)
```

### **SBD-12P (DSG) 利潤：**
```
月租利潤:
  客戶: $37.80
  成本: $15.00
  利潤: $22.80 (60.3%)

超量利潤:
  客戶: $2.70/KB
  成本: $1.25/KB
  利潤: $1.45/KB (53.7%)
```

---

## 🔄 **重新初始化**

如果需要重新創建預設 Profiles：

```bash
# 1. 刪除現有 Profiles
rm -rf price_profiles/

# 2. 重新初始化
python scripts/initialize_profiles.py
```

**注意：** 這會刪除所有自定義的 Profiles！

---

## ✅ **執行輸出範例**

```bash
$ python scripts/initialize_profiles.py

============================================================
🚀 初始化預設 Price Profiles
============================================================
📝 創建客戶售價 Profile...
💾 儲存 Profile: price_profiles/customer/customer_2025H1.json
✅ 客戶售價 Profile 創建完成
📝 創建 Iridium 成本 Profile...
💾 儲存 Profile: price_profiles/iridium_cost/iridium_cost_2025H1.json
✅ Iridium 成本 Profile 創建完成

============================================================
📋 當前 Profiles 列表:
============================================================

🔓 未鎖定 customer_2025H1
   類型: customer
   名稱: 2025年上半年客戶售價
   生效日期: 2025-01-07
   方案數: 7

🔓 未鎖定 iridium_cost_2025H1
   類型: iridium_cost
   名稱: 2025年上半年 Iridium 成本價
   生效日期: 2025-06-23
   方案數: 7

============================================================
✅ 初始化完成！
============================================================
```

---

## 📝 **常見問題**

### **Q: Profile 已存在時會怎樣？**
A: 腳本會檢測到已存在的 Profile 並跳過創建：
```
ℹ️  客戶售價 Profile 已存在: customer_2025H1
ℹ️  Iridium 成本 Profile 已存在: iridium_cost_2025H1
```

### **Q: 可以修改預設 Profile 嗎？**
A: 生效後的 Profile 會自動鎖定，無法修改。如需調整價格：
1. 在 Web UI「Profile 管理」頁面創建新 Profile
2. 或手動編輯 JSON 檔案（生效前）

### **Q: DSG 價格為何是 Standard × 1.35？**
A: 這是 N3D 的定價策略，在 Standard 價格基礎上加 35%

### **Q: 為何客戶 Profile 生效日期是 2025-01-07？**
A: 這是 N3D 客戶售價的實際生效日期（根據 SBD_Airtime_STD.pdf）

### **Q: 為何 Iridium Profile 生效日期是 2025-06-23？**
A: 這是 Iridium Exhibit B 的發布日期（Ver 23 June 2025）

---

## 🎉 **完成！**

執行完成後，系統就可以使用這些 Profiles 進行：
- ✅ 費用計算
- ✅ 利潤分析
- ✅ 價格對比
- ✅ Profile 管理

**立即開始使用！** 🚀
