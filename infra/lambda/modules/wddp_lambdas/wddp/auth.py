import firebase_admin
from firebase_admin import credentials, auth


class TokenVerifier:
    def __init__(self, service_account_info):
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)

    def verify(self, id_token):
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        print('Token is valid. User ID:', decoded_token['uid'])
        return decoded_token

