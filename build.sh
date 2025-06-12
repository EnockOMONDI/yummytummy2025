#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting YummyTummy build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify Django installation
echo "🔍 Verifying Django installation..."
python -c "import django; print(f'Django version: {django.get_version()}')"

# Check Django configuration
echo "⚙️ Checking Django configuration..."
python manage.py check --deploy

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist (optional)
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@yummytummy.com', 'YummyTummy2024!')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
