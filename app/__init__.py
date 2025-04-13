import os
from flask import Flask, request, session
from flask_login import LoginManager
from dotenv import load_dotenv
from flask_babel import Babel
from apscheduler.schedulers.background import BackgroundScheduler
from app.scheduler import refresh_all_accounts_job

# Initialize the authentication manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

# Initialize Babel for internationalization
babel = Babel()

# Function to determine which language to use
def get_locale():
    # Priority 1: Try to get the language from the session (for current session)
    if 'language' in session:
        return session['language']
    
    # Priority 2: Check for the persistent cookie
    if request.cookies.get('user_language'):
        language = request.cookies.get('user_language')
        # If cookie exists but it's not a supported language, don't use it
        if language in ['fr', 'en', 'de', 'cs', 'eo']:
            # Update the session with the cookie value for consistency
            session['language'] = language
            return language
    
    # Priority 3: Use the best match with browser preferences
    return request.accept_languages.best_match(['fr', 'en', 'de', 'cs', 'eo'])

def create_app():
    # Create the Flask application
    app = Flask(__name__, instance_relative_config=True)
    
    # Make sure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Load configuration from the .env file
    env_path = os.path.join(app.instance_path, '.env')
    load_dotenv(env_path)
    
    # Configure the application
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.path.join(app.instance_path, 'association.sqlite'),
        DEBUG=os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't'),
    )
      # Configure Babel for internationalization
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'  # Default language: English
    # Use absolute path for translations directory
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'translations')
    app.config['LANGUAGES'] = {
        'fr': 'Français',
        'en': 'English',
        'de': 'Deutsch',
        'cs': 'Čeština',
        'eo': 'Esperanto'
    }
    
    # Initialize the login manager
    login_manager.init_app(app)
    
    # Initialize Babel with the language selection function
    babel.init_app(app, locale_selector=get_locale)
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    from app.auth import auth
    app.register_blueprint(auth)
    
    from app.nordigen_api import nordigen_bp
    app.register_blueprint(nordigen_bp)

    sched = BackgroundScheduler(daemon=True)
    # Schedule the job to run every day at 3 AM
    sched.add_job(refresh_all_accounts_job,'cron', hour=3, minute=42, id='refresh_all_accounts_job', replace_existing=True, args=[app])
    sched.start()
    return app