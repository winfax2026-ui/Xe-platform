import os, sys, threading, time
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE_DIR)

from flask import Flask, render_template, redirect, url_for, jsonify, send_from_directory
from flask_login import LoginManager
from flask_cors import CORS
from flask_mail import Mail
from werkzeug.security import generate_password_hash
from models import db, User, InviteCode, GlobalMiningStats, SystemConfig
from config import Config

# Initialize extensions
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__,
        template_folder=os.path.join(_BASE_DIR, '..', 'frontend', 'templates'),
        static_folder=os.path.join(_BASE_DIR, '..', 'frontend', 'static')
    )
    app.config.from_object(Config)
    
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    CORS(app)
    
    login_manager.login_view = '/'
    login_manager.login_message = '請先登入'
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.traffic_coin import tc_bp
    from routes.exchange import exchange_bp
    from routes.stock import stock_bp
    from routes.crypto import crypto_bp
    from routes.payment import payment_bp
    from routes.kyc import kyc_bp
    from routes.tradebot import tradebot_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tc_bp, url_prefix='/traffic-coin')
    app.register_blueprint(exchange_bp, url_prefix='/exchange')
    app.register_blueprint(stock_bp, url_prefix='/stocks')
    app.register_blueprint(crypto_bp, url_prefix='/crypto')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(kyc_bp, url_prefix='/kyc')
    app.register_blueprint(tradebot_bp, url_prefix='/tradebot')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # ── User Loader ──
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # ── Frontend Routes ──
    @app.route('/')
    def home():
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/mining')
    def mining():
        return render_template('mining.html')
    
    @app.route('/exchange-page')
    def exchange_page():
        return render_template('exchange.html')
    
    @app.route('/stocks-page')
    def stocks_page():
        return render_template('stocks.html')
    
    @app.route('/crypto-page')
    def crypto_page():
        return render_template('crypto.html')
    
    @app.route('/wallet')
    def wallet():
        return render_template('wallet.html')
    
    @app.route('/withdraw')
    def withdraw_page():
        return render_template('withdraw.html')
    
    @app.route('/deposit')
    def deposit_page():
        return render_template('deposit.html')
    
    @app.route('/kyc-page')
    def kyc_page():
        return render_template('kyc.html')
    
    @app.route('/tradebot-page')
    def tradebot_page():
        return render_template('tradebot.html')
    
    @app.route('/ledger')
    def ledger():
        return render_template('ledger.html')
    
    @app.route('/admin-panel')
    def admin_panel():
        return render_template('admin.html')
    
    @app.route('/transactions')
    def transactions():
        return render_template('transactions.html')
    
    @app.route('/robots.txt')
    def robots():
        return send_from_directory(app.static_folder, 'robots.txt')
    
    # ── API Health ──
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'platform': 'XE Platform v2.0', 'time': time.time()})
    
    return app

app = create_app()

# ── Auto-seed Database ──
def seed_database():
    with app.app_context():
        db.create_all()
        
        # Create default invite code
        if not InviteCode.query.filter_by(code=Config.DEFAULT_INVITE_CODE).first():
            ic = InviteCode(code=Config.DEFAULT_INVITE_CODE, max_uses=Config.INVITE_CODE_MAX_USES)
            db.session.add(ic)
        
        # Create admin user
        admin = User.query.filter_by(username=Config.ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=Config.ADMIN_USERNAME,
                email=Config.ADMIN_EMAIL,
                password_hash=generate_password_hash(Config.ADMIN_PASSWORD),
                invite_code_used=Config.DEFAULT_INVITE_CODE,
                is_admin=True,
                kyc_status='verified',
                kyc_email_verified=True,
                kyc_real_name='System Admin',
                kyc_id_number='ADMIN0001',
                kyc_phone='+85258088088',
                usd_balance=100000.0,
                tc_balance=1000.0,
                referral_code='XEADMIN'
            )
            db.session.add(admin)
        
        # Create global mining stats
        if not GlobalMiningStats.query.first():
            gs = GlobalMiningStats(total_tc_mined=0, total_mining_seconds=0)
            db.session.add(gs)
        
        db.session.commit()
        print("[SEED] Database initialized successfully")

seed_database()

# ── Background Mining Worker ──
def mining_worker():
    """Process active mining sessions every 5 seconds"""
    with app.app_context():
        from routes.traffic_coin import _active_mining, _mining_lock
        
        while True:
            try:
                with _mining_lock:
                    current_time = time.time()
                    # This is a passive worker - mining earnings are calculated on stop
                    # Active session tracking is handled in routes/traffic_coin.py
                    pass
                time.sleep(5)
            except:
                time.sleep(5)

mining_thread = threading.Thread(target=mining_worker, daemon=True)
mining_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
