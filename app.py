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
        headers = {'Authorization': f'Bearer {HOUSECANARY_API_KEY}'}
        
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
            if 'zip/details' in details_item:  # Changed from 'zip//details' to 'zip/details'
                market_data['details'] = details_item['zip/details']
                print(f"Found details data: {market_data['details']}")
            else:
                print(f"Key zip/details not found in response for details")
        
        # Process rental data
        if rental_data and isinstance(rental_data, list) and len(rental_data) > 0:
            rental_item = rental_data[0]
            if 'zip/hcri' in rental_item:  # Changed from 'zip//hcri' to 'zip/hcri'
                market_data['rental'] = rental_item['zip/hcri']
                print(f"Found rental data: {market_data['rental']}")
            else:
                print(f"Key zip/hcri not found in response for rental")
        
        # Process grade data
        if grade_data and isinstance(grade_data, list) and len(grade_data) > 0:
            grade_item = grade_data[0]
            if 'zip/market_grade' in grade_item:  # Changed from 'zip//market_grade' to 'zip/market_grade'
                market_data['grade'] = grade_item['zip/market_grade']
                print(f"Found grade data: {market_data['grade']}")
            else:
                print(f"Key zip/market_grade not found in response for grade")
        
        print(f"Final market_data: {market_data}")
        
        return jsonify(market_data)
        
    except Exception as e:
        print(f"Error fetching market data: {str(e)}")
        return jsonify({'error': 'Failed to fetch market data'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

