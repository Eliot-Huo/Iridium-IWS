"""
系統設定配置
安全性要求：所有敏感資訊必須透過 st.secrets 讀取
絕不硬編碼任何帳號、密碼或金鑰
"""
from __future__ import annotations
import os
import json
from typing import Optional, Dict, Any


class ConfigurationError(Exception):
    """配置錯誤異常"""
    pass


def _load_secrets() -> Optional[Any]:
    """
    載入 Streamlit secrets
    
    Returns:
        secrets 物件或 None
    """
    try:
        import streamlit as st
        return st.secrets
    except (ImportError, FileNotFoundError, AttributeError):
        return None


def _get_secret(key: str, default: Any = None, required: bool = False) -> Any:
    """
    安全地從 st.secrets 讀取配置
    
    Args:
        key: 配置鍵名
        default: 預設值
        required: 是否為必要配置
        
    Returns:
        配置值
        
    Raises:
        ConfigurationError: 當必要配置缺失時
    """
    secrets = _load_secrets()
    
    if secrets is not None:
        try:
            value = secrets.get(key, default)
            if value is not None:
                return value
        except Exception:
            pass
    
    # 嘗試從環境變數讀取
    env_value = os.getenv(key, default)
    
    if required and env_value is None:
        raise ConfigurationError(
            f"Required configuration '{key}' is missing. "
            f"Please set it in .streamlit/secrets.toml or environment variables."
        )
    
    return env_value


# ==================== IWS API 設定 ====================
# 從 st.secrets 讀取 IWS 憑證
IWS_USER = _get_secret('IWS_USER', '')
IWS_PASS = _get_secret('IWS_PASS', '')
IWS_ENDPOINT = _get_secret('IWS_ENDPOINT', 'https://ws.iridium.com/services/information.asmx')

# IWS 連線參數
IWS_TIMEOUT = int(_get_secret('IWS_TIMEOUT', '30'))
IWS_MAX_RETRIES = int(_get_secret('IWS_MAX_RETRIES', '3'))


# ==================== FTP 設定 ====================
# 從 st.secrets 讀取 FTP 憑證
FTP_HOST = _get_secret('FTP_HOST', 'cdr.iridium.com')
FTP_USER = _get_secret('FTP_USER', '')
FTP_PASS = _get_secret('FTP_PASS', '')
FTP_PORT = int(_get_secret('FTP_PORT', '21'))

# FTP 連線參數
FTP_TIMEOUT = int(_get_secret('FTP_TIMEOUT', '60'))
FTP_PASSIVE_MODE = _get_secret('FTP_PASSIVE_MODE', True)  # 被動模式（穿透防火牆）


# ==================== GCP 服務帳號設定 ====================
def get_gcp_service_account_json() -> Optional[str]:
    """
    從 st.secrets 讀取 GCP 服務帳號並轉換為 JSON 字串
    
    Returns:
        JSON 字串或 None
    """
    secrets = _load_secrets()
    
    if secrets is not None:
        try:
            gcp_account = secrets.get('gcp_service_account')
            if gcp_account and isinstance(gcp_account, dict):
                return json.dumps(gcp_account)
        except Exception:
            pass
    
    # 嘗試從環境變數讀取
    env_json = os.getenv('GCP_SERVICE_ACCOUNT_JSON')
    return env_json


# GCP 服務帳號 JSON
GCP_SERVICE_ACCOUNT_JSON = get_gcp_service_account_json()


# ==================== 通用設定 ====================
REQUEST_TIMEOUT = int(_get_secret('REQUEST_TIMEOUT', '30'))
DEBUG_MODE = _get_secret('DEBUG_MODE', False)


# ==================== 配置驗證 ====================
def validate_configuration(check_iws: bool = False, check_ftp: bool = False) -> Dict[str, bool]:
    """
    驗證配置完整性
    
    Args:
        check_iws: 是否檢查 IWS 配置
        check_ftp: 是否檢查 FTP 配置
        
    Returns:
        Dict[str, bool]: 驗證結果
    """
    results = {}
    
    if check_iws:
        results['iws_configured'] = bool(IWS_USER and IWS_PASS)
        results['iws_endpoint'] = bool(IWS_ENDPOINT)
    
    if check_ftp:
        results['ftp_configured'] = bool(FTP_USER and FTP_PASS)
        results['ftp_host'] = bool(FTP_HOST)
    
    return results


def get_configuration_status() -> str:
    """
    取得配置狀態摘要
    
    Returns:
        str: 配置狀態描述
    """
    status = []
    
    # IWS 狀態
    if IWS_USER and IWS_PASS:
        status.append("✓ IWS 已配置")
    else:
        status.append("✗ IWS 未配置")
    
    # FTP 狀態
    if FTP_USER and FTP_PASS:
        status.append("✓ FTP 已配置")
    else:
        status.append("✗ FTP 未配置")
    
    # GCP 狀態
    if GCP_SERVICE_ACCOUNT_JSON:
        status.append("✓ GCP 服務帳號已配置")
    else:
        status.append("✗ GCP 服務帳號未配置")
    
    return " | ".join(status)
