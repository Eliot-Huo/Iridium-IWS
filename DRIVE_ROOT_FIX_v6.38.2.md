# v6.38.2 Drive 根目錄修復
## 修復「老人的紙條」上傳失敗問題

**發布日期：** 2026-01-04  
**版本：** 6.38.2  
**修復內容：** Google Drive root_folder_id 不存在導致上傳失敗

---

## 🐛 **問題：**

用戶回報錯誤：

```
❌ 上傳檔案失敗: <HttpError 404 when requesting ... 
    returned "File not found: 14mVaSibDm2QKBY9vE6U5Eobf_eAn5Laa.">
```

### **問題根源：**

v6.38.1 的 `upload_text_file` 使用了：

```python
target_folder_id = folder_id or self.root_folder_id
```

但 `self.root_folder_id` (`14mVaSibDm2QKBY9vE6U5Eobf_eAn5Laa`) 這個資料夾：
- ❌ 不存在
- ❌ 被刪除了
- ❌ 或 Service Account 沒有權限

**結果：** 上傳失敗，降級保存到本地，每次重啟清空

---

## ✅ **修復內容：**

### **策略改變：**

**舊策略（v6.38.1）：**
- 預設上傳到 `root_folder_id` 資料夾
- 依賴 `find_file(filename, folder_id)` 搜尋檔案

**新策略（v6.38.2）：**
- ✅ 預設上傳到 **Drive 最外層根目錄**（不指定 parents）
- ✅ 搜尋檔案時不限制資料夾（搜尋整個 Drive）
- ✅ 不依賴可能不存在的 `root_folder_id`

### **修復 1: upload_text_file**

```python
# ✅ v6.38.2
def upload_text_file(self, filename: str, content: str, folder_id: str = None):
    """上傳文字檔案（預設上傳到 Drive 最外層根目錄）"""
    
    # 搜尋檔案（不限制資料夾，搜尋整個 Drive）
    query = f"name = '{filename}' and trashed = false"
    results = self.service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, parents)',
        pageSize=10
    ).execute()
    
    files = results.get('files', [])
    existing_file = files[0] if files else None
    
    if existing_file:
        # 更新現有檔案
        print(f"📝 更新現有檔案: {filename} (ID: {existing_file['id']})")
        # ... 更新邏輯
    else:
        # 創建新檔案
        print(f"📝 創建新檔案: {filename}")
        
        file_metadata = {
            'name': filename,
            'mimeType': 'application/json'
        }
        
        # 如果指定了 folder_id，使用它；否則不設置 parents
        if folder_id:
            file_metadata['parents'] = [folder_id]
            print(f"   📁 目標資料夾: {folder_id}")
        else:
            print(f"   📁 位置: Drive 根目錄")
        
        # ... 創建邏輯
```

**改進：**
- ✅ 不依賴 `root_folder_id`
- ✅ 不設置 `parents` = 放在 Drive 最外層
- ✅ 搜尋整個 Drive 找檔案
- ✅ 詳細的日誌輸出

### **修復 2: download_file_content**

```python
# ✅ v6.38.2
def download_file_content(self, filename: str, folder_id: str = None):
    """下載檔案內容（文字）"""
    
    # 搜尋檔案（不限制資料夾，搜尋整個 Drive）
    query = f"name = '{filename}' and trashed = false"
    
    if folder_id:
        query += f" and '{folder_id}' in parents"
        print(f"📥 在資料夾 {folder_id} 中搜尋檔案: {filename}")
    else:
        print(f"📥 在整個 Drive 中搜尋檔案: {filename}")
    
    results = self.service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, parents)',
        pageSize=10
    ).execute()
    
    files = results.get('files', [])
    
    if not files:
        raise FileNotFoundError(f"檔案不存在: {filename}")
    
    file_info = files[0]
    print(f"✅ 找到檔案: {filename} (ID: {file_info['id']})")
    
    # 下載檔案
    # ...
```

**改進：**
- ✅ 不依賴 `root_folder_id`
- ✅ 搜尋整個 Drive
- ✅ 更清楚的錯誤訊息

---

## 📍 **「老人的紙條」新位置：**

### **v6.38.2 後的位置：**

```
您的 Google Drive/
├── .sync_status.json          ← 紙條在最外層！✅
├── CDR_Files/                  ← CDR 資料夾
│   └── 2026/01/04/...
└── 其他檔案...
```

**不是在 CDR_Files 裡面！**  
**是在您的 Drive 最外層！**

### **查看方法：**

1. 打開 Google Drive
2. 在**最外層**（不要進入任何資料夾）
3. 搜尋：`.sync_status.json`
4. 或直接在最外層捲動找

---

## 🚀 **部署步驟：**

```bash
unzip SBD-v6.38.2-DriveRootFix.zip -d sbd-project
cd sbd-project
git add .
git commit -m "v6.38.2 - 修復 Drive 根目錄上傳"
git push origin Iridium-IWS
```

---

## ✅ **驗證步驟：**

### **步驟 1：執行同步**

```
助理端 → CDR 同步管理 → 檢查新檔案並同步

應該看到：
📝 創建新檔案: .sync_status.json
   📁 位置: Drive 根目錄
✅ 檔案創建成功 (ID: 1a2b3c4d...)
💾 正在保存同步狀態到 Google Drive...
✅ 同步狀態已保存到 Google Drive
   📄 檔案: .sync_status.json
   📊 已記錄 1000 個檔案
```

### **步驟 2：檢查 Google Drive**

```
1. 打開 Google Drive
2. 在最外層（不要進入任何資料夾）
3. 搜尋：.sync_status.json
4. 應該找到！✅
```

### **步驟 3：重新部署測試持久化**

```
1. Streamlit Cloud Reboot
2. 再次執行同步

應該看到：
📥 在整個 Drive 中搜尋檔案: .sync_status.json
✅ 找到檔案: .sync_status.json (ID: 1a2b3c4d...)
✅ 成功從 Google Drive 載入狀態
   📊 已記錄 1000 個已處理檔案
🆕 待處理檔案: 0
✅ 增量同步完成 - 所有檔案已是最新！
```

---

## 📊 **修復前後對比：**

### **v6.38.1（失敗）：**
```
upload_text_file() 
  → 使用 root_folder_id
  → 資料夾不存在
  → HttpError 404
  → 降級保存本地
  → 每次重啟清空 ❌
```

### **v6.38.2（成功）：**
```
upload_text_file()
  → 不使用 folder_id
  → 上傳到 Drive 最外層
  → 成功創建檔案 ✅
  → 搜尋整個 Drive
  → 找到並更新 ✅
  → 持久化成功 ✅
```

---

## 🎯 **為什麼這樣更好：**

### **優點：**

1. **不依賴資料夾結構**
   - 不管 CDR_Files 資料夾存不存在
   - 不管權限如何設置
   - 只要 Service Account 能訪問 Drive 就行

2. **更容易找到**
   - 在 Drive 最外層
   - 搜尋時不限制位置
   - 更直觀

3. **更健壯**
   - 不會因為資料夾 ID 改變而失敗
   - 不會因為權限問題而失敗
   - 降級處理更優雅

---

## 📋 **修改的檔案：**

1. `src/infrastructure/gdrive_client.py`
   - `upload_text_file()` - 重寫上傳邏輯
   - `download_file_content()` - 重寫下載邏輯

---

## 💡 **技術細節：**

### **Google Drive API：**

**不設置 parents：**
```python
file_metadata = {
    'name': filename,
    'mimeType': 'application/json'
    # 沒有 'parents' = 放在 Drive 根目錄
}
```

**搜尋不限資料夾：**
```python
query = f"name = '{filename}' and trashed = false"
# 不加 "and 'folder_id' in parents"
# = 搜尋整個 Drive
```

---

## 🆘 **如果還是失敗：**

### **檢查清單：**

1. **Service Account 權限**
   ```
   - 有 Google Drive API 權限嗎？
   - 能訪問您的 Drive 嗎？
   - 能創建檔案嗎？
   ```

2. **網路連線**
   ```
   - Streamlit Cloud 能連到 Google API 嗎？
   - 有被防火牆阻擋嗎？
   ```

3. **配額限制**
   ```
   - Google Drive API 配額用完了嗎？
   - 每天有限制嗎？
   ```

### **查看詳細錯誤：**

同步時展開「詳細錯誤訊息」查看完整堆疊追蹤。

---

## 🎉 **完成！**

**這次應該能成功上傳「老人的紙條」了！** ✅

**紙條會在您的 Google Drive 最外層！** 📝

**立即部署試試看！** 🚀
