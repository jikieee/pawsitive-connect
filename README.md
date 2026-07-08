# 🐾 Pawsitive Connect — Setup Guide

A Django web app for reporting stray/injured cats & dogs and tracking their rescue journey.

## 📁 Project Structure

```
pawsitive_connect/
├── manage.py
├── requirements.txt
├── pawsitive_connect/
│   ├── __init__.py
│   ├── settings.py
│   └── urls.py
├── core/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
└── templates/
    ├── login.html
    └── dashboard.html
```

## 🚀 Quick Start

### 1. Create & Activate Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Apply Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 5. Run Development Server
```bash
python manage.py runserver
```

Then open: **http://127.0.0.1:8000**

## 🔗 URL Routes

| URL | View | Description |
|-----|------|-------------|
| `/` | home_redirect | Redirects to login or dashboard |
| `/login/` | login_view | Login page |
| `/logout/` | logout_view | Logout |
| `/dashboard/` | dashboard | Main dashboard (auth required) |
| `/api/dashboard-stats/` | dashboard_stats_api | JSON stats |
| `/api/recent-reports/` | recent_reports_api | JSON report list |
| `/admin/` | Django admin | Superuser area |

## ✨ Features Built

### Login Page
- Animated floating paw-print background
- Split panel layout (brand left, form right)
- Password show/hide toggle
- Live stats display (reports, rescued, adoptable)
- Error messages with shake animation
- Smooth entrance animations

### Dashboard
- Sidebar navigation with active states & badge counts
- 4 stat cards with animated count-up numbers
- Bar/Line toggle activity chart (Chart.js)
- Animal type donut chart
- Live recent reports loaded via fetch API
- Rescue status tracker with animated steps
- Map hotspot preview placeholder
- Report Animal modal with form
- Live search filter on reports
- Notification panel
- Logout button

## 🔧 VSCode Extensions Recommended

- Python (Microsoft)
- Django (Baptiste Darthenay)
- Pylance
- SQLite Viewer
- Thunder Client (API testing)
