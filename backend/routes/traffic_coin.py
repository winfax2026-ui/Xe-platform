import os, sys, time, threading, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Transaction, GlobalMiningStats, BroadcastLedger
from datetime import datetime

tc_bp = Blueprint('traffic_coin', __name__)

# ── Traffic Coin Mining ──
# 1 TC = 1 USD, mined every 10 seconds
# Simulates global world-time mining

# Active mining sessions (user_id -> start_time)
_active_mining = {}
_mining_lock = threading.Lock()

@tc_bp.route('/start', methods=['POST'])
@login_required
def start_mining():
    with _mining_lock:
        if current_user.id in _active_mining:
            return jsonify({'success': False, 'message': '已經在挖掘中'})

        _active_mining[current_user.id] = time.time()
        current_user.is_mining = True
        current_user.mining_started_at = datetime.utcnow()
        db.session.commit()

    return jsonify({
        'success': True,
        'message': '⛏️ 流量金挖掘已開始！每10秒產出1 TC (=1 USD)',
        'started_at': datetime.utcnow().isoformat()
    })

@tc_bp.route('/stop', methods=['POST'])
@login_required
def stop_mining():
    tc_earned = 0.0
    with _mining_lock:
        if current_user.id not in _active_mining:
            return jsonify({'success': False, 'message': '沒有正在進行的挖掘'})

        elapsed = time.time() - _active_mining[current_user.id]
        tc_earned = elapsed / 10.0 * 1.0  # 10s = 1 TC
        del _active_mining[current_user.id]

    if tc_earned > 0:
        current_user.tc_balance += tc_earned
        current_user.total_mined_tc += tc_earned
        current_user.is_mining = False
        current_user.mining_started_at = None

        tx = Transaction(
            user_id=current_user.id, tx_type='mine', currency='TC',
            amount=round(tc_earned, 4), status='confirmed',
            description=f'流量金挖掘 {round(tc_earned, 4)} TC',
            is_broadcast=True
        )
        tx.tx_hash = tx.generate_tx_hash()
        db.session.add(tx)

        # Update global stats
        gs = GlobalMiningStats.query.first()
        if not gs:
            gs = GlobalMiningStats()
            db.session.add(gs)
        gs.total_tc_mined += tc_earned
        gs.total_mining_seconds += elapsed

        # Broadcast to public ledger
        bl = BroadcastLedger(
            tx_hash=tx.tx_hash,
            user_id=current_user.id,
            username_public=current_user.username[:3] + '***',
            tx_type='mine',
            amount=round(tc_earned, 4),
            currency='TC',
            status='confirmed'
        )
        db.session.add(bl)
        db.session.commit()

    return jsonify({
        'success': True,
        'message': f'⛏️ 挖掘結束！獲得 {round(tc_earned, 4)} TC (=${round(tc_earned, 2)} USD)',
        'tc_earned': round(tc_earned, 4),
        'usd_value': round(tc_earned, 2),
        'total_tc': round(current_user.tc_balance, 4)
    })

@tc_bp.route('/stats', methods=['GET'])
@login_required
def mining_stats():
    is_mining = current_user.id in _active_mining
    current_session_tc = 0.0
    elapsed = 0.0

    if is_mining:
        with _mining_lock:
            if current_user.id in _active_mining:
                elapsed = time.time() - _active_mining[current_user.id]
                current_session_tc = elapsed / 10.0

    gs = GlobalMiningStats.query.first()
    active_miners = len(_active_mining)

    return jsonify({
        'success': True,
        'stats': {
            'is_mining': is_mining,
            'current_session_seconds': round(elapsed, 1),
            'current_session_tc': round(current_session_tc, 4),
            'current_session_usd': round(current_session_tc, 2),
            'total_tc': round(current_user.tc_balance, 4),
            'total_usd_value': round(current_user.tc_balance, 2),
            'total_mined_tc': round(current_user.total_mined_tc, 4),
            'tc_rate_per_10s': 1.0,
            'tc_rate_per_hour': 360.0,
            'tc_rate_per_day': 8640.0,
            'usd_rate_per_day': 8640.0,
            'global_total_tc_mined': round(gs.total_tc_mined, 2) if gs else 0,
            'global_total_miners': active_miners,
            'mining_started_at': current_user.mining_started_at.isoformat() if current_user.mining_started_at else None
        }
    })

@tc_bp.route('/convert', methods=['POST'])
@login_required
def convert_tc():
    data = request.get_json() or request.form
    amount = float(data.get('amount', 0))
    to_currency = data.get('to', 'USD').upper()

    if amount <= 0:
        return jsonify({'success': False, 'message': '金額必須大於0'})

    if current_user.tc_balance < amount:
        return jsonify({'success': False, 'message': '流量金不足'})

    if to_currency == 'USD':
        usd_amount = amount * 1.0  # 1 TC = 1 USD
        current_user.tc_balance -= amount
        current_user.usd_balance += usd_amount

        tx = Transaction(
            user_id=current_user.id, tx_type='exchange', currency='TC→USD',
            amount=amount, status='confirmed',
            description=f'流量金轉換: {amount} TC → ${usd_amount} USD',
            is_broadcast=False
        )
        tx.tx_hash = tx.generate_tx_hash()
        db.session.add(tx)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'✅ {amount} TC 已轉換為 ${usd_amount} USD',
            'tc_balance': round(current_user.tc_balance, 4),
            'usd_balance': round(current_user.usd_balance, 2)
        })

    elif to_currency == 'HKD':
        from routes.exchange import get_usd_to_hkd
        rate = get_usd_to_hkd()
        usd = amount * 1.0
        hkd = usd * rate
        current_user.tc_balance -= amount
        current_user.hkd_balance += hkd

        tx = Transaction(
            user_id=current_user.id, tx_type='exchange', currency='TC→HKD',
            amount=amount, status='confirmed',
            description=f'流量金轉換: {amount} TC → HK${hkd:.2f}',
            is_broadcast=False
        )
        tx.tx_hash = tx.generate_tx_hash()
        db.session.add(tx)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'✅ {amount} TC 已轉換為 HK${hkd:.2f} (匯率: 1 USD = {rate} HKD)',
            'tc_balance': round(current_user.tc_balance, 4),
            'hkd_balance': round(hkd, 2)
        })

    return jsonify({'success': False, 'message': '不支援的轉換貨幣'})
