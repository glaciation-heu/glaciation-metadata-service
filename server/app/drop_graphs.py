# the script should talk to metadata service directly
# it should retrieve the time stamps

from typing import Any, Dict

import time
from datetime import datetime, timedelta
from re import search
from urllib.parse import urlencode

import requests
import schedule
from loguru import logger


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
    logger.debug(local_query(read_file("app/query_files/query_timestamps.txt")))
    timestamps = {}
    for graphURI in graphURIs:
        found = search(r"timestamp:(\d+)", graphURI)
        if found:
            timestamps[graphURI] = int(found.group(1))

    return timestamps


def job():
    timestamps = get_timestamps()

    logger.debug(timestamps)

    cutoff_time = datetime.now() - timedelta(days=1)
    cutoff_timestamp = int(cutoff_time.timestamp()) * 1000

    query = ""
    for graphURI in timestamps:
        if timestamps[graphURI] < cutoff_timestamp:
            if len(query) > 0:
                query += "\n"
            query += f"DROP GRAPH <{graphURI}>;"

    local_query(query, True)
    logger.info(f"Performed:\n{query}")


# schedule.every().day.at("23:59").do(job)
schedule.every().minute.at(":30").do(job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
