"""
Copy this file to local_settings.py and change the appropriate values
"""

# Absolute path of skd root

PROJECT_DIR = "/usr/local/skd"

# Database configuration

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',             # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/usr/local/skd/sshkeys.db',            # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

FORCE_SCRIPT_NAME = "/"
