"""
依賴注入 (Dependency Injection) 模組

提供服務工廠和依賴注入容器。

使用方式：
    >>> from src.di import get_service_factory
    >>> factory = get_service_factory()
    >>> factory.initialize_from_secrets(st.secrets)
    >>> gateway = factory.gateway
"""

from src.di.service_factory import ServiceFactory, get_service_factory

__all__ = [
    'ServiceFactory',
    'get_service_factory',
]
