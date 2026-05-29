import sys
sys.path.insert(0, '.')
from app import app
from models import db, User, InviteCode, Transaction
from werkzeug.security import generate_password_hash
import random

with app.app_context():
    # 先確保邀請碼存在
    code = InviteCode.query.filter_by(code='XE2026').first()
    if not code:
        code = InviteCode(code='XE2026', max_uses=9999, is_active=True)
        db.session.add(code)
        db.session.flush()
    
    username = 'winfax'
    email = 'winfax2026@gmail.com'
    
    existing = User.query.filter_by(username=username).first()
    if existing:
        print(f'✅ 用戶 {username} 已經存在')
        print(f'   密碼: winfax888')
        print(f'   USD: {existing.usd_balance}')
        print(f'   TC: {existing.tc_balance}')
        print(f'   KYC: {existing.kyc_status}')
    else:
        ref_code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=8))
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash('winfax888'),
            invite_code_used='XE2026',
            referral_code=ref_code,
            usd_balance=1000.0,
            tc_balance=100.0,
            kyc_status='verified',
            kyc_email_verified=True,
            kyc_real_name='Winfax User',
            kyc_id_number='HKID123456',
            kyc_phone='+85258088088'
        )
        db.session.add(user)
        code.used_count += 1
        db.session.commit()  # Commit FIRST so user has an ID
        
        # Now add transaction with the real user_id
        tx = Transaction(
            user_id=user.id,
            tx_type='bonus', currency='USD',
            amount=1000.0, status='confirmed',
            description='管理員開戶獎金',
            is_broadcast=False
        )
        tx.tx_hash = tx.generate_tx_hash()
        db.session.add(tx)
        db.session.commit()
        
        print(f'✅ 用戶 {username} 創建成功！')
        print(f'   Email: {email}')
        print(f'   密碼: winfax888')
        print(f'   USD: 1000.0')
        print(f'   TC: 100.0')
        print(f'   KYC: ✅ 已認證')
