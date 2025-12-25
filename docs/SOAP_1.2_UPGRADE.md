# 🔧 SOAP 1.2 升級報告

## ✅ 架構師審核 WSDL 完成

根據 `iws_training.wsdl`，Iridium IWS 使用 **SOAP 1.2** 而非 SOAP 1.1。

---

## 📋 SOAP 1.1 vs SOAP 1.2 差異

| 項目 | SOAP 1.1 | SOAP 1.2 |
|------|----------|----------|
| **命名空間** | `http://schemas.xmlsoap.org/soap/envelope/` | `http://www.w3.org/2003/05/soap-envelope` |
| **Content-Type** | `text/xml; charset=utf-8` | `application/soap+xml; charset=utf-8` |
| **SOAPAction** | HTTP Header: `SOAPAction: "action"` | Content-Type 中: `action="action"` |
| **Fault Code** | `<faultcode>` | `<soap:Code><soap:Value>` |
| **Fault String** | `<faultstring>` | `<soap:Reason><soap:Text>` |
| **其他命名空間** | 需要 xsi, xsd | 不需要 xsi, xsd |

---

## 🔧 修正內容

### 檔案：`src/infrastructure/iws_gateway.py`

#### 修正 1: 升級 SOAP 版本 (Line 40-42)

**修正前**：
```python
NAMESPACES = {
    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',  # ❌ SOAP 1.1
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',   # ❌ 不需要
    'xsd': 'http://www.w3.org/2001/XMLSchema',            # ❌ 不需要
    'tns': 'http://www.iridium.com'
}
```

**修正後**：
```python
NAMESPACES = {
    'soap': 'http://www.w3.org/2003/05/soap-envelope',  # ✅ SOAP 1.2
    'tns': 'http://www.iridium.com'                      # ✅ 簡化
}
```

#### 修正 2: SOAP Envelope 結構 (Line 110-118)

**修正前**：
```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
```

**修正後**：
```xml
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
```

#### 修正 3: HTTP Headers (Line 202-205)

**修正前**：
```python
headers = {
    'Content-Type': 'text/xml; charset=utf-8',                    # ❌ SOAP 1.1
    'SOAPAction': f'"{soap_action}"',                             # ❌ SOAP 1.1
    'Accept': 'text/xml'
}
```

**修正後**：
```python
headers = {
    'Content-Type': f'application/soap+xml; charset=utf-8; action="{self.IWS_NS}/{soap_action}"',  # ✅ SOAP 1.2
    'Accept': 'application/soap+xml, text/xml'
}
```

#### 修正 4: SOAP Fault 解析 (Line 269-286)

**修正前**（SOAP 1.1）：
```python
faultcode = fault.findtext('faultcode', 'Unknown')
faultstring = fault.findtext('faultstring', 'Unknown error')
```

**修正後**（SOAP 1.2 with 向後相容）：
```python
# SOAP 1.2: soap:Code/soap:Value
code_elem = fault.find('soap:Code/soap:Value', self.NAMESPACES)
if code_elem is None:
    code_elem = fault.find('.//Code/Value')
if code_elem is None:
    code_elem = fault.find('.//faultcode')  # 向後相容 SOAP 1.1

faultcode = code_elem.text if code_elem is not None else 'Unknown'

# SOAP 1.2: soap:Reason/soap:Text
reason_elem = fault.find('soap:Reason/soap:Text', self.NAMESPACES)
if reason_elem is None:
    reason_elem = fault.find('.//Reason/Text')
if reason_elem is None:
    reason_elem = fault.find('.//faultstring')  # 向後相容 SOAP 1.1

faultstring = reason_elem.text if reason_elem is not None else 'Unknown error'
```

---

## 📊 SOAP 1.2 Fault 結構對照

### SOAP 1.1 Fault
```xml
<soap:Fault>
    <faultcode>Client.InvalidIMEI</faultcode>
    <faultstring>Invalid IMEI format</faultstring>
    <detail>...</detail>
</soap:Fault>
```

### SOAP 1.2 Fault
```xml
<soap:Fault>
    <soap:Code>
        <soap:Value>Client.InvalidIMEI</soap:Value>
    </soap:Code>
    <soap:Reason>
        <soap:Text xml:lang="en">Invalid IMEI format</soap:Text>
    </soap:Reason>
    <soap:Detail>...</soap:Detail>
</soap:Fault>
```

---

## 🎯 完整的 SOAP 1.2 請求範例

### activateSubscriber 請求

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
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
                            <destination>0.0.0.0</destination>
                            <deliveryMethod>DIRECT_IP</deliveryMethod>
                            <geoDataFlag>false</geoDataFlag>
                            <moAckFlag>false</moAckFlag>
                        </deliveryDetail>
                    </deliveryDetails>
                </sbdSubscriberAccount>
            </request>
        </activateSubscriber>
    </soap:Body>
</soap:Envelope>
```

### HTTP Headers
```
POST /iws/services/IWSService HTTP/1.1
Content-Type: application/soap+xml; charset=utf-8; action="http://www.iridium.com/activateSubscriber"
Accept: application/soap+xml, text/xml
Authorization: Basic <base64>
```

---

## ✅ 預期結果

升級到 SOAP 1.2 後，應該能夠：

1. ✅ 正確發送符合 WSDL 規範的請求
2. ✅ 接收並解析 Iridium 的真實業務回應
3. ✅ 正確處理 SOAP 1.2 Fault（如 ALREADY_ACTIVE）
4. ✅ 向後相容 SOAP 1.1 回應（如果伺服器混用）

---

## 🧪 驗證測試

### 測試 1: 檢查 SOAP Envelope
```python
gateway = IWSGateway()
envelope = gateway._build_soap_envelope('<test/>')
print(envelope)
# 應該包含: xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
```

### 測試 2: 檢查 HTTP Headers
```python
# 在 _send_soap_request 中檢查
print(headers['Content-Type'])
# 應該是: application/soap+xml; charset=utf-8; action="http://www.iridium.com/activateSubscriber"
```

### 測試 3: 啟用設備
```python
try:
    result = gateway.activate_subscriber(
        imei='300534066711380',
        plan_id='SBD12'
    )
    print(f"✅ Success: {result}")
except IWSException as e:
    print(f"Business Error: {e.error_code}")
    # 應該能正確解析 SOAP 1.2 Fault
```

---

## 📋 修正檔案清單

| 檔案 | 修正內容 | 狀態 |
|------|----------|------|
| `iws_gateway.py` | 升級至 SOAP 1.2 | ✅ 完成 |
| `app.py` | (無需修改) | ✅ OK |
| `sbd_service.py` | (無需修改) | ✅ OK |

---

## 🚀 部署步驟

### 方式 A：單檔案更新（推薦）⭐

**只需更新 1 個檔案**：`src/infrastructure/iws_gateway.py`

#### GitHub 網頁操作：

1. 開啟 `src/infrastructure/iws_gateway.py`
2. 點擊「編輯」（鉛筆圖示）
3. 全選刪除舊內容
4. 貼上新的 `iws_gateway.py` 內容
5. 提交變更

### 方式 B：使用完整打包

```bash
# 下載 SBD-Final.tar.gz
tar -xzf SBD-Final.tar.gz
cd YOUR_REPO
cp -r SBD-Final/* .
git add .
git commit -m "feat: Upgrade to SOAP 1.2 specification"
git push
```

---

## 🎉 完成後的預期改進

1. **符合 WSDL 規範** ✅
   - 正確使用 SOAP 1.2 命名空間
   - 正確的 Content-Type 格式
   - 無多餘的 xsi/xsd 命名空間

2. **真實業務回應** ✅
   - 能正確接收 Iridium 的回應
   - 能正確解析業務錯誤（如 ALREADY_ACTIVE）
   - Transaction ID 提取正確

3. **向後相容** ✅
   - 同時支援 SOAP 1.2 和 SOAP 1.1 回應
   - Fault 解析兼容兩個版本

4. **程式碼品質** ✅
   - 清晰的註解說明 SOAP 1.2 規範
   - 完整的錯誤處理
   - 便於維護和擴展

---

**升級版本**: v4.0 → v4.1  
**SOAP 版本**: 1.1 → 1.2  
**狀態**: ✅ **準備部署**

---

**更新日期**: 2025-12-25  
**審核人員**: 架構師  
**結論**: 🎊 **完全符合 WSDL 規範，準備接收真實業務回應**
