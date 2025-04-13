"""
This module handles background scheduled tasks for the application.
"""
import os
import json
from flask import current_app
from app.nordigen_api import get_client
import time
# from sqlalchemy.orm.exc import DetachedInstanceError

def refresh_all_accounts_job(app):
    """
    Background job to refresh all user accounts from Nordigen API.
    This runs daily to ensure account data is up to date.
    """
    with app.app_context():
        print(time.strftime("%A, %d. %B %Y %I:%M:%S %p"))
        try:
            current_app.logger.info("Starting scheduled refresh of all accounts")
            
            # Initialize Nordigen client
            client = get_client()
            
            # Get all users who have account data
            instance_path = current_app.instance_path
            user_files = {}
            
            # Find all user-related files in the instance directory
            for filename in os.listdir(instance_path):
                if filename.startswith('account_data_') and filename.endswith('.json'):
                    # Extract user_id from filename (account_data_1.json -> 1)
                    try:
                        user_id = int(filename.replace('account_data_', '').replace('.json', ''))
                        if user_id not in user_files:
                            user_files[user_id] = []
                        user_files[user_id].append(filename)
                    except ValueError:
                        continue
            
            # Process each user's accounts
            total_users = len(user_files)
            users_processed = 0
            accounts_updated = 0
            
            for user_id, files in user_files.items():
                try:
                    current_app.logger.info(f"Processing accounts for user {user_id}")
                    
                    # Get requisition map if available
                    requisition_map = {}
                    req_map_file = os.path.join(instance_path, f'requisition_map_{user_id}.json')
                    if os.path.exists(req_map_file):
                        try:
                            with open(req_map_file, 'r') as f:
                                requisition_map = json.load(f)
                        except json.JSONDecodeError:
                            current_app.logger.error(f"Error parsing requisition map for user {user_id}")
                    
                    # Get account data file
                    data_file = os.path.join(instance_path, f'account_data_{user_id}.json')
                    if not os.path.exists(data_file):
                        continue
                    
                    try:
                        with open(data_file, 'r') as f:
                            accounts_data = json.load(f)
                    except json.JSONDecodeError:
                        current_app.logger.error(f"Error parsing account data for user {user_id}")
                        continue
                    
                    # Update each account for this user
                    updated_accounts = []
                    
                    for account in accounts_data:
                        account_id = account.get('id')
                        if not account_id:
                            continue
                            
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
                            accounts_updated += 1
                            
                        except Exception as e:
                            current_app.logger.error(f"Error refreshing account {account_id}: {str(e)}")
                    
                    # Save updated account data back to file
                    if updated_accounts:
                        with open(data_file, 'w') as f:
                            json.dump(updated_accounts, f, indent=4)
                        current_app.logger.info(f"Updated {len(updated_accounts)} accounts for user {user_id}")
                    
                    users_processed += 1
                    
                except Exception as e:
                    current_app.logger.error(f"Error processing user {user_id}: {str(e)}")
            
            current_app.logger.info(f"Completed scheduled refresh: "
                                f"processed {users_processed}/{total_users} users, "
                                f"updated {accounts_updated} accounts.")
                    
        except Exception as e:
            current_app.logger.error(f"Error in scheduled account refresh job: {str(e)}")
