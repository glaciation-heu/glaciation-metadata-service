# the script should talk to metadata service directly
# it should retrieve the time stamps

#from 
from datetime import datetime, timedelta
from urllib.parse import urlencode
import numpy as np
import requests

import schedule
import time

def read_file(fname):
    with open(fname, "r") as f:
        return f.read()

def local_query(self, query: str | None = None) -> Any:
    """
    Queries Local Metadata service
    """
    if query is None:
        query = self.query

    params = {"query": query}
    encoded_query = urlencode(params)
    base_url = "http://192.168.4.26:32732/api/v0/graph" # Address of the Metadata Service!
    full_url = f"{base_url}?{encoded_query}"

    response = requests.get(full_url)

    return response.json()

def job():

    timestamps = np.array(
        [
            timestamp["graphURI"]["value"]
            for timestamp in local_query(
                read_file("query_timestamps.txt")
            )['results']['bindings']
        ]
    )
    
    cutoff_time = datetime.now() - timedelta(days=1)
    cutoff_timestamp = int(cutoff_time.timestamp())*1000

    for i in range(len(timestamps)):
        ts = int(timestamps[i].split(':')[-1])
        
        if ts<cutoff_timestamp:
            query=f"DROP GRAPH <timestamp:{ts}>"

            params = {"query": query}
            encoded_query = urlencode(params)
            base_url = "http://127.0.0.1:8000/api/v0/graph" #Address of the Metadata Service!
            full_url = f"{base_url}?{encoded_query}"

            response = requests.post(full_url)
            # res=super_local_query("DROP GRAPH <" + timestamps[i]+'>')
            print(response)
            

schedule.every().day.at("23:59").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)