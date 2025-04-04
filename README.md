# Amazon to eBay Lister

A Python application that helps you list Amazon products on eBay automatically. The application scrapes product information from Amazon and creates eBay listings with proper categorization and image handling.

## Features

- Scrapes product details from Amazon URLs
- Automatically uploads product images to Dropbox
- Dynamic eBay category selection
- Automatic handling of item specifics
- Proper shipping details extraction from Amazon
- Uses eBay Trading API for listing creation

## Requirements

- Python 3.7+
- Chrome/Chromium browser
- Dropbox account
- eBay developer account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/rahulgandhi0/amzlister.git
cd amzlister
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up configuration files:
   - Create `dropbox_token.txt` with your Dropbox access token
   - Create `ebay.yaml` with your eBay API credentials:
     ```yaml
     appid: your_app_id
     devid: your_dev_id
     certid: your_cert_id
     token: your_user_token
     payment_policy_id: your_payment_policy_id
     return_policy_id: your_return_policy_id
     fulfillment_policy_id: your_fulfillment_policy_id
     ```

## Usage

1. Run the main application:
```bash
python main.py
```

2. Enter an Amazon product URL in the input field
3. Click "Scrape Product" to fetch product details
4. Select the appropriate eBay category
5. Click "Post to eBay" to create the listing

## Configuration

### Dropbox Setup
1. Create a Dropbox app at https://www.dropbox.com/developers
2. Generate an access token with the following permissions:
   - files.content.write
   - files.content.read
   - sharing.write
3. Save the token in `dropbox_token.txt`

### eBay Setup
1. Register as an eBay developer
2. Create an application and get API credentials
3. Generate user tokens
4. Create business policies (payment, return, shipping)
5. Add credentials to `ebay.yaml`

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/) 