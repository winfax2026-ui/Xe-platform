import os

_BASE = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'xe-platform-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(_BASE, 'xe_platform.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin credentials
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin888'
    ADMIN_EMAIL = 'admin@xeplatform.com'

    # Invite code
    DEFAULT_INVITE_CODE = 'XE2026'
    INVITE_CODE_MAX_USES = 9999

    # Exchange rates (live via CoinGecko, fallback)
    USD_TO_HKD = 7.82
    EUR_TO_USD = 1.08
    GBP_TO_USD = 1.26
    JPY_TO_USD = 0.0067
    CNY_TO_USD = 0.14

    # FPS config (Hong Kong)
    FPS_API_KEY = os.environ.get('FPS_API_KEY', 'fps_sandbox_key')
    FPS_MERCHANT_ID = os.environ.get('FPS_MERCHANT_ID', 'XE_FPS_HK001')
    FPS_PHONE = '+85258088088'
    FPS_EMAIL = 'payment@xeplatform.com'
    FPS_FPS_ID = 'XE168888'

    # PayPal
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', 'sandbox_client_id')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', 'sandbox_secret')
    PAYPAL_MODE = 'sandbox'

    # WeChat Pay HK
    WECHAT_MERCHANT_ID = os.environ.get('WECHAT_MERCHANT_ID', 'wx_hk_merchant')
    WECHAT_API_KEY = os.environ.get('WECHAT_API_KEY', 'wx_sandbox_key')

    # Alipay HK
    ALIPAY_MERCHANT_ID = os.environ.get('ALIPAY_MERCHANT_ID', 'ali_hk_merchant')
    ALIPAY_PRIVATE_KEY = os.environ.get('ALIPAY_PRIVATE_KEY', 'ali_sandbox_key')

    # SMTP for KYC email verification
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@xeplatform.com')

    # Trading API (mock — replace with real Binance/Bybit keys)
    BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY', '')
    BYBIT_API_KEY = os.environ.get('BYBIT_API_KEY', '')

    # Stock market mock API config
    STOCK_API_BASE = 'https://finnhub.io/api/v1'
    STOCK_API_KEY = os.environ.get('STOCK_API_KEY', 'sandbox_cks7e')

    # Mining config
    MINING_SECONDS_PER_TC = 10     # 10 seconds = 1 Traffic Coin
    TC_TO_USD = 1.0                # 1 TC = 1 USD
    MAX_MINING_HOURS_PER_DAY = 24  # No cap for now
    GLOBAL_MINING_RATE = 1.0       # Multiplier

    # Broadcast / public ledger
    BLOCKCHAIN_EXPLORER_URL = 'https://xeplatform.com/ledger'

    # KYC
    KYC_REQUIRED_FOR_WITHDRAWAL = True
    MAX_WITHDRAWAL_PER_DAY_USD = 50000

    # CoinGecko
    COINGECKO_API = 'https://api.coingecko.com/api/v3'
