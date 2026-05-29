import os, sys, hashlib, time, random, platform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()

# ── User ──
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    invite_code_used = db.Column(db.String(20), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # KYC
    kyc_status = db.Column(db.String(20), default='pending')  # pending / verified / rejected
    kyc_email_code = db.Column(db.String(10), default='')
    kyc_email_verified = db.Column(db.Boolean, default=False)
    kyc_real_name = db.Column(db.String(100), default='')
    kyc_id_number = db.Column(db.String(50), default='')
    kyc_phone = db.Column(db.String(30), default='')
    kyc_verified_at = db.Column(db.DateTime, nullable=True)
    kyc_public_id = db.Column(db.String(64), unique=True, nullable=True)  # Public lookup ID

    # Wallets (USD base)
    usd_balance = db.Column(db.Float, default=0.0)
    hkd_balance = db.Column(db.Float, default=0.0)
    tc_balance = db.Column(db.Float, default=0.0)  # Traffic Coin

    # Withdrawal limits
    withdrawn_today_usd = db.Column(db.Float, default=0.0)
    last_withdrawal_reset = db.Column(db.DateTime, default=datetime.utcnow)

    # Trading bot balance
    bot_usd = db.Column(db.Float, default=0.0)
    bot_btc = db.Column(db.Float, default=0.0)
    bot_eth = db.Column(db.Float, default=0.0)
    bot_usdt = db.Column(db.Float, default=0.0)
    bot_hkd = db.Column(db.Float, default=0.0)

    # Referral
    referred_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    referral_earnings = db.Column(db.Float, default=0.0)

    # Mining stats
    total_mined_tc = db.Column(db.Float, default=0.0)
    mining_started_at = db.Column(db.DateTime, nullable=True)
    is_mining = db.Column(db.Boolean, default=False)

    # Two-factor
    totp_secret = db.Column(db.String(32), default='')

    def __repr__(self):
        return f'<User {self.username}>'

# ── Invite Code ──
class InviteCode(db.Model):
    __tablename__ = 'invite_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    max_uses = db.Column(db.Integer, default=100)
    used_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self):
        return self.is_active and self.used_count < self.max_uses

# ── Transaction Log (Broadcast public ledger) ──
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tx_type = db.Column(db.String(30), nullable=False)  # mine / deposit / withdraw / exchange / trade / referral / gift
    currency = db.Column(db.String(10), nullable=False)  # TC / USD / HKD / BTC / ETH / USDT
    amount = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending / confirmed / failed / broadcast
    description = db.Column(db.String(500), default='')
    target = db.Column(db.String(200), default='')  # bank account / wallet address / email
    is_broadcast = db.Column(db.Boolean, default=False)  # Public on ledger
    broadcast_tx_id = db.Column(db.String(64), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='transactions', lazy=True)

    def generate_tx_hash(self):
        raw = f"{self.user_id}{self.tx_type}{self.amount}{self.currency}{time.time()}{random.random()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

# ── Withdrawal Record ──
class Withdrawal(db.Model):
    __tablename__ = 'withdrawals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount_usd = db.Column(db.Float, nullable=False)
    amount_local = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='HKD')
    method = db.Column(db.String(30), nullable=False)  # fps / paypal / wechat / alipay / crypto
    account_info = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / processing / confirmed / failed
    kyc_verified = db.Column(db.Boolean, default=False)
    broadcast_hash = db.Column(db.String(64), unique=True, nullable=True)
    fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='withdrawals', lazy=True)

    def generate_broadcast(self):
        raw = f"WITHDRAW:{self.user_id}:{self.amount_usd}:{self.method}:{time.time()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

# ── Deposit Record ──
class Deposit(db.Model):
    __tablename__ = 'deposits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    method = db.Column(db.String(30), nullable=False)  # fps / paypal / wechat / alipay / crypto
    account_info = db.Column(db.String(500), default='')
    status = db.Column(db.String(20), default='pending')
    tx_hash = db.Column(db.String(64), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='deposits', lazy=True)

# ── Crypto Wallet ──
class CryptoWallet(db.Model):
    __tablename__ = 'crypto_wallets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    currency = db.Column(db.String(10), nullable=False)  # BTC / ETH / USDT / etc
    balance = db.Column(db.Float, default=0.0)
    address = db.Column(db.String(200), unique=True, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='crypto_wallets', lazy=True)

# ── Stock Portfolio ──
class StockPortfolio(db.Model):
    __tablename__ = 'stock_portfolios'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Float, default=0.0)
    avg_price = db.Column(db.Float, default=0.0)
    market = db.Column(db.String(5), default='US')  # US / HK

    user = db.relationship('User', backref='stock_portfolio', lazy=True)

# ── Trade Bot Orders ──
class TradeBotOrder(db.Model):
    __tablename__ = 'trade_bot_orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pair = db.Column(db.String(20), nullable=False)  # BTC/USDT, ETH/USDT
    order_type = db.Column(db.String(10), nullable=False)  # buy / sell
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    filled = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='open')  # open / filled / cancelled
    exchange = db.Column(db.String(20), default='binance')  # binance / bybit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='bot_orders', lazy=True)

# ── Broadcast Ledger (Public) ──
class BroadcastLedger(db.Model):
    __tablename__ = 'broadcast_ledger'
    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username_public = db.Column(db.String(20), nullable=False)  # masked
    tx_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='confirmed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ── Exchange Rate Cache ──
class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rates'
    id = db.Column(db.Integer, primary_key=True)
    pair = db.Column(db.String(20), unique=True, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

# ── Global Mining Stats ──
class GlobalMiningStats(db.Model):
    __tablename__ = 'global_mining_stats'
    id = db.Column(db.Integer, primary_key=True)
    total_tc_mined = db.Column(db.Float, default=0.0)
    total_mining_seconds = db.Column(db.Float, default=0.0)
    total_miners = db.Column(db.Integer, default=0)
    global_rate = db.Column(db.Float, default=1.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

# ── System Config ──
class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
