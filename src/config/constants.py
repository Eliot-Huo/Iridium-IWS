"""
系統常數定義
"""

# 資費方案（月租費）
RATE_PLANS = {
    'SBD12': 12.00,   # 基礎方案
    'SBDO': 24.00,    # 標準方案
    'SBD17': 17.00,   # 進階方案
    'SBD30': 30.00,   # 專業方案
}

# 啟用費用
ACTIVATION_FEE = 50.00

# 暫停費用
SUSPENSION_FEE = 0.00
MONTHLY_SUSPENDED_FEE = 5.00  # 暫停期間月費

# 恢復費用
RESUMPTION_FEE = 10.00

# 終止費用
TERMINATION_FEE = 0.00

# FTP 設定
FTP_HOST = "ftp.example.com"
FTP_PORT = 21
FTP_TIMEOUT = 30

# IWS 設定
IWS_TIMEOUT = 60
IWS_MAX_RETRIES = 3

# 系統設定
DEFAULT_TIMEZONE = 'Asia/Taipei'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
