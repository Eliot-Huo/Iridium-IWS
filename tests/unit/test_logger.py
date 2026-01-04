"""
測試結構化日誌系統

驗證日誌記錄、格式化、敏感資訊過濾等功能。
"""
import json
import logging
from io import StringIO

from src.utils.logger import StructuredLogger, LoggerFactory, get_logger
from src.utils.exceptions import SBDException, ValidationError


class TestStructuredLogger:
    """測試結構化日誌記錄器"""
    
    def test_basic_logging(self):
        """測試基本日誌記錄"""
        # 使用 StringIO 捕捉日誌輸出
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        logger = StructuredLogger('test_logger', enable_console=False)
        logger.logger.addHandler(handler)
        
        # 記錄日誌
        logger.info("Test message", key="value")
        
        # 驗證輸出
        output = stream.getvalue()
        assert "Test message" in output
        assert "INFO" in output
    
    def test_json_format(self):
        """測試 JSON 格式輸出"""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        logger = StructuredLogger('test_json', enable_console=False)
        logger.logger.addHandler(handler)
        
        logger.info("JSON test", user_id="123", action="login")
        
        # 解析 JSON
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        assert log_data['message'] == "JSON test"
        assert log_data['level'] == "INFO"
        assert log_data['user_id'] == "123"
        assert log_data['action'] == "login"
        assert 'timestamp' in log_data
    
    def test_exception_logging(self):
        """測試異常日誌記錄"""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        logger = StructuredLogger('test_exception', enable_console=False)
        logger.logger.addHandler(handler)
        
        # 創建異常
        exc = ValidationError(
            field='imei',
            value='123',
            reason='Too short'
        )
        
        # 記錄異常
        logger.error("Validation failed", exception=exc)
        
        # 驗證輸出
        output = stream.getvalue()
        log_data = json.loads(output.strip())
        
        assert log_data['level'] == "ERROR"
        assert 'exception_details' in log_data
        assert log_data['exception_details']['exception_type'] == 'ValidationError'
    
    def test_sensitive_data_filtering(self):
        """測試敏感資訊過濾"""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        logger = StructuredLogger('test_security', enable_console=False)
        logger.logger.addHandler(handler)
        
        # 記錄包含敏感資訊的日誌
        logger.info(
            "User authenticated",
            username="user123",
            password="secret123",  # 應該被過濾
            api_key="abc-def-ghi"  # 應該被過濾
        )
        
        # 驗證輸出
        output = stream.getvalue()
        log_data = json.loads(output.strip())
        
        # 敏感資訊應該被過濾
        assert log_data['password'] == '***REDACTED***'
        assert log_data['api_key'] == '***REDACTED***'
        # 一般資訊應該保留
        assert log_data['username'] == 'user123'


class TestLoggerFactory:
    """測試日誌工廠"""
    
    def test_singleton_behavior(self):
        """測試單例行為（同名 logger 只創建一次）"""
        logger1 = LoggerFactory.get_logger('my_logger')
        logger2 = LoggerFactory.get_logger('my_logger')
        
        # 應該是同一個實例
        assert logger1 is logger2
    
    def test_different_loggers(self):
        """測試不同名稱的 logger"""
        logger1 = LoggerFactory.get_logger('logger1')
        logger2 = LoggerFactory.get_logger('logger2')
        
        # 應該是不同實例
        assert logger1 is not logger2
    
    def test_configure_global_level(self):
        """測試全域配置"""
        LoggerFactory.configure(level=logging.DEBUG)
        
        logger = LoggerFactory.get_logger('test_config')
        assert logger.logger.level == logging.DEBUG


class TestConvenienceFunction:
    """測試便捷函式"""
    
    def test_get_logger(self):
        """測試 get_logger 便捷函式"""
        logger = get_logger('convenience_test')
        
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == 'convenience_test'


def test_all_log_levels():
    """測試所有日誌等級"""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    
    logger = StructuredLogger('test_levels', level=logging.DEBUG, enable_console=False)
    logger.logger.addHandler(handler)
    
    # 記錄不同等級的日誌
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # 驗證輸出
    output = stream.getvalue()
    lines = output.strip().split('\n')
    
    assert len(lines) == 5
    
    # 驗證每個等級
    log_data = [json.loads(line) for line in lines]
    assert log_data[0]['level'] == 'DEBUG'
    assert log_data[1]['level'] == 'INFO'
    assert log_data[2]['level'] == 'WARNING'
    assert log_data[3]['level'] == 'ERROR'
    assert log_data[4]['level'] == 'CRITICAL'


if __name__ == '__main__':
    # 執行基本測試
    print("Testing StructuredLogger...")
    
    # 測試 1: 基本日誌
    logger = get_logger('test', enable_console=True)
    logger.info("Test info message", user_id="123")
    
    # 測試 2: 異常日誌
    try:
        raise ValidationError(field='test', value='invalid', reason='Test error')
    except ValidationError as e:
        logger.error("Caught validation error", exception=e)
    
    # 測試 3: 敏感資訊過濾
    logger.info("Login attempt", username="user", password="secret")
    
    print("\n✅ Manual tests completed!")
