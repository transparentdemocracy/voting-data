import requests
import json
import os

PAGE_SIZE=10

def search_motions(event, context):
    q = event.get("queryStringParameters", {}).get('q', "")
    page = int(event.get("queryStringParameters", {}).get('page', "0"))

    query = {
      "size":PAGE_SIZE,
      "from":max(0, page) * PAGE_SIZE
    }

    if q != "":
        query["query"] = {
          "query_string": {
            "query": q
          }
        }

    # TODO: pass body with query, see website project for correct query
    secret = os.environ['ES_AUTH']
    url = "https://%s@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/motions/_search" % (secret)
    response = requests.post("https://lter47onzt:o5ipi1ua3p@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443/motions/_search", json=query)
    body = response.text

    return {
        'statusCode': 200,
        'body': body
    }


