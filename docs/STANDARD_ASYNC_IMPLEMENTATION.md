# 🎯 标准异步处理实现 - 基于 IWS 文档

## ✅ **您完全正确！**

我之前的方案**不完整**。根据您提供的 IWS 文档，标准做法是：

1. ✅ 提交请求并获取 **TransactionID**
2. ✅ 使用 **getQueueEntry** 轮询处理状态 ← **我遗漏了这个！**
3. ✅ 当状态为 DONE 时，验证账户状态
4. ✅ 如果失败，使用 **getIwsRequest** 获取错误详情 ← **我也遗漏了这个！**

---

## ❌ **我的方案的问题**

### **我建议的（不完整）**

```python
# 只用 accountSearch 轮询
while True:
    status = accountSearch(imei)
    if status == 'ACTIVE':
        break
    sleep(30)
```

**缺点**：
- ❌ 没有使用 TransactionID
- ❌ 没有使用 getQueueEntry（标准方式）
- ❌ 只能看到最终状态，看不到进度（PENDING/WORKING/DONE）
- ❌ 无法获取详细的错误信息

---

## ✅ **正确的实现（基于 IWS 文档）**

### **完整流程**

```
步骤 1: 提交请求
┌─────────────────────────────────────────┐
│ POST accountUpdate / setSubscriberStatus│
│                                         │
│ 响应:                                   │
│   <transactionId>TXN-12345</transactionId>│
└─────────────────────────────────────────┘
          ↓
步骤 2: 使用 TransactionID 轮询队列状态
┌─────────────────────────────────────────┐
│ while True:                             │
│   status = getQueueEntry(TXN-12345)     │
│                                         │
│   if status == 'DONE':                  │
│     break  # 成功                       │
│   elif status == 'ERROR':               │
│     error = getIwsRequest(TXN-12345)    │
│     raise Exception(error)              │
│   elif status in ['PENDING', 'WORKING']:│
│     sleep(30)  # 继续等待              │
└─────────────────────────────────────────┘
          ↓
步骤 3: 验证最终状态
┌─────────────────────────────────────────┐
│ account = getSubscriberAccount(imei)    │
│ verify account.status == 'ACTIVE'       │
└─────────────────────────────────────────┘
```

---

## 📋 **需要添加的 API**

### **1. getQueueEntry (关键！)**

根据 WSDL 文档，这是标准的异步状态查询方法。

**请求示例**：
```xml
<tns:getQueueEntry xmlns:tns="http://www.iridium.com/">
    <request>
        <iwsUsername>IWSN3D</iwsUsername>
        <signature>...</signature>
        <serviceProviderAccountNumber>200883</serviceProviderAccountNumber>
        <timestamp>2025-12-26T03:00:00Z</timestamp>
        <queueEntryId>TXN-12345</queueEntryId>
    </request>
</tns:getQueueEntry>
```

**响应示例**：
```xml
<queueEntry>
    <status>DONE</status>  <!-- PENDING/WORKING/DONE/ERROR -->
    <requestId>TXN-12345</requestId>
    <serviceType>SHORT_BURST_DATA</serviceType>
    <operation>accountUpdate</operation>
    <timestamp>2025-12-26T03:05:23Z</timestamp>
</queueEntry>
```

**Python 实现**：
```python
def get_queue_entry(self, transaction_id: str) -> Dict:
    """
    查询队列条目状态
    
    Args:
        transaction_id: 交易 ID
        
    Returns:
        Dict: {
            'status': 'PENDING'/'WORKING'/'DONE'/'ERROR',
            'operation': 操作类型,
            'timestamp': 时间戳
        }
    """
    action_name = 'getQueueEntry'
    timestamp = self._generate_timestamp()
    signature = self._generate_signature(action_name, timestamp)
    
    body = f'''<tns:getQueueEntry xmlns:tns="{self.IWS_NS}">
        <request>
            <iwsUsername>{self.username}</iwsUsername>
            <signature>{signature}</signature>
            <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
            <timestamp>{timestamp}</timestamp>
            <queueEntryId>{transaction_id}</queueEntryId>
        </request>
    </tns:getQueueEntry>'''
    
    response_xml = self._send_soap_request(
        soap_action=action_name,
        soap_body=body
    )
    
    # 解析响应
    root = ET.fromstring(response_xml)
    status_elem = root.find('.//status')
    operation_elem = root.find('.//operation')
    
    return {
        'status': status_elem.text if status_elem is not None else 'UNKNOWN',
        'operation': operation_elem.text if operation_elem is not None else 'N/A',
        'transaction_id': transaction_id
    }
```

---

### **2. getIwsRequest (错误诊断)**

用于获取失败请求的详细错误信息。

**请求示例**：
```xml
<tns:getIwsRequest xmlns:tns="http://www.iridium.com/">
    <request>
        <iwsUsername>IWSN3D</iwsUsername>
        <signature>...</signature>
        <serviceProviderAccountNumber>200883</serviceProviderAccountNumber>
        <timestamp>2025-12-26T03:00:00Z</timestamp>
        <requestId>TXN-12345</requestId>
    </request>
</tns:getIwsRequest>
```

**响应示例**：
```xml
<iwsRequest>
    <requestId>TXN-12345</requestId>
    <response>原始 SOAP 响应...</response>
    <errorMessage>设备不存在或资费冲突</errorMessage>
</iwsRequest>
```

**Python 实现**：
```python
def get_iws_request(self, transaction_id: str) -> Dict:
    """
    获取 IWS 请求详情（用于错误诊断）
    
    Args:
        transaction_id: 交易 ID
        
    Returns:
        Dict: {
            'response': 原始响应,
            'error_message': 错误信息
        }
    """
    action_name = 'getIwsRequest'
    timestamp = self._generate_timestamp()
    signature = self._generate_signature(action_name, timestamp)
    
    body = f'''<tns:getIwsRequest xmlns:tns="{self.IWS_NS}">
        <request>
            <iwsUsername>{self.username}</iwsUsername>
            <signature>{signature}</signature>
            <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
            <timestamp>{timestamp}</timestamp>
            <requestId>{transaction_id}</requestId>
        </request>
    </tns:getIwsRequest>'''
    
    response_xml = self._send_soap_request(
        soap_action=action_name,
        soap_body=body
    )
    
    # 解析响应
    root = ET.fromstring(response_xml)
    response_elem = root.find('.//response')
    error_elem = root.find('.//errorMessage')
    
    return {
        'transaction_id': transaction_id,
        'response': response_elem.text if response_elem is not None else '',
        'error_message': error_elem.text if error_elem is not None else 'No error message'
    }
```

---

### **3. getSubscriberAccount (详细账户信息)**

获取账户的完整信息（比 accountSearch 更详细）。

**请求示例**：
```xml
<tns:getSubscriberAccount xmlns:tns="http://www.iridium.com/">
    <request>
        <iwsUsername>IWSN3D</iwsUsername>
        <signature>...</signature>
        <serviceProviderAccountNumber>200883</serviceProviderAccountNumber>
        <timestamp>2025-12-26T03:00:00Z</timestamp>
        <subscriberAccountNumber>SUB-49059741895</subscriberAccountNumber>
    </request>
</tns:getSubscriberAccount>
```

**Python 实现**：
```python
def get_subscriber_account(self, account_number: str) -> Dict:
    """
    获取订阅者账户详细信息
    
    Args:
        account_number: 订阅者账号（例如 SUB-49059741895）
        
    Returns:
        Dict: 账户详细信息
    """
    action_name = 'getSubscriberAccount'
    timestamp = self._generate_timestamp()
    signature = self._generate_signature(action_name, timestamp)
    
    body = f'''<tns:getSubscriberAccount xmlns:tns="{self.IWS_NS}">
        <request>
            <iwsUsername>{self.username}</iwsUsername>
            <signature>{signature}</signature>
            <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
            <timestamp>{timestamp}</timestamp>
            <subscriberAccountNumber>{account_number}</subscriberAccountNumber>
        </request>
    </tns:getSubscriberAccount>'''
    
    response_xml = self._send_soap_request(
        soap_action=action_name,
        soap_body=body
    )
    
    # 解析响应（根据实际 WSDL）
    root = ET.fromstring(response_xml)
    status_elem = root.find('.//accountStatus')
    plan_elem = root.find('.//planName')
    
    return {
        'account_number': account_number,
        'status': status_elem.text if status_elem is not None else 'UNKNOWN',
        'plan_name': plan_elem.text if plan_elem is not None else 'N/A'
    }
```

---

## 🔄 **标准异步操作实现**

### **完整的异步恢复设备**

```python
def resume_subscriber_with_tracking(self,
                                   imei: str,
                                   reason: str = "恢复设备",
                                   wait_for_completion: bool = True,
                                   max_wait_time: int = 600,
                                   poll_interval: int = 30) -> Dict:
    """
    标准异步恢复设备（使用 TransactionID + getQueueEntry）
    
    流程:
    1. 提交请求获取 TransactionID
    2. 使用 getQueueEntry 轮询状态
    3. 验证最终账户状态
    4. 如果失败，获取错误详情
    """
    
    print("\n" + "="*80)
    print("🔄 标准异步恢复设备")
    print("="*80)
    print(f"IMEI: {imei}")
    print("="*80 + "\n")
    
    start_time = time.time()
    
    # 步骤 1: 提交请求
    print("[步骤 1] 提交恢复请求...")
    
    try:
        # 先查找账号
        search_result = self.search_account(imei)
        if not search_result['found']:
            raise IWSException(f"Account not found for IMEI: {imei}")
        
        account_number = search_result['subscriber_account_number']
        
        # 提交状态变更
        action_name, soap_body = self._build_set_subscriber_account_status_body(
            imei=imei,
            new_status="ACTIVE",
            reason=reason
        )
        
        response_xml = self._send_soap_request(
            soap_action=action_name,
            soap_body=soap_body,
            timeout=60
        )
        
        # 提取 TransactionID
        transaction_id = self._extract_transaction_id(response_xml)
        
        if not transaction_id:
            print("⚠️  未获取到 TransactionID，回退到账户状态轮询")
            # 回退到原来的方法
            return self._poll_account_status(imei, max_wait_time, poll_interval)
        
        print(f"✅ 请求已提交")
        print(f"   TransactionID: {transaction_id}")
        
        if not wait_for_completion:
            return {
                'status': 'SUBMITTED',
                'transaction_id': transaction_id,
                'message': '请求已提交，需要 5-10 分钟处理'
            }
        
        # 步骤 2: 使用 TransactionID 轮询队列状态
        print("\n[步骤 2] 轮询处理状态...")
        print(f"TransactionID: {transaction_id}")
        print(f"最大等待时间: {max_wait_time} 秒\n")
        
        iteration = 0
        last_status = None
        
        while time.time() - start_time < max_wait_time:
            iteration += 1
            elapsed = int(time.time() - start_time)
            
            print(f"[检查 #{iteration}] 耗时: {elapsed} 秒")
            
            try:
                # 查询队列状态
                queue_info = self.get_queue_entry(transaction_id)
                queue_status = queue_info['status']
                
                # 状态变化时输出
                if queue_status != last_status:
                    print(f"  队列状态: {last_status or '初始'} → {queue_status}")
                    last_status = queue_status
                else:
                    print(f"  队列状态: {queue_status}")
                
                # 检查是否完成
                if queue_status == 'DONE':
                    # 步骤 3: 验证最终账户状态
                    print("\n[步骤 3] 验证最终账户状态...")
                    
                    account_info = self.get_subscriber_account(account_number)
                    final_status = account_info['status']
                    
                    print(f"✅ 操作完成！")
                    print(f"   最终状态: {final_status}")
                    print(f"   总耗时: {elapsed} 秒")
                    
                    return {
                        'status': 'COMPLETED',
                        'transaction_id': transaction_id,
                        'final_status': final_status,
                        'elapsed_time': elapsed,
                        'message': '设备已成功恢复'
                    }
                
                elif queue_status == 'ERROR':
                    # 步骤 4: 获取错误详情
                    print("\n[步骤 4] 获取错误详情...")
                    
                    error_info = self.get_iws_request(transaction_id)
                    error_message = error_info['error_message']
                    
                    print(f"❌ 操作失败")
                    print(f"   错误: {error_message}")
                    
                    return {
                        'status': 'ERROR',
                        'transaction_id': transaction_id,
                        'error_message': error_message,
                        'elapsed_time': elapsed
                    }
                
            except Exception as e:
                print(f"  ⚠️  状态检查失败: {e}")
            
            # 等待后重试
            remaining = max_wait_time - elapsed
            next_check = min(poll_interval, remaining)
            
            if next_check > 0:
                print(f"  等待 {next_check} 秒后重试...\n")
                time.sleep(next_check)
        
        # 超时
        elapsed = int(time.time() - start_time)
        print(f"\n⏰ 操作超时（{elapsed} 秒）")
        
        return {
            'status': 'TIMEOUT',
            'transaction_id': transaction_id,
            'last_queue_status': last_status,
            'elapsed_time': elapsed,
            'message': '操作超时，但可能仍在处理中'
        }
        
    except Exception as e:
        elapsed = int(time.time() - start_time)
        return {
            'status': 'ERROR',
            'message': str(e),
            'elapsed_time': elapsed
        }
```

---

## 📊 **对比：我的方案 vs 标准方案**

| 方面 | 我的方案 | 标准方案（IWS 文档） |
|------|---------|---------------------|
| 状态查询 | accountSearch | ✅ getQueueEntry |
| 使用标识 | IMEI | ✅ TransactionID |
| 状态粒度 | PENDING/ACTIVE | ✅ PENDING/WORKING/DONE/ERROR |
| 错误诊断 | 无 | ✅ getIwsRequest |
| 最终验证 | 无 | ✅ getSubscriberAccount |
| 标准性 | ❌ 非标准 | ✅ IWS 推荐方式 |

---

## 🎯 **下一步行动**

### **1. 添加缺失的 API（优先）**

```python
# 添加到 iws_gateway.py
- get_queue_entry(transaction_id)
- get_iws_request(transaction_id)
- get_subscriber_account(account_number)
```

### **2. 更新异步操作方法**

```python
# 使用标准流程
- resume_subscriber_with_tracking()
- update_plan_with_tracking()
- suspend_subscriber_with_tracking()
```

### **3. 测试验证**

```bash
# 测试标准异步流程
python test_standard_async.py
```

---

## 🙏 **再次感谢！**

**您的反馈非常宝贵！**

我之前的方案：
- ✅ 理解了异步操作的概念
- ✅ 知道需要轮询
- ❌ **但遗漏了 IWS 的标准 API**

您提供的文档：
- ✅ 揭示了 **getQueueEntry**（标准方式）
- ✅ 说明了 **TransactionID** 的使用
- ✅ 提供了 **getIwsRequest**（错误诊断）
- ✅ 完整的异步处理流程

**这是正确的、标准的实现方式！**

---

## 📝 **总结**

### **关键API（我遗漏的）**

1. **getQueueEntry** - 标准的队列状态查询
2. **getIwsRequest** - 错误详情获取
3. **getSubscriberAccount** - 账户信息验证

### **标准流程**

```
提交 → TransactionID → getQueueEntry → 验证 → 完成
```

**这才是 IWS 推荐的标准做法！**

---

**感谢您提供准确的 IWS 文档！这确保了我们的实现符合最佳实践！** 🙏
