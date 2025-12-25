# 🚨 GitHub 手動覆蓋指南

## 📦 檔案

使用這個檔案：**`iws_gateway_CLEAN.py`** 或 **`iws_gateway.py`**（兩者內容相同）

---

## 📋 3 步驟覆蓋

### 步驟 1️⃣: 打開 GitHub 檔案

在瀏覽器中打開：
```
https://github.com/YOUR_USERNAME/YOUR_REPO/blob/main/src/infrastructure/iws_gateway.py
```

點擊 **鉛筆圖示** (Edit this file)

---

### 步驟 2️⃣: 全選刪除舊內容

在 GitHub 編輯器中：
- **全選**: `Ctrl + A` (Windows/Linux) 或 `Cmd + A` (Mac)
- **刪除**: `Delete` 或 `Backspace`

---

### 步驟 3️⃣: 貼上新內容

1. **打開下載的檔案** `iws_gateway_CLEAN.py`
2. **全選**: `Ctrl + A` 或 `Cmd + A`
3. **複製**: `Ctrl + C` 或 `Cmd + C`
4. **回到 GitHub 編輯器**
5. **貼上**: `Ctrl + V` 或 `Cmd + V`
6. **滾動檢查**：確保內容完整
7. **提交**:
   - Commit message: `fix: Update to WSDL-compliant activateSubscriber`
   - 點擊 **"Commit changes"**

---

## ✅ 驗證

提交後，檢查檔案內容：

1. 在 GitHub 上查看檔案
2. 搜尋 `ActivateDevice`（應該找不到）
3. 搜尋 `activateSubscriber`（應該看到多處）
4. 搜尋 `IWS_NS = 'http://www.iridium.com'`（應該看到，注意無結尾斜線）

---

## 🎯 確認清單

- [ ] 打開 GitHub 檔案編輯器
- [ ] 全選並刪除舊內容
- [ ] 複製新檔案內容
- [ ] 貼上到 GitHub 編輯器
- [ ] 檢查內容完整
- [ ] 提交變更
- [ ] 驗證沒有 `ActivateDevice`

---

**完成！系統應該會發送正確的 `activateSubscriber` 指令。** ✅
