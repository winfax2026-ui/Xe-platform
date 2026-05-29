import os, sys, json, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Transaction, ExchangeRate
from datetime import datetime

exchange_bp = Blueprint('exchange', __name__)

# ── Live Rate Fetcher ──
def fetch_coingecko_rate():
    """Fetch USD/HKD from CoinGecko, fallback to config"""
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price?ids=usd&vs_currencies=hkd'
        req = urllib.request.Request(url, headers={'User-Agent': 'XEPlatform/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return float(data['usd']['hkd'])
    except:
        from config import Config
        return Config.USD_TO_HKD

def get_usd_to_hkd():
    """Get cached or fresh USD→HKD rate"""
    rate = ExchangeRate.query.filter_by(pair='USDHKD').first()
    if rate and (datetime.utcnow() - rate.updated_at).seconds < 300:
        return rate.rate
    live = fetch_coingecko_rate()
    if rate:
        rate.rate = live
        rate.updated_at = datetime.utcnow()
    else:
        rate = ExchangeRate(pair='USDHKD', rate=live)
        db.session.add(rate)
    db.session.commit()
    return live

def get_usd_to_cny():
    """Get USD→CNY rate"""
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price?ids=usd&vs_currencies=cny'
        req = urllib.request.Request(url, headers={'User-Agent': 'XEPlatform/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return float(data['usd']['cny'])
    except:
        return 7.24

# ── Routes ──

@exchange_bp.route('/rates', methods=['GET'])
def get_rates():
    """Get all live exchange rates"""
    usd_to_hkd = get_usd_to_hkd()
    usd_to_cny = get_usd_to_cny()

    rates = {
        'USD': 1.0,
        'HKD': usd_to_hkd,
        'CNY': usd_to_cny,
        'TC': 1.0,  # 1 TC = 1 USD
        'BTC': 0, 'ETH': 0, 'USDT': 1.0
    }

    # Try to get crypto prices
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether&vs_currencies=usd'
        req = urllib.request.Request(url, headers={'User-Agent': 'XEPlatform/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            crypto = json.loads(resp.read().decode())
            rates['BTC'] = float(crypto.get('bitcoin', {}).get('usd', 0))
            rates['ETH'] = float(crypto.get('ethereum', {}).get('usd', 0))
            rates['USDT'] = float(crypto.get('tether', {}).get('usd', 1.0))
    except:
        rates['BTC'] = 67500
        rates['ETH'] = 3450
        rates['USDT'] = 1.0

    return jsonify({
        'success': True,
        'rates': rates,
        'updated_at': datetime.utcnow().isoformat()
    })

@exchange_bp.route('/convert', methods=['POST'])
@login_required
def convert_currency():
    data = request.get_json() or request.form
    from_curr = data.get('from', '').upper()
    to_curr = data.get('to', '').upper()
    amount = float(data.get('amount', 0))

    if amount <= 0:
        return jsonify({'success': False, 'message': '金額必須大於0'})

    # Get live rates
    rates_resp = get_rates()
    rates = json.loads(rates_resp.get_data(as_text=True))['rates']

    if from_curr not in rates or to_curr not in rates:
        return jsonify({'success': False, 'message': '不支援的貨幣對'})

    usd_value = amount / rates[from_curr]
    converted = usd_value * rates[to_curr]

    return jsonify({
        'success': True,
        'from': from_curr,
        'to': to_curr,
        'amount': amount,
        'converted': round(converted, 8),
        'rate': round(rates[to_curr] / rates[from_curr], 8),
        'usd_value': round(usd_value, 8),
        'live_rates': {k: round(v, 8) for k, v in rates.items()}
    })

@exchange_bp.route('/exchange', methods=['POST'])
@login_required
def execute_exchange():
    """Exchange one currency to another in user's wallet"""
    data = request.get_json() or request.form
    from_curr = data.get('from', '').upper()
    to_curr = data.get('to', '').upper()
    amount = float(data.get('amount', 0))

    if amount <= 0:
        return jsonify({'success': False, 'message': '金額必須大於0'})

    if from_curr == to_curr:
        return jsonify({'success': False, 'message': '不能兌換相同貨幣'})

    # Check balance
    balance_map = {
        'USD': current_user.usd_balance,
        'HKD': current_user.hkd_balance,
        'TC': current_user.tc_balance
    }

    if from_curr not in balance_map:
        return jsonify({'success': False, 'message': '不支援的來源貨幣'})

    if balance_map[from_curr] < amount:
        return jsonify({'success': False, 'message': f'{from_curr} 餘額不足'})

    rates_resp = get_rates()
    rates = json.loads(rates_resp.get_data(as_text=True))['rates']

    if to_curr not in rates:
        return jsonify({'success': False, 'message': '不支援的目標貨幣'})

    usd_value = 0
    if from_curr == 'TC':
        usd_value = amount * 1.0  # 1 TC = 1 USD
    elif from_curr == 'HKD':
        usd_value = amount / rates['HKD']
    else:
        usd_value = amount

    converted = 0
    if to_curr == 'TC':
        converted = usd_value * 1.0
    elif to_curr == 'HKD':
        converted = usd_value * rates['HKD']
    else:
        converted = usd_value * rates.get(to_curr, 1.0)

    # Deduct from source
    if from_curr == 'USD':
        current_user.usd_balance -= amount
    elif from_curr == 'HKD':
        current_user.hkd_balance -= amount
    elif from_curr == 'TC':
        current_user.tc_balance -= amount

    # Add to target
    if to_curr == 'USD':
        current_user.usd_balance += converted
    elif to_curr == 'HKD':
        current_user.hkd_balance += converted
    elif to_curr == 'TC':
        current_user.tc_balance += converted
    else:
        current_user.usd_balance += converted

    tx = Transaction(
        user_id=current_user.id, tx_type='exchange',
        currency=f'{from_curr}→{to_curr}',
        amount=amount, status='confirmed',
        description=f'兌換: {amount} {from_curr} → {round(converted, 4)} {to_curr}',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'✅ {amount} {from_curr} → {round(converted, 4)} {to_curr}',
        'usd_balance': round(current_user.usd_balance, 2),
        'hkd_balance': round(current_user.hkd_balance, 2),
        'tc_balance': round(current_user.tc_balance, 4)
    })
