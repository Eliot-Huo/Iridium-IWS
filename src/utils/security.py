"""
安全工具模組

提供敏感資訊過濾、加密等安全相關功能。

Author: Senior Python Software Architect
Date: 2026-01-04
"""
import re
from typing import Pattern, Dict


class SensitiveDataFilter:
    """
    敏感資訊過濾器
    
    用於清除日誌、錯誤訊息中的敏感資訊（密碼、API Key、Token 等）。
    防止敏感資訊洩露到日誌檔案或錯誤訊息中。
    
    Example:
        >>> text = "password=secret123 api_key=abc123"
        >>> SensitiveDataFilter.sanitize(text)
        'password=***REDACTED*** api_key=***REDACTED***'
    """
    
    # 敏感資訊匹配模式
    PATTERNS: Dict[str, Pattern] = {
        'password': re.compile(
            r'password["\s:=]+([^"\s,}]+)',
            re.IGNORECASE
        ),
        'api_key': re.compile(
            r'api[_-]?key["\s:=]+([^"\s,}]+)',
            re.IGNORECASE
        ),
        'secret': re.compile(
            r'secret["\s:=]+([^"\s,}]+)',
            re.IGNORECASE
        ),
        'token': re.compile(
            r'token["\s:=]+([^"\s,}]+)',
            re.IGNORECASE
        ),
        'authorization': re.compile(
            r'authorization["\s:=]+([^"\s,}]+)',
            re.IGNORECASE
        ),
        'bearer': re.compile(
            r'bearer\s+([^\s,}]+)',
            re.IGNORECASE
        ),
    }
    
    # 替換文字
    REDACTED_TEXT = '***REDACTED***'
    
    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        清除文字中的敏感資訊
        
        Args:
            text: 原始文字
            
        Returns:
            已清除敏感資訊的文字
            
        Example:
            >>> SensitiveDataFilter.sanitize("password=secret")
            'password=***REDACTED***'
        """
        if not text:
            return text
        
        sanitized = text
        
        for pattern_name, pattern in cls.PATTERNS.items():
            sanitized = pattern.sub(
                lambda m: f"{pattern_name}={cls.REDACTED_TEXT}",
                sanitized
            )
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: dict) -> dict:
        """
        清除字典中的敏感資訊
        
        Args:
            data: 原始字典
            
        Returns:
            已清除敏感資訊的字典（新字典）
            
        Example:
            >>> data = {'username': 'user', 'password': 'secret'}
            >>> SensitiveDataFilter.sanitize_dict(data)
            {'username': 'user', 'password': '***REDACTED***'}
        """
        if not isinstance(data, dict):
            return data
        
        # 敏感欄位名稱
        sensitive_keys = {
            'password', 'passwd', 'pwd',
            'api_key', 'apikey', 'api-key',
            'secret', 'token', 'auth',
            'authorization', 'bearer'
        }
        
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                # 敏感欄位，替換值
                sanitized[key] = cls.REDACTED_TEXT
            elif isinstance(value, dict):
                # 遞迴處理字典
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, str):
                # 字串值，檢查是否包含敏感資訊
                sanitized[key] = cls.sanitize(value)
            else:
                # 其他類型，保持原樣
                sanitized[key] = value
        
        return sanitized


def mask_imei(imei: str, visible_digits: int = 4) -> str:
    """
    遮罩 IMEI（保留部分數字）
    
    Args:
        imei: 完整 IMEI
        visible_digits: 顯示的尾數數字數量
        
    Returns:
        遮罩後的 IMEI
        
    Example:
        >>> mask_imei('300534066711380')
        '***********1380'
        >>> mask_imei('300534066711380', visible_digits=6)
        '*********711380'
    """
    if not imei or len(imei) <= visible_digits:
        return imei
    
    mask_length = len(imei) - visible_digits
    return '*' * mask_length + imei[-visible_digits:]


def validate_imei_checksum(imei: str) -> bool:
    """
    驗證 IMEI 檢查碼（Luhn 演算法）
    
    Luhn 演算法：
    1. 從右到左，對奇數位（1, 3, 5...）的數字加倍
    2. 如果加倍後大於 9，則減去 9
    3. 將所有數字相加
    4. 如果總和能被 10 整除，則檢查碼正確
    
    Args:
        imei: 15 位 IMEI 號碼
        
    Returns:
        True 如果檢查碼正確，否則 False
        
    Example:
        >>> validate_imei_checksum('490154203237518')
        True
        >>> validate_imei_checksum('123456789012345')
        False
        
    Note:
        IMEI 的 Luhn 演算法實作可能因來源而異。
        本實作基於 ISO/IEC 7812-1 標準。
        如果驗證失敗，不一定表示 IMEI 無效，
        因為某些舊設備可能使用不同的檢查碼算法。
    """
    if not imei or len(imei) != 15 or not imei.isdigit():
        return False
    
    # Luhn 演算法（從右到左）
    digits = [int(d) for d in imei]
    checksum = 0
    
    for i in range(len(digits) - 1, -1, -1):
        digit = digits[i]
        
        # 從右到左，奇數位置（索引為偶數）的數字需要加倍
        if (len(digits) - 1 - i) % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        
        checksum += digit
    
    return checksum % 10 == 0
