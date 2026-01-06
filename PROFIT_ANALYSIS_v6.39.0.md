# v6.39.0 利潤分析功能
## 動態價格管理 + 利潤計算

**發布日期：** 2026-01-04  
**版本：** 6.39.0  
**新功能：** 自動計算每個 IMEI 的利潤

---

## ✨ **新功能：**

### **利潤分析顯示**

在助理模式查詢 IMEI 費用時，自動顯示：

```
📈 使用量明細
**使用統計**：
- 總用量：12,345,678 bytes
- 訊息數：520 則
- Mailbox Check：15 次
- Registration：2 次

─────────────────────────

💰 利潤分析

Iridium 成本        本月利潤             利潤率
$45.50             $22.30 ▲ 32.9%      32.9%

從 Iridium 的       客戶收費 -            利潤 / 客戶收費
進貨成本            Iridium 成本          × 100%
```

---

## 🎯 **設計原則：**

### **1. 不寫死價格（Non-Hardcoded）** ✅

```
❌ 舊方式：價格寫死在程式碼中
✅ 新方式：價格存在 JSON 檔案中，可動態調整
```

**兩套價格系統：**

1. **客戶售價**（N3D 售價）
   - 檔案：`price_history.json`
   - 管理器：`PriceManager`
   - 預設值：根據 `SBD_Airtime_STD.pdf`

2. **Iridium 成本價**（進貨價）
   - 檔案：`iridium_cost_price_history.json`
   - 管理器：`IridiumCostPriceManager`
   - 預設值：根據 `SBD_IridiumPrice.pdf`

### **2. 支援價格版本管理** ✅

```python
# 價格變動時，創建新版本
new_price = price_manager.add_new_price(
    plan_name='SBD12',
    monthly_rate=30.00,  # 從 $28 漲到 $30
    effective_date='2026-02-01',
    notes='2月價格調整'
)

# 歷史帳單仍使用當時的價格
bill_jan = calculator.calculate_monthly_bill(
    imei='xxx',
    year=2026,
    month=1,  # 用 1月的價格：$28
    ...
)

bill_feb = calculator.calculate_monthly_bill(
    imei='xxx',
    year=2026,
    month=2,  # 用 2月的價格：$30
    ...
)
```

### **3. 自動計算利潤** ✅

```python
# 系統自動計算
利潤 = 客戶售價 - Iridium 成本價
利潤率 = (利潤 / 客戶售價) × 100%
```

---

## 📊 **價格配置：**

### **客戶售價（N3D）：**

根據 `SBD_Airtime_STD.pdf`（2025/1/7）

| 方案 | 月租費 | 包含流量 | 超量費 | Mailbox | Registration |
|------|--------|----------|--------|---------|--------------|
| SBD0 | $20.00 | 0 bytes | $2.10/KB | $0.02 | $0.02 |
| SBD12 | $28.00 | 12,000 | $2.00/KB | $0.02 | $0.02 |
| SBD17 | $30.00 | 17,000 | $1.60/KB | $0.02 | $0.02 |
| SBD30 | $50.00 | 30,000 | $1.50/KB | $0.02 | $0.02 |

### **Iridium 成本價：**

根據 `SBD_IridiumPrice.pdf`（2025年6月版本）

| 方案 | 月租費 | 包含流量 | 超量費 | Mailbox | Registration |
|------|--------|----------|--------|---------|--------------|
| SBD0 | $10.00 | 0 bytes | $0.75/KB | $0.01 | $0.01 |
| SBD12 | $14.00 | 12,000 | $0.80/KB | $0.01 | $0.01 |
| SBD17 | $15.00 | 17,000 | $1.00/KB | $0.01 | $0.01 |
| SBD30 | $25.00 | 30,000 | $0.75/KB | $0.01 | $0.01 |

### **毛利率分析：**

| 方案 | 月租毛利 | 月租毛利率 | 超量毛利 | 超量毛利率 |
|------|----------|-----------|----------|-----------|
| SBD0 | $10.00 | 50.0% | $1.35/KB | 64.3% |
| SBD12 | $14.00 | 50.0% | $1.20/KB | 60.0% |
| SBD17 | $15.00 | 50.0% | $0.60/KB | 37.5% |
| SBD30 | $25.00 | 50.0% | $0.75/KB | 50.0% |

---

## 💡 **如何調整價格？**

### **方法 1：助理頁面（未來功能）**

```
助理端 → 價格管理 → 調整價格
```

（此功能待實作）

### **方法 2：直接修改 JSON 檔案**

**調整客戶售價：**
```bash
編輯 price_history.json

{
  "plan_name": "SBD12",
  "monthly_rate": 30.00,  # 從 28 改成 30
  "effective_date": "2026-02-01",
  "notes": "2月價格調漲"
}
```

**調整 Iridium 成本價：**
```bash
編輯 iridium_cost_price_history.json

{
  "plan_name": "SBD12",
  "monthly_rate": 15.00,  # 從 14 改成 15
  "effective_date": "2026-03-01",
  "notes": "Iridium 3月調價"
}
```

### **方法 3：使用 API（程式化）**

```python
from src.config.price_rules import get_price_manager, get_cost_price_manager

# 調整客戶售價
price_manager = get_price_manager()
price_manager.add_new_price(
    plan_name='SBD12',
    monthly_rate=30.00,
    overage_per_1000=2.00,
    effective_date='2026-02-01',
    notes='價格調整'
)

# 調整 Iridium 成本價
cost_manager = get_cost_price_manager()
cost_manager.add_new_price(
    plan_name='SBD12',
    monthly_rate=15.00,
    overage_per_1000=0.80,
    effective_date='2026-03-01',
    notes='Iridium 調價'
)
```

---

## 🔧 **技術實作：**

### **新增的檔案：**

1. **iridium_cost_price_history.json**
   - Iridium 成本價格歷史記錄
   - 自動創建，無需手動建立

### **修改的檔案：**

1. **src/config/price_rules.py**
   - 新增 `IRIDIUM_COST_PRICES` 預設價格
   - 新增 `get_cost_price_manager()` 函數
   - 新增 `init_cost_price_manager()` 函數

2. **src/services/billing_calculator.py**
   - `MonthlyBill` 新增利潤欄位
   - `BillingCalculator` 新增成本價管理器
   - `calculate_monthly_bill` 新增利潤計算

3. **render_billing_page.py**
   - 新增利潤分析顯示區塊

---

## 📈 **使用範例：**

### **查詢 IMEI 費用（自動顯示利潤）**

```
助理端 → 費用查詢
IMEI: 300534066711380
月份: 2026/01

結果：
─────────────────────────
📈 使用量明細

**使用統計**：
- 總用量：25,000 bytes
- 計費用量：25,000 bytes  
- 訊息數：150 則
- Mailbox Check：10 次
- Registration：2 次

**費用明細**：
- 月租費：$28.00 (SBD12)
- 超量費：$26.00 (13KB × $2.00)
- Mailbox：$0.20 (10 × $0.02)
- Registration：$0.04 (2 × $0.02)
- **總費用：$54.24**

─────────────────────────
💰 利潤分析

Iridium 成本        本月利潤             利潤率
$24.50             $29.74 ▲ 54.8%      54.8%

成本明細：
- 月租費：$14.00
- 超量費：$10.40 (13KB × $0.80)
- Mailbox：$0.10 (10 × $0.01)
- Registration：$0.02 (2 × $0.01)
```

---

## ✅ **驗證步驟：**

### **步驟 1：部署**

```bash
unzip SBD-v6.39.0-ProfitAnalysis.zip -d sbd-project
cd sbd-project
git add .
git commit -m "v6.39.0 - 利潤分析功能"
git push origin Iridium-IWS
```

### **步驟 2：初次啟動**

第一次啟動時會自動創建：
```
✅ 載入價格歷史...
📥 初始化 Iridium 成本價格...
✅ Iridium 成本價格初始化完成
✅ 價格管理器初始化完成
```

### **步驟 3：查詢測試**

```
助理端 → 費用查詢
IMEI: [任意 IMEI]
月份: 2026/01

應該看到：
💰 利潤分析
Iridium 成本        本月利潤             利潤率
$XX.XX             $XX.XX ▲ XX.X%      XX.X%
```

### **步驟 4：檢查檔案**

```bash
ls -la
應該有：
- price_history.json              (客戶售價)
- iridium_cost_price_history.json (Iridium 成本價)
```

---

## 🎯 **未來改進：**

### **階段 1：價格管理介面（待實作）**

```
助理端 → 價格管理

客戶售價管理：
- 查看歷史價格
- 新增價格版本
- 預覽價格變更影響

Iridium 成本價管理：
- 查看歷史成本
- 更新成本價格
- 成本趨勢分析
```

### **階段 2：利潤報表（待實作）**

```
助理端 → 利潤報表

- 每月利潤統計
- 利潤率趨勢
- 各方案利潤對比
- 高利潤 / 低利潤 IMEI 分析
```

### **階段 3：價格優化建議（待實作）**

```
系統分析：
- 哪些方案利潤率過低
- 建議調整價格策略
- 市場競爭力分析
```

---

## 💡 **重要提醒：**

### **價格變更影響：**

1. **歷史帳單不受影響**
   - 計費時使用當時的價格
   - 價格版本管理確保準確性

2. **新價格立即生效**
   - 下次查詢使用新價格
   - 依 `effective_date` 決定

3. **利潤計算自動更新**
   - 客戶售價或成本價變動
   - 利潤自動重新計算

---

## 🎉 **完成！**

**現在您可以：**
- ✅ 查詢 IMEI 費用時自動看到利潤
- ✅ 動態調整客戶售價
- ✅ 動態調整 Iridium 成本價
- ✅ 追蹤價格變更歷史
- ✅ 分析每個 IMEI 的獲利能力

**所有價格都不是寫死的！** 🚀

**隨時可以調整！** 💪

**立即部署試試看！** ✨
