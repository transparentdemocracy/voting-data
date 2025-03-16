import os

import requests

DEFAULT_TIMEOUT = 30
PAGE_SIZE = 100


def get_motion(event, _context):
    motion_id = event.get("requestContext", {}).get("http", {})["path"][1:]
    secret = os.environ['ES_AUTH']
    url = f"https://{secret}@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/motions/_doc/{motion_id}"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    body = response.text
    return {
        'statusCode': 200,
        'body': body
    }


def search_motions(event, _context):
    params = event.get("queryStringParameters", {})
    q = params.get('q', "")
    page = int(params.get('page', "0"))
    min_date = params.get('minDate', None)
    max_date = params.get('maxDate', None)

    return search("motions", "votingDate", min_date, max_date, q, page)


def search_plenaries(event, _context):
    params = event.get("queryStringParameters", {})
    q = params.get('q', "")

    page = int(params.get('page', "0"))
    min_date = params.get('minDate', None)
    max_date = params.get('maxDate', None)

    return search("plenaries", "date", min_date, max_date, q, page)


def search(index, date_field, min_date, max_date, q, page=0):
    query = create_query(date_field, page, q, min_date, max_date)

    secret = os.environ['ES_AUTH']
    url = f"https://{secret}@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/{index}/_search"
    response = requests.post(url, json=query, timeout=DEFAULT_TIMEOUT)
    body = response.text

    return {
        'statusCode': 200,
        'body': body
    }


def create_query(date_field, page, q, min_date=None, max_date=None):
    query = {
        "size": PAGE_SIZE,
        "from": max(0, page) * PAGE_SIZE,
        "sort": [
            {date_field: {"order": "desc"}}
        ],
    }

    conditions = []
    if q != "":
        conditions.append({"simple_query_string": {"query": q, "fields": ["*"], "default_operator": "and"}})
        # conditions.append({"multi_match": {
        #     "query": q,
        #     "fields": ["*"]
        # }})
    if min_date is not None or max_date is not None:
        date_filter = {}
        if min_date is not None:
            date_filter["gte"] = min_date
        if max_date is not None:
            date_filter["lte"] = max_date

        conditions.append({"range": {date_field: date_filter}})

    if len(conditions) == 1:
        query["query"] = conditions[0]

    if len(conditions) > 1:
        query["query"] = {"bool": {"must": conditions}}

    return query

