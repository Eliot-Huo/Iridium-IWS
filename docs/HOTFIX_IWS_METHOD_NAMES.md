# 🚨 緊急修正：IWS Gateway 方法名稱不匹配

## ❌ 問題描述

**錯誤訊息**：
```
Unexpected error during IWS execution for request ACT-785794-20251225005634: 
'IWSGateway' object has no attribute 'activate_device'
```

**根本原因**：
- `sbd_service.py` 調用舊的方法名 `activate_device()`
- `iws_gateway.py` 已更新為 `activate_subscriber()`
- 方法名稱不匹配導致執行失敗

---

## ✅ 修正內容

### 檔案：`src/services/sbd_service.py`

**修正位置**：Line 224-232

#### 修正 1: ACTIVATE (Line 225)

**修正前**：
```python
if request.action_type == ActionType.ACTIVATE:
    result = iws_gateway.activate_device(request.imei, request.plan_id)  # ❌
```

**修正後**：
```python
if request.action_type == ActionType.ACTIVATE:
    result = iws_gateway.activate_subscriber(request.imei, request.plan_id)  # ✅
```

#### 修正 2: SUSPEND (Line 228)

**修正前**：
```python
elif request.action_type == ActionType.SUSPEND:
    result = iws_gateway.suspend_device(request.imei)  # ❌
```

**修正後**：
```python
elif request.action_type == ActionType.SUSPEND:
    result = iws_gateway.suspend_subscriber(request.imei)  # ✅
```

#### 修正 3: RESUME (Line 231)

**修正前**：
```python
elif request.action_type == ActionType.RESUME:
    result = iws_gateway.resume_device(request.imei)  # ❌
```

**修正後**：
```python
elif request.action_type == ActionType.RESUME:
    result = iws_gateway.resume_subscriber(request.imei)  # ✅
```

---

## 📋 IWS Gateway 正確方法對照表

| 動作 | 舊方法名稱 (❌) | 新方法名稱 (✅) |
|------|----------------|----------------|
| 啟用 | `activate_device()` | `activate_subscriber()` |
| 暫停 | `suspend_device()` | `suspend_subscriber()` |
| 恢復 | `resume_device()` | `resume_subscriber()` |

---

## 🔍 為什麼會發生這個問題？

1. **IWS Gateway v4.0** 為了符合 WSDL 規範，將方法名稱更新為：
   - `activateSubscriber` → `activate_subscriber()`
   - `setSubscriberAccountStatus` → `suspend_subscriber()` / `resume_subscriber()`

2. **sbd_service.py** 還在使用舊的方法名稱：
   - `activate_device()`
   - `suspend_device()`
   - `resume_device()`

3. **結果**：運行時找不到方法，拋出 `AttributeError`

---

## 🚀 部署步驟

### 緊急修正（單一檔案）

**只需更新 1 個檔案**：
- `src/services/sbd_service.py`

#### GitHub 網頁操作：

1. 開啟 `src/services/sbd_service.py`
2. 點擊「編輯」（鉛筆圖示）
3. 找到 Line 225、228、231
4. 執行以下替換：
   - Line 225: `activate_device` → `activate_subscriber`
   - Line 228: `suspend_device` → `suspend_subscriber`
   - Line 231: `resume_device` → `resume_subscriber`
5. 提交變更

### 完整部署（使用打包）

```bash
# 1. 下載最新的 SBD-Final.tar.gz

# 2. 解壓縮
tar -xzf SBD-Final.tar.gz

# 3. 部署到 GitHub
cd YOUR_REPO
cp -r SBD-Final/* .
git add .
git commit -m "fix: Update IWS Gateway method names in sbd_service"
git push
```

---

## ✅ 驗證測試

部署後，執行以下測試確認修正成功：

### 測試 1: 啟用請求

```python
# 建立啟用請求
request = sbd_service.create_activation_request(
    imei='300534066711380',
    plan_id='SBD12',
    requester='Test User'
)

# 核准並執行
sbd_service.approve_and_execute(
    request_id=request.request_id,
    assistant_name='Test Assistant',
    execute_iws=True
)
```

**預期結果**：
- ✅ 不應該出現 `'IWSGateway' object has no attribute 'activate_device'` 錯誤
- ✅ 應該成功調用 `activate_subscriber()`
- ✅ 請求狀態應該更新為 `EXECUTED` 或保持 `APPROVED`（視 IWS 回應）

### 測試 2: 暫停請求

```python
# 建立暫停請求
request = sbd_service.create_suspend_request(
    imei='300534066711380',
    requester='Test User'
)

# 核准並執行
sbd_service.approve_and_execute(
    request_id=request.request_id,
    assistant_name='Test Assistant',
    execute_iws=True
)
```

**預期結果**：
- ✅ 成功調用 `suspend_subscriber()`

### 測試 3: 恢復請求

```python
# 建立恢復請求
request = sbd_service.create_resume_request(
    imei='300534066711380',
    requester='Test User'
)

# 核准並執行
sbd_service.approve_and_execute(
    request_id=request.request_id,
    assistant_name='Test Assistant',
    execute_iws=True
)
```

**預期結果**：
- ✅ 成功調用 `resume_subscriber()`

---

## 📊 修正影響範圍

| 組件 | 影響 | 狀態 |
|------|------|------|
| IWS Gateway | 無影響 | ✅ 已正確實作 |
| sbd_service.py | **需更新** | ✅ 已修正 |
| cdr_service.py | 無影響 | ✅ 無需修改 |
| app.py | 無影響 | ✅ 無需修改 |
| Repository | 無影響 | ✅ 無需修改 |

---

## 🔧 未來預防措施

### 1. 單元測試

建議添加單元測試以捕捉此類錯誤：

```python
def test_activate_subscriber_method_exists():
    """測試 IWSGateway 是否有 activate_subscriber 方法"""
    gateway = IWSGateway()
    assert hasattr(gateway, 'activate_subscriber')
    assert callable(gateway.activate_subscriber)

def test_sbd_service_calls_correct_methods():
    """測試 SBDService 調用正確的 IWS Gateway 方法"""
    mock_gateway = Mock(spec=IWSGateway)
    service = SBDService(repository, iws_gateway=mock_gateway)
    
    # 測試啟用
    service.approve_and_execute(request_id, 'assistant', True)
    mock_gateway.activate_subscriber.assert_called_once()
```

### 2. 類型檢查

使用 mypy 進行靜態類型檢查：

```bash
mypy src/services/sbd_service.py
```

### 3. 集成測試

在部署前執行完整的集成測試，確保所有組件正確協作。

---

## 🎯 總結

**問題**：方法名稱不匹配  
**原因**：IWS Gateway 已更新，sbd_service 未同步  
**修正**：更新 3 個方法調用  
**影響**：僅 1 個檔案  
**優先級**：🚨 **緊急**（影響核心功能）  

---

**修正狀態**: ✅ 完成  
**測試狀態**: ⚠️ 需驗證  
**部署狀態**: 🚀 準備部署  

**更新日期**: 2025-12-25  
**緊急程度**: 🚨 高  
**預計解決時間**: < 5 分鐘
