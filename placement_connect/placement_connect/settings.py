# 1. FIX: Update Allowed Hosts to include Render
# Change the old ALLOWED_HOSTS = [] to this:
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,.onrender.com').split(',')

# 2. FIX: Configure Middleware for Static Files
# You must add WhiteNoiseMiddleware IMMEDIATELY after SecurityMiddleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # <--- ADD THIS LINE HERE
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 3. FIX: Database Pathing (Optional but safer)
# Ensure the path is a string for broader compatibility
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}

# 4. STATIC FILES (Already mostly correct, but double-check this section)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# This line ensures your site is fast and files are compressed
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'