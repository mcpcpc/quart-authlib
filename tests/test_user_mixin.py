from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock
from unittest.mock import patch
from quart import Quart
from authlib.jose import JsonWebKey
from authlib.jose.errors import InvalidClaimError
from authlib.oidc.core.grants.util import generate_id_token

from quart_authlib import OAuth

from .utils import get_bearer_token
from .utils import read_key_file

secret_key = JsonWebKey.import_key("secret", {"kty": "oct", "kid": "f"})


class QuartUserMixinTest(IsolatedAsyncioTestCase):
    async def test_fetch_userinfo(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            fetch_token=get_bearer_token,
            userinfo_endpoint="https://i.b/userinfo",
        )

        def fake_send(sess, req, **kwargs):
            resp = MagicMock()
            resp.json = lambda: {"sub": "123"}
            resp.status_code = 200
            return resp

        async with app.test_request_context(path="/"):
            with patch("requests.sessions.Session.send", fake_send):
                user = client.userinfo()
                self.assertEqual(user.sub, "123")

    async def test_parse_id_token(self):
        token = get_bearer_token()
        id_token = generate_id_token(
            token,
            {"sub": "123"},
            secret_key,
            alg="HS256",
            iss="https://i.b",
            aud="dev",
            exp=3600,
            nonce="n",
        )

        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            fetch_token=get_bearer_token,
            jwks={"keys": [secret_key.as_dict()]},
            issuer="https://i.b",
            id_token_signing_alg_values_supported=["HS256", "RS256"],
        )
        async with app.test_request_context(path="/"):
            self.assertIsNone(client.parse_id_token(token, nonce="n"))

            token["id_token"] = id_token
            user = client.parse_id_token(token, nonce="n")
            self.assertEqual(user.sub, "123")

            claims_options = {"iss": {"value": "https://i.b"}}
            user = client.parse_id_token(
                token, nonce="n", claims_options=claims_options
            )
            self.assertEqual(user.sub, "123")

            claims_options = {"iss": {"value": "https://i.c"}}
            self.assertRaises(
                InvalidClaimError, client.parse_id_token, token, "n", claims_options
            )

    async def test_parse_id_token_nonce_supported(self):
        token = get_bearer_token()
        id_token = generate_id_token(
            token,
            {"sub": "123", "nonce_supported": False},
            secret_key,
            alg="HS256",
            iss="https://i.b",
            aud="dev",
            exp=3600,
        )

        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            fetch_token=get_bearer_token,
            jwks={"keys": [secret_key.as_dict()]},
            issuer="https://i.b",
            id_token_signing_alg_values_supported=["HS256", "RS256"],
        )
        async with app.test_request_context(path="/"):
            token["id_token"] = id_token
            user = client.parse_id_token(token, nonce="n")
            self.assertEqual(user.sub, "123")

    async def test_runtime_error_fetch_jwks_uri(self):
        token = get_bearer_token()
        id_token = generate_id_token(
            token,
            {"sub": "123"},
            secret_key,
            alg="HS256",
            iss="https://i.b",
            aud="dev",
            exp=3600,
            nonce="n",
        )

        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        alt_key = secret_key.as_dict()
        alt_key["kid"] = "b"
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            fetch_token=get_bearer_token,
            jwks={"keys": [alt_key]},
            issuer="https://i.b",
            id_token_signing_alg_values_supported=["HS256"],
        )
        async with app.test_request_context(path="/"):
            token["id_token"] = id_token
            self.assertRaises(RuntimeError, client.parse_id_token, token, "n")

    async def test_force_fetch_jwks_uri(self):
        secret_keys = read_key_file("jwks_private.json")
        token = get_bearer_token()
        id_token = generate_id_token(
            token,
            {"sub": "123"},
            secret_keys,
            alg="RS256",
            iss="https://i.b",
            aud="dev",
            exp=3600,
            nonce="n",
        )

        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            fetch_token=get_bearer_token,
            jwks={"keys": [secret_key.as_dict()]},
            jwks_uri="https://i.b/jwks",
            issuer="https://i.b",
        )

        def fake_send(sess, req, **kwargs):
            resp = MagicMock()
            resp.json = lambda: read_key_file("jwks_public.json")
            resp.status_code = 200
            return resp

        async with app.test_request_context(path="/"):
            self.assertIsNone(client.parse_id_token(token, nonce="n"))

            with patch("requests.sessions.Session.send", fake_send):
                token["id_token"] = id_token
                user = client.parse_id_token(token, nonce="n")
                self.assertEqual(user.sub, "123")
