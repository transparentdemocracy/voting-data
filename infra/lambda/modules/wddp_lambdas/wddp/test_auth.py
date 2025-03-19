import json
import unittest

from firebase_admin.auth import ExpiredIdTokenError

from wddp.auth import TokenVerifier

EXAMPLE_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsImtpZCI6ImEwODA2N2Q4M2YwY2Y5YzcxNjQyNjUwYzUyMWQ0ZWZhNWI2YTNlMDkiLCJ0eXAiOiJKV1QifQ"
    ".eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vd2RkcC1kMTQzMSIsImF1ZCI6IndkZHAtZDE0MzEiLCJhdXRoX3RpbWUiOjE3NDIxNjEwMTUsInVzZXJfaWQiOiJucWk1aENxbDB0Y040c1VwUmhxM1MyVFlPazkyIiwic3ViIjoibnFpNWhDcWwwdGNONHNVcFJocTNTMlRZT2s5MiIsImlhdCI6MTc0MjIzNTMwNCwiZXhwIjoxNzQyMjM4OTA0LCJlbWFpbCI6ImthcmVsQHZlcnZhZWtlLmluZm8iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJrYXJlbEB2ZXJ2YWVrZS5pbmZvIl19LCJzaWduX2luX3Byb3ZpZGVyIjoicGFzc3dvcmQifX0.A162hNg8yV1NVzPBDrDACNBrqjsd6d28UXznaQef-pCh_rRB0KLq3y1elUcLhdxNKDqkLeROwgZxQXOwRq2j1jEG7BE1fHi1TEUSFYhPf_hHl5T3ttnDYorakIpmyF8bmjovw5Ubm7VKVAyVcnXriSCiZqCq1Sbhe0fC2dHqllQm7367UsQ1BHmu4v3MnVvCCpRRCflJ5NkiKn04CnYfOQfhq-3T2UnXNivB5_VrSqMZ63t34kPX8zOdr0_D7FrXTQyUj5vlqC5Y8Yxkz_Ww5VD_9uyh_7KFUr7UQ91C9g2degr1SUOtDuaNQvNMmBdd6V0m8Bg_80R57h8Iw7SKaQ")


class TokenVerifierTest(unittest.TestCase):

    def test_token_verifier(self):
        token_verifier = TokenVerifier(json.loads(blah))

        try:
            actual = token_verifier.verify(EXAMPLE_TOKEN)
            print(actual)
        except ExpiredIdTokenError as expired:
            self.assertTrue(expired.cause.args[0].startswith("Token expired, 1742238904 < "), "Expiration message")
