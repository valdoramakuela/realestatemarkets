from flask import Flask, render_template, request, jsonify
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import base64

app = Flask(__name__)

# API configuration
API_CONFIG = {
    'base_url': 'https://api.housecanary.com/v2',
    'api_key': '2835Q6GDS5P3ARNRLWNN',  # Your API key
    'api_secret': 'YOUR_API_SECRET',    # You need to add your API secret
    'timeout': 10
}

# API configuration - Update these with your actual credentials
API_CONFIG = {
    'base_url': 'https://api.housecanary.com/v2',
    'api_key': '2835Q6GDS5P3ARNRLWNN',
    'api_secret': '',  # Add your API secret here
    'timeout': 10
}

def make_api_request(endpoint, zipcode):
    """Make API request to HouseCanary API with multiple auth methods"""
    try:
        url = f"{API_CONFIG['base_url']}{endpoint}"
        params = {'zipcode': zipcode}
        
        print(f"Making request to: {url} with zipcode: {zipcode}")
        
        # Method 1: Try Basic Auth with key:secret
        if API_CONFIG['api_secret']:
            auth = (API_CONFIG['api_key'], API_CONFIG['api_secret'])
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, auth=auth, headers=headers, params=params, timeout=API_CONFIG['timeout'])
            if response.status_code == 200:
                return response.json()
            print(f"Basic auth failed: {response.status_code} - {response.text}")
        
        # Method 2: Try with Authorization header (your current method)
        auth_string = base64.b64encode(f"{API_CONFIG['api_key']}:".encode()).decode()
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=API_CONFIG['timeout'])
        if response.status_code == 200:
            return response.json()
        print(f"Header auth failed: {response.status_code} - {response.text}")
        
        # Method 3: Try with just API key as Authorization
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {API_CONFIG["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=API_CONFIG['timeout'])
        if response.status_code == 200:
            return response.json()
        print(f"Bearer auth failed: {response.status_code} - {response.text}")
        
        # Method 4: Try with API key in params
        params['api_key'] = API_CONFIG['api_key']
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=API_CONFIG['timeout'])
        if response.status_code == 200:
            return response.json()
        print(f"Param auth failed: {response.status_code} - {response.text}")
        
        return None
        
    except Exception as e:
        print(f"Error making API request for {endpoint}: {str(e)}")
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
            key: executor.submit(make_api_request, endpoint, zipcode)
            for key, endpoint in endpoints.items()
        }
        
        for key, future in futures.items():
            try:
                response = future.result()
                if response and f"zip{endpoints[key].replace('zip', '')}" in response:
                    api_response = response[f"zip{endpoints[key].replace('zip', '')}"]
                    if api_response.get('api_code') == 0:
                        market_data[key] = api_response.get('result')
                    else:
                        print(f"API error for {key}: {api_response.get('api_code_description')}")
                        market_data[key] = None
                else:
                    print(f"Invalid response format for {key}: {response}")
                    market_data[key] = None
            except Exception as e:
                print(f"Error getting {key} data: {str(e)}")
                market_data[key] = None
    
    return market_data

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/api/market-data')
def api_market_data():
    """API endpoint to fetch market data"""
    zipcode = request.args.get('zipcode', '').strip()
    
    if not zipcode:
        return jsonify({'error': 'ZIP code is required'}), 400
    
    if not zipcode.isdigit() or len(zipcode) != 5:
        return jsonify({'error': 'Please enter a valid 5-digit ZIP code'}), 400
    
    try:
        market_data = fetch_market_data(zipcode)
        return jsonify({
            'success': True,
            'data': market_data,
            'zipcode': zipcode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching market data: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
