#!/bin/bash
"""
XE Platform 部署腳本
股票及虛擬貨幣平台 XE 版 - 一鍵部署
"""

echo "================================================"
echo "  🏦 XE 平台 - 一鍵部署腳本"
echo "  股票及虛擬貨幣平台 XE 版"
echo "================================================"
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安裝，請先安裝 Python 3.8+"
    echo "   安裝指令: pkg install python"
    exit 1
fi

echo "✅ Python3 已安裝: $(python3 --version)"

# 2. Install dependencies
echo ""
echo "📦 安裝依賴套件..."
cd "$(dirname "$0")/backend"

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虛擬環境已創建"
fi

source venv/bin/activate
pip install -r requirements.txt -q

if [ $? -eq 0 ]; then
    echo "✅ 依賴套件安裝完成"
else
    echo "❌ 安裝失敗，請嘗試手動安裝: pip install -r requirements.txt"
    exit 1
fi

# 3. Setup database
echo ""
echo "🗄️  初始化資料庫..."
python3 -c "
from app import app
from models import db, InviteCode
with app.app_context():
    db.create_all()
    # Create default invite codes for admin
    admin_invite = InviteCode(code='XE2024', max_uses=100)
    db.session.add(admin_invite)
    db.session.commit()
    print('✅ 資料庫初始化完成')
    print('📋 默認邀請碼: XE2024')
"

# 4. Create admin user
echo ""
echo "👤 創建管理員帳戶..."
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
            password_hash=generate_password_hash('admin123'),
            invite_code='XE2024',
            is_admin=True,
            kyc_status='verified',
            kyc_email_verified=True,
            kyc_identity_verified=True,
            usd_balance=10000,
            traffic_coin_balance=5000
        )
        db.session.add(admin)
        db.session.commit()
        print('✅ 管理員帳戶已創建')
        print('   用戶名: admin')
        print('   密碼: admin123')
    else:
        print('✅ 管理員帳戶已存在')
"

# 5. Start server
echo ""
echo "================================================"
echo "  🚀 XE 平台啟動！"
echo "================================================"
echo ""
echo "📋 訪問地址: http://localhost:5000"
echo "📋 管理員: admin / admin123"
echo "📋 邀請碼: XE2024"
echo ""
echo "⚠️  注意："
echo "- 使用公共網路時請修改密碼"
echo "- 在 config.py 中配置真實的 API 金鑰"
echo "- 配置 SMTP 以啟用電郵功能"
echo ""
echo "🔄 啟動服務器..."

# Generate a simple start script
echo "#!/bin/bash
cd \"\$(dirname \"\$0\")/backend\"
source venv/bin/activate
export FLASK_APP=app.py
export FLASK_DEBUG=True
python app.py
" > ../start.sh
chmod +x ../start.sh

# Start the app
cd ../backend
python app.py
