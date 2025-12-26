"""
IWS Gateway 异步操作示例
适应 5-10 分钟的后台处理时间
"""
import sys
import time
from datetime import datetime, timezone
sys.path.insert(0, '/Users/eliothuo/Downloads/files (1)/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException
import xml.etree.ElementTree as ET

# ========== 憑證配置 ==========
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "FvGr2({sE4V4TJ:"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

class IWSAsyncOperations:
    """IWS 异步操作包装器"""
    
    def __init__(self, gateway: IWSGateway):
        self.gateway = gateway
    
    def check_account_status(self, imei: str) -> dict:
        """
        检查账号当前状态
        
        Returns:
            {
                'status': 'ACTIVE'/'PENDING'/'SUSPENDED'/etc,
                'plan_name': 方案名称,
                'last_updated': 最后更新时间,
                'can_update': 是否可以操作
            }
        """
        try:
            result = self.gateway.search_account(imei)
            if not result['found']:
                return {
                    'status': 'NOT_FOUND',
                    'can_update': False,
                    'message': 'Account not found'
                }
            
            # 使用内部方法获取详细状态
            action_name, soap_body = self.gateway._build_account_search_body(imei)
            response_xml = self.gateway._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            # 解析响应
            root = ET.fromstring(response_xml)
            subscribers = root.findall('.//subscriber')
            
            for subscriber in subscribers:
                imei_elem = subscriber.find('.//imei')
                if imei_elem is not None and imei_elem.text == imei:
                    status_elem = subscriber.find('.//accountStatus')
                    plan_elem = subscriber.find('.//planName')
                    updated_elem = subscriber.find('.//lastUpdated')
                    
                    status = status_elem.text if status_elem is not None else 'UNKNOWN'
                    
                    return {
                        'status': status,
                        'plan_name': plan_elem.text if plan_elem is not None else 'N/A',
                        'last_updated': updated_elem.text if updated_elem is not None else 'N/A',
                        'can_update': status not in ['PENDING', 'DEACTIVATED'],
                        'imei': imei,
                        'message': f'Status: {status}'
                    }
            
            return {
                'status': 'UNKNOWN',
                'can_update': False,
                'message': 'Could not parse status'
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'can_update': False,
                'message': str(e)
            }
    
    def resume_subscriber_async(self,
                               imei: str,
                               reason: str = "恢复设备",
                               wait_for_completion: bool = True,
                               max_wait_time: int = 600,  # 10 分钟
                               poll_interval: int = 30) -> dict:
        """
        异步恢复设备（适合 5-10 分钟的处理时间）
        
        Args:
            imei: 设备 IMEI
            reason: 恢复原因
            wait_for_completion: 是否等待完成
            max_wait_time: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
        
        Returns:
            {
                'status': 'SUBMITTED'/'COMPLETED'/'TIMEOUT'/'ERROR',
                'final_status': 最终账号状态,
                'elapsed_time': 耗时（秒）,
                'message': 说明
            }
        """
        print("\n" + "="*80)
        print("🔄 异步恢复设备")
        print("="*80)
        print(f"IMEI: {imei}")
        print(f"等待完成: {wait_for_completion}")
        print(f"最大等待: {max_wait_time} 秒")
        print(f"轮询间隔: {poll_interval} 秒")
        print("="*80 + "\n")
        
        start_time = time.time()
        
        # 阶段 1: 提交请求
        print("[阶段 1] 提交恢复请求...")
        
        try:
            # 尝试调用 API（允许超时）
            try:
                result = self.gateway.resume_subscriber(imei=imei, reason=reason)
                print("✅ 请求已提交并收到响应")
                request_submitted = True
            except Exception as e:
                error_msg = str(e).lower()
                if 'timeout' in error_msg:
                    print("⏰ 请求超时，但可能已被系统接受")
                    request_submitted = True  # 假设已提交
                else:
                    print(f"❌ 提交失败: {e}")
                    return {
                        'status': 'ERROR',
                        'message': str(e),
                        'elapsed_time': int(time.time() - start_time)
                    }
            
            submit_time = int(time.time() - start_time)
            print(f"提交耗时: {submit_time} 秒\n")
            
            # 如果不等待完成，立即返回
            if not wait_for_completion:
                return {
                    'status': 'SUBMITTED',
                    'message': '请求已提交，需要 5-10 分钟处理',
                    'elapsed_time': submit_time,
                    'next_steps': [
                        '等待 5-10 分钟',
                        f'运行: check_account_status("{imei}")',
                        '检查设备是否变为 ACTIVE'
                    ]
                }
            
            # 阶段 2: 等待完成（轮询状态）
            print("[阶段 2] 等待操作完成...")
            print(f"最大等待时间: {max_wait_time} 秒")
            print(f"每 {poll_interval} 秒检查一次状态\n")
            
            last_status = None
            iteration = 0
            
            while time.time() - start_time < max_wait_time:
                iteration += 1
                elapsed = int(time.time() - start_time)
                
                # 检查当前状态
                print(f"[检查 #{iteration}] 耗时: {elapsed} 秒")
                
                try:
                    status_info = self.check_account_status(imei)
                    current_status = status_info.get('status')
                    plan_name = status_info.get('plan_name', 'N/A')
                    
                    # 状态变化时详细输出
                    if current_status != last_status:
                        print(f"  状态变化: {last_status or '初始'} → {current_status}")
                        print(f"  方案: {plan_name}")
                        last_status = current_status
                    else:
                        print(f"  状态: {current_status}")
                    
                    # 检查是否完成
                    if current_status == 'ACTIVE':
                        print(f"\n✅ 操作成功完成！")
                        print(f"总耗时: {elapsed} 秒")
                        return {
                            'status': 'COMPLETED',
                            'final_status': 'ACTIVE',
                            'plan_name': plan_name,
                            'message': '设备已成功恢复',
                            'elapsed_time': elapsed,
                            'iterations': iteration
                        }
                    
                    elif current_status == 'ERROR':
                        print(f"\n❌ 操作失败")
                        return {
                            'status': 'ERROR',
                            'final_status': current_status,
                            'message': status_info.get('message', '操作失败'),
                            'elapsed_time': elapsed
                        }
                    
                    elif current_status not in ['PENDING', 'SUSPENDED']:
                        print(f"\n⚠️  意外状态: {current_status}")
                        return {
                            'status': 'UNEXPECTED',
                            'final_status': current_status,
                            'message': f'账号处于意外状态: {current_status}',
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
            print("   操作可能仍在后台处理中")
            
            return {
                'status': 'TIMEOUT',
                'final_status': last_status or 'UNKNOWN',
                'message': f'操作超时但可能仍在处理中',
                'elapsed_time': elapsed,
                'iterations': iteration,
                'next_steps': [
                    '等待几分钟后再次检查',
                    f'运行: check_account_status("{imei}")',
                    '如果长时间未完成，联系技术支持'
                ]
            }
            
        except Exception as e:
            elapsed = int(time.time() - start_time)
            print(f"\n❌ 发生错误: {e}")
            return {
                'status': 'ERROR',
                'message': str(e),
                'elapsed_time': elapsed
            }


# ========================================
# 测试脚本
# ========================================

if __name__ == "__main__":
    print("="*80)
    print("🧪 IWS 异步操作测试")
    print("="*80)
    print("说明: 此测试适应 IWS 的 5-10 分钟处理时间")
    print("="*80 + "\n")
    
    # 初始化
    gateway = IWSGateway(
        username=IWS_USERNAME,
        password=IWS_PASSWORD,
        sp_account=IWS_SP_ACCOUNT,
        endpoint=IWS_ENDPOINT
    )
    
    async_ops = IWSAsyncOperations(gateway)
    
    # 测试 IMEI
    TEST_IMEI = "300534066711380"  # 使用另一个 IMEI 避免之前的 PENDING
    
    print("测试选项:")
    print("1. 只提交请求（立即返回）")
    print("2. 提交并等待完成（最多 10 分钟）")
    print("3. 只检查当前状态")
    print()
    
    choice = input("请选择 (1/2/3): ").strip()
    
    if choice == "1":
        # 只提交，不等待
        print("\n执行: 只提交请求\n")
        result = async_ops.resume_subscriber_async(
            imei=TEST_IMEI,
            reason="测试异步提交",
            wait_for_completion=False  # 不等待
        )
        
        print("\n" + "="*80)
        print("📊 结果")
        print("="*80)
        for key, value in result.items():
            print(f"{key}: {value}")
        print("="*80)
        
    elif choice == "2":
        # 提交并等待
        print("\n执行: 提交并等待完成（最多 10 分钟）\n")
        result = async_ops.resume_subscriber_async(
            imei=TEST_IMEI,
            reason="测试异步等待",
            wait_for_completion=True,   # 等待完成
            max_wait_time=600,          # 10 分钟
            poll_interval=30            # 30 秒检查一次
        )
        
        print("\n" + "="*80)
        print("📊 最终结果")
        print("="*80)
        for key, value in result.items():
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")
        print("="*80)
        
    elif choice == "3":
        # 只检查状态
        print("\n执行: 检查当前状态\n")
        status = async_ops.check_account_status(TEST_IMEI)
        
        print("\n" + "="*80)
        print("📊 账号状态")
        print("="*80)
        for key, value in status.items():
            print(f"{key}: {value}")
        print("="*80)
        
        if status['status'] == 'PENDING':
            print("\n⏳ 账号仍在 PENDING 状态")
            print("   建议等待 5-10 分钟后再次检查")
        elif status['status'] == 'ACTIVE':
            print("\n✅ 账号已是 ACTIVE 状态")
        elif status['can_update']:
            print("\n✅ 账号可以进行操作")
        else:
            print(f"\n⚠️  账号状态: {status['status']}")
    
    else:
        print("无效选择")
    
    print("\n测试完成")
