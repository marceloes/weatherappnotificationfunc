import azure.cosmos.cosmos_client as cmos
import azure.cosmos.documents as documents
import azure.cosmos.errors as errors
import azure.cosmos.partition_key as partition_key
import azure.cosmos.http_constants as http_constants
from azure.storage.queue import QueueClient
import json
import uuid
import os
import logging
import time

COSMOS_HOST = os.environ['COSMOS_ACCOUNT_URI']
MASTER_KEY = os.environ['COSMOS_ACCOUNT_KEY']
DATABASE_ID = os.environ['COSMOS_DB_ID']
COLLECTION_ID = os.environ['COSMOS_BUILDINGS_COLL']
QUEUE_STORAGE_ACCOUNT = os.environ['QUEUE_STORAGE_ACCOUNT']
QUEUE_STORAGE_KEY = os.environ['QUEUE_STORAGE_KEY']
QUEUE_NAME = os.environ['QUEUE_NAME']


db_link = f"dbs/{DATABASE_ID}"  
buildings_container_link = f"{db_link}/colls/buildings"
alerts_container_link = f"{db_link}/colls/alerts"
recommendations_container_link = f"{db_link}/colls/recommendations"

cosmos = cmos.CosmosClient(COSMOS_HOST, {'masterKey': MASTER_KEY})
queue = QueueClient(account_url=QUEUE_STORAGE_ACCOUNT, queue_name=QUEUE_NAME, credential=QUEUE_STORAGE_KEY)

def transform_location_info(json_object):
    lat = float(json_object['Lat (B#)'])
    lon = float(json_object['Long (B#)'])
    json_object['location'] = {
        'type': 'Point',
        'coordinates': [lon, lat]
    }
    return json_object

def cosmos_db_import_data(building_file_path, recommendations_file_path):
    #connect to db. create it if needed
    logging.info("Connecting to database...")
    try:
        database = cosmos.CreateDatabase({"id": DATABASE_ID})
    except errors.HTTPFailure as e:
        if e.status_code == http_constants.StatusCodes.CONFLICT:
            logging.warning("Database already exists")
            database = cosmos.ReadDatabase(db_link)
        else:
            logging.error(f'Error: {str(e)}')
            exit(10)

    #create recommendations container if needed
    logging.info("Connecting to recommendations container...")
    container_def = {
        'id': 'recommendations',
        'partitionKey': {
            'paths': ['/alertType'],
            'kind': documents.PartitionKind.Hash
        }
    }
    try:
        container = cosmos.CreateContainer(db_link, container_def, {'offerThroughput': 400})
    except errors.HTTPFailure as e:
        if e.status_code == http_constants.StatusCodes.CONFLICT:
            logging.warning("Container already exists")
        else:
            logging.error(f'Error: {str(e)}')
            exit(11)

    #create alerts container if needed
    logging.info("Connecting to alerts container...")
    container_def = {
        'id': 'alerts',
        'DefaultTimeToLive': 18000,
        'partitionKey': {
            'paths': ['/areaId'],
            'kind': documents.PartitionKind.Hash
        }
    }
    try:
        container = cosmos.CreateContainer(db_link, container_def, {'offerThroughput': 400})
    except errors.HTTPFailure as e:
        if e.status_code == http_constants.StatusCodes.CONFLICT:
            logging.warning("Container already exists")
        else:
            logging.error(f'Error: {str(e)}')
            exit(11)

    #create buildings container if needed
    logging.info("Connecting to buildings container...")
    container_def = {
        'id': 'buildings',
        'partitionKey': {
            'paths': ['/City'],
            'kind': documents.PartitionKind.Hash
        }
    }
    try:
        container = cosmos.CreateContainer(db_link, container_def, {'offerThroughput': 400})
    except errors.HTTPFailure as e:
        if e.status_code == http_constants.StatusCodes.CONFLICT:
            logging.warning("Container already exists")
            container = cosmos.ReadContainer(buildings_container_link)
        else:
            logging.error(f'Error: {str(e)}')
            exit(11)

    logging.info("Importing recommendations...")
    with open(recommendations_file_path) as json_file:
        recs = json.load(json_file)       
        for r in recs:
            logging.info(f"Creating item {r['FriendlyName']}")            
            cosmos.UpsertItem(recommendations_container_link, r)

    logging.info("Importing buildings...")
    with open(building_file_path) as json_file:
        buildings = json.load(json_file)       
        for b in buildings:
            logging.info(f"Creating item {b['Site Name']}")            
            cosmos.UpsertItem(buildings_container_link, transform_location_info(b))

def get_buildings():
    #connect to cosmos db
    sql = f"SELECT * FROM {COLLECTION_ID} b"
    buildings = cosmos.QueryItems(buildings_container_link,sql,{'enableCrossPartitionQuery':True})
    return buildings

def get_buildings_in_polygon(polygon):
    sql = "SELECT * FROM " + COLLECTION_ID + " b WHERE ST_WITHIN(b.location, { 'type':'Polygon', 'coordinates': " + json.dumps(polygon) + "})"
    affected_buildings = cosmos.QueryItems(buildings_container_link, sql, {'enableCrossPartitionQuery':True})
    return affected_buildings

def alert_already_sent(alert_detail):
    sql = f"SELECT VALUE COUNT(1) FROM alerts c WHERE c.identifier = '{alert_detail['identifier']}' and c.areaId = '{alert_detail['areaId']}'"
    alerts = cosmos.QueryItems(alerts_container_link, sql)
    for a in alerts:
        if a > 0:
            return True
        else:
            return False

def save_alert(alert_detail):
    current_time = round(time.time())
    alert_expiration_time = int(alert_detail['expireTimeUTC'])
    time_to_live = alert_expiration_time - current_time
    if time_to_live > 0:      
        alert_detail['ttl'] = time_to_live

    cosmos.UpsertItem(alerts_container_link, alert_detail)

def get_alert_recommendations(alert_type):
    sql = f"SELECT r.Recommendations FROM recommendations r WHERE r.alertType = '{alert_type}'"
    recs = cosmos.QueryItems(recommendations_container_link, sql, {'enableCrossPartitionQuery':True})
    return recs

def put_email_request_msg(email_msg):
    queue.send_message(json.dumps(email_msg, default=lambda o: o.__dict__))

