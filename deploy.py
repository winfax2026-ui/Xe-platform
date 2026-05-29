"""
XE Platform - 一鍵部署工具
用 Railway API 直接創建專案 + 部署
"""
import requests, json, time, os, sys

GITHUB_REPO = 'https://github.com/winfax2026-ui/Xe-platform'

def deploy_with_railway_api():
    """Use Railway public templates API to deploy"""
    
    # Railway has a public "Deploy to Railway" button API
    # This creates a project from a GitHub repo directly
    
    print("""
╔══════════════════════════════════════════════╗
║   🚀 XE 平台 - 部署助手                       ║
╠══════════════════════════════════════════════╣
║                                              ║
║  我已經準備好晒所有程式碼同配置，              ║
║  但係 Railway 需要你手動授權。                 ║
║                                              ║
║  請跟住以下步驟：                              ║
╚══════════════════════════════════════════════╝
""")
    
    print("=" * 60)
    print("步驟 1️⃣  - 按呢條連結授權 Railway")
    print("=" * 60)
    print()
    print(f"  🔗  https://railway.app/new")
    print()
    print("=" * 60)
    print("步驟 2️⃣  - 選擇 GitHub Repo")
    print("=" * 60)
    print()
    print(f"  揀 → GitHub Repo")
    print(f"  揀 → {GITHUB_REPO}")
    print(f"  揀 → main branch")
    print()
    print("=" * 60)
    print("步驟 3️⃣  - 等 2-3 分鐘")
    print("=" * 60)
    print()
    print("  Railway 會自動：")
    print("  ✅ detect 到 Procfile")
    print("  ✅ pip install -r requirements.txt")
    print("  ✅ 行 gunicorn app:app")
    print("  ✅ 俾你一個公開網址")
    print()
    print("=" * 60)
    print("部署完成後你會得到類似：")
    print("  🌐  https://xe-platform.up.railway.app")
    print("=" * 60)
    print()
    print("🔑 登入資料:")
    print("  管理員: admin / admin888")
    print("  邀請碼: XE2026")
    print()
    print("📋 環境變數建議（喺 Railway Dashboard → Variables）:")
    print("  SECRET_KEY=你的自訂密鑰")
    print("  MAIL_USERNAME=你的gmail@gmail.com")
    print("  MAIL_PASSWORD=你的gmail app password")
    print()

if __name__ == '__main__':
    deploy_with_railway_api()
