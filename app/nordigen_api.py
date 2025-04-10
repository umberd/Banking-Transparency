import os
import json
from datetime import datetime
from flask import Blueprint, redirect, url_for, session, request, render_template, flash, current_app
from flask_login import login_required, current_user
from nordigen import NordigenClient

nordigen_bp = Blueprint('nordigen', __name__, url_prefix='/nordigen')

def get_client():
    """Initialize Nordigen client with credentials from environment variables"""
    secret_id = os.environ.get('NORDIGEN_SECRET_ID')
    secret_key = os.environ.get('NORDIGEN_SECRET_KEY')
    
    if not secret_id or not secret_key:
        raise ValueError("Nordigen credentials are not configured")
    
    client = NordigenClient(
        secret_id=secret_id,
        secret_key=secret_key
    )
    
    # Ensure we have a valid token
    try:
        # Generate a new access token
        token_data = client.generate_token()
        current_app.logger.info("New token successfully generated")
    except Exception as e:
        current_app.logger.error(f"Error generating token: {str(e)}")
        raise
    
    return client

def save_institutions_to_file(institutions, user_id):
    """Save institutions data to a file instead of session"""
    file_path = os.path.join(current_app.instance_path, f'institutions_{user_id}.json')
    with open(file_path, 'w') as f:
        json.dump(institutions, f)
    return file_path

def get_institutions_from_file(user_id):
    """Get institutions data from file"""
    file_path = os.path.join(current_app.instance_path, f'institutions_{user_id}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []

def save_account_ids_to_file(account_ids, user_id):
    """Save account IDs to a file instead of session"""
    file_path = os.path.join(current_app.instance_path, f'account_ids_{user_id}.json')
    with open(file_path, 'w') as f:
        json.dump(account_ids, f)
    return file_path

def get_account_ids_from_file(user_id):
    """Get account IDs from file"""
    file_path = os.path.join(current_app.instance_path, f'account_ids_{user_id}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []

@nordigen_bp.route('/init')
@login_required
def init_nordigen():
    """Initialize connection with Nordigen and display available banks"""
    try:
        client = get_client()
        
        # Get list of institutions (banks) available in the country inside .env
        institutions = client.institution.get_institutions(country=os.environ.get('NORDIGEN_COUNTRY'))
        
        # Save institution list to file instead of session
        save_institutions_to_file(institutions, current_user.id)
        
        # Store only a reference in the session
        session['has_institutions'] = True
        
        return render_template('select_bank.html', institutions=institutions)
    except Exception as e:
        current_app.logger.error(f"Error during initialization: {str(e)}")
        flash(f"Error connecting to Nordigen API: {str(e)}", "error")
        return redirect(url_for('main.dashboard'))

@nordigen_bp.route('/select-bank/<institution_id>')
@login_required
def select_bank(institution_id):
    """Create a requisition link for a selected bank"""
    client = get_client()
    
    # Configure redirect after authentication
    redirect_uri = url_for('nordigen.bank_callback', _external=True)
    
    try:
        # Log information for debugging
        current_app.logger.info(f"Attempting to connect to institution {institution_id}")
        current_app.logger.info(f"Redirect URI: {redirect_uri}")
        current_app.logger.info(f"User ID: {current_user.id}")
        
        # Create a unique reference ID
        reference_id = f"user_{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Use the two required positional arguments
        requisition = client.requisition.create_requisition(
            redirect_uri,  # First positional argument: redirect_uri
            reference_id,  # Second positional argument: reference_id
            institution_id=institution_id  # Named argument: institution_id
        )
        
        # Log Nordigen's response
        current_app.logger.info(f"Requisition successfully created: {requisition['id']}")
        current_app.logger.info(f"Complete response: {requisition}")
        
        # Save requisition ID in session
        session['requisition_id'] = requisition['id']
        
        # Check if link is available in the response
        if 'link' in requisition and requisition['link']:
            return redirect(requisition['link'])
        else:
            # If link is not provided, it's an API issue
            raise ValueError("Redirection link was not provided by the Nordigen API")
            
    except Exception as e:
        # Detailed error logging
        current_app.logger.error(f"Error creating requisition for {institution_id}: {str(e)}")
        current_app.logger.error(f"Exception type: {type(e).__name__}")
        
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # More informative error message
        flash(f"Error connecting to the bank ({institution_id}): {str(e)}", "error")
        
        # Redirect to the bank selection page instead of dashboard
        return redirect(url_for('nordigen.init_nordigen'))

# Fix: Add route alias to be compatible with the generated URL
@nordigen_bp.route('/callback')
@nordigen_bp.route('/bank-callback')
@login_required
def bank_callback():
    """Process return from bank authentication"""
    client = get_client()
    
    # Get requisition ID from session
    requisition_id = session.get('requisition_id')
    
    if not requisition_id:
        flash("Session expired. Please start again.", "error")
        return redirect(url_for('nordigen.init_nordigen'))
    
    # Get requisition details
    requisition = client.requisition.get_requisition_by_id(requisition_id)
    
    # Check if authentication is complete
    if not requisition.get('accounts'):
        flash("Bank authentication failed or was cancelled.", "error")
        return redirect(url_for('nordigen.init_nordigen'))
    
    # Store account IDs in file instead of session
    save_account_ids_to_file(requisition['accounts'], current_user.id)
    
    # Store only a reference in the session
    session['has_account_ids'] = True
    
    # Redirect to accounts page
    return redirect(url_for('nordigen.list_accounts'))

@nordigen_bp.route('/accounts')
@login_required
def list_accounts():
    """Display list of available accounts directly from Nordigen API"""
    client = get_client()
    
    try:
        # Get requisition ID from session
        requisition_id = session.get('requisition_id')
        
        if not requisition_id:
            # Try to find the latest requisition for this user directly from Nordigen
            try:
                # List all requisitions and find the most recent ones for this user
                requisitions = client.requisition.get_requisitions()
                user_requisitions = [r for r in requisitions['results'] 
                                   if r['reference'].startswith(f"user_{current_user.id}_")]
                
                if user_requisitions:
                    # Sort by created date (newest first)
                    user_requisitions.sort(key=lambda r: r.get('created', ''), reverse=True)
                    requisition_id = user_requisitions[0]['id']
                    current_app.logger.info(f"Found existing requisition {requisition_id} for user {current_user.id}")
                else:
                    flash("No accounts available. Please connect a bank account first.", "info")
                    return redirect(url_for('nordigen.init_nordigen'))
            except Exception as e:
                current_app.logger.error(f"Error fetching requisitions: {str(e)}")
                flash("No active bank connections found. Please connect a bank account.", "warning")
                return redirect(url_for('nordigen.init_nordigen'))
        
        # Get requisition details directly from Nordigen API
        requisition = client.requisition.get_requisition_by_id(requisition_id)
        account_ids = requisition.get('accounts', [])
        
        if not account_ids:
            flash("No accounts available. Please try again.", "error")
            return redirect(url_for('nordigen.init_nordigen'))
        
        # For reference, save the account IDs to a local file (but don't rely on it)
        save_account_ids_to_file(account_ids, current_user.id)
        
        accounts_data = []
        
        # Get details for each account directly from Nordigen API
        for account_id in account_ids:
            try:
                # Get basic account information from API
                account = client.account_api(account_id)
                transactions = account.get_transactions()
                account_details = account.get_details()
                account_balances = account.get_balances()
                
                # Ensure transactions structure is correct
                if 'transactions' not in transactions:
                    transactions = {'transactions': {'booked': [], 'pending': []}}

                # Store data in our list
                accounts_data.append({
                    'id': account_id,
                    'name': account_details.get('account', {}).get('name', 'Unnamed account'),
                    'iban': account_details.get('account', {}).get('iban', 'IBAN not available'),
                    'currency': account_details.get('account', {}).get('currency', 'EUR'),
                    'balances': account_balances.get('balances', []),
                    'transactions': transactions.get('transactions', {'booked': [], 'pending': []})

                })
                
            except Exception as e:
                current_app.logger.error(f"Error retrieving account details for {account_id}: {str(e)}")
        
        # Cache account data for later use (but don't rely on this for retrievals)
        with open(os.path.join(current_app.instance_path, f'account_data_{current_user.id}.json'), 'w') as f:
            json.dump(accounts_data, f, indent=4)
        
        # Store mapping between account IDs and requisition IDs for deletion purposes
        requisition_map_file = os.path.join(current_app.instance_path, f'requisition_map_{current_user.id}.json')
        requisition_map = {}
        
        if os.path.exists(requisition_map_file):
            try:
                with open(requisition_map_file, 'r') as f:
                    requisition_map = json.load(f)
            except:
                requisition_map = {}
        
        # Map each account ID to its requisition
        for account_id in account_ids:
            requisition_map[account_id] = requisition_id
            
        # Save the updated mapping
        with open(requisition_map_file, 'w') as f:
            json.dump(requisition_map, f, indent=4)
            
        return render_template('accounts.html', accounts=accounts_data)
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving account details: {str(e)}")
        flash(f"Error retrieving account details: {str(e)}", "error")
        return redirect(url_for('nordigen.init_nordigen'))

@nordigen_bp.route('/transactions/<account_id>')
@login_required
def view_transactions(account_id):
    """Display transactions for a specific account directly from Nordigen API"""
    client = get_client()
    
    try:
        # Get all account information directly from Nordigen API
        account_api = client.account_api(account_id)
        transactions = account_api.get_transactions()
        account_details = account_api.get_details()
        account_balances = account_api.get_balances()
        
        # Ensure transactions structure is correct
        if 'transactions' not in transactions:
            transactions = {'transactions': {'booked': [], 'pending': []}}
        
        # Create full account object from API data
        current_account = {
            'id': account_id,
            'name': account_details.get('account', {}).get('name', 'Unnamed account'),
            'iban': account_details.get('account', {}).get('iban', 'IBAN not available'),
            'currency': account_details.get('account', {}).get('currency', 'EUR'),
            'balances': account_balances.get('balances', []),
            'transactions': transactions.get('transactions', {'booked': [], 'pending': []})
        }
        
        # Ensure required transaction keys exist
        if 'booked' not in current_account['transactions']:
            current_account['transactions']['booked'] = []
        if 'pending' not in current_account['transactions']:
            current_account['transactions']['pending'] = []
        
        # Update cache file if it exists (but don't rely on it for retrievals)
        data_file = os.path.join(current_app.instance_path, f'account_data_{current_user.id}.json')
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    accounts_data = json.load(f)
                
                # Update or add this account in the cache
                updated = False
                for i, acc in enumerate(accounts_data):
                    if acc['id'] == account_id:
                        accounts_data[i] = current_account
                        updated = True
                        break
                
                if not updated:
                    accounts_data.append(current_account)
                
                # Write updated cache
                with open(data_file, 'w') as f:
                    json.dump(accounts_data, f, indent=4)
            except Exception as e:
                current_app.logger.warning(f"Could not update cache file: {str(e)}")
        
        return render_template('transactions.html', 
                            account=current_account, 
                            transactions=current_account['transactions'])
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving transactions: {str(e)}")
        flash(f"Error retrieving transactions: {str(e)}", "error")
        return redirect(url_for('nordigen.list_accounts'))

@nordigen_bp.route('/delete-account/<account_id>')
@login_required
def delete_account(account_id):
    """Delete an account from the current user and Nordigen API"""
    try:
        # Initialize Nordigen client
        client = get_client()
        
        # Find requisition ID for this account from Nordigen API
        requisition_map_file = os.path.join(current_app.instance_path, f'requisition_map_{current_user.id}.json')
        requisition_map = {}
        
        if os.path.exists(requisition_map_file):
            with open(requisition_map_file, 'r') as f:
                try:
                    requisition_map = json.load(f)
                except:
                    requisition_map = {}
        
        # If we don't have a mapping for this account, try to find it from the API
        if account_id not in requisition_map:
            try:
                requisitions = client.requisition.get_requisitions()
                user_requisitions = [r for r in requisitions['results'] 
                                   if r['reference'].startswith(f"user_{current_user.id}_")]
                
                # Check each requisition to find our account
                for req in user_requisitions:
                    req_details = client.requisition.get_requisition_by_id(req['id'])
                    if account_id in req_details.get('accounts', []):
                        requisition_map[account_id] = req['id']
                        # Save the updated mapping
                        with open(requisition_map_file, 'w') as f:
                            json.dump(requisition_map, f, indent=4)
                        break
            except Exception as e:
                current_app.logger.error(f"Error searching requisitions for account {account_id}: {str(e)}")
        
        # If we have a mapping for this account, delete the requisition from Nordigen
        if account_id in requisition_map:
            requisition_id = requisition_map[account_id]
            try:
                # Delete requisition from Nordigen API
                client.requisition.delete_requisition(requisition_id=requisition_id)
                current_app.logger.info(f"Successfully deleted requisition {requisition_id} from Nordigen API")
                
                # Remove this account from our mapping
                del requisition_map[account_id]
                
                # Save updated mapping
                with open(requisition_map_file, 'w') as f:
                    json.dump(requisition_map, f, indent=4)
            except Exception as e:
                current_app.logger.error(f"Error deleting requisition from Nordigen API: {str(e)}")
                flash(f"Warning: Could not delete account from Nordigen API: {str(e)}", "warning")
        
        # Update the local cache file if it exists
        data_file = os.path.join(current_app.instance_path, f'account_data_{current_user.id}.json')
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    accounts_data = json.load(f)
                
                # Filter to remove selected account
                accounts_data = [acc for acc in accounts_data if acc['id'] != account_id]
                
                # Update data file
                with open(data_file, 'w') as f:
                    json.dump(accounts_data, f, indent=4)
            except Exception as e:
                current_app.logger.warning(f"Could not update cache file: {str(e)}")
        
        flash("Account was successfully deleted.", "success")
        
    except Exception as e:
        current_app.logger.error(f"Error deleting account {account_id}: {str(e)}")
        flash(f"Error deleting account: {str(e)}", "error")
    
    return redirect(url_for('main.dashboard'))

@nordigen_bp.route('/delete-all-accounts')
@login_required
def delete_all_accounts():
    """Delete all accounts from the current user and Nordigen API"""
    try:
        # Initialize Nordigen client
        client = get_client()
        
        # Get all user's requisitions directly from Nordigen API
        requisitions = client.requisition.get_requisitions()
        user_requisitions = [r for r in requisitions['results'] 
                           if r['reference'].startswith(f"user_{current_user.id}_")]
        
        # Delete all requisitions from Nordigen API
        deleted_count = 0
        error_count = 0
        
        for req in user_requisitions:
            try:
                requisition_id = req['id']
                # Delete requisition from Nordigen API
                client.requisition.delete_requisition(requisition_id=requisition_id)
                current_app.logger.info(f"Successfully deleted requisition {requisition_id} from Nordigen API")
                deleted_count += 1
            except Exception as e:
                current_app.logger.error(f"Error deleting requisition {req['id']}: {str(e)}")
                error_count += 1
        
        # Clean up local cache files
        files_to_clean = [
            os.path.join(current_app.instance_path, f'account_data_{current_user.id}.json'),
            os.path.join(current_app.instance_path, f'account_ids_{current_user.id}.json'),
            os.path.join(current_app.instance_path, f'requisition_map_{current_user.id}.json')
        ]
        
        for file_path in files_to_clean:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        if deleted_count > 0:
            flash(f"Successfully deleted {deleted_count} bank connections from Nordigen API.", "success")
        
        if error_count > 0:
            flash(f"Failed to delete {error_count} bank connections from Nordigen API.", "warning")
            
        if deleted_count == 0 and error_count == 0:
            flash("No accounts to delete.", "info")
            
    except Exception as e:
        current_app.logger.error(f"Error deleting accounts: {str(e)}")
        flash(f"Error deleting accounts: {str(e)}", "error")
    
    return redirect(url_for('main.dashboard'))

@nordigen_bp.route('/refresh-accounts')
@login_required
def refresh_accounts():
    """Refresh data for all user accounts directly from Nordigen API"""
    try:
        # Initialize Nordigen client
        client = get_client()
        
        # Get all user requisitions directly from Nordigen API
        requisitions = client.requisition.get_requisitions()
        user_requisitions = [r for r in requisitions['results'] 
                           if r['reference'].startswith(f"user_{current_user.id}_")]
        
        if not user_requisitions:
            flash("No accounts to refresh. Please connect a bank account first.", "warning")
            return redirect(url_for('nordigen.init_nordigen'))
        
        # Sort by created date (newest first) and get all account IDs
        user_requisitions.sort(key=lambda r: r.get('created', ''), reverse=True)
        
        # Create a list for all account IDs from all requisitions
        all_account_ids = []
        for req in user_requisitions:
            req_details = client.requisition.get_requisition_by_id(req['id'])
            all_account_ids.extend(req_details.get('accounts', []))
        
        if not all_account_ids:
            flash("No accounts to refresh.", "info")
            return redirect(url_for('main.dashboard'))
        
        # Refresh information for each account
        updated_accounts = []
        for account_id in all_account_ids:
            try:
                # Get updated account information directly from API
                account_api = client.account_api(account_id)
                account_details = account_api.get_details()
                account_balances = account_api.get_balances()
                account_transactions = account_api.get_transactions()
                
                # Create updated account object from fresh API data
                updated_account = {
                    'id': account_id,
                    'name': account_details.get('account', {}).get('name', 'Unnamed account'),
                    'iban': account_details.get('account', {}).get('iban', 'IBAN not available'),
                    'currency': account_details.get('account', {}).get('currency', 'EUR'),
                    'balances': account_balances.get('balances', []),
                    'transactions': account_transactions.get('transactions', {'booked': [], 'pending': []})
                }
                
                # Ensure required keys exist for transactions
                if 'booked' not in updated_account['transactions']:
                    updated_account['transactions']['booked'] = []
                if 'pending' not in updated_account['transactions']:
                    updated_account['transactions']['pending'] = []
                
                updated_accounts.append(updated_account)
                
            except Exception as e:
                current_app.logger.error(f"Error refreshing account {account_id}: {str(e)}")
        
        # Update the cache file with fresh data
        data_file = os.path.join(current_app.instance_path, f'account_data_{current_user.id}.json')
        with open(data_file, 'w') as f:
            json.dump(updated_accounts, f, indent=4)
        
        # Update mapping between account IDs and requisition IDs
        requisition_map = {}
        for req in user_requisitions:
            req_details = client.requisition.get_requisition_by_id(req['id'])
            for acc_id in req_details.get('accounts', []):
                requisition_map[acc_id] = req['id']
                
        # Save the updated mapping
        requisition_map_file = os.path.join(current_app.instance_path, f'requisition_map_{current_user.id}.json')
        with open(requisition_map_file, 'w') as f:
            json.dump(requisition_map, f, indent=4)
        
        flash("All accounts were successfully refreshed.", "success")
        
    except Exception as e:
        current_app.logger.error(f"Error refreshing accounts: {str(e)}")
        flash(f"Error refreshing accounts: {str(e)}", "error")
    
    return redirect(url_for('main.dashboard'))