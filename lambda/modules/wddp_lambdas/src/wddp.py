import os

import requests

PAGE_SIZE = 10


def search_motions(event, context):
    q = event.get("queryStringParameters", {}).get('q', "")
    page = int(event.get("queryStringParameters", {}).get('page', "0"))

    return search("motions", q, page)


def get_motion(event, context):
    id = event.get("requestContext", {}).get("http", {})["path"][1:]
    return get("motions", id)


def search_plenaries(event, context):
    q = event.get("queryStringParameters", {}).get('q', "")
    page = int(event.get("queryStringParameters", {}).get('page', "0"))

    return search("plenaries", q, page)


def search(index, q, page):
    query = {
        "size": PAGE_SIZE,
        "from": max(0, page) * PAGE_SIZE,
        # "sort": [
        #     {"date": {"order": "desc"}}
        # ]

    }

    if q != "":
        query["query"] = {
            "query_string": {
                "query": q
            }
        }

    secret = os.environ['ES_AUTH']
    url = "https://%s@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/%s/_search" % (secret, index)
    response = requests.post(url, json=query)
    body = response.text

    return {
        'statusCode': 200,
        'body': body
    }


def get(index, id):
    secret = os.environ['ES_AUTH']
    url = "https://%s@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/%s/_doc/%s" % (secret, index, id)
    response = requests.get(url)
    body = response.text

    return {
        'statusCode': 200,
        'body': body
    }
