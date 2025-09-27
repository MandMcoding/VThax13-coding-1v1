# VThax13-coding-1v1
This is the start of something beautiful. Our VT hacks 13 project, with Salif, Ari, Jorge, and Marwan. 

## Getting Started

### Dependencies

python version 

### Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate    # (Windows)
# source venv/bin/activate  # (Mac/Linux)
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

WebSockets via Django Channels
`pip install django djangorestframework djangorestframework-simplejwt channels channels-redis redis`

pip install djangorestframework
pip install django channels channels_redis daphne

PostgreSQL
`pip install psycopg2-binary`
ASGI server for dev:
`pip install daphne`



### Frontend
cd frontend
npm install
npm install react-router-dom
npm run dev

project structure:
VThax13-coding-1v1/
├── frontend/          # React + Vite app
├── backend/           # Django project
│   ├── core/          # Global settings
│   ├── game/          # Example app (API endpoints)
│   └── venv/          # Python virtual environment
└── README.md