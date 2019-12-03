import datetime
import logging
import json 
import requests
import os
import sys
sys.path.append(os.path.abspath(""))

import azure.functions as func
from sharedcode import dbhelper as dbh
from sharedcode import emailrequestmsg as emsg

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    #if mytimer.past_due:
    #    logging.warning('The timer is past due!')
    
    logging.getLogger().setLevel(logging.INFO)

    alert_full_list = []
    product_list = [
      "619","620","621","622","623","630"
    ]

    alert_headlines = api_get_alert_headlines(os.environ['WEATHER_ADMIN_CODE'])['alerts']
    
    for prod in product_list:
        logging.warning(f"Checking product code {prod}")       
        product_info = api_get_product_info(prod)        
        feature_time = product_info["products"][prod]["time"][0]
        feature_list = api_get_product_features(prod, feature_time)["features"]
        logging.info(f"Number of features for product {prod} : {len(feature_list)}")
        
        for ah in alert_headlines:
            feature = get_feature_contains_alert(feature_list, ah['detailKey'])
            if feature == None:
                logging.info(f"\tNo feature with alert id {ah['identifier']} and area {ah['areaId']} found. Skipping...")
                continue
            else:
                alert_detail = api_get_alert_details(feature["properties"]["detailKey"])              

                #add alert detail info to the feature
                feature["properties"]["alert_detail_data"] = alert_detail['alertDetail']                        
                feature["properties"]["alert_detail_data"]['buildings'] = []
                feature["properties"]["alert_detail_data"]['Recommendations'] = []
                
                if not dbh.alert_already_sent(alert_detail['alertDetail']):
                    #check if any building is in scope            
                    affected_buildings = dbh.get_buildings_in_polygon(feature["geometry"]["coordinates"][0])
                    at_least_one_building_affected = False
                    for b in affected_buildings:
                        at_least_one_building_affected = True
                        logging.info(f"\t\tFound building affected by alert: {b['id']} {b['Building Name']}")
                        #add affected building info to alert
                        feature["properties"]["alert_detail_data"]['buildings'].append(b)

                    if at_least_one_building_affected:
                        #add recommendations                        
                        recommendations = dbh.get_alert_recommendations(feature['properties']['alert_detail_data']['phenomena'])
                        for r in recommendations:
                            feature["properties"]["alert_detail_data"]['Recommendations'] = r['Recommendations']

                        dbh.save_alert(feature["properties"]["alert_detail_data"])
                        #log_alert_detail(feature)                      
                        alert_saved = True  

                        #send email request to queue
                        email_request_msg = emsg.EmailRequestMessage.from_alert_detail_json(feature["properties"]["alert_detail_data"])
                        dbh.put_email_request_msg(email_request_msg)                

                    else:
                        logging.info(f"\tNo buildings affected by alert: {ah['identifier']}; areaId = {ah['areaId']}")
                
                else:
                    logging.warning(f"\tAlert already sent: {ah['identifier']}; areaId = {ah['areaId']}")

#### Weather.com API handling
def api_get_alert_headlines(adminDistrictCode):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}/v3/alerts/headlines?adminDistrictCode={adminDistrictCode}&format=json&language=en-US&apiKey={os.environ['WEATHER_API_KEY']}"
    response = requests.get(url)
    if response.status_code == 200:
       return response.json()
    elif response.status_code == 204:
       return json.loads("{ }")
    else:
       logging.error(f'Error calling api_get_alert_headlines: {response.text}')
    

def api_get_product_info(productCode, maxTimes = 1):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}/v2/vector-api/products/{productCode}/info?meta=true&max-times={maxTimes}&apiKey={os.environ['WEATHER_API_KEY']}"
    response = requests.get(url)
    if response.status_code == 200:
       return response.json()
    elif response.status_code == 204:
       return json.loads("{ }")
    else:
       logging.error(f'Error calling api_get_feature_info: {response.text}')

def api_get_alert_details(alertid):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}/v3/alerts/detail?alertId={alertid}&format=json&language=en-US&apiKey={os.environ['WEATHER_API_KEY']}"
    response = requests.get(url)
    if response.status_code == 200:
       return response.json()
    elif response.status_code == 204:
       return None
    else:
       logging.error(f'Error calling api_get_alert_details: {response.text}')

def api_get_product_features(productCode, time, lod = 1, x = 0, y = 0, tilesize = 256):
    url = f"{os.environ['WEATHER_API_ENDPOINT']}/v2/vector-api/products/{productCode}/features?time={time}&lod={lod}&x={x}&y={y}&tile-size={tilesize}&apiKey={os.environ['WEATHER_API_KEY']}"
    response = requests.get(url)
    if response.status_code == 200:
       return response.json()
    elif response.status_code == 204:
       return json.loads("{ }")
    else:
       logging.error(f'Error calling api_get_product_features: {response.text}')

#### Building data
def notify_building_managers(building, weather_feature):
    if (building['O&M Responsibility'] != 'None'):
        logging.warning(f"\t\tNotification sent to B# ({building['id']} {building['Building Name']}), notified person: {building['MSM']}")    
    
def log_alert_detail(weather_feature):
    logging.warning(f"\tAlert: {weather_feature['properties']['alert_detail_data']}")
    
#### Search function
def get_feature_contains_alert(feature_collection, alert_detail_key):
    for f in feature_collection:
        if f['properties']['detailKey'] == alert_detail_key:
            return f
    return None