import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from flask import Flask, redirect, request, jsonify
from google_auth_oauthlib.flow import Flow
import requests

app = Flask(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/business.manage"
]

REDIRECT_URI = "http://localhost:8000/auth/callback"

flow = Flow.from_client_secrets_file(
    "credentials.json",
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)


@app.route("/")
def login():

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account"
    )

    return redirect(auth_url)


@app.route("/auth/callback")
def callback():

    # FETCH TOKEN
    flow.fetch_token(
        authorization_response=request.url
    )

    credentials = flow.credentials

    access_token = credentials.token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # STEP 1 → FETCH BUSINESS ACCOUNTS
    accounts_res = requests.get(
        "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
        headers=headers
    )

    try:
        accounts_data = accounts_res.json()
    except Exception:
        return {
            "step": "accounts",
            "status_code": accounts_res.status_code,
            "response_text": accounts_res.text
        }

    accounts = accounts_data.get("accounts", [])

    if not accounts:
        return jsonify({
            "error": "No business accounts found",
            "accounts_response": accounts_data
        })

    # PICK FIRST ACCOUNT
    account_name = accounts[0]["name"]

    # STEP 2 → FETCH LOCATIONS
    locations_res = requests.get(
        f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations",
        headers=headers,
        params={
            "readMask": "name,title,storeCode"
        }
    )

    try:
        locations_data = locations_res.json()
    except Exception:
        return {
            "step": "locations",
            "status_code": locations_res.status_code,
            "response_text": locations_res.text
        }

    locations = locations_data.get("locations", [])

    if not locations:
        return jsonify({
            "error": "No locations found",
            "locations_response": locations_data
        })

    # PICK FIRST LOCATION
    location_name = locations[0]["name"]

    # location_name example:
    # locations/123456789

    location_id = location_name.split("/")[-1]

    # STEP 3 → FETCH REVIEWS
    reviews_url = (
        f"https://mybusiness.googleapis.com/v4/"
        f"{account_name}/locations/{location_id}/reviews"
    )

    reviews_res = requests.get(
        reviews_url,
        headers=headers
    )

    try:
        reviews_data = reviews_res.json()
    except Exception:
        return {
            "step": "reviews",
            "status_code": reviews_res.status_code,
            "response_text": reviews_res.text
        }

    return jsonify({
        "account_used": account_name,
        "location_used": location_name,
        "reviews_response": reviews_data
    })


if __name__ == "__main__":
    app.run(port=8000, debug=True)