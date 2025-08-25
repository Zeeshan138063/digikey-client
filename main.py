import json
import time
from pathlib import Path
import digikey
import os
import logging
import requests
from digikey.v3.productinformation import KeywordSearchRequest
from decouple import config



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("product_search.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)



class DgkeySdk:

    def __init__(self):
        # Build paths inside the project like this: BASE_DIR / 'subdir'.
        self.base_dir = Path(__file__).resolve().parent

        self.client_id = config('DIGIKEY_CLIENT_ID')
        self.client_secret = config('DIGIKEY_CLIENT_SECRET')
        os.environ['DIGIKEY_CLIENT_ID'] = self.client_id
        os.environ['DIGIKEY_CLIENT_SECRET'] = self.client_secret
        os.environ['DIGIKEY_STORAGE_PATH'] = f"{self.base_dir}"  # '/home/zeeshan/PycharmProjects/dkey/prod'
        os.environ['DIGIKEY_CLIENT_SANDBOX'] = config('DIGIKEY_CLIENT_SANDBOX', 'False')

    def get_access_token(self):
        """Reads access token from a JSON file.

        Args:
          file_path: The path to the JSON file (optional, defaults to a specific path).

        Returns:
          The access token as a string.
        """
        file_path = f"{self.base_dir}/token_storage.json"
        if not os.path.exists(file_path):
            self.token_update()

        with open(file_path, 'r') as f:
            data = json.load(f)
            return data['access_token']

    def token_update(self):
        # Query product number
        # dkpn = '296-6501-1-ND'
        # part = digi_key.product_details(dkpn)

        # for category in categories:
        # Search for parts
        search_request = KeywordSearchRequest(keywords="Batteries Rechargeable (Secondary)", record_count=10,
                                              record_start_position=0,
                                              filters={"ManufacturerFilter.id": 2946}
                                              )
        result = digikey.keyword_search(body=search_request)
        time.sleep(5)

    def _search_product(self, keyword, limit=50, offset=0, manufactured_id=2946, max_retries=10, backoff_factor=2, user_id=None):
        """
        Performs a product search on DigiKey API with retry logic for non-200 responses.

        Args:
            keyword (str): The search keyword.
            limit (int): The maximum number of results to return.
            offset (int): The offset for pagination.
            manufactured_id (int): The manufacturer ID to filter by.
            max_retries (int): The maximum number of retry attempts.
            backoff_factor (int): The backoff factor for exponential backoff.

        Returns:
            dict: The parsed API response as a dictionary.
        """

        url = "https://api.digikey.com/products/v4/search/keyword"
        access_token = self.get_access_token()
        payload = {
            "Keywords": keyword,
            "Limit": limit,
            "Offset": offset,
            "FilterOptionsRequest": {
                "ManufacturerFilter": [
                    {
                        "Id": manufactured_id
                    }
                ]
            },
            "SortOptions": {
                "Field": "Supplier",
                "SortOrder": "Descending"
            }
        }
        jsonify_payload = json.dumps(payload)
        headers = {
            'X-DIGIKEY-Client-Id': self.client_id,
            # 'X-DIGIKEY-Locale-Site': 'en',
            # 'X-DIGIKEY-Locale-Language': 'US',
            # 'X-DIGIKEY-Locale-Currency': 'USD',
            'X-DIGIKEY-Locale-Site': 'en',
            'X-DIGIKEY-Locale-Language': 'CA',
            'X-DIGIKEY-Locale-Currency': 'CAD',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }

        retries = 0
        while retries < max_retries:
            try:
                logger.info(f"Sending request with payload: {jsonify_payload} and headers: {headers}")
                response = requests.post(url, headers=headers, data=jsonify_payload)
                response.raise_for_status()
                logger.info(f"Request successful: {response.status_code}")
                payload['url']=url
                payload['headers']=headers
                # ScrapingLog.log_scraping_request(user_id=user_id, payload= json.dumps(payload),headers=headers,
                #                                  response=response.json())
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed on attempt {retries + 1}/{max_retries} with error: {e}")
                retries += 1
                backoff  = backoff_factor ** retries
                logger.info(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
                logger.info("Updating token...")
                self.token_update()

        logger.error("All retry attempts failed. Returning empty dictionary.")
        return {}  # Return empty dict if all retries fail

    def search_products(self, categories,manufactured_id, user_id=None):

        for category in categories:
            offset = 0  # category.get('offset', 0)
            limit = 50  # category.get('limit', 50)
            while True:
                response = self._search_product(category, limit=limit, offset=offset, manufactured_id=manufactured_id, user_id=user_id)
                if not response:
                    break
                product_count = response.get('ProductsCount', 0)
                logger.info(f"scrapped {product_count} products...")
                products = response.get('Products', [])
                logger.info(f"storing {len(products)} products...")
                self.process_products(products, offset, limit)
                offset += limit
                if offset >= product_count:
                    break
    def process_products(self, products, offset, limit):
        """
        Process and store products data to JSON file in formatted way.
        
        Args:
            products (list): List of product data from API response
            offset (int): Current offset for pagination
            limit (int): Limit of products per request
        """
        url = f"https://api.digikey.com/products/v4/search/keyword?offset={offset}&limit={limit}"
        
        # Create a structured data object to store
        batch_data = {
            "metadata": {
                "url": url,
                "offset": offset,
                "limit": limit,
                "product_count": len(products),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            },
            "products": products
        }
        
        # Define the JSON file path
        json_file_path = f"{self.base_dir}/api_responses.json"
        
        try:
            # Load existing data if file exists
            existing_data = []
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                        if not isinstance(existing_data, list):
                            existing_data = [existing_data]  # Convert to list if it's a single object
                    except json.JSONDecodeError:
                        logger.warning("Existing JSON file is corrupted, starting fresh")
                        existing_data = []
            
            # Append new batch data
            existing_data.append(batch_data)
            
            # Write formatted JSON to file
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully stored {len(products)} products to {json_file_path}")
            
            # Also print product info for debugging (optional)
            for i, product in enumerate(products):
                logger.info(f"Product {offset + i + 1}: {product.get('ManufacturerPartNumber', 'N/A')} - {product.get('ProductDescription', 'N/A')}")
                
        except Exception as e:
            logger.error(f"Error storing products to JSON file: {e}")
            # Fallback to printing if file storage fails
            for product in products:
                print(product)



if __name__ == '__main__':
    dg = DgkeySdk()
    dg.search_products(categories=("Amplifiers",),manufactured_id=2946,user_id=None)