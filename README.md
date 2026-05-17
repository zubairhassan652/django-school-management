# Installation
Run below command to install it
```
pip install django-school-management
```

Add app in installed apps like below.
```
INSTALLED_APPS = [
    ...
    'school_management',
]
```

Add middleware like
```
...
'school_management.middleware.ActivityLoggingMiddleware',
```

# Run Migrations
```
python manage.py migrate
```

# Visit Admin Site
Visit admin site using superuser or any random user
