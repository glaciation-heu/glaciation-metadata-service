# the script should talk to metadata service directly
# it should retrieve the time stamps

from typing import Any

import time
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
import schedule
from loguru import logger
from numpy import array


def read_file(fname):
    with open(fname, "r") as f:
        return f.read()


def local_query(query: str) -> Any:
    """
    Queries Local Metadata service
    """
    params = {"query": query}
    encoded_query = urlencode(params)
    base_url = "http://localhost:80/api/v0/graph"  # Address of the Metadata Service!
    full_url = f"{base_url}?{encoded_query}"

    try:
        response = requests.get(full_url)
        return response.json()
    except Exception as e:
        logger.error(e)
        return {"head": {}, "results": {"bindings": []}}


def job():
    timestamps = array(
        [
            timestamp["graphURI"]["value"]
            for timestamp in local_query(
                read_file("app/query_files/query_timestamps.txt")
            )["results"]["bindings"]
        ]
    )

    logger.debug(timestamps)

    cutoff_time = datetime.now() - timedelta(days=1)
    cutoff_timestamp = int(cutoff_time.timestamp()) * 1000

    for i in range(len(timestamps)):
        ts = int(timestamps[i].split(":")[-1])

        if ts < cutoff_timestamp:
            query = f"DROP GRAPH <{timestamps[i]}>"

            params = {"query": query}
            encoded_query = urlencode(params)
            base_url = (
                "http://localhost:80/api/v0/graph"  # Address of the Metadata Service!
            )
            full_url = f"{base_url}?{encoded_query}"
            logger.debug(full_url)

            # response = requests.post(full_url)
            # # res=super_local_query("DROP GRAPH <" + timestamps[i]+'>')
            # logger.debug(response)

            logger.info(f"Dropped graph <{timestamps[i]}>.")


# schedule.every().day.at("23:59").do(job)
schedule.every().minute.at(":30").do(job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
