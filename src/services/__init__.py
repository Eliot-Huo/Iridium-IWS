"""
服務層模組

提供業務邏輯與協調層服務。

可用的服務：
- SBDService: SBD 業務邏輯服務
- CDRService: CDR 協調服務
"""

from .sbd_service import SBDService
from .cdr_service import CDRService, SimpleCDRRecord, CDRServiceException

__all__ = [
    'SBDService',
    'CDRService',
    'SimpleCDRRecord',
    'CDRServiceException',
]
