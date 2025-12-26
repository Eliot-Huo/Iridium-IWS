"""
IWS Gateway - 标准异步 API 补充
添加 IWS 文档中推荐的队列查询和错误诊断 API
"""
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import time
from datetime import datetime, timezone

# ===== 添加到 IWSGateway 类中的方法 =====

def get_queue_entry(self, transaction_id: str) -> Dict:
    """
    查询队列条目状态（标准异步状态查询）
    
    这是 IWS 推荐的标准方式来追踪异步操作的处理进度。
    
    Args:
        transaction_id: 从 API 响应中获取的 Transaction ID
        
    Returns:
        Dict: {
            'status': 'PENDING'/'WORKING'/'DONE'/'ERROR',
            'transaction_id': 交易ID,
            'operation': 操作类型,
            'timestamp': 时间戳
        }
        
    Example:
        >>> result = gateway.resume_subscriber(imei)
        >>> txn_id = result['transaction_id']
        >>> status = gateway.get_queue_entry(txn_id)
        >>> print(status['status'])  # PENDING/WORKING/DONE/ERROR
    """
    print(f"\n[IWS] 查询队列状态...")
    print(f"Transaction ID: {transaction_id}")
    
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
    
    # 尝试多种路径查找状态
    status_elem = root.find('.//status')
    if status_elem is None:
        status_elem = root.find('.//{http://www.iridium.com/}status')
    
    operation_elem = root.find('.//operation')
    if operation_elem is None:
        operation_elem = root.find('.//{http://www.iridium.com/}operation')
    
    timestamp_elem = root.find('.//timestamp')
    if timestamp_elem is None:
        timestamp_elem = root.find('.//{http://www.iridium.com/}timestamp')
    
    status = status_elem.text if status_elem is not None else 'UNKNOWN'
    
    print(f"[IWS] 队列状态: {status}")
    
    return {
        'status': status,
        'transaction_id': transaction_id,
        'operation': operation_elem.text if operation_elem is not None else 'N/A',
        'timestamp': timestamp_elem.text if timestamp_elem is not None else 'N/A'
    }


def get_iws_request(self, transaction_id: str) -> Dict:
    """
    获取 IWS 请求详情（用于错误诊断）
    
    当队列状态为 ERROR 时，使用此方法获取详细的错误信息。
    
    Args:
        transaction_id: Transaction ID
        
    Returns:
        Dict: {
            'transaction_id': 交易ID,
            'response': 原始SOAP响应,
            'error_message': 错误信息,
            'error_code': 错误代码
        }
        
    Example:
        >>> queue_status = gateway.get_queue_entry(txn_id)
        >>> if queue_status['status'] == 'ERROR':
        >>>     error_info = gateway.get_iws_request(txn_id)
        >>>     print(error_info['error_message'])
    """
    print(f"\n[IWS] 获取请求详情...")
    print(f"Transaction ID: {transaction_id}")
    
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
    if response_elem is None:
        response_elem = root.find('.//{http://www.iridium.com/}response')
    
    error_elem = root.find('.//errorMessage')
    if error_elem is None:
        error_elem = root.find('.//{http://www.iridium.com/}errorMessage')
    
    error_code_elem = root.find('.//errorCode')
    if error_code_elem is None:
        error_code_elem = root.find('.//{http://www.iridium.com/}errorCode')
    
    error_message = error_elem.text if error_elem is not None else 'No error message'
    
    print(f"[IWS] 错误信息: {error_message}")
    
    return {
        'transaction_id': transaction_id,
        'response': response_elem.text if response_elem is not None else '',
        'error_message': error_message,
        'error_code': error_code_elem.text if error_code_elem is not None else 'N/A'
    }


def get_subscriber_account(self, account_number: str) -> Dict:
    """
    获取订阅者账户详细信息（用于最终验证）
    
    在异步操作完成后，使用此方法验证账户的最终状态。
    
    Args:
        account_number: 订阅者账号（例如 SUB-49059741895）
        
    Returns:
        Dict: {
            'account_number': 账号,
            'status': 账户状态,
            'plan_name': 费率方案,
            'imei': IMEI,
            'activation_date': 启用日期,
            'last_updated': 最后更新时间
        }
        
    Example:
        >>> account_info = gateway.get_subscriber_account('SUB-49059741895')
        >>> print(account_info['status'])  # ACTIVE/SUSPENDED/etc
    """
    print(f"\n[IWS] 获取账户信息...")
    print(f"Account: {account_number}")
    
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
    
    # 解析响应
    root = ET.fromstring(response_xml)
    
    # 查找账户信息
    status_elem = root.find('.//accountStatus')
    if status_elem is None:
        status_elem = root.find('.//{http://www.iridium.com/}accountStatus')
    
    plan_elem = root.find('.//planName')
    if plan_elem is None:
        plan_elem = root.find('.//{http://www.iridium.com/}planName')
    
    imei_elem = root.find('.//imei')
    if imei_elem is None:
        imei_elem = root.find('.//{http://www.iridium.com/}imei')
    
    activation_elem = root.find('.//activationDate')
    if activation_elem is None:
        activation_elem = root.find('.//{http://www.iridium.com/}activationDate')
    
    updated_elem = root.find('.//lastUpdated')
    if updated_elem is None:
        updated_elem = root.find('.//{http://www.iridium.com/}lastUpdated')
    
    status = status_elem.text if status_elem is not None else 'UNKNOWN'
    
    print(f"[IWS] 账户状态: {status}")
    
    return {
        'account_number': account_number,
        'status': status,
        'plan_name': plan_elem.text if plan_elem is not None else 'N/A',
        'imei': imei_elem.text if imei_elem is not None else 'N/A',
        'activation_date': activation_elem.text if activation_elem is not None else 'N/A',
        'last_updated': updated_elem.text if updated_elem is not None else 'N/A'
    }


def wait_for_operation_completion(self,
                                  transaction_id: str,
                                  account_number: str,
                                  max_wait_time: int = 600,
                                  poll_interval: int = 30) -> Dict:
    """
    等待异步操作完成（标准 IWS 流程）
    
    使用 TransactionID 轮询 getQueueEntry，
    当状态为 DONE 时验证账户状态。
    
    Args:
        transaction_id: 交易ID
        account_number: 订阅者账号
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
        
    Returns:
        Dict: {
            'status': 'COMPLETED'/'ERROR'/'TIMEOUT',
            'transaction_id': 交易ID,
            'final_account_status': 最终账户状态,
            'elapsed_time': 耗时,
            'message': 说明
        }
    """
    print("\n" + "="*80)
    print("⏳ 等待操作完成（使用 getQueueEntry 轮询）")
    print("="*80)
    print(f"Transaction ID: {transaction_id}")
    print(f"Account: {account_number}")
    print(f"最大等待时间: {max_wait_time} 秒")
    print(f"轮询间隔: {poll_interval} 秒")
    print("="*80 + "\n")
    
    start_time = time.time()
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
                print(f"  队列状态变化: {last_status or '初始'} → {queue_status}")
                last_status = queue_status
            
            # 检查是否完成
            if queue_status == 'DONE':
                print("\n✅ 队列状态为 DONE，验证账户状态...")
                
                # 验证最终账户状态
                account_info = self.get_subscriber_account(account_number)
                final_status = account_info['status']
                
                print(f"✅ 操作成功完成！")
                print(f"   最终账户状态: {final_status}")
                print(f"   费率方案: {account_info['plan_name']}")
                print(f"   总耗时: {elapsed} 秒\n")
                
                return {
                    'status': 'COMPLETED',
                    'transaction_id': transaction_id,
                    'final_account_status': final_status,
                    'plan_name': account_info['plan_name'],
                    'elapsed_time': elapsed,
                    'iterations': iteration,
                    'message': '操作成功完成'
                }
            
            elif queue_status == 'ERROR':
                print("\n❌ 队列状态为 ERROR，获取错误详情...")
                
                # 获取错误详情
                error_info = self.get_iws_request(transaction_id)
                
                print(f"❌ 操作失败")
                print(f"   错误代码: {error_info['error_code']}")
                print(f"   错误信息: {error_info['error_message']}\n")
                
                return {
                    'status': 'ERROR',
                    'transaction_id': transaction_id,
                    'error_code': error_info['error_code'],
                    'error_message': error_info['error_message'],
                    'elapsed_time': elapsed,
                    'message': f"操作失败: {error_info['error_message']}"
                }
            
            elif queue_status in ['PENDING', 'WORKING']:
                print(f"  继续等待... (状态: {queue_status})")
            else:
                print(f"  ⚠️  未知状态: {queue_status}")
            
        except Exception as e:
            print(f"  ⚠️  查询失败: {e}")
        
        # 等待后重试
        remaining = max_wait_time - elapsed
        next_check = min(poll_interval, remaining)
        
        if next_check > 0:
            print(f"  等待 {next_check} 秒后重试...\n")
            time.sleep(next_check)
    
    # 超时
    elapsed = int(time.time() - start_time)
    print(f"\n⏰ 操作超时（{elapsed} 秒）")
    print(f"   最后队列状态: {last_status}")
    print(f"   操作可能仍在后台处理中\n")
    
    return {
        'status': 'TIMEOUT',
        'transaction_id': transaction_id,
        'last_queue_status': last_status,
        'elapsed_time': elapsed,
        'iterations': iteration,
        'message': '操作超时，但可能仍在处理中'
    }


# ===== 使用示例 =====

if __name__ == "__main__":
    """
    演示标准异步流程
    """
    
    # 初始化 Gateway
    from iws_gateway import IWSGateway
    
    gateway = IWSGateway(
        username="IWSN3D",
        password="FvGr2({sE4V4TJ:",
        sp_account="200883",
        endpoint="https://iwstraining.iridium.com:8443/iws-current/iws"
    )
    
    # 示例 1: 恢复设备（标准流程）
    print("="*80)
    print("示例 1: 恢复设备（标准异步流程）")
    print("="*80)
    
    imei = "300534066711380"
    
    # 步骤 1: 提交请求
    print("\n[步骤 1] 提交恢复请求...")
    result = gateway.resume_subscriber(imei=imei, reason="测试标准流程")
    
    if 'transaction_id' not in result or not result['transaction_id']:
        print("❌ 未获取到 TransactionID，无法使用标准流程")
        exit(1)
    
    transaction_id = result['transaction_id']
    print(f"✅ 获取到 TransactionID: {transaction_id}")
    
    # 获取账号
    search_result = gateway.search_account(imei)
    account_number = search_result['subscriber_account_number']
    
    # 步骤 2-3: 等待完成并验证
    print("\n[步骤 2-3] 等待操作完成...")
    final_result = gateway.wait_for_operation_completion(
        transaction_id=transaction_id,
        account_number=account_number,
        max_wait_time=600,
        poll_interval=30
    )
    
    # 输出最终结果
    print("\n" + "="*80)
    print("📊 最终结果")
    print("="*80)
    for key, value in final_result.items():
        print(f"{key}: {value}")
    print("="*80)
