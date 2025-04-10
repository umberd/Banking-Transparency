from flask import Blueprint, render_template, redirect, url_for, current_app, request, session, make_response
from flask_login import login_required, current_user
import os
import json
from datetime import datetime, timedelta

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Homepage"""
    # Add debug information about the current language
    from flask_babel import get_locale
    current_lang = str(get_locale())
    print(f"Current language from Babel: {current_lang}")
    print(f"Language in session: {session.get('language', 'Not set')}")
    print(f"Language in cookie: {request.cookies.get('user_language', 'Not set')}")
    
    return render_template('index.html', debug_lang=current_lang)

@main.route('/set_language/<language>')
def set_language(language):
    """Change interface language"""
    # Get the next page to redirect to
    next_url = request.referrer or url_for('main.index')
    
    # Create response for redirect
    response = make_response(redirect(next_url))
    
    # Check if the language is supported
    if language in current_app.config['LANGUAGES']:
        # Set language in session (for current session)
        session['language'] = language
        
        # Also set a persistent cookie that will last for 365 days
        expires = datetime.now() + timedelta(days=365)
        response.set_cookie('user_language', language, expires=expires)
    
    return response

@main.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for the logged in user"""
    # Check if the user has account data
    data_file = os.path.join(
        current_app.instance_path, 
        f'account_data_{current_user.id}.json'
    )
    
    accounts_data = []
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                accounts_data = json.load(f)
        except:
            pass
    
    return render_template('dashboard.html', accounts=accounts_data)

@main.route('/transparency')
def transparency():
    """Public account transparency page"""
    # Check if user is logged in to get their specific data
    if current_user.is_authenticated:
        # Get logged-in user's account data
        data_file = os.path.join(
            current_app.instance_path, 
            f'account_data_{current_user.id}.json'
        )
    else:
        # For public view, get admin's account data (ID 1)
        data_file = os.path.join(
            current_app.instance_path, 
            'account_data_1.json'  # Using the admin account (ID 1) data for public view
        )
    
    accounts_data = []
    transactions = []
    total_balance = 0
    number_of_accounts = 0
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                accounts_data = json.load(f)
            
            # Extract transactions from all accounts
            for account in accounts_data:
                number_of_accounts += 1
                if 'balances' in account:
                    print(f"Account: {account.get('balances', [{}])}")
                    balance = account.get('balances', [{}])[0].get('balanceAmount', {}).get('amount', 0)
                    print(f"Balance: {balance}")
                    total_balance += float(balance) if isinstance(balance, str) else balance
                if 'transactions' in account:
                    # Associate transactions with their account
                    for category in ['booked', 'pending']:
                        if category in account.get('transactions', {}):
                            for tx in account['transactions'][category]:
                                tx['account_name'] = account.get('name', 'Unknown account')
                                tx['account_id'] = account.get('id')
                                tx['status'] = category
                                transactions.append(tx)
        except Exception as e:
            current_app.logger.error(f"Error retrieving transactions: {str(e)}")
    
    # Sort transactions by date safely
    try:
        transactions.sort(
            key=lambda x: datetime.strptime(
                x.get('valueDate', x.get('bookingDate', '1900-01-01')), 
                '%Y-%m-%d'
            ),
            reverse=True
        )
    except Exception as e:
        current_app.logger.error(f"Error sorting transactions: {str(e)}")
        # If sorting fails, at least we have unsorted transactions


    return render_template('transparency.html', 
                         total_balance=total_balance, 
                         transactions=transactions, 
                         number_of_accounts=number_of_accounts)