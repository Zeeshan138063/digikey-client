import json
import time
import os
import logging
import requests
from pathlib import Path
from decouple import config

# Setup logging
logger = logging.getLogger(__name__)


class ProductDetailsAPI:
    """
    DigiKey Product Details API client for retrieving detailed product information
    using manufacturer part numbers or DigiKey part numbers.
    """

    def __init__(self):
        # Build paths inside the project like this: BASE_DIR / 'subdir'.
        self.base_dir = Path(__file__).resolve().parent

        self.client_id = config('DIGIKEY_CLIENT_ID')
        self.client_secret = config('DIGIKEY_CLIENT_SECRET')
        os.environ['DIGIKEY_CLIENT_ID'] = self.client_id
        os.environ['DIGIKEY_CLIENT_SECRET'] = self.client_secret
        os.environ['DIGIKEY_STORAGE_PATH'] = f"{self.base_dir}"
        os.environ['DIGIKEY_CLIENT_SANDBOX'] = config('DIGIKEY_CLIENT_SANDBOX', 'False')

    def get_access_token(self):
        """Reads access token from a JSON file."""
        file_path = f"{self.base_dir}/token_storage.json"
        if not os.path.exists(file_path):
            logger.error("Token file not found. Please run the main search API first to generate token.")
            return None

        with open(file_path, 'r') as f:
            data = json.load(f)
            return data['access_token']

    def get_product_details(self, product_number, manufacturer_id=None, max_retries=3, backoff_factor=2):
        """
        Get detailed product information for a specific product number.
        
        Args:
            product_number (str): The manufacturer part number or DigiKey part number
            manufacturer_id (int, optional): Manufacturer ID for exact matching
            max_retries (int): Maximum number of retry attempts
            backoff_factor (int): Backoff factor for exponential backoff
            
        Returns:
            dict: The parsed API response as a dictionary
        """
        
        # URL encode the product number to handle special characters
        encoded_product_number = requests.utils.quote(product_number, safe='')
        url = f"https://api.digikey.com/products/v4/search/{encoded_product_number}/productdetails"
        
        access_token = self.get_access_token()
        if not access_token:
            return {}
        
        headers = {
            'X-DIGIKEY-Client-Id': self.client_id,
            'X-DIGIKEY-Locale-Site': 'US',  # Changed to US for better compatibility
            'X-DIGIKEY-Locale-Language': 'en',  # Changed to en
            'X-DIGIKEY-Locale-Currency': 'USD',  # Changed to USD for better compatibility
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        params = {}
        if manufacturer_id:
            params['manufacturerId'] = str(manufacturer_id)
        
        retries = 0
        while retries < max_retries:
            try:
                logger.info(f"Fetching product details for: {product_number}")
                logger.info(f"URL: {url}")
                logger.info(f"Params: {params}")
                response = requests.get(url, headers=headers, params=params)
                
                # Log response details for debugging
                logger.info(f"Response status: {response.status_code}")
                if response.status_code == 404:
                    logger.warning(f"Product not found: {product_number}")
                    logger.info("This might be because:")
                    logger.info("1. The product number format is incorrect")
                    logger.info("2. A DigiKey part number might work better")
                    logger.info("3. The manufacturer ID might be incorrect")
                    return {}
                
                response.raise_for_status()
                logger.info(f"Product details request successful: {response.status_code}")
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    logger.error(f"Product not found (404): {product_number}")
                    return {}
                logger.error(f"HTTP error on attempt {retries + 1}/{max_retries}: {e}")
                retries += 1
                if retries < max_retries:
                    backoff = backoff_factor ** retries
                    logger.info(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed on attempt {retries + 1}/{max_retries} with error: {e}")
                retries += 1
                if retries < max_retries:
                    backoff = backoff_factor ** retries
                    logger.info(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)

        logger.error("All retry attempts failed. Returning empty dictionary.")
        return {}

    def map_product_details_to_structure(self, api_response):
        """
        Maps DigiKey ProductDetails API response to the required structure.
        
        Args:
            api_response (dict): Full API response from ProductDetails endpoint
            
        Returns:
            dict: Mapped product data following the required structure
        """
        if not api_response or 'Product' not in api_response:
            logger.error("Invalid API response structure")
            return {}
        
        product = api_response['Product']
        
        def safe_get(obj, key, default=""):
            """Safely get nested dictionary values."""
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default
        
        def get_parameter_value(parameters, parameter_text, default=""):
            """Extract parameter value by parameter text."""
            if not parameters:
                return default
            for param in parameters:
                if param.get('ParameterText') == parameter_text:
                    return param.get('ValueText', default)
            return default
        
        def format_bulk_prices(variations):
            """Format bulk pricing information."""
            if not variations or not variations[0].get('StandardPricing'):
                return ""
            
            pricing_list = []
            for price_tier in variations[0]['StandardPricing']:
                qty = price_tier.get('BreakQuantity', 0)
                price = price_tier.get('UnitPrice', 0)
                pricing_list.append(f"{qty}+-{price}")
            return ";".join(pricing_list)
        
        def get_base_price(variations):
            """Get the first unit price from StandardPricing table."""
            if not variations or not variations[0].get('StandardPricing'):
                return 0
            
            first_pricing = variations[0]['StandardPricing'][0]
            return first_pricing.get('UnitPrice', 0)
        
        def format_photos(photo_url):
            """Format photo URLs."""
            if photo_url:
                return f"{photo_url}|{photo_url}"
            return ""
        
        def format_datasheets(datasheet_url):
            """Format datasheet URLs."""
            if datasheet_url:
                # Remove leading // if present
                if datasheet_url.startswith('//'):
                    datasheet_url = 'https:' + datasheet_url
                return datasheet_url
            return ""
        
        def get_category_hierarchy(category):
            """Extract category hierarchy."""
            if not category:
                return "", "", "", "", ""
            
            main_category = category.get('Name', '')
            subcategory = ""
            sub_subcategory = ""
            sub_sub_subcategory = ""
            sub_sub_sub_subcategory = ""
            
            child_categories = category.get('ChildCategories', [])
            if child_categories:
                subcategory = child_categories[0].get('Name', '')
                
                if len(child_categories) > 1:
                    sub_subcategory = child_categories[1].get('Name', '')
                if len(child_categories) > 2:
                    sub_sub_subcategory = child_categories[2].get('Name', '')
                if len(child_categories) > 3:
                    sub_sub_sub_subcategory = child_categories[3].get('Name', '')
            
            return main_category, subcategory, sub_subcategory, sub_sub_subcategory, sub_sub_sub_subcategory
        
        def format_other_names(other_names):
            """Format other names list."""
            if other_names and isinstance(other_names, list):
                return ",".join(other_names)
            return ""
        
        # Extract data from the product
        parameters = product.get('Parameters', [])
        variations = product.get('ProductVariations', [])
        description = product.get('Description', {})
        manufacturer = product.get('Manufacturer', {})
        category = product.get('Category', {})
        classifications = product.get('Classifications', {})
        series = product.get('Series', {})
        
        # Get category hierarchy
        main_cat, sub_cat, sub_sub_cat, sub_sub_sub_cat, sub_sub_sub_sub_cat = get_category_hierarchy(category)
        
        # Map to required structure
        mapped_product = {
            "Product_Name_En": safe_get(description, 'ProductDescription'),
            "ManufacturerPartNumber": product.get('ManufacturerProductNumber', ''),
            "Manufacturer_Name": safe_get(manufacturer, 'Name'),
            "Series": safe_get(series, 'Name'),
            "ShortDescription_En": safe_get(description, 'ProductDescription'),
            "Description_En": safe_get(description, 'DetailedDescription'),
            "CountryOfOrigin": "",  # Not available in API response
            "ExpirationDate": "",  # Not available in API response
            "RoHSCompliant": safe_get(classifications, 'RohsStatus'),
            "BasePrice": get_base_price(variations),
            "BulkPrices": format_bulk_prices(variations),
            "StockQuantity": product.get('QuantityAvailable', 0),
            "LeadTimeInDays": f"{product.get('ManufacturerLeadWeeks', '')} Weeks" if product.get('ManufacturerLeadWeeks') else "",
            "Manufacturer_Standard_Package": variations[0].get('StandardPackage', '') if variations else '',
            "PackagingType": variations[0].get('PackageType', {}).get('Name', '') if variations else '',
            "Warnings": "",  # Not available in API response
            "Photos": format_photos(product.get('PhotoUrl')),
            "Photos360": "",  # Not available in API response
            "Datasheets": format_datasheets(product.get('DatasheetUrl')),
            "Environmental_Information": "",  # Not available in API response
            "Featured_Product": "",  # Not available in API response
            "MSDS_Material_Safety_Datasheet": "",  # Not available in API response
            "Product_Brief": "",  # Not available in API response
            "Category": main_cat,
            "Subcategory": sub_cat,
            "Sub-Subcategory": sub_sub_cat,
            "Sub-sub-subcategory": sub_sub_sub_cat,
            "Sub-sub-sub-subcategory": sub_sub_sub_sub_cat,
            "Moisture_Sensitivity_Level_(MSL)": safe_get(classifications, 'MoistureSensitivityLevel'),
            "REACH_Status": safe_get(classifications, 'ReachStatus'),
            "ECCN": safe_get(classifications, 'ExportControlClassNumber'),
            "HTSUS": safe_get(classifications, 'HtsusCode'),
            "Other_Names": format_other_names(product.get('OtherNames')),
            "Alternate_Color": "",  # Not available in API response
            "Alternate_Length": "",  # Not available in API response
            "Type": get_parameter_value(parameters, 'Type'),
            "Part_Status": safe_get(product.get('ProductStatus', {}), 'Status'),
            "Color": get_parameter_value(parameters, 'Color'),
            "Width": get_parameter_value(parameters, 'Width'),
            "Length": get_parameter_value(parameters, 'Length'),
            "Shelf_Life": get_parameter_value(parameters, 'Shelf Life'),
            "Shelf_Life_Start": "",  # Not available in API response
            "Storage/Refrigeration_Temperature": get_parameter_value(parameters, 'Storage/Refrigeration Temperature'),
            "Features": get_parameter_value(parameters, 'Features'),
            "Base_Product_Number": safe_get(product.get('BaseProductNumber', {}), 'Name'),
            "Material": get_parameter_value(parameters, 'Material'),
            "Shrinkage_Ratio": get_parameter_value(parameters, 'Shrinkage Ratio'),
            "Inner_Diameter_-_Supplied": get_parameter_value(parameters, 'Inner Diameter - Supplied'),
            "Inner_Diameter_-_Recovered": get_parameter_value(parameters, 'Inner Diameter - Recovered'),
            "Recovered_Wall_Thickness": get_parameter_value(parameters, 'Recovered Wall Thickness'),
            "Operating_Temperature": get_parameter_value(parameters, 'Operating Temperature'),
            "Shrink_Temperature": get_parameter_value(parameters, 'Shrink Temperature'),
            "Link": product.get('ProductUrl', '')
        }
        
        return mapped_product

    def process_and_store_product_details(self, product_number, manufacturer_id=None):
        """
        Fetch product details and store them in formatted JSON files.
        
        Args:
            product_number (str): The product number to fetch details for
            manufacturer_id (int, optional): Manufacturer ID for exact matching
            
        Returns:
            dict: Mapped product data or empty dict if failed
        """
        # Get product details from API
        api_response = self.get_product_details(product_number, manufacturer_id)
        
        if not api_response:
            logger.error(f"Failed to fetch product details for {product_number}")
            return {}
        
        # Map the product details
        try:
            mapped_product = self.map_product_details_to_structure(api_response)
            if not mapped_product:
                logger.error(f"Failed to map product details for {product_number}")
                return {}
        except Exception as e:
            logger.error(f"Error mapping product {product_number}: {e}")
            return {}
        
        # Store the results
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        
        # Create structured data
        result_data = {
            "metadata": {
                "product_number": product_number,
                "manufacturer_id": manufacturer_id,
                "timestamp": timestamp,
                "api_endpoint": "ProductDetails"
            },
            "mapped_product": mapped_product,
            "raw_response": api_response
        }
        
        # Define file paths
        mapped_file_path = f"{self.base_dir}/product_details_mapped.json"
        raw_file_path = f"{self.base_dir}/product_details_raw.json"
        
        try:
            # Store mapped product details
            existing_mapped_data = []
            if os.path.exists(mapped_file_path):
                with open(mapped_file_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_mapped_data = json.load(f)
                        if not isinstance(existing_mapped_data, list):
                            existing_mapped_data = [existing_mapped_data]
                    except json.JSONDecodeError:
                        logger.warning("Existing mapped JSON file is corrupted, starting fresh")
                        existing_mapped_data = []
            
            existing_mapped_data.append(result_data)
            
            with open(mapped_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_mapped_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully stored mapped product details for {product_number} to {mapped_file_path}")
            
            # Store raw response
            existing_raw_data = []
            if os.path.exists(raw_file_path):
                with open(raw_file_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_raw_data = json.load(f)
                        if not isinstance(existing_raw_data, list):
                            existing_raw_data = [existing_raw_data]
                    except json.JSONDecodeError:
                        logger.warning("Existing raw JSON file is corrupted, starting fresh")
                        existing_raw_data = []
            
            existing_raw_data.append({
                "metadata": {
                    "product_number": product_number,
                    "manufacturer_id": manufacturer_id,
                    "timestamp": timestamp
                },
                "raw_response": api_response
            })
            
            with open(raw_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_raw_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully stored raw product details for {product_number} to {raw_file_path}")
            
            return mapped_product
            
        except Exception as e:
            logger.error(f"Error storing product details for {product_number}: {e}")
            return {}

    def bulk_get_product_details(self, product_numbers, manufacturer_id=None):
        """
        Fetch product details for multiple product numbers.
        
        Args:
            product_numbers (list): List of product numbers to fetch
            manufacturer_id (int, optional): Manufacturer ID for exact matching
            
        Returns:
            list: List of mapped product data
        """
        results = []
        
        for product_number in product_numbers:
            logger.info(f"Processing product: {product_number}")
            mapped_product = self.process_and_store_product_details(product_number, manufacturer_id)
            
            if mapped_product:
                results.append(mapped_product)
                logger.info(f"Successfully processed: {product_number}")
            else:
                logger.error(f"Failed to process: {product_number}")
            
            # Add delay between requests to be respectful to the API
            time.sleep(1)
        
        logger.info(f"Bulk processing completed. Successfully processed {len(results)} out of {len(product_numbers)} products.")
        return results


if __name__ == '__main__':
    # Example usage
    api = ProductDetailsAPI()
    
    # Try with DigiKey part numbers (these work better with ProductDetails API)
    digikey_part_numbers = [
        "FP034K-200-ND",  # DigiKey part number for FP-301 3/4" BL 200'
        "19-FP-3013/4\"BL200'-DS-ND"  # Alternative DigiKey part number
    ]
    
    # Try with manufacturer part number first
    print("Trying with manufacturer part number...")
    manufacturer_part = "FP-301 3/4\" BL 200'"
    result = api.process_and_store_product_details(manufacturer_part, manufacturer_id=19)
    
    if result:
        print(f"✅ Successfully fetched details for manufacturer part: {manufacturer_part}")
        print(f"Product Name: {result.get('Product_Name_En', 'N/A')}")
        print(f"Base Price: {result.get('BasePrice', 'N/A')}")
        print(f"Stock Quantity: {result.get('StockQuantity', 'N/A')}")
    else:
        print(f"❌ Failed to fetch details for manufacturer part: {manufacturer_part}")
        print("Trying with DigiKey part numbers...")
        
        # Try with DigiKey part numbers
        for dk_part in digikey_part_numbers:
            print(f"\nTrying DigiKey part: {dk_part}")
            result = api.process_and_store_product_details(dk_part)
            
            if result:
                print(f"✅ Successfully fetched details for DigiKey part: {dk_part}")
                print(f"Product Name: {result.get('Product_Name_En', 'N/A')}")
                print(f"Manufacturer Part: {result.get('ManufacturerPartNumber', 'N/A')}")
                print(f"Base Price: {result.get('BasePrice', 'N/A')}")
                print(f"Stock Quantity: {result.get('StockQuantity', 'N/A')}")
                break
            else:
                print(f"❌ Failed to fetch details for DigiKey part: {dk_part}")
        else:
            print("❌ All attempts failed. The product might not exist or API might have issues.")
