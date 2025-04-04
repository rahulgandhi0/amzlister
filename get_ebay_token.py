import base64
import requests
import webbrowser
from urllib.parse import urlencode, unquote

# Load credentials from ebay.yaml
import yaml

# eBay OAuth credentials
CLIENT_ID = 'RahulGan-autolist-PRD-8f75d2108-786ee44c'
CLIENT_SECRET = 'PRD-f75d210854a3-0bd6-462e-9634-d92e'
REDIRECT_URI = 'Rahul_Gandhi-RahulGan-autoli-mrylv'

def get_authorization_url():
    """Generate the authorization URL for user consent"""
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/sell.reputation https://api.ebay.com/oauth/api_scope/sell.reputation.readonly https://api.ebay.com/oauth/api_scope/commerce.notification.subscription https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly https://api.ebay.com/oauth/api_scope/sell.stores https://api.ebay.com/oauth/api_scope/sell.stores.readonly https://api.ebay.com/oauth/scope/sell.edelivery'
    }
    return f"https://auth.ebay.com/oauth2/authorize?{urlencode(params)}"

def exchange_code_for_token(authorization_code):
    """Exchange the authorization code for an access token"""
    url = 'https://api.ebay.com/identity/v1/oauth2/token'
    
    # Decode the authorization code
    decoded_code = unquote(authorization_code)
    print(f"\nDecoded authorization code: {decoded_code}")
    
    # Create Basic Auth header
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    base64_auth = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {base64_auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': decoded_code,
        'redirect_uri': REDIRECT_URI
    }
    
    print("\nSending request with:")
    print(f"Client ID: {CLIENT_ID}")
    print(f"Redirect URI: {REDIRECT_URI}")
    
    response = requests.post(url, headers=headers, data=data)
    return response.json()

def main():
    # Open the authorization URL in the default browser
    auth_url = get_authorization_url()
    print(f"Opening authorization URL in your browser...")
    print(f"If it doesn't open automatically, please visit: {auth_url}")
    webbrowser.open(auth_url)
    
    # Get the authorization code from the user
    print("\nAfter authorizing, you'll be redirected to a URL.")
    print("Please copy the 'code' parameter from that URL and paste it here.")
    authorization_code = input("Enter the authorization code: ").strip()
    
    try:
        # Exchange the code for a token
        token_response = exchange_code_for_token(authorization_code)
        
        if 'access_token' in token_response:
            # Update the ebay.yaml file with the new token
            with open('ebay.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            config['token'] = token_response['access_token']
            config['appid'] = CLIENT_ID
            config['certid'] = CLIENT_SECRET
            config['devid'] = '2deb63a2-4795-4a3c-8761-387ce66a08ab'
            
            with open('ebay.yaml', 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            print("\nSuccess! Your new token has been saved to ebay.yaml")
            print(f"Token expires in: {token_response.get('expires_in', 'unknown')} seconds")
        else:
            print("\nError getting token:")
            print(token_response)
            
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == '__main__':
    main() 