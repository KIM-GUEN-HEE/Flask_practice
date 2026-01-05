import os

BASE_DIR = os.path.dirname(__file__)

SQLALCHEMY_DATABASE_URI = 'sqlite:///{}'.format(os.path.join(BASE_DIR, 'pybo.db'))
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "dev"

# Google OAuth2 settings (set these as environment variables in production)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

# When testing on localhost you can enable insecure transport (only dev!)
# export OAUTHLIB_INSECURE_TRANSPORT=1
# SMTP / Mail settings (used by pybo.email_utils.send_verification_email)
# Configure these via environment variables in production.
MAIL_SERVER = os.environ.get('MAIL_SERVER')
# MAIL_PORT should be an integer (e.g., 587 for TLS, 465 for SSL)
MAIL_PORT = int(os.environ.get('MAIL_PORT')) if os.environ.get('MAIL_PORT') else None
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
