import os, sys, hashlib, smtplib, random, string
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Transaction, BroadcastLedger
from datetime import datetime
from config import Config

kyc_bp = Blueprint('kyc', __name__)

def send_verification_email(to_email, code):
    """Send KYC verification code via email"""
    try:
        if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
            server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
            server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            msg = f"""Subject: XE平台 - KYC電郵驗證碼

尊敬的 {current_user.username if current_user.is_authenticated else '用戶'}，

您的KYC電郵驗證碼是: {code}

此驗證碼將在10分鐘後失效。

如非本人操作，請忽略此郵件。

XE平台 (股票及虛擬貨幣平台Xe版)
https://xeplatform.com
"""
            server.sendmail(Config.MAIL_DEFAULT_SENDER, to_email, msg.encode('utf-8'))
            server.quit()
            return True
        else:
            print(f"[EMAIL SANDBOX] Verification code for {to_email}: {code}")
            return False
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

@kyc_bp.route('/status', methods=['GET'])
@login_required
def get_kyc_status():
    return jsonify({
        'success': True,
        'kyc': {
            'status': current_user.kyc_status,
            'email_verified': current_user.kyc_email_verified,
            'real_name': current_user.kyc_real_name,
            'phone': current_user.kyc_phone,
            'public_id': current_user.kyc_public_id,
            'verified_at': current_user.kyc_verified_at.isoformat() if current_user.kyc_verified_at else None
        },
        'required_steps': [
            {'step': 'email', 'name': '電郵驗證', 'completed': current_user.kyc_email_verified},
            {'step': 'identity', 'name': '身份信息', 'completed': bool(current_user.kyc_real_name)},
            {'step': 'submission', 'name': '提交審核', 'completed': current_user.kyc_status == 'submitted'}
        ]
    })

@kyc_bp.route('/send-email-code', methods=['POST'])
@login_required
def send_email_code():
    """Send verification code to user's registered email"""
    code = ''.join(random.choices(string.digits, k=6))
    current_user.kyc_email_code = code
    
    sent = send_verification_email(current_user.email, code)
    db.session.commit()
    
    sandbox_msg = ''
    if not sent:
        sandbox_msg = f' [沙箱模式] 驗證碼: {code}'
    
    return jsonify({
        'success': True,
        'message': f'驗證碼已發送到 {current_user.email}{sandbox_msg}',
        'code': code if not sent else None  # Only show in sandbox
    })

@kyc_bp.route('/verify-email', methods=['POST'])
@login_required
def verify_email_code():
    data = request.get_json() or request.form
    code = data.get('code', '').strip()
    
    if code == current_user.kyc_email_code:
        current_user.kyc_email_verified = True
        current_user.kyc_email_code = ''
        db.session.commit()
        return jsonify({'success': True, 'message': '✅ 電郵驗證成功！'})
    else:
        return jsonify({'success': False, 'message': '❌ 驗證碼錯誤，請重新發送'})

@kyc_bp.route('/submit', methods=['POST'])
@login_required
def submit_kyc():
    """Submit KYC information"""
    data = request.get_json() or request.form
    
    if not current_user.kyc_email_verified:
        return jsonify({'success': False, 'message': '請先完成電郵驗證'})
    
    real_name = data.get('real_name', '').strip()
    id_number = data.get('id_number', '').strip()
    phone = data.get('phone', '').strip()
    
    if not all([real_name, id_number, phone]):
        return jsonify({'success': False, 'message': '請填寫所有KYC資料'})
    
    # Generate public KYC ID (for authentication)
    public_id = hashlib.sha256(f"{current_user.id}{real_name}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16].upper()
    
    current_user.kyc_real_name = real_name
    current_user.kyc_id_number = id_number
    current_user.kyc_phone = phone
    current_user.kyc_status = 'submitted'
    current_user.kyc_public_id = public_id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '✅ KYC資料已提交，等待審核中（通常1-24小時）',
        'public_id': public_id,
        'status': 'submitted'
    })

@kyc_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
def approve_kyc(user_id):
    """Admin: approve KYC"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '管理員權限不足'})
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用戶不存在'})
    
    user.kyc_status = 'verified'
    user.kyc_verified_at = datetime.utcnow()
    
    # Broadcast KYC verification to public ledger
    bl = BroadcastLedger(
        tx_hash=hashlib.sha256(f"KYC:{user.id}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:32],
        user_id=user.id,
        username_public=user.username[:2] + '***',
        tx_type='kyc_verified',
        amount=1.0,
        currency='KYC',
        status='confirmed'
    )
    db.session.add(bl)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'✅ {user.username} 的KYC已通過認證'})

@kyc_bp.route('/public/<public_id>', methods=['GET'])
def public_kyc_lookup(public_id):
    """Public KYC verification - anyone can verify"""
    user = User.query.filter_by(kyc_public_id=public_id).first()
    if not user:
        return jsonify({'success': False, 'message': 'KYC ID不存在'})
    
    return jsonify({
        'success': True,
        'verified': user.kyc_status == 'verified',
        'kyc_info': {
            'public_id': user.kyc_public_id,
            'username': user.username[:2] + '***',
            'status': user.kyc_status,
            'verified_at': user.kyc_verified_at.isoformat() if user.kyc_verified_at else None
        }
    })
