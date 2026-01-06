"""
Unit Tests - Subscriber Domain Model
訂戶領域模型單元測試範例
"""

import unittest
from datetime import datetime

from src.domain.subscriber import Subscriber
from src.utils.types import SubscriberStatus
from src.utils.exceptions import ValidationError, BusinessRuleViolationError


class TestSubscriber(unittest.TestCase):
    """測試 Subscriber Domain Model"""
    
    def setUp(self):
        """測試前準備"""
        self.valid_imei = "123456789012345"
        self.valid_account = "ACC123"
        self.valid_plan = "SBD12"
    
    def test_create_valid_subscriber(self):
        """測試建立有效訂戶"""
        subscriber = Subscriber(
            imei=self.valid_imei,
            account_number=self.valid_account,
            status=SubscriberStatus.PENDING,
            plan_id=self.valid_plan
        )
        
        self.assertEqual(subscriber.imei, self.valid_imei)
        self.assertEqual(subscriber.status, SubscriberStatus.PENDING)
    
    def test_invalid_imei_raises_error(self):
        """測試無效 IMEI 拋出例外"""
        with self.assertRaises(ValidationError):
            Subscriber(
                imei="123",  # 太短
                account_number=self.valid_account,
                status=SubscriberStatus.PENDING,
                plan_id=self.valid_plan
            )
    
    def test_can_activate_from_pending(self):
        """測試 PENDING 狀態可以啟用"""
        subscriber = Subscriber(
            imei=self.valid_imei,
            account_number=self.valid_account,
            status=SubscriberStatus.PENDING,
            plan_id=self.valid_plan
        )
        
        self.assertTrue(subscriber.can_activate())
    
    def test_cannot_activate_from_active(self):
        """測試 ACTIVE 狀態不能啟用"""
        subscriber = Subscriber(
            imei=self.valid_imei,
            account_number=self.valid_account,
            status=SubscriberStatus.ACTIVE,
            plan_id=self.valid_plan
        )
        
        self.assertFalse(subscriber.can_activate())
    
    def test_activate_changes_status(self):
        """測試啟用改變狀態"""
        subscriber = Subscriber(
            imei=self.valid_imei,
            account_number=self.valid_account,
            status=SubscriberStatus.SUSPENDED,
            plan_id=self.valid_plan
        )
        
        subscriber.activate()
        
        self.assertTrue(subscriber.is_active())
        self.assertIsNotNone(subscriber.activation_date)
    
    def test_cannot_suspend_deactivated_subscriber(self):
        """測試不能暫停已註銷的訂戶"""
        subscriber = Subscriber(
            imei=self.valid_imei,
            account_number=self.valid_account,
            status=SubscriberStatus.DEACTIVATED,
            plan_id=self.valid_plan
        )
        
        self.assertFalse(subscriber.can_suspend())
        
        with self.assertRaises(BusinessRuleViolationError):
            subscriber.suspend()
    
    def test_change_plan_updates_plan_id(self):
        """測試變更方案更新 plan_id"""
        subscriber = Subscriber(
            imei=self.valid_imei,
            account_number=self.valid_account,
            status=SubscriberStatus.ACTIVE,
            plan_id="SBD12"
        )
        
        subscriber.change_plan("SBD17", "升級方案")
        
        self.assertEqual(subscriber.plan_id, "SBD17")
        self.assertIn("SBD12", subscriber.notes)
        self.assertIn("SBD17", subscriber.notes)
    
    def test_to_dict_and_from_dict(self):
        """測試序列化和反序列化"""
        original = Subscriber(
            imei=self.valid_imei,
            account_number=self.valid_account,
            status=SubscriberStatus.ACTIVE,
            plan_id=self.valid_plan,
            customer_name="Test Customer"
        )
        
        # 序列化
        data = original.to_dict()
        
        # 反序列化
        restored = Subscriber.from_dict(data)
        
        self.assertEqual(restored.imei, original.imei)
        self.assertEqual(restored.status, original.status)
        self.assertEqual(restored.customer_name, original.customer_name)


if __name__ == '__main__':
    unittest.main()
