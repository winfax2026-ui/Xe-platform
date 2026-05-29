import os, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Transaction, CryptoWallet
from datetime import datetime

crypto_bp = Blueprint('crypto', __name__)

# Mock crypto prices (updated by CoinGecko in exchange route)
CRYPTO_SYMBOLS = {
    'BTC': {'name': 'Bitcoin', 'decimals': 8},
    'ETH': {'name': 'Ethereum', 'decimals': 8},
    'USDT': {'name': 'Tether', 'decimals': 2},
    'BNB': {'name': 'Binance Coin', 'decimals': 6},
    'SOL': {'name': 'Solana', 'decimals': 6},
    'XRP': {'name': 'Ripple', 'decimals': 6},
    'ADA': {'name': 'Cardano', 'decimals': 6},
    'DOGE': {'name': 'Dogecoin', 'decimals': 4}
}

@crypto_bp.route('/prices', methods=['GET'])
def get_crypto_prices():
    """Get live crypto prices from CoinGecko"""
    symbols = ','.join([
        'bitcoin', 'ethereum', 'tether', 'binancecoin',
        'solana', 'ripple', 'cardano', 'dogecoin'
    ])
    try:
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={symbols}&vs_currencies=usd&include_24hr_change=true'
        req = urllib.request.Request(url, headers={'User-Agent': 'XEPlatform/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        
        prices = {
            'BTC': {'price': data.get('bitcoin', {}).get('usd', 67500), 'change': data.get('bitcoin', {}).get('usd_24h_change', 0)},
            'ETH': {'price': data.get('ethereum', {}).get('usd', 3450), 'change': data.get('ethereum', {}).get('usd_24h_change', 0)},
            'USDT': {'price': data.get('tether', {}).get('usd', 1.0), 'change': data.get('tether', {}).get('usd_24h_change', 0)},
            'BNB': {'price': data.get('binancecoin', {}).get('usd', 580), 'change': data.get('binancecoin', {}).get('usd_24h_change', 0)},
            'SOL': {'price': data.get('solana', {}).get('usd', 145), 'change': data.get('solana', {}).get('usd_24h_change', 0)},
            'XRP': {'price': data.get('ripple', {}).get('usd', 0.62), 'change': data.get('ripple', {}).get('usd_24h_change', 0)},
            'ADA': {'price': data.get('cardano', {}).get('usd', 0.45), 'change': data.get('cardano', {}).get('usd_24h_change', 0)},
            'DOGE': {'price': data.get('dogecoin', {}).get('usd', 0.12), 'change': data.get('dogecoin', {}).get('usd_24h_change', 0)}
        }
    except:
        prices = {s: {'price': 0, 'change': 0} for s in CRYPTO_SYMBOLS}
        prices['BTC']['price'] = 67500
        prices['ETH']['price'] = 3450
        prices['USDT']['price'] = 1.0

    return jsonify({
        'success': True,
        'prices': prices,
        'updated_at': datetime.utcnow().isoformat()
    })

@crypto_bp.route('/wallet', methods=['GET'])
@login_required
def get_crypto_wallet():
    """Get user's crypto wallet balances"""
    wallets = CryptoWallet.query.filter_by(user_id=current_user.id).all()
    wallet_data = {}
    for w in wallets:
        wallet_data[w.currency] = {'balance': w.balance, 'address': w.address}
    
    # Add bot balances
    wallet_data['USD'] = {'balance': current_user.bot_usd, 'address': ''}
    wallet_data['BTC'] = {'balance': current_user.bot_btc, 'address': ''}
    wallet_data['ETH'] = {'balance': current_user.bot_eth, 'address': ''}
    wallet_data['USDT'] = {'balance': current_user.bot_usdt, 'address': ''}
    
    return jsonify({
        'success': True,
        'wallet': wallet_data
    })

@crypto_bp.route('/buy', methods=['POST'])
@login_required
def buy_crypto():
    data = request.get_json() or request.form
    currency = data.get('currency', 'BTC').upper()
    amount_usd = float(data.get('amount_usd', 0))
    
    if amount_usd <= 0:
        return jsonify({'success': False, 'message': '金額必須大於0'})
    
    if current_user.usd_balance < amount_usd:
        return jsonify({'success': False, 'message': f'USD不足 (需要 ${amount_usd})'})
    
    # Get price
    prices_resp = get_crypto_prices()
    prices = json.loads(prices_resp.get_data(as_text=True))['prices']
    
    if currency not in prices or not prices[currency]['price']:
        return jsonify({'success': False, 'message': f'不支援的加密貨幣: {currency}'})
    
    price = prices[currency]['price']
    amount_crypto = amount_usd / price
    
    current_user.usd_balance -= amount_usd
    
    # Update crypto wallet
    wallet = CryptoWallet.query.filter_by(user_id=current_user.id, currency=currency).first()
    if not wallet:
        wallet = CryptoWallet(user_id=current_user.id, currency=currency, balance=0)
        db.session.add(wallet)
    wallet.balance += amount_crypto
    wallet.updated_at = datetime.utcnow()
    
    # Also add to bot wallet
    if currency == 'BTC':
        current_user.bot_btc += amount_crypto
    elif currency == 'ETH':
        current_user.bot_eth += amount_crypto
    elif currency == 'USDT':
        current_user.bot_usdt += amount_crypto
    
    tx = Transaction(
        user_id=current_user.id, tx_type='trade', currency=currency,
        amount=amount_crypto, status='confirmed',
        description=f'買入 {amount_crypto:.6f} {currency} @ ${price}',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ 買入 {amount_crypto:.6f} {currency} @ ${price}',
        'balance_usd': round(current_user.usd_balance, 2),
        'crypto_balance': round(wallet.balance, 8)
    })

@crypto_bp.route('/sell', methods=['POST'])
@login_required
def sell_crypto():
    data = request.get_json() or request.form
    currency = data.get('currency', 'BTC').upper()
    amount_crypto = float(data.get('amount', 0))
    
    if amount_crypto <= 0:
        return jsonify({'success': False, 'message': '數量必須大於0'})
    
    wallet = CryptoWallet.query.filter_by(user_id=current_user.id, currency=currency).first()
    if not wallet or wallet.balance < amount_crypto:
        return jsonify({'success': False, 'message': f'{currency} 不足'})
    
    prices_resp = get_crypto_prices()
    prices = json.loads(prices_resp.get_data(as_text=True))['prices']
    price = prices.get(currency, {}).get('price', 0)
    
    if not price:
        return jsonify({'success': False, 'message': f'無法獲取 {currency} 價格'})
    
    usd_received = amount_crypto * price
    
    wallet.balance -= amount_crypto
    current_user.usd_balance += usd_received
    
    if currency == 'BTC':
        current_user.bot_btc -= amount_crypto
    elif currency == 'ETH':
        current_user.bot_eth -= amount_crypto
    elif currency == 'USDT':
        current_user.bot_usdt -= amount_crypto
    
    tx = Transaction(
        user_id=current_user.id, tx_type='trade', currency=currency,
        amount=amount_crypto, status='confirmed',
        description=f'賣出 {amount_crypto:.6f} {currency} → ${usd_received:.2f}',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ 賣出 {amount_crypto:.6f} {currency} → ${usd_received:.2f}',
        'balance_usd': round(current_user.usd_balance, 2),
        'crypto_balance': round(wallet.balance, 8)
    })
