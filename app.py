from flask import Flask, render_template, request, jsonify
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import base64
from datetime import datetime, timedelta
import re

app = Flask(__name__)

USERNAME = 'dhenry@nomadicrealestate.com'
PASSWORD = 'qasnex-4joSxu-qigbet'

def format_address_to_slug(address):
    """Convert address to API slug format"""
    # Remove extra spaces and normalize
    address = re.sub(r'\s+', ' ', address.strip())
    
    # Replace spaces with hyphens
    slug = address.replace(' ', '-')
    
    # Remove special characters except hyphens and alphanumeric
    slug = re.sub(r'[^a-zA-Z0-9\-]', '', slug)
    
    return slug

def make_api_request(endpoint, zipcode=None, slug=None, start_date=None, end_date=None):
    """Make API request using Basic Auth (username:password)"""
    try:
        url = f"https://api.housecanary.com/v2{endpoint}"
        params = {}
        
        if zipcode:
            params['zipcode'] = zipcode
        if slug:
            params['slug'] = slug
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date

        # Encode username:password in Base64
        auth_string = f"{USERNAME}:{PASSWORD}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {encoded_auth}'
        }

        print(f"Requesting: {url} with params: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"API request failed: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Error making API request: {str(e)}")
        return None

def fetch_market_data(zipcode):
    """Fetch market data from multiple endpoints concurrently"""
    market_data = {
        'details': None,
        'rental': None,
        'grade': None
    }
    
    # Define API endpoints
    endpoints = {
        'details': '/zip/details',
        'rental': '/zip/hcri',
        'grade': '/zip/market_grade'
    }
    
    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            key: executor.submit(make_api_request, endpoint, zipcode=zipcode)
            for key, endpoint in endpoints.items()
        }
        
        for key, future in futures.items():
            try:
                response = future.result()
                print(f"Processing {key} response: {response}")
                
                if response and isinstance(response, list) and len(response) > 0:
                    # Response is an array, get the first item
                    data_item = response[0]
                    endpoint_key = f"zip{endpoints[key].replace('zip', '')}"
                    
                    if endpoint_key in data_item:
                        api_response = data_item[endpoint_key]
                        if api_response.get('api_code') == 0:
                            market_data[key] = api_response.get('result')
                            print(f"Successfully extracted {key} data: {market_data[key]}")
                        else:
                            print(f"API error for {key}: {api_response.get('api_code_description')}")
                            market_data[key] = None
                    else:
                        print(f"Key {endpoint_key} not found in response for {key}")
                        market_data[key] = None
                else:
                    print(f"Invalid response format for {key}: {response}")
                    market_data[key] = None
            except Exception as e:
                print(f"Error getting {key} data: {str(e)}")
                market_data[key] = None
    
    print(f"Final market_data: {market_data}")
    return market_data

def fetch_address_market_data(address, start_date=None, end_date=None):
    """Fetch market data from address-based endpoints"""
    slug = format_address_to_slug(address)
    print(f"Formatted address '{address}' to slug: '{slug}'")
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
    
    # For forecast, we want future dates
    forecast_start = datetime.now().strftime('%Y-%m-%d')
    forecast_end = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    
    market_data = {
        'rpi_forecast': None,
        'rpi_historical': None,
        'rpi_ts_forecast': None,
        'rpi_ts_historical': None
    }
    
    # Define API endpoints for address-based searches
    endpoints = {
        'rpi_forecast': '/property/zip_rpi_forecast',
        'rpi_historical': '/property/zip_rpi_historical',
        'rpi_ts_forecast': '/property/zip_rpi_ts_forecast',
        'rpi_ts_historical': '/property/zip_rpi_ts_historical'
    }
    
    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        
        for key, endpoint in endpoints.items():
            if key == 'rpi_ts_forecast':
                # Time series forecast needs future date range
                futures[key] = executor.submit(
                    make_api_request, endpoint, slug=slug, 
                    start_date=forecast_start, end_date=forecast_end
                )
            elif key == 'rpi_ts_historical':
                # Time series historical uses provided date range
                futures[key] = executor.submit(
                    make_api_request, endpoint, slug=slug, 
                    start_date=start_date, end_date=end_date
                )
            else:
                # Regular endpoints don't need date range
                futures[key] = executor.submit(make_api_request, endpoint, slug=slug)
        
        for key, future in futures.items():
            try:
                response = future.result()
                print(f"Processing {key} response: {response}")
                
                if response and isinstance(response, list) and len(response) > 0:
                    # Response is an array, get the first item
                    data_item = response[0]
                    # Use the correct single slash format for property endpoints
                    endpoint_key = endpoints[key].replace('/property/', 'property/')
                    
                    if endpoint_key in data_item:
                        api_response = data_item[endpoint_key]
                        if api_response.get('api_code') == 0:
                            market_data[key] = api_response
                            print(f"Successfully extracted {key} data")
                        else:
                            print(f"API error for {key}: {api_response.get('api_code_description')}")
                            market_data[key] = None
                    else:
                        print(f"Key {endpoint_key} not found in response for {key}")
                        market_data[key] = None
                else:
                    print(f"Invalid response format for {key}: {response}")
                    market_data[key] = None
            except Exception as e:
                print(f"Error getting {key} data: {str(e)}")
                market_data[key] = None
    
    print(f"Final address market_data: {market_data}")
    return market_data

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/api/market-data')
def get_market_data():
    zipcode = request.args.get('zipcode')
    if not zipcode:
        return jsonify({'error': 'ZIP code is required'}), 400
    
    try:
        # API endpoints
        details_url = f"https://api.housecanary.com/v2/zip/details?zipcode={zipcode}"
        rental_url = f"https://api.housecanary.com/v2/zip/hcri?zipcode={zipcode}"
        grade_url = f"https://api.housecanary.com/v2/zip/market_grade?zipcode={zipcode}"
        
        print(f"Requesting: {details_url}")
        print(f"Requesting: {rental_url}")
        print(f"Requesting: {grade_url}")
        
        # Make API calls with authentication
        auth_string = f"{USERNAME}:{PASSWORD}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {encoded_auth}'
        }
        
        details_response = requests.get(details_url, headers=headers)
        rental_response = requests.get(rental_url, headers=headers)
        grade_response = requests.get(grade_url, headers=headers)
        
        # Parse responses
        details_data = details_response.json() if details_response.status_code == 200 else []
        rental_data = rental_response.json() if rental_response.status_code == 200 else []
        grade_data = grade_response.json() if grade_response.status_code == 200 else []
        
        print(f"Processing details response: {details_data}")
        print(f"Processing rental response: {rental_data}")
        print(f"Processing grade response: {grade_data}")
        
        # Extract data with correct keys (single slash, not double slash)
        market_data = {
            'details': None,
            'rental': None,
            'grade': None
        }
        
        # Process details data
        if details_data and isinstance(details_data, list) and len(details_data) > 0:
            details_item = details_data[0]
            if 'zip/details' in details_item:
                market_data['details'] = details_item['zip/details']
                print(f"Found details data: {market_data['details']}")
            else:
                print(f"Key zip/details not found in response for details")
        
        # Process rental data
        if rental_data and isinstance(rental_data, list) and len(rental_data) > 0:
            rental_item = rental_data[0]
            if 'zip/hcri' in rental_item:
                market_data['rental'] = rental_item['zip/hcri']
                print(f"Found rental data: {market_data['rental']}")
            else:
                print(f"Key zip/hcri not found in response for rental")
        
        # Process grade data
        if grade_data and isinstance(grade_data, list) and len(grade_data) > 0:
            grade_item = grade_data[0]
            if 'zip/market_grade' in grade_item:
                market_data['grade'] = grade_item['zip/market_grade']
                print(f"Found grade data: {market_data['grade']}")
            else:
                print(f"Key zip/market_grade not found in response for grade")
        
        print(f"Final market_data: {market_data}")
        
        return jsonify(market_data)
        
    except Exception as e:
        print(f"Error fetching market data: {str(e)}")
        return jsonify({'error': 'Failed to fetch market data'}), 500

@app.route('/api/market-data-by-address')
def get_market_data_by_address():
    """Get market data by address using the new RPI endpoints"""
    address = request.args.get('address')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    period = request.args.get('period')  # New parameter for predefined periods
    
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    # Handle predefined periods
    if period:
        end_date = datetime.now().strftime('%Y-%m-%d')
        if period == '1Y':
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        elif period == '5Y':
            start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
        elif period == '10Y':
            start_date = (datetime.now() - timedelta(days=10*365)).strftime('%Y-%m-%d')
        elif period == 'All':
            start_date = (datetime.now() - timedelta(days=20*365)).strftime('%Y-%m-%d')  # 20 years max
    
    try:
        market_data = fetch_address_market_data(address, start_date, end_date)
        return jsonify(market_data)
        
    except Exception as e:
        print(f"Error fetching address market data: {str(e)}")
        return jsonify({'error': 'Failed to fetch market data'}), 500

@app.route('/api/rpi-forecast')
def get_rpi_forecast():
    """Get RPI forecast for a specific address"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    try:
        slug = format_address_to_slug(address)
        response = make_api_request('/property/zip_rpi_forecast', slug=slug)
        return jsonify(response)
    except Exception as e:
        print(f"Error fetching RPI forecast: {str(e)}")
        return jsonify({'error': 'Failed to fetch RPI forecast'}), 500

@app.route('/api/rpi-historical')
def get_rpi_historical():
    """Get RPI historical data for a specific address"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    try:
        slug = format_address_to_slug(address)
        response = make_api_request('/property/zip_rpi_historical', slug=slug)
        return jsonify(response)
    except Exception as e:
        print(f"Error fetching RPI historical: {str(e)}")
        return jsonify({'error': 'Failed to fetch RPI historical data'}), 500

@app.route('/api/rpi-ts-forecast')
def get_rpi_ts_forecast():
    """Get RPI time series forecast for a specific address"""
    address = request.args.get('address')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    try:
        slug = format_address_to_slug(address)
        response = make_api_request('/property/zip_rpi_ts_forecast', slug=slug, 
                                  start_date=start_date, end_date=end_date)
        return jsonify(response)
    except Exception as e:
        print(f"Error fetching RPI TS forecast: {str(e)}")
        return jsonify({'error': 'Failed to fetch RPI time series forecast'}), 500

@app.route('/api/rpi-ts-historical')
def get_rpi_ts_historical():
    """Get RPI time series historical data for a specific address"""
    address = request.args.get('address')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
    
    try:
        slug = format_address_to_slug(address)
        response = make_api_request('/property/zip_rpi_ts_historical', slug=slug, 
                                  start_date=start_date, end_date=end_date)
        return jsonify(response)
    except Exception as e:
        print(f"Error fetching RPI TS historical: {str(e)}")
        return jsonify({'error': 'Failed to fetch RPI time series historical data'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
