from flask import Flask, render_template, request, jsonify
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import base64

app = Flask(__name__)

# Replace with your real HouseCanary credentials
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
    """Fetch relevant market data from multiple endpoints concurrently"""
    market_data = {}

    # Define API endpoints
    endpoints = {
        'details': '/zip/details',
        'rental': '/zip/hcri',
        'grade': '/zip/market_grade'
    }

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            key: executor.submit(make_api_request, endpoint, zipcode)
            for key, endpoint in endpoints.items()
        }

        for key, future in futures.items():
            try:
                response = future.result()

                if not response or not isinstance(response, dict):
                    print(f"[{key}] Invalid or empty response.")
                    continue

                # Convert endpoint path to key format in response
                response_key = endpoints[key].lstrip('/').replace('/', '/')

                if response_key not in response:
                    print(f"[{key}] Key '{response_key}' not in response.")
                    continue

                result_block = response[response_key]
                if result_block.get("api_code") != 0:
                    print(f"[{key}] API error: {result_block.get('api_code_description')}")
                    continue

                result = result_block.get("result", {})

                # Extract only required fields based on endpoint
                if key == 'details':
                    single_family = result.get("single_family", {})
                    market_data.update({
                        'listings_on_market': single_family.get("inventory_total"),
                        'price_median': single_family.get("price_median"),
                        'estimated_sales_total': single_family.get("estimated_sales_total"),
                        'months_of_inventory_median': single_family.get("months_of_inventory_median"),
                        'days_on_market_median': single_family.get("days_on_market_median")
                    })

                elif key == 'rental':
                    market_data['gross_yield_median'] = result.get("gross_yield_median")

                elif key == 'grade':
                    market_data['market_grade'] = result.get("market_grade")

            except Exception as e:
                print(f"Error fetching data for {key}: {str(e)}")

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









