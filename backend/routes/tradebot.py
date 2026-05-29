import os, sys, json, urllib.request, random, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Transaction, TradeBotOrder
from datetime import datetime, timedelta

tradebot_bp = Blueprint('tradebot', __name__)

# ── Simulated Exchange Engine (KPI/IP connection simulation) ──

EXCHANGES = {
    'binance': {
        'name': 'Binance',
        'api_url': 'https://api.binance.com/api/v3',
        'ws_url': 'wss://stream.binance.com:9443/ws',
        'kpi': 'BINANCE_KPI_v2.0',
        'ip': '52.84.124.100'
    },
    'bybit': {
        'name': 'Bybit',
        'api_url': 'https://api.bybit.com/v5',
        'ws_url': 'wss://stream.bybit.com/v5/public/linear',
        'kpi': 'BYBIT_KPI_v3.1',
        'ip': '13.33.240.200'
    },
    'okx': {
        'name': 'OKX',
        'api_url': 'https://www.okx.com/api/v5',
        'ws_url': 'wss://ws.okx.com:8443/ws/v5/public',
        'kpi': 'OKX_KPI_v5',
        'ip': '47.254.25.100'
    }
}

TRADING_PAIRS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT']

def get_mock_price(pair):
    """Get simulated market price"""
    base_prices = {
        'BTC/USDT': 67500, 'ETH/USDT': 3450, 'BNB/USDT': 580,
        'SOL/USDT': 145, 'XRP/USDT': 0.62, 'ADA/USDT': 0.45
    }
    base = base_prices.get(pair, 100)
    change = random.gauss(0, base * 0.003)  # 0.3% random walk
    return round(base + change, 2)

@tradebot_bp.route('/exchanges', methods=['GET'])
def get_exchanges():
    """Get connected exchanges with KPI/IP info"""
    return jsonify({
        'success': True,
        'exchanges': EXCHANGES,
        'connected': True,
        'pairs': TRADING_PAIRS
    })

@tradebot_bp.route('/market/<pair>', methods=['GET'])
def get_market_data(pair):
    """Get real-time market data for a trading pair"""
    pair = pair.upper()
    if pair not in TRADING_PAIRS:
        return jsonify({'success': False, 'message': '不支援的交易對'})
    
    bid = get_mock_price(pair)
    ask = bid * 1.001  # 0.1% spread
    volume = random.randint(100, 10000)
    
    return jsonify({
        'success': True,
        'pair': pair,
        'bid': bid,
        'ask': ask,
        'spread': round(ask - bid, 2),
        'volume_24h': volume,
        'high_24h': round(bid * 1.05, 2),
        'low_24h': round(bid * 0.95, 2),
        'change_24h': round(random.gauss(0, 3), 2),
        'exchange': 'Binance (via XE Bot)',
        'timestamp': datetime.utcnow().isoformat()
    })

@tradebot_bp.route('/balance', methods=['GET'])
@login_required
def get_bot_balance():
    """Get trading bot wallet balance"""
    return jsonify({
        'success': True,
        'bot_wallet': {
            'USD': round(current_user.bot_usd, 2),
            'BTC': round(current_user.bot_btc, 8),
            'ETH': round(current_user.bot_eth, 8),
            'USDT': round(current_user.bot_usdt, 2),
            'HKD': round(current_user.bot_hkd, 2)
        },
        'total_value_usd': round(
            current_user.bot_usd + current_user.bot_usdt +
            current_user.bot_btc * 67500 + current_user.bot_eth * 3450, 2
        )
    })

@tradebot_bp.route('/transfer-in', methods=['POST'])
@login_required
def transfer_to_bot():
    """Transfer USD to trading bot wallet"""
    data = request.get_json() or request.form
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'success': False, 'message': '金額無效'})
    
    if current_user.usd_balance < amount:
        return jsonify({'success': False, 'message': f'USD不足 (需要 ${amount})'})
    
    current_user.usd_balance -= amount
    current_user.bot_usd += amount
    
    tx = Transaction(
        user_id=current_user.id, tx_type='exchange', currency='USD',
        amount=amount, status='confirmed',
        description=f'充值到交易機械人錢包: ${amount}',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ ${amount} 已轉入交易機械人錢包',
        'usd_balance': round(current_user.usd_balance, 2),
        'bot_usd': round(current_user.bot_usd, 2)
    })

@tradebot_bp.route('/transfer-out', methods=['POST'])
@login_required
def transfer_from_bot():
    """Transfer USD from trading bot wallet back to main"""
    data = request.get_json() or request.form
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'success': False, 'message': '金額無效'})
    
    if current_user.bot_usd < amount:
        return jsonify({'success': False, 'message': f'機械人錢包USD不足 (需要 ${amount})'})
    
    current_user.bot_usd -= amount
    current_user.usd_balance += amount
    
    tx = Transaction(
        user_id=current_user.id, tx_type='exchange', currency='USD',
        amount=amount, status='confirmed',
        description=f'從交易機械人錢包轉出: ${amount}',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ ${amount} 已轉回主錢包',
        'usd_balance': round(current_user.usd_balance, 2),
        'bot_usd': round(current_user.bot_usd, 2)
    })

@tradebot_bp.route('/place-order', methods=['POST'])
@login_required
def place_order():
    """Place a limit order on the trading bot"""
    data = request.get_json() or request.form
    pair = data.get('pair', '').upper()
    order_type = data.get('type', 'buy').lower()
    price = float(data.get('price', 0))
    quantity = float(data.get('quantity', 0))
    exchange = data.get('exchange', 'binance').lower()
    
    if pair not in TRADING_PAIRS:
        return jsonify({'success': False, 'message': '不支援的交易對'})
    if price <= 0 or quantity <= 0:
        return jsonify({'success': False, 'message': '價格或數量無效'})
    
    # Check balance
    total = price * quantity
    if order_type == 'buy':
        if current_user.bot_usd < total:
            return jsonify({'success': False, 'message': f'機械人錢包USD不足 (需要 ${total:.2f})'})
        current_user.bot_usd -= total
    else:
        currency = pair.split('/')[0]
        bot_balance = getattr(current_user, f'bot_{currency.lower()}', 0)
        if bot_balance < quantity:
            return jsonify({'success': False, 'message': f'機械人錢包{currency}不足'})
        setattr(current_user, f'bot_{currency.lower()}', bot_balance - quantity)
    
    order = TradeBotOrder(
        user_id=current_user.id,
        pair=pair,
        order_type=order_type,
        price=price,
        quantity=quantity,
        filled=quantity,  # Instant fill in simulation
        status='filled',
        exchange=exchange
    )
    db.session.add(order)
    
    # Update bot balance for filled order
    if order_type == 'buy':
        currency = pair.split('/')[0]
        current_bal = getattr(current_user, f'bot_{currency.lower()}', 0)
        setattr(current_user, f'bot_{currency.lower()}', current_bal + quantity)
    else:
        current_user.bot_usd += total
    
    tx = Transaction(
        user_id=current_user.id, tx_type='trade', currency=pair,
        amount=total, status='confirmed',
        description=f'交易機械人: {order_type.upper()} {quantity} {pair} @ ${price} ({exchange.upper()})',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ 訂單已成交: {order_type.upper()} {quantity} {pair} @ ${price}',
        'order': {
            'id': order.id,
            'pair': pair,
            'type': order_type,
            'price': price,
            'quantity': quantity,
            'status': 'filled',
            'exchange': exchange
        },
        'bot_wallet': {
            'USD': round(current_user.bot_usd, 2),
            'BTC': round(current_user.bot_btc, 8),
            'ETH': round(current_user.bot_eth, 8),
            'USDT': round(current_user.bot_usdt, 2)
        }
    })

@tradebot_bp.route('/orders', methods=['GET'])
@login_required
def get_orders():
    """Get user's trade bot orders"""
    orders = TradeBotOrder.query.filter_by(user_id=current_user.id)\
        .order_by(TradeBotOrder.created_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'orders': [{
            'id': o.id,
            'pair': o.pair,
            'type': o.order_type,
            'price': o.price,
            'quantity': o.quantity,
            'filled': o.filled,
            'status': o.status,
            'exchange': o.exchange,
            'created_at': o.created_at.isoformat()
        } for o in orders]
    })

@tradebot_bp.route('/auto-trade', methods=['POST'])
@login_required
def auto_trade():
    """
    Simple auto-trading bot: place mock trades automatically.
    This simulates a grid trading / market making strategy.
    """
    data = request.get_json() or request.form
    pair = data.get('pair', 'BTC/USDT').upper()
    amount_per_trade = float(data.get('amount', 100))  # USD per trade
    
    if pair not in TRADING_PAIRS:
        return jsonify({'success': False, 'message': '不支援的交易對'})
    
    if current_user.bot_usd < amount_per_trade:
        return jsonify({'success': False, 'message': '機械人錢包資金不足'})
    
    current_price = get_mock_price(pair)
    
    # Simulate grid trading: place buy below market, sell above
    buy_price = round(current_price * 0.995, 2)
    sell_price = round(current_price * 1.005, 2)
    quantity = amount_per_trade / current_price
    
    # Place buy order
    buy_order = TradeBotOrder(
        user_id=current_user.id, pair=pair, order_type='buy',
        price=buy_price, quantity=quantity, filled=quantity,
        status='filled', exchange='binance'
    )
    db.session.add(buy_order)
    current_user.bot_usd -= amount_per_trade
    currency = pair.split('/')[0]
    current_bal = getattr(current_user, f'bot_{currency.lower()}', 0)
    setattr(current_user, f'bot_{currency.lower()}', current_bal + quantity)
    
    # Place sell order
    sell_order = TradeBotOrder(
        user_id=current_user.id, pair=pair, order_type='sell',
        price=sell_price, quantity=quantity * 0.5, filled=quantity * 0.5,
        status='filled', exchange='binance'
    )
    db.session.add(sell_order)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'🤖 自動交易已執行: {pair} (買 @ ${buy_price}, 賣 @ ${sell_price})',
        'trades': [
            {'type': 'buy', 'pair': pair, 'price': buy_price, 'quantity': round(quantity, 6)},
            {'type': 'sell', 'pair': pair, 'price': sell_price, 'quantity': round(quantity * 0.5, 6)}
        ],
        'current_price': current_price
    })
