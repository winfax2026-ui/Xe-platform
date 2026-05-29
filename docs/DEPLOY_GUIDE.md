# 股票及虛擬貨幣平台 XE 版 - 雲端部署指南

## 方法一：Railway（推薦，最簡單免費）

1. 訪問 https://railway.app/
2. 用 GitHub 帳號登入
3. 點擊 "New Project" → "Deploy from GitHub"
4. 把 xe-platform 文件上傳到你自己的 GitHub 倉庫
5. Railway 會自動檢測並部署
6. 部署完成後，Railway 會給你一個 xx.railway.app 的網址

## 方法二：Render（免費）

1. 訪問 https://render.com/
2. 用 GitHub 帳號登入
3. 點擊 "New +" → "Web Service"
4. 連接你的 GitHub 倉庫
5. 設定：
   - Name: xe-platform
   - Runtime: Python 3
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && gunicorn app:app`
6. 選擇 Free 方案
7. 點擊 "Create Web Service"
8. 等待 2-3 分鐘部署完成
9. Render 會給你一個 onrender.com 的網址

## 方法三：用你的手機臨時上線（ngrok）

在你手機 Termux 安裝 Python 後：
```bash
pkg install python
cd ~/xe-platform/backend
pip install -r requirements.txt
python app.py &
# 新開一個 terminal
pkg install ngrok
ngrok http 5000
# ngrok 會給你一個 https://xxxx.ngrok-free.app 的網址
```
