import datetime
import os
import json

import requests
from firebase_admin.auth import InvalidIdTokenError

from auth import TokenVerifier

DEFAULT_TIMEOUT = 30
PAGE_SIZE = 100


class ElasticRepo:
    def __init__(self, host, secret=None):
        self.motions_url = f"https://{host}/motions/_search" if secret is None else f"https://{secret}@{host}/motions/_search"

    def search_motions(self, q, page, min_date, max_date):
        query = create_query("votingDate", page, q, min_date.isoformat() if min_date else None, max_date.isoformat() if max_date else None)
        response = requests.post(self.motions_url, json=query, timeout=DEFAULT_TIMEOUT)
        return response.text


class TimeProvider:
    def get_date(self):
        return datetime.date.today()


class Application:
    def __init__(self, elastic_repo: ElasticRepo, time_provider: TimeProvider):
        self.elastic_repo = elastic_repo
        self.time_provider = time_provider

    def search_motions(self, q, min_date, max_date: datetime.date = None, page=0, authenticated=False):
        if max_date is None:
            max_date = self.time_provider.get_date()

        if not authenticated:
            max_date = min(max_date, self.time_provider.get_date() - datetime.timedelta(days=14))

        return self.elastic_repo.search_motions(q, page, min_date, max_date)


class Rest:
    def __init__(self, app: Application, token_verifier: TokenVerifier):
        self.app = app
        self.token_verifier = token_verifier

    def handle_search_motions(self, event, context):
        authenticated, response = self.check_token(event)
        if response is not None:
            return response

        params = event.get("queryStringParameters", {})
        q = params.get('q', "")
        min_date_param = params.get('minDate', None)
        max_date_param = params.get('maxDate', None)

        min_date = None if min_date_param is None else datetime.date.fromisoformat(min_date_param)
        max_date = None if max_date_param is None else datetime.date.fromisoformat(max_date_param)
        page = int(params.get('page', "0"))

        return {
            'statusCode': 200,
            'body': self.app.search_motions(q, min_date, max_date, page, authenticated)
        }

    def check_token(self, event):
        authz_header = event['headers'].get('Authorization', None)
        if authz_header is None:
            return False, None
        if not authz_header.startswith("Bearer "):
            return False, {
                'statusCode': 403,
                'body': "invalid id token"
            }

        token = authz_header.split(" ", 1)[1]
        try:
            self.token_verifier.verify(token)
        except InvalidIdTokenError:
            return False, {
                'statusCode': 403,
                'body': "invalid id token"
            }
        return True, None


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


def create_rest(
    host=os.environ.get("ES_HOST", "transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443"),
    secret=os.environ.get("ES_AUTH", None),
    service_account_info=os.environ.get("FIREBASE_SERVICE_ACCOUNT_INFO", None)):
    token_verifier = None if service_account_info is None else TokenVerifier(json.loads(service_account_info))
    time_provider = TimeProvider()
    repo = ElasticRepo(host, secret)

    app = Application(repo, time_provider)

    return Rest(app, token_verifier)


REST = create_rest()


def search_motions(event, context):
    return REST.handle_search_motions(event, context)

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
