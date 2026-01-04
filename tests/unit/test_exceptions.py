"""
測試異常體系

驗證所有異常類別的功能是否正常。
"""
import pytest
from datetime import datetime

from src.utils.exceptions import (
    SBDException,
    ErrorSeverity,
    NetworkError,
    AuthenticationError,
    ValidationError,
    IMEIValidationError,
    ResourceNotFoundError,
    BillingCalculationError,
    IWSException,
    ConfigurationError,
)
from src.utils.security import (
    SensitiveDataFilter,
    mask_imei,
    validate_imei_checksum,
)


class TestSBDException:
    """測試基礎異常類別"""
    
    def test_basic_exception(self):
        """測試基本異常創建"""
        exc = SBDException("Test error")
        
        assert str(exc) == "SBDException: Test error"
        assert exc.message == "Test error"
        assert exc.severity == ErrorSeverity.ERROR
        assert isinstance(exc.timestamp, datetime)
    
    def test_exception_with_details(self):
        """測試包含詳細資訊的異常"""
        exc = SBDException(
            "Test error",
            details={'key': 'value'},
            severity=ErrorSeverity.CRITICAL
        )
        
        assert exc.details == {'key': 'value'}
        assert exc.severity == ErrorSeverity.CRITICAL
    
    def test_exception_to_dict(self):
        """測試異常轉字典"""
        exc = SBDException(
            "Test error",
            details={'field': 'value'},
            context={'user_id': '123'}
        )
        
        result = exc.to_dict()
        
        assert result['exception_type'] == 'SBDException'
        assert result['message'] == 'Test error'
        assert result['details'] == {'field': 'value'}
        assert result['context'] == {'user_id': '123'}
        assert 'timestamp' in result


class TestValidationError:
    """測試驗證錯誤"""
    
    def test_validation_error(self):
        """測試驗證錯誤創建"""
        exc = ValidationError(
            field='imei',
            value='123',
            reason='IMEI must be 15 digits'
        )
        
        assert 'imei' in exc.message
        assert exc.details['field'] == 'imei'
        assert exc.details['value'] == '123'
        assert exc.details['reason'] == 'IMEI must be 15 digits'
    
    def test_imei_validation_error(self):
        """測試 IMEI 驗證錯誤"""
        exc = IMEIValidationError(
            imei='12345',
            reason='Too short'
        )
        
        assert exc.details['field'] == 'imei'
        assert exc.details['value'] == '12345'


class TestNetworkError:
    """測試網路錯誤"""
    
    def test_network_error_with_endpoint(self):
        """測試包含端點的網路錯誤"""
        exc = NetworkError(
            "Connection failed",
            endpoint='https://example.com',
            timeout=30
        )
        
        assert exc.message == "Connection failed"
        assert exc.details['endpoint'] == 'https://example.com'
        assert exc.details['timeout'] == 30


class TestAuthenticationError:
    """測試認證錯誤"""
    
    def test_authentication_error(self):
        """測試認證錯誤"""
        exc = AuthenticationError(
            "Login failed",
            username='testuser'
        )
        
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.details['username'] == 'testuser'


class TestResourceNotFoundError:
    """測試資源不存在錯誤"""
    
    def test_resource_not_found(self):
        """測試資源不存在錯誤"""
        exc = ResourceNotFoundError(
            resource_type='device',
            resource_id='300534066711380'
        )
        
        assert 'Device not found' in exc.message
        assert exc.details['resource_type'] == 'device'
        assert exc.details['resource_id'] == '300534066711380'


class TestIWSException:
    """測試 IWS 異常"""
    
    def test_iws_exception_with_error_code(self):
        """測試包含錯誤代碼的 IWS 異常"""
        exc = IWSException(
            "IWS API failed",
            error_code='IMEI_NOT_FOUND',
            response_text='password=secret api_key=abc123'
        )
        
        assert exc.error_code == 'IMEI_NOT_FOUND'
        # 敏感資訊應該被過濾
        assert 'REDACTED' in exc.details['response_text']
        assert 'secret' not in exc.details['response_text']


class TestSensitiveDataFilter:
    """測試敏感資訊過濾器"""
    
    def test_sanitize_password(self):
        """測試過濾密碼"""
        text = "password=secret123"
        result = SensitiveDataFilter.sanitize(text)
        
        assert 'secret123' not in result
        assert 'REDACTED' in result
    
    def test_sanitize_api_key(self):
        """測試過濾 API Key"""
        text = "api_key=abc123def456"
        result = SensitiveDataFilter.sanitize(text)
        
        assert 'abc123def456' not in result
        assert 'REDACTED' in result
    
    def test_sanitize_multiple_secrets(self):
        """測試過濾多個敏感資訊"""
        text = "password=pwd123 api_key=key456 token=tok789"
        result = SensitiveDataFilter.sanitize(text)
        
        assert 'pwd123' not in result
        assert 'key456' not in result
        assert 'tok789' not in result
        assert result.count('REDACTED') == 3
    
    def test_sanitize_dict(self):
        """測試過濾字典"""
        data = {
            'username': 'user123',
            'password': 'secret',
            'api_key': 'key123'
        }
        
        result = SensitiveDataFilter.sanitize_dict(data)
        
        assert result['username'] == 'user123'
        assert result['password'] == '***REDACTED***'
        assert result['api_key'] == '***REDACTED***'
    
    def test_sanitize_nested_dict(self):
        """測試過濾嵌套字典"""
        data = {
            'user': {
                'name': 'John',
                'password': 'secret'
            }
        }
        
        result = SensitiveDataFilter.sanitize_dict(data)
        
        assert result['user']['name'] == 'John'
        assert result['user']['password'] == '***REDACTED***'


class TestIMEIHelpers:
    """測試 IMEI 輔助函式"""
    
    def test_mask_imei(self):
        """測試 IMEI 遮罩"""
        imei = '300534066711380'
        
        # 預設保留 4 位
        result = mask_imei(imei)
        assert result == '***********1380'
        
        # 保留 6 位
        result = mask_imei(imei, visible_digits=6)
        assert result == '*********711380'
    
    def test_validate_imei_checksum_valid(self):
        """測試有效的 IMEI 檢查碼"""
        # 測試 IMEI（已知有效）
        valid_imei = '300534066711380'
        
        result = validate_imei_checksum(valid_imei)
        assert result is True
    
    def test_validate_imei_checksum_invalid(self):
        """測試無效的 IMEI 檢查碼"""
        # 錯誤的檢查碼
        invalid_imei = '123456789012345'
        
        result = validate_imei_checksum(invalid_imei)
        assert result is False
    
    def test_validate_imei_wrong_length(self):
        """測試錯誤長度的 IMEI"""
        short_imei = '12345'
        
        result = validate_imei_checksum(short_imei)
        assert result is False
    
    def test_validate_imei_non_numeric(self):
        """測試非數字 IMEI"""
        alpha_imei = 'ABC123456789012'
        
        result = validate_imei_checksum(alpha_imei)
        assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
