# Transparency - Banking Transparency Platform

A Flask-based web application that allows members of an association to connect their bank accounts and provide transparency into financial transactions. This application supports multiple languages (English, French, German, Czech, and Esperanto) and integrates with Nordigen/GoCardless API for secure bank account access.

## Features

- User authentication system
- Multi-language support (EN, FR, DE, CS, EO)
- Bank account connection via Nordigen API
- Transaction viewing and transparency features
- Responsive design with Bootstrap 5

## TO DO:
- Complete translation files
- make a CRON to update account transparancy.
- multi-account support with a database maybe?
- public page


## Requirements

- Python 3.8+
- Flask and related extensions
- Nordigen API credentials

## Installation

### Setting up the environment

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pirate-transparancy
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create your environment configuration:
   ```bash
   # Copy the example environment file
   cp .env.example instance/.env
   
   # Edit the file with your actual credentials
   ```

## Configuration

Edit the `instance/.env` file with your specific settings:

```
# Nordigen/GoCardless API credentials
NORDIGEN_SECRET_ID=your_nordigen_secret_id_here
NORDIGEN_SECRET_KEY=your_nordigen_secret_key_here

# Flask configuration
SECRET_KEY=your_flask_secret_key_here
DEBUG=True  # Set to False in production

# Authentication settings
ADMIN_PASSWORD=your_secure_admin_password_here

# Nordigen Country code
NORDIGEN_COUNTRY=FR
```

## Running the Application

### Development Mode

1. Make sure your virtual environment is activated
2. Compile translations:
   ```bash
   python compile_translations_direct.py
   ```
3. Run the development server:
   ```bash
   python app.py
   ```
4. Access the application at http://localhost:5000

### Production Mode

1. Set `DEBUG=False` in your `instance/.env` file
2. Set a strong `SECRET_KEY` in your `instance/.env` file
3. Consider using a production WSGI server like Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
   ```
4. Or with uWSGI:
   ```bash
   pip install uwsgi
   uwsgi --http 0.0.0.0:5000 --module app:app
   ```

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t transparency-app .
   ```

2. Run the container:
   ```bash
   docker run -d --name transparency-app \
     -p 5000:5000 \
     -v $(pwd)/instance:/app/instance \
     transparency-app
   ```
   
   For Windows PowerShell:
   ```powershell
   docker run -d --name transparency-app `
     -p 5000:5000 `
     -v ${PWD}/instance:/app/instance `
     transparency-app
   ```

3. Make sure your `instance/.env` file is correctly configured before building/running the Docker container.

## Translations

The application supports the following languages:
- English (en)
- French (fr)
- German (de)
- Czech (cs)
- Esperanto (eo)

To recompile translations after making changes to the .po files:
```bash
python compile_translations_direct.py
```

## User Guide

1. Access the application through your browser
2. Login with the admin credentials (default username: `admin`, password: set in your .env file)
3. Navigate to "Connect bank" to connect your bank account via Nordigen
4. View your transactions in the Dashboard and Transparency sections
5. Switch languages using the dropdown in the navigation bar

## Security Notes

- Always change default passwords
- In production, ensure `DEBUG=False`
- Keep your `.env` file secure and never commit it to version control
- The `instance` directory contains sensitive data; secure it appropriately

## License

Copyright (c) 2025 Umber "Gravfu" D.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Credits

Maintainer: Umber "Gravfu" D.
