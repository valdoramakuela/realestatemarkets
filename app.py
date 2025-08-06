from flask import Flask, render_template, request, jsonify
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import base64

app = Flask(__name__)

USERNAME = 'dhenry@nomadicrealestate.com'
PASSWORD = 'qasnex-4joSxu-qigbet'

def make_api_request(endpoint, zipcode):
    """Make API request using Basic Auth (username:password)"""
    try:
        url = f"https://api.housecanary.com/v2{endpoint}"
        params = {'zipcode': zipcode}

        # Encode username:password in Base64
        auth_string = f"{USERNAME}:{PASSWORD}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {encoded_auth}'
        }

        print(f"Requesting: {url}?zipcode={zipcode}")
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
            key: executor.submit(make_api_request, endpoint, zipcode)
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
