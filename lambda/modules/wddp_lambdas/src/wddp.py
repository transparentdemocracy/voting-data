import os

import requests

DEFAULT_TIMEOUT = 30
PAGE_SIZE = 10


def search_motions(event, _context):
    q = event.get("queryStringParameters", {}).get('q', "")
    page = int(event.get("queryStringParameters", {}).get('page', "0"))

    return search("motions", create_query(page, q, "votingDate"))


def get_motion(event, _context):
    motion_id = event.get("requestContext", {}).get("http", {})["path"][1:]
    return get("motions", motion_id)


def search_plenaries(event, _context):
    q = event.get("queryStringParameters", {}).get('q', "")
    page = int(event.get("queryStringParameters", {}).get('page', "0"))

    return search("plenaries", create_query(page, q, "date"))


def search(index, query):
    secret = os.environ['ES_AUTH']
    url = f"https://{secret}@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/{index}/_search"
    response = requests.post(url, json=query, timeout=DEFAULT_TIMEOUT)
    body = response.text

    return {
        'statusCode': 200,
        'body': body
    }


def create_query(page, q, date_field):
    query = {
        "size": PAGE_SIZE,
        "from": max(0, page) * PAGE_SIZE,
        "sort": [
            {date_field: {"order": "desc"}}
        ]

    }
    if q != "":
        query["query"] = {
            "query_string": {
                "query": q
            }
        }

    return query


def get(index, doc_id):
    secret = os.environ['ES_AUTH']
    url = f"https://{secret}@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/{index}/_doc/{doc_id}"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    body = response.text

    return {
        'statusCode': 200,
        'body': body
    }
