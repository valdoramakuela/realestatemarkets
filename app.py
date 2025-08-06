from flask import Flask, render_template, request, jsonify
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import base64
import concurrent.futures


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
    """Fetch and parse HouseCanary market data for a given ZIP code"""

    endpoints = {
        "details": "/zip/details",
        "rental": "/zip/hcri",
        "grade": "/zip/market_grade"
    }

    market_data = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_key = {
            executor.submit(make_api_request, endpoint, zipcode): key
            for key, endpoint in endpoints.items()
        }

        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            response = future.result()
            endpoint_key = endpoints[key].lstrip('/')  # ✅ Fixed here

            if response and isinstance(response, list):
                response_item = response[0]

                if endpoint_key in response_item:
                    data_block = response_item[endpoint_key]
                    if data_block.get("api_code") == 0:
                        result = data_block.get("result")

                        # Drill down based on endpoint type
                        if key == "details":
                            market_data["single_family"] = result.get("single_family", {})
                            market_data["multi_family"] = result.get("multi_family", {})
                        elif key == "rental":
                            market_data["rental_yield"] = {
                                "average": result.get("gross_yield_average"),
                                "median": result.get("gross_yield_median"),
                                "count": result.get("gross_yield_count"),
                            }
                        elif key == "grade":
                            market_data["market_grade"] = result.get("market_grade")
                    else:
                        print(f"[{key}] API error: {data_block.get('api_code_description')}")
                else:
                    print(f"[{key}] Missing key '{endpoint_key}' in response")
            else:
                print(f"[{key}] Invalid or empty response")

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














