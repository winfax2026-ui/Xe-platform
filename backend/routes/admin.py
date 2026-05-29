import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, InviteCode, Transaction, BroadcastLedger, GlobalMiningStats
from datetime import datetime, timedelta
import random, string

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '權限不足'})
    
    total_users = User.query.count()
    total_verified_kyc = User.query.filter_by(kyc_status='verified').count()
    total_pending_kyc = User.query.filter_by(kyc_status='submitted').count()
    gs = GlobalMiningStats.query.first()
    
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(20).all()
    
    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'verified_kyc': total_verified_kyc,
            'pending_kyc': total_pending_kyc,
            'total_tc_mined': round(gs.total_tc_mined, 2) if gs else 0,
            'total_mining_seconds': round(gs.total_mining_seconds, 0) if gs else 0,
            'active_miners': gs.total_miners if gs else 0
        },
        'recent_transactions': [{
            'id': t.id, 'tx_hash': t.tx_hash,
            'type': t.tx_type, 'currency': t.currency,
            'amount': t.amount, 'status': t.status,
            'created_at': t.created_at.isoformat()
        } for t in recent_transactions]
    })

@admin_bp.route('/users', methods=['GET'])
@login_required
def list_users():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '權限不足'})
    
    users = User.query.order_by(User.created_at.desc()).limit(100).all()
    return jsonify({
        'success': True,
        'users': [{
            'id': u.id, 'username': u.username, 'email': u.email,
            'kyc_status': u.kyc_status, 'is_admin': u.is_admin,
            'is_active': u.is_active, 'usd_balance': u.usd_balance,
            'tc_balance': u.tc_balance,
            'total_mined_tc': u.total_mined_tc,
            'created_at': u.created_at.isoformat()
        } for u in users]
    })

@admin_bp.route('/invite-codes', methods=['GET', 'POST'])
@login_required
def manage_invite_codes():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '權限不足'})
    
    if request.method == 'POST':
        data = request.get_json() or request.form
        code = data.get('code', '').upper() or ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=8))
        max_uses = int(data.get('max_uses', 100))
        
        ic = InviteCode(code=code, max_uses=max_uses, created_by=current_user.id)
        db.session.add(ic)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'邀請碼 {code} 已建立', 'code': code})
    
    codes = InviteCode.query.order_by(InviteCode.created_at.desc()).all()
    return jsonify({
        'success': True,
        'invite_codes': [{
            'id': c.id, 'code': c.code,
            'max_uses': c.max_uses, 'used_count': c.used_count,
            'is_active': c.is_active, 'created_at': c.created_at.isoformat()
        } for c in codes]
    })

@admin_bp.route('/user/<int:user_id>/balance', methods=['POST'])
@login_required
def adjust_balance(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.get_json() or request.form
    currency = data.get('currency', 'USD').upper()
    amount = float(data.get('amount', 0))
    action_type = data.get('action', 'add')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用戶不存在'})
    
    balance_map = {
        'USD': 'usd_balance', 'HKD': 'hkd_balance', 'TC': 'tc_balance'
    }
    if currency not in balance_map:
        return jsonify({'success': False, 'message': '不支援的貨幣'})
    
    field = balance_map[currency]
    current = getattr(user, field)
    
    if action_type == 'add':
        setattr(user, field, current + amount)
    elif action_type == 'set':
        setattr(user, field, amount)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ {user.username} 的 {currency} 已更新',
        'new_balance': getattr(user, field)
    })
