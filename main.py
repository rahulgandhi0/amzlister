import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                            QLabel, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
import json
import yaml
import uuid
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

class CategorySelector:
    def __init__(self, parent_layout):
        self.parent_layout = parent_layout
        self.category_layouts = {}
        self.category_combos = {}
        self.category_tree = {}
        self.current_path = {}
        
        # Add first level
        self.add_category_level(0)
        
        # Connect events
        self.category_combos[0].currentIndexChanged.connect(lambda: self.on_category_selected(0))
        
    def add_category_level(self, level):
        """Add a new category selection level to the UI"""
        layout = QHBoxLayout()
        combo = QComboBox()
        combo.setPlaceholderText("Select category...")
        
        layout.addWidget(QLabel(f"Category Level {level + 1}:"))
        layout.addWidget(combo)
        
        self.parent_layout.addLayout(layout)
        self.category_layouts[level] = layout
        self.category_combos[level] = combo
        
    def clear_category_levels(self, start_level=0):
        """Clear category levels starting from the given level"""
        for level in sorted(self.category_layouts.keys()):
            if level >= start_level:
                layout = self.category_layouts[level]
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                self.parent_layout.removeItem(layout)
                del self.category_layouts[level]
                del self.category_combos[level]
                if level in self.current_path:
                    del self.current_path[level]
                    
    def fetch_categories(self, category_id=None):
        """Fetch categories from eBay Taxonomy API"""
        try:
            with open('ebay.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            headers = {
                'Authorization': f'Bearer {config["token"]}',
                'Content-Type': 'application/json'
            }
            
            # First, get the default category tree ID
            response = requests.get(
                'https://api.ebay.com/commerce/taxonomy/v1/get_default_category_tree_id?marketplace_id=EBAY_US',
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get category tree ID: {response.text}")
                
            tree_id = response.json()['categoryTreeId']
            
            # If no category_id provided, get top-level categories
            if category_id is None:
                response = requests.get(
                    f'https://api.ebay.com/commerce/taxonomy/v1/category_tree/{tree_id}',
                    headers=headers
                )
            else:
                # Get subcategories for the selected category
                response = requests.get(
                    f'https://api.ebay.com/commerce/taxonomy/v1/category_tree/{tree_id}/get_category_subtree?category_id={category_id}',
                    headers=headers
                )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get categories: {response.text}")
                
            return response.json()
            
        except Exception as e:
            print(f"Error fetching categories: {str(e)}")
            return None
            
    def on_category_selected(self, level):
        """Handle category selection at a specific level"""
        if level not in self.category_combos:
            return
            
        combo = self.category_combos[level]
        selected_text = combo.currentText()
        if not selected_text:
            return
            
        try:
            # Extract category ID from the selected text
            category_id = selected_text.split("(")[-1].replace(")", "").strip()
            
            # Update current path
            self.current_path[level] = category_id
            
            # Clear subsequent levels
            self.clear_category_levels(level + 1)
            
            # Fetch subcategories
            response = self.fetch_categories(category_id)
            if response and 'categorySubtreeNode' in response:
                subcategories = response['categorySubtreeNode'].get('childCategoryTreeNodes', [])
                
                if subcategories:
                    next_level = level + 1
                    self.add_category_level(next_level)
                    new_combo = self.category_combos[next_level]
                    
                    # Add subcategories to the new dropdown
                    for category in subcategories:
                        cat_id = category['category']['categoryId']
                        cat_name = category['category']['categoryName']
                        new_combo.addItem(f"{cat_name} ({cat_id})")
                    
                    # Connect the new dropdown's selection event
                    new_combo.currentIndexChanged.connect(lambda: self.on_category_selected(next_level))
                    
        except Exception as e:
            print(f"Error in category selection: {str(e)}")
            print("Selected text:", selected_text)
            
    def get_selected_category_id(self):
        """Get the ID of the last selected category (leaf node)"""
        if not self.current_path:
            return None
        return list(self.current_path.values())[-1]

class AmazonEbayScraper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Amazon to eBay Scraper")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize Dropbox client
        self.dbx = None
        try:
            with open('dropbox_token.txt', 'r') as f:
                token = f.read().strip()
                self.dbx = dropbox.Dropbox(token)
        except:
            QMessageBox.warning(self, "Warning", "Dropbox token not found. Please add your token to dropbox_token.txt")
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter Amazon Product URL")
        url_layout.addWidget(self.url_input)
        
        # Scrape button
        self.scrape_button = QPushButton("Scrape Product")
        self.scrape_button.clicked.connect(self.scrape_product)
        url_layout.addWidget(self.scrape_button)
        layout.addLayout(url_layout)
        
        # Category selection
        category_container = QWidget()
        category_layout = QVBoxLayout(category_container)
        self.category_selector = CategorySelector(category_layout)
        layout.addWidget(category_container)
        
        # Results display
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        layout.addWidget(self.results_display)
        
        # Post to eBay button
        self.ebay_button = QPushButton("Post to eBay")
        self.ebay_button.clicked.connect(self.post_to_ebay)
        self.ebay_button.setEnabled(False)
        layout.addWidget(self.ebay_button)
        
        self.product_data = None
        self.driver = None
        
        # Load initial categories
        self.load_initial_categories()

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in headless mode
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Use local ChromeDriver
            driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver")
            if not os.path.exists(driver_path):
                QMessageBox.critical(self, "Error", "ChromeDriver not found. Please place chromedriver in the same directory as main.py")
                return None
                
            # Set executable permissions
            os.chmod(driver_path, 0o755)
            
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"ChromeDriver setup failed: {str(e)}")
            return None

    def scrape_product(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter an Amazon URL")
            return
            
        try:
            if not self.driver:
                self.setup_driver()
                
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 10)
            
            # Scrape product information
            title = wait.until(EC.presence_of_element_located((By.ID, "productTitle"))).text.strip()
            
            # Get price (handling different price formats)
            try:
                price = self.driver.find_element(By.CLASS_NAME, "a-price-whole").text.strip()
                cents = self.driver.find_element(By.CLASS_NAME, "a-price-fraction").text.strip()
                price = f"{price}.{cents}"
            except:
                try:
                    price = self.driver.find_element(By.CLASS_NAME, "a-offscreen").text.strip()
                    price = price.replace("$", "").replace(",", "")
                except:
                    price = "Price not found"
            
            # Get description
            description = ""
            try:
                description = self.driver.find_element(By.ID, "productDescription").text.strip()
            except:
                try:
                    description = self.driver.find_element(By.ID, "feature-bullets").text.strip()
                except:
                    description = "Description not found"
                
            # Get product details
            details = {}
            try:
                detail_bullets = self.driver.find_elements(By.CSS_SELECTOR, "#detailBullets_feature_div li")
                for bullet in detail_bullets:
                    text = bullet.text.strip()
                    if ":" in text:
                        key, value = text.split(":", 1)
                        details[key.strip()] = value.strip()
            except:
                details = {"Error": "Could not fetch product details"}
                
            # Get image URLs
            images = []
            try:
                # Try to get the main product image first
                main_image = self.driver.find_element(By.ID, "landingImage")
                if main_image:
                    image_url = main_image.get_attribute("src")
                    if image_url:
                        # Convert thumbnail URL to full-size image URL
                        image_url = image_url.split('._')[0] + "._AC_SL1500_.jpg"
                        images.append(image_url)
                        print(f"Found main image URL: {image_url}")
                
                # Try to get additional images
                alt_images = self.driver.find_elements(By.CSS_SELECTOR, "#altImages img.a-dynamic-image")
                for img in alt_images:
                    image_url = img.get_attribute("src")
                    if image_url and "sprite" not in image_url:
                        # Convert thumbnail URL to full-size image URL
                        image_url = image_url.split('._')[0] + "._AC_SL1500_.jpg"
                        if image_url not in images:
                            images.append(image_url)
                            print(f"Found additional image URL: {image_url}")
            except Exception as e:
                print(f"Error getting images: {str(e)}")
                
            # Store the data
            self.product_data = {
                "title": title,
                "price": price,
                "description": description,
                "details": details,
                "images": images
            }
            
            # Display the results
            display_text = f"""
Title: {title}
Price: ${price}
Description: {description}
Number of Images Found: {len(images)}

Product Details:
"""
            for key, value in details.items():
                display_text += f"{key}: {value}\n"
                
            if images:
                display_text += "\nImage URLs:\n"
                for url in images:
                    display_text += f"{url}\n"
            else:
                display_text += "\nNo images found!"
                
            self.results_display.setText(display_text)
            self.ebay_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            
    def download_and_prepare_image(self, image_url):
        """Download image locally and prepare it for eBay upload"""
        try:
            # Create temp directory if it doesn't exist
            import os
            temp_dir = "temp_images"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # Generate unique filename
            import uuid
            filename = f"{temp_dir}/{uuid.uuid4()}.jpg"
            
            # Download image
            response = requests.get(image_url, stream=True)
            if response.status_code != 200:
                raise Exception(f"Failed to download image: {response.status_code}")
            
            # Save image locally
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify the image was saved
            if not os.path.exists(filename):
                raise Exception("Failed to save image locally")
            
            return filename
            
        except Exception as e:
            raise Exception(f"Failed to download and prepare image: {str(e)}")

    def upload_to_dropbox(self, image_url):
        try:
            # Download the image
            print(f"Attempting to download image from: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Generate a unique filename
            image_filename = str(uuid.uuid4()) + '.jpg'
            
            # Ensure amazon_images folder exists
            if not os.path.exists('amazon_images'):
                os.makedirs('amazon_images')
                print("Created amazon_images folder")
            else:
                print("Found existing amazon_images folder")
            
            # Save image locally first
            local_path = os.path.join('amazon_images', image_filename)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"Saved image locally to: {local_path}")
            
            # Upload to Dropbox
            dropbox_path = f"/amazon_images/{image_filename}"
            print(f"Uploading to Dropbox as: {dropbox_path}")
            
            with open(local_path, 'rb') as f:
                self.dbx.files_upload(f.read(), dropbox_path)
            print("Successfully uploaded file to Dropbox")
            
            # Get temporary direct link
            try:
                result = self.dbx.files_get_temporary_link(dropbox_path)
                direct_link = result.link
                print(f"Generated temporary direct link: {direct_link}")
            except Exception as e:
                print(f"Error getting temporary link: {str(e)}")
                # Fallback to shared link if temporary link fails
                shared_link = self.dbx.sharing_create_shared_link(dropbox_path)
                direct_link = shared_link.url.replace('www.dropbox.com', 'dl.dropboxusercontent.com').replace('?dl=0', '?raw=1')
                print(f"Fallback to shared link: {direct_link}")
            
            # Verify the image is accessible
            verify_response = requests.head(direct_link, timeout=30)
            verify_response.raise_for_status()
            print("Verified image URL is accessible")
            
            # Clean up local file
            os.remove(local_path)
            print("Cleaned up local file")
            
            return direct_link
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading or verifying image: {str(e)}")
            raise Exception(f"Failed to download or verify image: {str(e)}")
        except dropbox.exceptions.DropboxException as e:
            print(f"Dropbox error: {str(e)}")
            raise Exception(f"Failed to upload to Dropbox: {str(e)}")
        except Exception as e:
            print(f"Unexpected error in upload_to_dropbox: {str(e)}")
            raise Exception(f"Failed to process image: {str(e)}")

    def post_to_ebay(self):
        if not self.product_data:
            QMessageBox.warning(self, "Error", "No product data to post")
            return
            
        try:
            # Load eBay credentials from config
            with open('ebay.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            # Verify required credentials are present
            required_fields = ["appid", "devid", "certid", "token"]
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                raise Exception(f"Missing required eBay credentials in ebay.yaml: {', '.join(missing_fields)}")
            
            # Get and validate image URL
            image_url = None
            if "images" in self.product_data and self.product_data["images"]:
                image_url = self.product_data["images"][0]
                print(f"Found main image URL: {image_url}")
            
            if not image_url:
                raise Exception("No image URL found in product data")
            
            # Upload image to Dropbox and get direct link
            try:
                hosted_image_url = self.upload_to_dropbox(image_url)
                print(f"Successfully got hosted image URL: {hosted_image_url}")
                
                # Verify the image URL is valid and accessible
                verify_response = requests.head(hosted_image_url, timeout=30)
                verify_response.raise_for_status()
                print("Verified image URL is accessible")
                
                if not hosted_image_url.startswith('https://'):
                    raise Exception("Invalid image URL format - must be HTTPS")
                    
                # XML encode the URL
                hosted_image_url = escape(hosted_image_url)
            except Exception as e:
                raise Exception(f"Failed to process image: {str(e)}")
            
            if not hosted_image_url:
                raise Exception("Failed to get hosted image URL")
            
            # Clean up and format the price
            price = str(self.product_data["price"]).replace("$", "").replace(",", "").strip()
            try:
                price = "{:.2f}".format(float(price))
            except:
                price = "99.99"  # Default price if parsing fails
            
            # Extract shipping dimensions and weight from product details
            dimensions = "12 x 12 x 12"  # Default dimensions
            weight = 1  # Default weight in pounds
            sku = ""  # Default empty SKU
            
            if "details" in self.product_data:
                details = self.product_data["details"]
                
                # Extract dimensions
                if "Product Dimensions" in details:
                    dim_str = details["Product Dimensions"]
                    # Extract numbers from string like "13.78 x 9.65 x 3.94 inches"
                    import re
                    numbers = re.findall(r'\d+\.?\d*', dim_str)
                    if len(numbers) >= 3:
                        dimensions = f"{numbers[0]} x {numbers[1]} x {numbers[2]}"
                
                # Extract weight
                if "Product Dimensions" in details:
                    weight_str = details["Product Dimensions"]
                    # Extract weight from string like "3.44 Pounds"
                    weight_match = re.search(r'(\d+\.?\d*)\s*Pounds?', weight_str)
                    if weight_match:
                        weight = int(float(weight_match.group(1)) + 0.5)  # Round up to nearest pound
                
                # Extract ASIN for SKU
                if "ASIN" in details:
                    sku = details["ASIN"]
            
            # Prepare headers for eBay Trading API
            headers = {
                'X-EBAY-API-SITEID': '0',  # US site
                'X-EBAY-API-COMPATIBILITY-LEVEL': '1399',  # Latest version
                'X-EBAY-API-CALL-NAME': 'AddItem',
                'X-EBAY-API-APP-NAME': config["appid"],
                'X-EBAY-API-DEV-NAME': config["devid"],
                'X-EBAY-API-CERT-NAME': config["certid"],
                'Content-Type': 'text/xml'
            }
            
            # Prepare AddItem XML request
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<AddItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{config["token"]}</eBayAuthToken>
  </RequesterCredentials>
  <ErrorLanguage>en_US</ErrorLanguage>
  <WarningLevel>High</WarningLevel>
  <Item>
    <Title>{self.product_data["title"][:80]}</Title>
    <Description><![CDATA[{self.product_data["description"]}]]></Description>
    <PrimaryCategory>
      <CategoryID>{self.category_selector.get_selected_category_id()}</CategoryID>
    </PrimaryCategory>
    <StartPrice>{price}</StartPrice>
    <CategoryMappingAllowed>true</CategoryMappingAllowed>
    <ConditionID>1000</ConditionID>
    <Country>US</Country>
    <Currency>USD</Currency>
    <ListingDuration>GTC</ListingDuration>
    <ListingType>FixedPriceItem</ListingType>
    <PictureDetails>
      <PhotoDisplay>PicturePack</PhotoDisplay>
      <GalleryType>Gallery</GalleryType>
      <PictureURL>{hosted_image_url}</PictureURL>
    </PictureDetails>
    <PostalCode>95125</PostalCode>
    <Quantity>1</Quantity>
    <SKU>{sku}</SKU>
    <ItemSpecifics>
      <NameValueList>
        <Name>Brand</Name>
        <Value>Unbranded</Value>
      </NameValueList>
      <NameValueList>
        <Name>Type</Name>
        <Value>Other</Value>
      </NameValueList>
    </ItemSpecifics>
    <ShippingPackageDetails>
      <MeasurementUnit>English</MeasurementUnit>
      <PackageDepth>{dimensions.split(' x ')[2]}</PackageDepth>
      <PackageLength>{dimensions.split(' x ')[0]}</PackageLength>
      <PackageWidth>{dimensions.split(' x ')[1]}</PackageWidth>
      <ShippingPackage>PackageThickEnvelope</ShippingPackage>
      <WeightMajor>{weight}</WeightMajor>
      <WeightMinor>0</WeightMinor>
    </ShippingPackageDetails>
    <SellerProfiles>
      <SellerPaymentProfile>
        <PaymentProfileID>{config["payment_policy_id"]}</PaymentProfileID>
      </SellerPaymentProfile>
      <SellerReturnProfile>
        <ReturnProfileID>{config["return_policy_id"]}</ReturnProfileID>
      </SellerReturnProfile>
      <SellerShippingProfile>
        <ShippingProfileID>{config["fulfillment_policy_id"]}</ShippingProfileID>
      </SellerShippingProfile>
    </SellerProfiles>
    <Site>US</Site>
  </Item>
</AddItemRequest>"""
            
            print("Sending request to eBay API...")
            print(f"Headers: {str(headers)}")
            print(f"XML Request: {xml_request}")
            
            # Make the API call
            response = requests.post(
                'https://api.ebay.com/ws/api.dll',
                headers=headers,
                data=xml_request.encode('utf-8')
            )
            
            print(f"eBay API Response: {response.text}")
            
            # Parse the response
            root = ET.fromstring(response.text)
            
            # Check for success
            ack = root.find(".//Ack")
            if ack is not None and ack.text == "Success":
                item_id = root.find(".//ItemID")
                if item_id is not None:
                    QMessageBox.information(self, "Success", f"Item listed successfully! Item ID: {item_id.text}")
                else:
                    QMessageBox.information(self, "Success", "Item listed successfully!")
            else:
                # Get error messages
                errors = root.findall(".//Errors")
                error_messages = []
                for error in errors:
                    short_msg = error.find("ShortMessage")
                    long_msg = error.find("LongMessage")
                    if long_msg is not None:
                        error_messages.append(long_msg.text)
                    elif short_msg is not None:
                        error_messages.append(short_msg.text)
                
                error_text = "\n".join(error_messages) if error_messages else "Unknown error occurred"
                QMessageBox.critical(self, "Error", f"Failed to list item:\n{error_text}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            print(f"Error in post_to_ebay: {str(e)}")

    def closeEvent(self, event):
        if self.driver:
            self.driver.quit()
        event.accept()

    def load_initial_categories(self):
        """Load top-level categories into the first dropdown"""
        try:
            response = self.category_selector.fetch_categories()
            if response and 'rootCategoryNode' in response:
                categories = response['rootCategoryNode'].get('childCategoryTreeNodes', [])
                combo = self.category_selector.category_combos[0]
                combo.clear()
                
                for category in categories:
                    cat_id = category['category']['categoryId']
                    cat_name = category['category']['categoryName']
                    combo.addItem(f"{cat_name} ({cat_id})")
                    
        except Exception as e:
            print(f"Error loading initial categories: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AmazonEbayScraper()
    window.show()
    sys.exit(app.exec()) 