import os, sys, hashlib, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify, session as flask_session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, InviteCode, Transaction, BroadcastLedger
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or request.form
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    invite_code = data.get('invite_code', '').strip().upper()

    if not all([username, email, password]):
        return jsonify({'success': False, 'message': '請填寫所有欄位'})

    if len(password) < 6:
        return jsonify({'success': False, 'message': '密碼至少6位'})

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用戶名已存在'})

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '電郵已被註冊'})

    # 如果有邀請碼就驗證，冇嘅就當成公開註冊
    if invite_code:
        code = InviteCode.query.filter_by(code=invite_code).first()
        if not code or not code.is_valid():
            return jsonify({'success': False, 'message': '邀請碼無效或已用盡'})
        code.used_count += 1

    # Generate referral code
    ref_code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=8))

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        invite_code_used=invite_code or '公開註冊',
        referral_code=ref_code,
        usd_balance=10.0  # Welcome bonus
    )
    db.session.add(user)
    db.session.commit()

    # Log transaction
    tx = Transaction(
        user_id=user.id, tx_type='bonus', currency='USD',
        amount=10.0, status='confirmed', description='註冊歡迎獎金',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '註冊成功！歡迎加入 XE 平台',
        'user': {'username': username, 'email': email}
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or request.form
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    user = None
    if username:
        user = User.query.filter_by(username=username).first()
    elif email:
        user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'message': '用戶名/電郵或密碼錯誤'})

    if not user.is_active:
        return jsonify({'success': False, 'message': '帳戶已被禁用'})

    login_user(user, remember=True)
    user.last_withdrawal_reset = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'歡迎回來 {user.username}',
        'user': {
            'id': user.id, 'username': user.username, 'email': user.email,
            'is_admin': user.is_admin, 'kyc_status': user.kyc_status
        }
    })

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True, 'message': '已登出'})

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'is_admin': current_user.is_admin,
            'kyc_status': current_user.kyc_status,
            'kyc_email_verified': current_user.kyc_email_verified,
            'usd_balance': round(current_user.usd_balance, 2),
            'hkd_balance': round(current_user.hkd_balance, 2),
            'tc_balance': round(current_user.tc_balance, 2),
            'bot_usd': round(current_user.bot_usd, 2),
            'bot_btc': round(current_user.bot_btc, 8),
            'bot_eth': round(current_user.bot_eth, 8),
            'bot_usdt': round(current_user.bot_usdt, 2),
            'total_mined_tc': round(current_user.total_mined_tc, 4),
            'is_mining': current_user.is_mining,
            'referral_code': current_user.referral_code,
            'referral_earnings': round(current_user.referral_earnings, 2),
            'kyc_public_id': current_user.kyc_public_id,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else ''
        }
    })
