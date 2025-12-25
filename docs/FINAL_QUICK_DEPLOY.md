# 🚀 IWS Gateway Final - 快速部署指南

## ⚡ 一鍵部署

```bash
# 1. 備份
mkdir -p backups/final_$(date +%Y%m%d)
cp src/infrastructure/iws_gateway.py backups/final_*/

# 2. 部署
cp iws_gateway.py src/infrastructure/

# 3. 驗證
python3 -c "from src.infrastructure.iws_gateway import IWSGateway; print('✅')"

# 4. 測試
python3 test_iws_final.py
```

---

## 📋 Final 版本主要修正

### v4.0 → Final

| 項目 | v4.0 | Final |
|------|------|-------|
| activateSubscriber | ✅ | ✅ 保持不變 |
| 暫停 SOAP 操作 | ❌ suspendSubscriber | ✅ setSubscriberAccountStatus |
| 恢復 SOAP 操作 | ❌ resumeSubscriber | ✅ setSubscriberAccountStatus |
| 對外 API | suspend_subscriber() | ✅ 保持不變 |

**關鍵改進**: 使用正確的 `setSubscriberAccountStatus` 統一方法

---

## 🎯 正確的 XML 結構

### 啟用設備（保持不變）

```xml
<activateSubscriber xmlns="http://www.iridium.com">
    <request>
        <sbdSubscriberAccount>
            <plan>
                <sbdBundleId>SBD12</sbdBundleId>
                <lritFlagstate></lritFlagstate>
                <ringAlertsFlag>false</ringAlertsFlag>
            </plan>
            <imei>300534066711380</imei>
            <deliveryDetails>
                <deliveryDetail>
                    <destination>192.168.1.100</destination>
                    <deliveryMethod>DIRECT_IP</deliveryMethod>
                    <geoDataFlag>false</geoDataFlag>
                    <moAckFlag>false</moAckFlag>
                </deliveryDetail>
            </deliveryDetails>
        </sbdSubscriberAccount>
    </request>
</activateSubscriber>
```

### 暫停設備（新增）⭐

```xml
<setSubscriberAccountStatus xmlns="http://www.iridium.com">
    <request>
        <serviceType>SHORT_BURST_DATA</serviceType>
        <updateType>IMEI</updateType>
        <value>300534066711380</value>
        <newStatus>SUSPENDED</newStatus>
        <reason>系統自動暫停</reason>
    </request>
</setSubscriberAccountStatus>
```

### 恢復設備（新增）⭐

```xml
<setSubscriberAccountStatus xmlns="http://www.iridium.com">
    <request>
        <serviceType>SHORT_BURST_DATA</serviceType>
        <updateType>IMEI</updateType>
        <value>300534066711380</value>
        <newStatus>ACTIVE</newStatus>
        <reason>系統自動恢復</reason>
    </request>
</setSubscriberAccountStatus>
```

---

## 💡 使用範例

### 啟用

```python
from src.infrastructure.iws_gateway import IWSGateway

gateway = IWSGateway()
result = gateway.activate_subscriber(
    imei='300534066711380',
    plan_id='SBD12'
)
```

### 暫停

```python
result = gateway.suspend_subscriber(
    imei='300534066711380',
    reason='用戶請求暫停'
)
# result['new_status'] == 'SUSPENDED'
```

### 恢復

```python
result = gateway.resume_subscriber(
    imei='300534066711380',
    reason='用戶請求恢復'
)
# result['new_status'] == 'ACTIVE'
```

---

## ✅ 完整功能支援

| 功能 | SOAP 操作 | API 方法 | 狀態 |
|------|----------|----------|------|
| 啟用設備 | activateSubscriber | activate_subscriber() | ✅ |
| 暫停設備 | setSubscriberAccountStatus | suspend_subscriber() | ✅ |
| 恢復設備 | setSubscriberAccountStatus | resume_subscriber() | ✅ |

---

## 🎯 WSDL 合規性

- ✅ activateSubscriberRequestImpl
- ✅ accountStatusChangeRequestImpl
- ✅ 命名空間: http://www.iridium.com
- ✅ RPC/literal 封裝
- ✅ 所有必要元素完整

---

## ✅ 部署檢查清單

- [ ] 備份現有檔案
- [ ] 部署 Final 版本
- [ ] 驗證 Python 導入
- [ ] 執行測試腳本
- [ ] 實際測試啟用
- [ ] 實際測試暫停
- [ ] 實際測試恢復

---

**版本**: Final  
**狀態**: ✅ 準備好全功能部署  
**WSDL 合規**: ✅ 100%
