# DigiKey API Client

A comprehensive Python client for interacting with DigiKey's Product Information API v4. This client provides structured data extraction and mapping from DigiKey's product database with support for multiple API endpoints.

## 🚀 Features

- **Keyword Search API**: Search for products using keywords with advanced filtering
- **Product Details API**: Get detailed information for specific product numbers
- **Structured Data Mapping**: Automatically maps API responses to standardized format
- **Dual Storage System**: Saves both mapped and raw API responses
- **Error Handling**: Robust retry logic with exponential backoff
- **Token Management**: Automatic OAuth token handling and refresh
- **Pagination Support**: Handles large result sets with automatic pagination

## 📋 Requirements

- Python 3.7+
- DigiKey API credentials (Client ID and Client Secret)
- Required Python packages (see installation)

## 🛠️ Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd digikey-new-client
```

2. Install required packages:
```bash
pip install digikey-api requests python-decouple
```

3. Create a `.env` file in the project root:
```env
DIGIKEY_CLIENT_ID=your_client_id_here
DIGIKEY_CLIENT_SECRET=your_client_secret_here
DIGIKEY_CLIENT_SANDBOX=False
```

## 🔧 Configuration

### Getting DigiKey API Credentials

1. Visit [DigiKey Developer Portal](https://developer.digikey.com/)
2. Create an account and register your application
3. Obtain your Client ID and Client Secret
4. Add them to your `.env` file

## 📚 API Endpoints Supported

### 1. KeywordSearch
**Endpoint**: `https://api.digikey.com/products/v4/search/keyword`  
**Documentation**: [@DigiKey KeywordSearch](https://developer.digikey.com/products/product-information-v4/productsearch/keywordsearch)

Search for products using keywords with advanced filtering options.

### 2. ProductDetails
**Endpoint**: `https://api.digikey.com/products/v4/search/{productNumber}/productdetails`  
**Documentation**: [@DigiKey ProductDetails](https://developer.digikey.com/products/product-information-v4/productsearch/productdetails)

Get detailed information for specific manufacturer or DigiKey part numbers.

### 3. Categories
**Endpoint**: `https://api.digikey.com/products/v4/search/categories`  
**Documentation**: [@DigiKey Categories](https://developer.digikey.com/products/product-information-v4/productsearch/categories)

Retrieve all Product Categories. CategoryId can be used in KeywordSearch to restrict the search to a given Category.

### 4. Manufacturers
**Endpoint**: `https://api.digikey.com/products/v4/search/manufacturers`  
**Documentation**: [@DigiKey Manufacturers](https://developer.digikey.com/products/product-information-v4/productsearch/manufacturers)

Retrieve all Product Manufacturers. ManufacturerId can be used in KeywordSearch to restrict the search to a given Manufacturer.

### 5. AlternatePackaging
**Endpoint**: `https://api.digikey.com/products/v4/search/{productNumber}/alternatepackaging`  
**Documentation**: [@DigiKey AlternatePackaging](https://developer.digikey.com/products/product-information-v4/productsearch/alternatepackaging)

Find alternate packaging options for products.

### 6. Media
**Endpoint**: `https://api.digikey.com/products/v4/search/{productNumber}/media`  
**Documentation**: [@DigiKey Media](https://developer.digikey.com/products/product-information-v4/productsearch/media)

Retrieve media assets (photos, datasheets, videos) for products.

## 🎯 Usage Examples

### Keyword Search API

```python
from main import DgkeySdk

# Initialize the SDK
dg = DgkeySdk()

# Search for products
categories = ("Heat Shrink Tubing",)
manufacturer_id = 19  # 3M
dg.search_products(categories=categories, manufactured_id=manufacturer_id)
```

### Product Details API

```python
from product_details_api import ProductDetailsAPI

# Initialize the API client
api = ProductDetailsAPI()

# Get details for a specific product (works best with DigiKey part numbers)
result = api.process_and_store_product_details("FP034K-200-ND")

# Bulk processing
product_numbers = ["FP034K-200-ND", "19-FP-3013/4\"BL200'-DS-ND"]
results = api.bulk_get_product_details(product_numbers)
```

### Categories API (Planned)

```python
# Get all available categories
categories = api.get_categories()

# Find specific category ID
for category in categories:
    if "Heat Shrink" in category['Name']:
        category_id = category['CategoryId']
        print(f"Heat Shrink Category ID: {category_id}")

# Use category ID in keyword search for more targeted results
dg.search_products(categories=("Heat Shrink Tubing",), category_id=483)
```

### Manufacturers API (Planned)

```python
# Get all manufacturers
manufacturers = api.get_manufacturers()

# Find specific manufacturer ID
for manufacturer in manufacturers:
    if manufacturer['Name'] == '3M':
        manufacturer_id = manufacturer['Id']
        print(f"3M Manufacturer ID: {manufacturer_id}")  # Should be 19

# Use manufacturer ID in searches
dg.search_products(categories=("Heat Shrink Tubing",), manufactured_id=19)
```

## 📊 Data Mapping

The client automatically maps DigiKey API responses to a standardized structure with 50+ fields including:

### Core Product Information
- `Product_Name_En`: Product title/name
- `ManufacturerPartNumber`: Manufacturer's part number
- `Manufacturer_Name`: Manufacturer name
- `Series`: Product series
- `Description_En`: Detailed product description

### Pricing & Availability
- `BasePrice`: First unit price from pricing table
- `BulkPrices`: Formatted pricing tiers (qty+-price;qty+-price)
- `StockQuantity`: Available inventory
- `LeadTimeInDays`: Lead time with "Weeks" suffix

### Technical Specifications
- `Type`: Product type
- `Material`: Construction material
- `Operating_Temperature`: Operating temperature range
- `Features`: Product features
- `Color`: Product color
- `Length`: Product length

### Heat Shrink Specific Fields
- `Shrinkage_Ratio`: Shrinkage ratio (e.g., "2 to 1")
- `Inner_Diameter_-_Supplied`: Supplied inner diameter
- `Inner_Diameter_-_Recovered`: Recovered inner diameter
- `Recovered_Wall_Thickness`: Wall thickness after shrinking
- `Shrink_Temperature`: Temperature for shrinking
- `Shelf_Life`: Product shelf life
- `Storage/Refrigeration_Temperature`: Storage temperature

### Compliance & Classification
- `RoHSCompliant`: RoHS compliance status
- `REACH_Status`: REACH compliance status
- `ECCN`: Export Control Classification Number
- `HTSUS`: Harmonized Tariff Schedule code
- `Moisture_Sensitivity_Level_(MSL)`: MSL rating

### Media & Documentation
- `Photos`: Product photos (pipe-separated URLs)
- `Datasheets`: Datasheet URLs
- `Link`: Product page URL

### Category Hierarchy
- `Category`: Main category
- `Subcategory`: First-level subcategory
- `Sub-Subcategory`: Second-level subcategory
- `Sub-sub-subcategory`: Third-level subcategory
- `Sub-sub-sub-subcategory`: Fourth-level subcategory

## 📁 Output Files

The client generates several JSON files:

### Keyword Search API
- `api_responses_mapped.json`: Products in standardized structure
- `api_responses_raw.json`: Original API responses

### Product Details API
- `product_details_mapped.json`: Detailed products in standardized structure
- `product_details_raw.json`: Original detailed API responses

### File Structure Example
```json
[
  {
    "metadata": {
      "url": "https://api.digikey.com/products/v4/search/keyword",
      "offset": 0,
      "limit": 50,
      "product_count": 50,
      "timestamp": "2024-01-15 10:30:45"
    },
    "products": [
      {
        "Product_Name_En": "HEATSHRINK FP301 3/4\" BLACK",
        "ManufacturerPartNumber": "FP-301 3/4\" BL 200'",
        "BasePrice": 0.92795,
        "BulkPrices": "200+-0.92795;400+-0.85348;600+-0.8382",
        "LeadTimeInDays": "4 Weeks",
        // ... 40+ more mapped fields
      }
    ]
  }
]
```

## 🔍 Key Features & Best Practices

### Smart Parameter Extraction
The mapping system intelligently extracts parameter values from DigiKey's parameter arrays:

```python
# Automatically finds and extracts:
"Shelf_Life": get_parameter_value(parameters, 'Shelf Life')
"Material": get_parameter_value(parameters, 'Material')
"Operating_Temperature": get_parameter_value(parameters, 'Operating Temperature')
```

### Pricing Structure
- `BasePrice`: First unit price from the StandardPricing table
- `BulkPrices`: All pricing tiers formatted as `quantity+-unitprice;quantity+-unitprice`

### Product Number Compatibility
- **Keyword Search**: Works with manufacturer part numbers and keywords
- **Product Details**: Works best with DigiKey part numbers (e.g., "FP034K-200-ND")
- Extract DigiKey part numbers from search results for use with ProductDetails API

### Error Handling
- Automatic retry with exponential backoff
- Graceful handling of missing fields
- Detailed logging for debugging
- Token refresh on authentication failures

## 🐛 Troubleshooting

### Common Issues

1. **404 Not Found Error**
   - Use DigiKey part numbers instead of manufacturer part numbers for ProductDetails API
   - Extract DigiKey part numbers from search results: `product['ProductVariations'][0]['DigiKeyProductNumber']`

2. **Authentication Errors**
   - Verify your `.env` file has correct credentials
   - Run the keyword search first to generate initial token
   - Check if your API credentials have proper permissions

3. **Empty Results**
   - Verify manufacturer ID is correct
   - Check if the category/keyword exists
   - Review API rate limits

### Logging
The client provides detailed logging. Check the `product_search.log` file for debugging information.

## 📝 API Implementation Status

### ✅ Implemented
- **KeywordSearch API**: Full implementation with mapping and storage
- **ProductDetails API**: Full implementation with mapping and storage

### 🚧 Planned Implementation
- **Categories API**: Retrieve all product categories for targeted searching
- **Manufacturers API**: Get all manufacturers for precise filtering
- **AlternatePackaging API**: Find alternate packaging options
- **Media API**: Retrieve product media assets

### 🔮 Future Enhancements
- **Batch Processing**: Enhanced bulk processing capabilities
- **CSV Export**: Export mapped data to CSV format
- **Database Integration**: Direct database storage options
- **Caching System**: API response caching for better performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- [DigiKey Developer Portal](https://developer.digikey.com/)
- [DigiKey API Documentation](https://developer.digikey.com/products)
- [Python DigiKey Package](https://pypi.org/project/digikey-api/)

## 📞 Support

For issues related to:
- **DigiKey API**: Contact DigiKey Developer Support
- **This Client**: Open an issue in this repository

---

**Note**: This client is not officially affiliated with DigiKey Corporation. It's a third-party implementation for educational and development purposes.
