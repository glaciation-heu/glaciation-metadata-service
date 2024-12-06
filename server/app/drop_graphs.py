# the script should talk to metadata service directly
# it should retrieve the time stamps

from typing import Any, Dict

from datetime import datetime, timedelta
from os import getenv
from re import search
from time import sleep
from urllib.parse import urlencode

import requests
import schedule
from loguru import logger

TIME_WINDOW_MILLISECONDS = int(float(getenv("TIME_WINDOW_MILLISECONDS", "86400000")))
INTERVAL_TO_CHECK_IN_SECONDS = int(
    float(getenv("INTERVAL_TO_CHECK_IN_SECONDS", "86400"))
)


def read_file(fname):
    with open(fname, "r") as f:
        return f.read()


def local_query(query: str, update_query: bool = False) -> Any:
    """
    Queries Local Metadata service
    """
    params = {"query": query}
    encoded_query = urlencode(params)
    base_url = "http://localhost:80/api/v0/graph"  # Address of the Metadata Service!
    if update_query:
        base_url += "/update"
    full_url = f"{base_url}?{encoded_query}"

    try:
        response = requests.get(full_url)
        return response.json()
    except Exception as e:
        logger.error(e)
        return {"head": {}, "results": {"bindings": []}}


def get_timestamps() -> Dict[str, int]:
    graphURIs = [
        timestamp["graphURI"]["value"]
        for timestamp in local_query(read_file("app/query_files/query_timestamps.txt"))[
            "results"
        ]["bindings"]
    ]
    timestamps = {}
    for graphURI in graphURIs:
        found = search(r"timestamp:(\d+)", graphURI)
        if found:
            timestamps[graphURI] = int(found.group(1))

    return timestamps


def compaction() -> None:
    url = "http://localhost:80/api/v0/graph/compact"

    try:
        response = requests.post(url)
        if response.status_code == 200:
            logger.info("Compaction triggered successfully!")
            logger.debug(response.text)
        else:
            logger.error(f"Compaction failed: {response.text}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during compaction: {str(e)}")


def job():
    timestamps = get_timestamps()

    logger.debug(f"Timestamps found:\n{timestamps}")

    cutoff_time = datetime.now() - timedelta(milliseconds=TIME_WINDOW_MILLISECONDS)
    cutoff_timestamp = int(cutoff_time.timestamp()) * 1000

    query = ""
    for graphURI in timestamps:
        if timestamps[graphURI] < cutoff_timestamp:
            query += f"DROP GRAPH <{graphURI}>;\n"

    local_query(query, True)
    logger.info(f"Performed the following query:\n{query}")

    compaction()


schedule.every(INTERVAL_TO_CHECK_IN_SECONDS).seconds.do(job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        sleep(1)
