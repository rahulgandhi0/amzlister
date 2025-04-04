import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

APP_KEY = 'cchwygqtvqy7nnn'
APP_SECRET = 'jbudh1r4780mzsp'

def main():
    auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)
    
    authorize_url = auth_flow.start()
    print("1. Go to: " + authorize_url)
    print("2. Click \"Allow\" (you might have to log in first).")
    print("3. Copy the authorization code.")
    auth_code = input("Enter the authorization code here: ").strip()
    
    try:
        oauth_result = auth_flow.finish(auth_code)
        with open('dropbox_token.txt', 'w') as f:
            f.write(oauth_result.access_token)
        print("Access token saved to dropbox_token.txt")
    except Exception as e:
        print('Error: %s' % (e,))

if __name__ == '__main__':
    main() 