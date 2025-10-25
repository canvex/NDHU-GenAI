# NDHU-GenAI 東華專題

### 1️⃣建立虛擬環境(Linux/Mac)

```
python3 -m venv venv
```

### 1️⃣建立虛擬環境(Windows)

```
python -m venv venv
```

### 2️⃣啟動虛擬環境(Linux/Mac)

```
source venv/bin/activate
```

### 2️⃣啟動虛擬環境(Windows)

```
venv\Scripts\activate
```

### 3️⃣安裝所有套件

```
pip install -r requirements.txt
pip install google
```
### 4️⃣設定 Flask 主程式、開發模式 (Linux/Mac)

```
export FLASK_APP=run.py
export FLASK_ENV=development
```
### 4️⃣設定 Flask 主程式、開發模式 (Windows)

```
set FLASK_APP=run.py
set FLASK_ENV=development
```
### 5️⃣啟動 Flask 伺服器

```
flask run
```
```
python run.py
```
---
### 創建 `.env` 檔案

在專案的根目錄建立一個名為 `.env` 的檔案。此檔案將用來存放你的資料庫連線設定。<br>
在 `.env` 檔案中，加入以下設定：`DATABASE_URL=mysql+pymysql://...`

  ### 主要檔案分布

前端檔案位置：  
`templates/home/doc_auto_select.html`

後端檔案主要位置：  
`apps/home/routes.py`

資料庫檔案主要位置：  
`apps/authentication/models.py`

