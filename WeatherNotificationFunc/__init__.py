import datetime
import logging
import json 
import requests
import os
import azure.functions as func
import sharedcode.alert


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    #if mytimer.past_due:
    #    logging.info('The timer is past due!')

    #Obtain headlines for all products



    logging.info('Python timer trigger function ran at %s', utc_timestamp)

#### Weather.com API handling
def api_get_alert_headlines(adminDistrictCode):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}/v3/alerts/headlines?adminDistrictCode={adminDistrictCode}&format=json&language=en-US&apiKey={os.environ['WEATHER_API_KEY']}"
    response = requests.get(url)
    if response.status_code != 200:
       logging.error(f'Error calling api_get_alert_headlines: {response.text}')
    return response.json()

def api_get_product_info(productCode, maxTimes = 1):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}/v2/vector-api/products/{productCode}/info?meta=true&max-times={maxTimes}&apiKey={os.environ['WEATHER_API_KEY']"
    response = requests.get(url)
    if response.status_code != 200:
       logging.error(f'Error calling api_get_feature_info: {response.text}')
    return response.json()

def api_get_alert_details(alertid):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}v3/alerts/detail?alertId={alertid}&apiKey={os.environ['WEATHER_API_KEY']}"
    response = requests.get(url)
    if response.status_code != 200:
       logging.error(f'Error calling api_get_alert_details: {response.text}')
    return response.json()

def api_get_product_features(productCode, time, lod = 1, x = 0, y = 0, tilesize = 256):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}/v2/vector-api/products/{productCode}/features?time={time}&lod={lod}&x={x}&y={y}&tile-size={tilesize}&apiKey={os.environ['WEATHER_API_KEY']}"
    response = requests.get(url)
    if response.status_code != 200:
       logging.error(f'Error calling api_get_product_features: {response.text}')
    return response.json()

#### Logic
def do_everything():
    alert_full_list = []
    product_list = os.environ["WEATHER_PRODUCTS"]

    for prod in product_list:       
        product_info = api_get_product_info(prod)
        feature_time = product_info["products"][prod]["time"]
        feature_list = api_get_product_features(prod, feature_time)["features"]
        for feature in feature_list:
            alert_detail = api_get_alert_details(feature["properties"]["detailKey"])
            #add alert detail info to the feature
            feature["properties"]["alert_detail_data"] = alert_detail
            




        alert_list = api_get_alert_headlines(os.environ["WEATHER_ADMIN_CODES"])["alerts"]
        for alert_item in alert_list:
            
            #Create object to represent the alert and associated features (effectively joining data from 2 api calls)
            alert = alert(alert_item)

