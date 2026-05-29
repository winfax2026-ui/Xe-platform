#!/bin/bash
"""
XE Platform - Termux 部署腳本
適用於 Android Termux 環境
"""
set -e

echo "================================================"
echo "  🏦 XE 平台 - Termux 部署"
echo "================================================"
echo ""

# 1. Update packages
echo "📦 更新套件列表..."
pkg update -y

# 2. Install Python
echo ""
echo "📦 安裝 Python..."
pkg install -y python python-pip

# 3. Install dependencies
echo ""
echo "📦 安裝項目依賴..."
cd "$(dirname "$0")/backend"
pip install -r requirements.txt

# 4. Initialize database
echo ""
echo "🗄️  初始化資料庫..."
python3 -c "
from app import app
from models import db, InviteCode
with app.app_context():
    db.create_all()
    # Create default invite codes
    if not InviteCode.query.filter_by(code='XE2024').first():
        invite = InviteCode(code='XE2024', max_uses=1000)
        db.session.add(invite)
    
    if not InviteCode.query.filter_by(code='TEST888').first():
        invite2 = InviteCode(code='TEST888', max_uses=50)
        db.session.add(invite2)
    
    db.session.commit()
print('✅ 資料庫初始化完成')
print('📋 默認邀請碼: XE2024, TEST888')
"

# 5. Create admin user
echo ""
echo "👤 創建管理員..."
python3 -c "
from app import app
from models import db, User
from werkzeug.security import generate_password_hash
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@xeplatform.com',
            password_hash=generate_password_hash('admin888'),
            invite_code='XE2024',
            is_admin=True,
            kyc_status='verified',
            kyc_email_verified=True,
            kyc_identity_verified=True,
            usd_balance=100000,
            traffic_coin_balance=50000
        )
        db.session.add(admin)
        db.session.commit()
        print('✅ 管理員已創建: admin / admin888')
    else:
        print('✅ 管理員已存在')
"

echo ""
echo "================================================"
echo "  ✅ 部署完成！"
echo "================================================"
echo ""
echo "📋 啟動服務器:"
echo "   cd ~/xe-platform && bash start.sh"
echo ""
echo "📋 訪問地址: http://localhost:5000"
echo "📋 管理員: admin / admin888"
echo "📋 邀請碼: XE2024"
echo ""
echo "⚠️  注意：本機測試只能在本機訪問"
echo "   若要讓同一網絡的設備訪問，請使用:"
echo "   export HOST=0.0.0.0"
echo "   python app.py"
echo ""
