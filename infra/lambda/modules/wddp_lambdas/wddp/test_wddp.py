import datetime
import json
import unittest

from firebase_admin.auth import InvalidIdTokenError

from wddp import search_motions, Application, Rest

REFERENCE_TIME = datetime.date(2025, 2, 1)


class WddpTest(unittest.TestCase):

    def test_search_motions_no_params_without_auth(self):
        """ without authentication you don't get back the most recent results. Results are minimum 2 weeks old. """
        setup_test()

        event = {
            'headers': {},
            'httpMethod': 'POST',
            "queryStringParameters": {
            },
            'body': json.dumps({'page': 9})
        }
        response = search_motions(event, None)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual('motions found using , None, 2025-01-18, 0', response['body'])

    def test_search_motions_no_params_with_auth(self):
        """ without authentication you don't get back the most recent results. Results are minimum 2 weeks old. """
        setup_test()

        event = {
            'headers': {
                'Authorization': 'Bearer valid_id_token'
            },
            'httpMethod': 'POST',
            "queryStringParameters": {
            },
            'body': json.dumps({'page': 9})
        }
        response = search_motions(event, None)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual('motions found using , None, 2025-02-01, 0', response['body'])

    def test_search_motions_without_auth(self):
        """ without authentication you don't get back the most recent results. Results are minimum 2 weeks old. """
        setup_test()

        event = {
            'headers': {},
            'httpMethod': 'POST',
            "queryStringParameters": {
                "q": "somequery",
                "page": "9",
                "minDate": "2025-01-02",
                "maxDate": "2025-01-25"
            },
            'body': json.dumps({'page': 9})
        }
        response = search_motions(event, None)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual('motions found using somequery, 2025-01-02, 2025-01-18, 9', response['body'])

    def test_search_motions_with_valid_auth(self):
        """ with valid authentication there is no restriction on how recent your data can be """
        setup_test()

        event = {
            "headers": {
                "Authorization": "Bearer valid_id_token"
            },
            "queryStringParameters": {
                "q": "somequery",
                "page": "9",
                "minDate": "2025-01-02",
                "maxDate": "2025-02-01"
            },
            'httpMethod': 'POST',
            'body': json.dumps({'page': 9})
        }
        response = search_motions(event, None)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual('motions found using somequery, 2025-01-02, 2025-02-01, 9', response['body'])

    def test_search_motions_with_invalid_auth(self):
        """ with an invalid token you should get a 403 response """
        setup_test()

        event = {
            "headers": {
                "Authorization": "Bearer THIS_TOKEN_IS_INVALID"
            },
            "queryStringParameters": {
                "q": "somequery",
                "page": "9",
                "minDate": "2025-01-02",
                "maxDate": "2025-02-01"
            },
            'httpMethod': 'POST',
            'body': json.dumps({'page': 9})
        }
        response = search_motions(event, None)
        self.assertEqual(response['statusCode'], 403)
        self.assertEqual('invalid id token', response['body'])


class InMemoryRepo:
    motions = []

    def search_motions(self, q, page, min_date, max_date):
        return f"motions found using {q}, {min_date}, {max_date}, {page}"


class FakeTokenVerifier:
    def verify(self, id_token):
        if id_token == "valid_id_token":
            return

        raise InvalidIdTokenError("only valid_id_token is considered valid")


class FakeTimeProvider:
    def __init__(self, date: datetime.date):
        self.date = date

    def get_date(self):
        return self.date


def setup_test():
    repo = InMemoryRepo()
    app = Application(repo, FakeTimeProvider(REFERENCE_TIME))
    import wddp
    wddp.REST = Rest(app, FakeTokenVerifier())
