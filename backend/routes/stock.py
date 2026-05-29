import os, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Transaction, StockPortfolio
from datetime import datetime
import random, math

stock_bp = Blueprint('stock', __name__)

# ── Mock Stock Data ──
# Realistic price simulation
STOCKS_US = {
    'AAPL': {'name': 'Apple Inc.', 'price': 198.50, 'change': 0},
    'GOOGL': {'name': 'Alphabet Inc.', 'price': 175.20, 'change': 0},
    'MSFT': {'name': 'Microsoft Corp.', 'price': 425.30, 'change': 0},
    'TSLA': {'name': 'Tesla Inc.', 'price': 245.80, 'change': 0},
    'AMZN': {'name': 'Amazon.com', 'price': 178.90, 'change': 0},
    'NVDA': {'name': 'NVIDIA Corp.', 'price': 880.40, 'change': 0},
    'META': {'name': 'Meta Platforms', 'price': 505.60, 'change': 0},
    'BTC-USD': {'name': 'Bitcoin ETF', 'price': 67500, 'change': 0}
}

STOCKS_HK = {
    '0700': {'name': '騰訊控股 Tencent', 'price': 388.00, 'change': 0},
    '9988': {'name': '阿里巴巴 Alibaba', 'price': 82.50, 'change': 0},
    '0005': {'name': '匯豐控股 HSBC', 'price': 68.40, 'change': 0},
    '3690': {'name': '美團 Meituan', 'price': 118.20, 'change': 0},
    '1810': {'name': '小米集團 Xiaomi', 'price': 32.15, 'change': 0},
    '9618': {'name': '京東集團 JD.com', 'price': 142.80, 'change': 0},
    '9981': {'name': '新東方在線', 'price': 56.30, 'change': 0},
    '1024': {'name': '快手科技 Kuaishou', 'price': 64.50, 'change': 0}
}

def simulate_price_change(current_price):
    """Simulate realistic price movement"""
    change_pct = random.gauss(0, 0.02)  # ~2% std dev
    new_price = current_price * (1 + change_pct)
    return round(max(new_price, current_price * 0.5), 2), round(change_pct * 100, 2)

@stock_bp.route('/markets', methods=['GET'])
def get_markets():
    market = request.args.get('market', 'US').upper()

    us_prices = {}
    hk_prices = {}

    for sym, info in STOCKS_US.items():
        price, change = simulate_price_change(info['price'])
        STOCKS_US[sym]['price'] = price
        STOCKS_US[sym]['change'] = change
        us_prices[sym] = {**info, 'price': price, 'change': change}

    for sym, info in STOCKS_HK.items():
        price, change = simulate_price_change(info['price'])
        STOCKS_HK[sym]['price'] = price
        STOCKS_HK[sym]['change'] = change
        hk_prices[sym] = {**info, 'price': price, 'change': change}

    return jsonify({
        'success': True,
        'market': market,
        'stocks': us_prices if market == 'US' else hk_prices,
        'updated_at': datetime.utcnow().isoformat()
    })

@stock_bp.route('/buy', methods=['POST'])
@login_required
def buy_stock():
    data = request.get_json() or request.form
    symbol = data.get('symbol', '').upper()
    market = data.get('market', 'US').upper()
    shares = float(data.get('shares', 0))
    price = float(data.get('price', 0))

    if shares <= 0 or price <= 0:
        return jsonify({'success': False, 'message': '數量或價格無效'})

    total_cost = shares * price
    total_cost_usd = total_cost if market == 'US' else total_cost / 7.82

    if current_user.usd_balance < total_cost_usd:
        return jsonify({'success': False, 'message': f'USD 餘額不足 (需要 ${total_cost_usd:.2f})'})

    current_user.usd_balance -= total_cost_usd

    # Update portfolio
    existing = StockPortfolio.query.filter_by(
        user_id=current_user.id, symbol=symbol, market=market
    ).first()

    if existing:
        total_shares = existing.shares + shares
        total_cost_old = existing.shares * existing.avg_price
        total_cost_new = shares * price
        existing.avg_price = (total_cost_old + total_cost_new) / total_shares if total_shares > 0 else price
        existing.shares = total_shares
    else:
        existing = StockPortfolio(
            user_id=current_user.id, symbol=symbol,
            shares=shares, avg_price=price, market=market
        )
        db.session.add(existing)

    tx = Transaction(
        user_id=current_user.id, tx_type='trade', currency='USD',
        amount=total_cost_usd, status='confirmed',
        description=f'買入 {shares} 股 {symbol} @ ${price}',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'✅ 買入 {shares} 股 {symbol} @ ${price}',
        'usd_balance': round(current_user.usd_balance, 2),
        'portfolio': {
            'symbol': symbol,
            'shares': existing.shares,
            'avg_price': existing.avg_price
        }
    })

@stock_bp.route('/sell', methods=['POST'])
@login_required
def sell_stock():
    data = request.get_json() or request.form
    symbol = data.get('symbol', '').upper()
    market = data.get('market', 'US').upper()
    shares = float(data.get('shares', 0))
    price = float(data.get('price', 0))

    if shares <= 0:
        return jsonify({'success': False, 'message': '數量無效'})

    existing = StockPortfolio.query.filter_by(
        user_id=current_user.id, symbol=symbol, market=market
    ).first()

    if not existing or existing.shares < shares:
        return jsonify({'success': False, 'message': f'{symbol} 持股不足'})

    total_value = shares * price
    total_value_usd = total_value if market == 'US' else total_value / 7.82

    existing.shares -= shares
    current_user.usd_balance += total_value_usd

    if existing.shares <= 0:
        db.session.delete(existing)

    tx = Transaction(
        user_id=current_user.id, tx_type='trade', currency='USD',
        amount=total_value_usd, status='confirmed',
        description=f'賣出 {shares} 股 {symbol} @ ${price}',
        is_broadcast=False
    )
    tx.tx_hash = tx.generate_tx_hash()
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'✅ 賣出 {shares} 股 {symbol} @ ${price}',
        'usd_balance': round(current_user.usd_balance, 2)
    })

@stock_bp.route('/portfolio', methods=['GET'])
@login_required
def get_portfolio():
    holdings = StockPortfolio.query.filter_by(user_id=current_user.id).all()

    portfolio = []
    total_value = 0
    for h in holdings:
        stocks = STOCKS_US if h.market == 'US' else STOCKS_HK
        current_price = stocks.get(h.symbol, {}).get('price', 0)
        value = h.shares * current_price
        value_usd = value if h.market == 'US' else value / 7.82
        total_value += value_usd
        profit = (current_price - h.avg_price) * h.shares
        profit_pct = ((current_price - h.avg_price) / h.avg_price * 100) if h.avg_price else 0

        portfolio.append({
            'symbol': h.symbol,
            'market': h.market,
            'shares': h.shares,
            'avg_price': h.avg_price,
            'current_price': current_price,
            'total_value': round(value, 2),
            'total_value_usd': round(value_usd, 2),
            'profit': round(profit, 2),
            'profit_pct': round(profit_pct, 2)
        })

    return jsonify({
        'success': True,
        'portfolio': portfolio,
        'total_value_usd': round(total_value, 2),
        'usd_balance': round(current_user.usd_balance, 2)
    })
