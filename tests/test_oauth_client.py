#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import IsolatedAsyncioTestCase
from unittest import mock
from unittest.mock import MagicMock

from quart import Quart
from quart import session
from authlib.jose import JsonWebKey
from authlib.oidc.core.grants.util import generate_id_token
from authlib.common.urls import urlparse
from authlib.common.urls import url_decode
from cachelib import SimpleCache

from .utils import mock_send_value
from .utils import get_bearer_token

from quart_authlib import OAuth
from quart_authlib import OAuthError
from quart_authlib import QuartOAuth2App


class QuartOAuthTest(IsolatedAsyncioTestCase):
    async def test_register_remote_app(self):
        app = Quart(__name__)
        oauth = OAuth(app)
        self.assertRaises(AttributeError, lambda: oauth.dev)

        oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
        )
        self.assertEqual(oauth.dev.name, "dev")
        self.assertEqual(oauth.dev.client_id, "dev")

    async def test_register_conf_from_app(self):
        app = Quart(__name__)
        app.config.update(
            {
                "DEV_CLIENT_ID": "dev",
                "DEV_CLIENT_SECRET": "dev",
            }
        )
        oauth = OAuth(app)
        oauth.register("dev")
        self.assertEqual(oauth.dev.client_id, "dev")

    async def test_register_with_overwrite(self):
        app = Quart(__name__)
        app.config.update(
            {
                "DEV_CLIENT_ID": "dev-1",
                "DEV_CLIENT_SECRET": "dev",
                "DEV_ACCESS_TOKEN_PARAMS": {"foo": "foo-1"},
            }
        )
        oauth = OAuth(app)
        oauth.register(
            "dev", overwrite=True, client_id="dev", access_token_params={"foo": "foo"}
        )
        self.assertEqual(oauth.dev.client_id, "dev-1")
        self.assertEqual(oauth.dev.client_secret, "dev")
        self.assertEqual(oauth.dev.access_token_params["foo"], "foo-1")

    async def test_init_app_later(self):
        app = Quart(__name__)
        app.config.update(
            {
                "DEV_CLIENT_ID": "dev",
                "DEV_CLIENT_SECRET": "dev",
            }
        )
        oauth = OAuth()
        remote = oauth.register("dev")
        self.assertRaises(RuntimeError, lambda: oauth.dev.client_id)
        oauth.init_app(app)
        self.assertEqual(oauth.dev.client_id, "dev")
        self.assertEqual(remote.client_id, "dev")

        self.assertIsNone(oauth.cache)
        self.assertIsNone(oauth.fetch_token)
        self.assertIsNone(oauth.update_token)

    async def test_init_app_params(self):
        app = Quart(__name__)
        oauth = OAuth()
        oauth.init_app(app, SimpleCache())
        self.assertIsNotNone(oauth.cache)
        self.assertIsNone(oauth.update_token)

        oauth.init_app(app, update_token=lambda o: o)
        self.assertIsNotNone(oauth.update_token)

    async def test_create_client(self):
        app = Quart(__name__)
        oauth = OAuth(app)
        self.assertIsNone(oauth.create_client("dev"))
        oauth.register("dev", client_id="dev")
        self.assertIsNotNone(oauth.create_client("dev"))

    async def test_register_oauth1_remote_app(self):
        app = Quart(__name__)
        oauth = OAuth(app)
        client_kwargs = dict(
            client_id="dev",
            client_secret="dev",
            request_token_url="https://i.b/reqeust-token",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
            fetch_request_token=lambda: None,
            save_request_token=lambda token: token,
        )
        oauth.register("dev", **client_kwargs)
        self.assertEqual(oauth.dev.name, "dev")
        self.assertEqual(oauth.dev.client_id, "dev")

        oauth = OAuth(app, cache=SimpleCache())
        oauth.register("dev", **client_kwargs)
        self.assertEqual(oauth.dev.name, "dev")
        self.assertEqual(oauth.dev.client_id, "dev")

    async def test_oauth1_authorize_cache(self):
        app = Quart(__name__)
        app.secret_key = "!"
        cache = SimpleCache()
        oauth = OAuth(app, cache=cache)

        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            request_token_url="https://i.b/reqeust-token",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
        )

        async with app.test_request_context("/"):
            with mock.patch("requests.sessions.Session.send") as send:
                send.return_value = mock_send_value(
                    "oauth_token=foo&oauth_verifier=baz"
                )
                resp = client.authorize_redirect("https://b.com/bar")
                self.assertEqual(resp.status_code, 302)
                url = resp.headers.get("Location")
                self.assertIn("oauth_token=foo", url)

        async with app.test_request_context("/?oauth_token=foo"):
            with mock.patch("requests.sessions.Session.send") as send:
                send.return_value = mock_send_value(
                    "oauth_token=a&oauth_token_secret=b"
                )
                token = await client.authorize_access_token()
                self.assertEqual(token["oauth_token"], "a")

    async def test_oauth1_authorize_session(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            request_token_url="https://i.b/reqeust-token",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
        )

        async with app.test_request_context("/"):
            with mock.patch("requests.sessions.Session.send") as send:
                send.return_value = mock_send_value(
                    "oauth_token=foo&oauth_verifier=baz"
                )
                resp = client.authorize_redirect("https://b.com/bar")
                self.assertEqual(resp.status_code, 302)
                url = resp.headers.get("Location")
                self.assertIn("oauth_token=foo", url)
                data = session["_state_dev_foo"]

        async with app.test_request_context("/?oauth_token=foo"):
            session["_state_dev_foo"] = data
            with mock.patch("requests.sessions.Session.send") as send:
                send.return_value = mock_send_value(
                    "oauth_token=a&oauth_token_secret=b"
                )
                token = await client.authorize_access_token()
                self.assertEqual(token["oauth_token"], "a")

    async def test_register_oauth2_remote_app(self):
        app = Quart(__name__)
        oauth = OAuth(app)
        oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            refresh_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
            update_token=lambda name: "hi",
        )
        self.assertEqual(oauth.dev.name, "dev")
        session = oauth.dev._get_oauth_client()
        self.assertIsNotNone(session.update_token)

    async def test_oauth2_authorize(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
        )

        async with app.test_request_context("/"):
            resp = client.authorize_redirect("https://b.com/bar")
            self.assertEqual(resp.status_code, 302)
            url = resp.headers.get("Location")
            self.assertIn("state=", url)
            state = dict(url_decode(urlparse.urlparse(url).query))["state"]
            self.assertIsNotNone(state)
            data = session[f"_state_dev_{state}"]

        async with app.test_request_context(path=f"/?code=a&state={state}"):
            # session is cleared in tests
            session[f"_state_dev_{state}"] = data

            with mock.patch("requests.sessions.Session.send") as send:
                send.return_value = mock_send_value(get_bearer_token())
                token = await client.authorize_access_token()
                self.assertEqual(token["access_token"], "a")

        async with app.test_request_context(path="/"):
            self.assertEqual(client.token, None)

    async def test_oauth2_authorize_access_denied(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
        )

        async with app.test_request_context(
            path="/?error=access_denied&error_description=Not+Allowed"
        ):
            # session is cleared in tests
            with mock.patch("requests.sessions.Session.send"):
                with self.assertRaises(OAuthError):
                    await client.authorize_access_token()

    async def test_oauth2_authorize_via_custom_client(self):
        class CustomRemoteApp(QuartOAuth2App):
            OAUTH_APP_CONFIG = {"authorize_url": "https://i.b/custom"}

        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            client_cls=CustomRemoteApp,
        )
        async with app.test_request_context("/"):
            resp = client.authorize_redirect("https://b.com/bar")
            self.assertEqual(resp.status_code, 302)
            url = resp.headers.get("Location")
            self.assertTrue(url.startswith("https://i.b/custom?"))

    async def test_oauth2_authorize_with_metadata(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
        )
        self.assertRaises(RuntimeError, lambda: client.create_authorization_url(None))

        client = oauth.register(
            "dev2",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            server_metadata_url="https://i.b/.well-known/openid-configuration",
        )
        with mock.patch("requests.sessions.Session.send") as send:
            send.return_value = mock_send_value(
                {"authorization_endpoint": "https://i.b/authorize"}
            )

            async with app.test_request_context("/"):
                resp = client.authorize_redirect("https://b.com/bar")
                self.assertEqual(resp.status_code, 302)

    async def test_oauth2_authorize_code_challenge(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
            client_kwargs={"code_challenge_method": "S256"},
        )

        async with app.test_request_context("/"):
            resp = client.authorize_redirect("https://b.com/bar")
            self.assertEqual(resp.status_code, 302)
            url = resp.headers.get("Location")
            self.assertIn("code_challenge=", url)
            self.assertIn("code_challenge_method=S256", url)

            state = dict(url_decode(urlparse.urlparse(url).query))["state"]
            self.assertIsNotNone(state)
            data = session[f"_state_dev_{state}"]

            verifier = data["data"]["code_verifier"]
            self.assertIsNotNone(verifier)

        def fake_send(sess, req, **kwargs):
            self.assertIn(f"code_verifier={verifier}", req.body)
            return mock_send_value(get_bearer_token())

        path = f"/?code=a&state={state}"
        async with app.test_request_context(path=path):
            # session is cleared in tests
            session[f"_state_dev_{state}"] = data

            with mock.patch("requests.sessions.Session.send", fake_send):
                token = await client.authorize_access_token()
                self.assertEqual(token["access_token"], "a")

    async def test_openid_authorize(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        params = dict(kty="oct", kid="f")
        key = dict(JsonWebKey.import_key("secret", params))

        client = oauth.register(
            "dev",
            client_id="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
            client_kwargs={"scope": "openid profile"},
            jwks={"keys": [key]},
        )

        async with app.test_request_context("/"):
            resp = client.authorize_redirect("https://b.com/bar")
            self.assertEqual(resp.status_code, 302)

            url = resp.headers["Location"]
            query_data = dict(url_decode(urlparse.urlparse(url).query))

            state = query_data["state"]
            self.assertIsNotNone(state)
            session_data = session[f"_state_dev_{state}"]
            nonce = session_data["data"]["nonce"]
            self.assertIsNotNone(nonce)
            self.assertEqual(nonce, query_data["nonce"])

        token = get_bearer_token()
        token["id_token"] = generate_id_token(
            token,
            {"sub": "123"},
            key,
            alg="HS256",
            iss="https://i.b",
            aud="dev",
            exp=3600,
            nonce=query_data["nonce"],
        )
        path = f"/?code=a&state={state}"
        async with app.test_request_context(path=path):
            session[f"_state_dev_{state}"] = session_data
            with mock.patch("requests.sessions.Session.send") as send:
                send.return_value = mock_send_value(token)
                token = await client.authorize_access_token()
                self.assertEqual(token["access_token"], "a")
                self.assertIn("userinfo", token)

    #    async def test_oauth2_access_token_with_post(self):
    #        app = Quart(__name__)
    #        app.secret_key = "!"
    #        oauth = OAuth(app)
    #        client = oauth.register(
    #            "dev",
    #            client_id="dev",
    #            client_secret="dev",
    #            api_base_url="https://i.b/api",
    #            access_token_url="https://i.b/token",
    #            authorize_url="https://i.b/authorize",
    #        )
    #        payload = {"code": "a", "state": "b"}
    #        async with app.test_request_context(path="/", data=payload, method="POST"):
    #            session["_state_dev_b"] = {"data": payload}
    #            with mock.patch("requests.sessions.Session.send") as send:
    #                send.return_value = mock_send_value(get_bearer_token())
    #                token = await client.authorize_access_token()
    #                self.assertEqual(token["access_token"], "a")

    async def test_access_token_with_fetch_token(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth()

        token = get_bearer_token()
        oauth.init_app(app, fetch_token=lambda name: token)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
        )

        def fake_send(sess, req, **kwargs):
            auth = req.headers["Authorization"]
            self.assertEqual(auth, "Bearer {}".format(token["access_token"]))
            resp = MagicMock()
            resp.text = "hi"
            resp.status_code = 200
            return resp

        async with app.test_request_context("/"):
            with mock.patch("requests.sessions.Session.send", fake_send):
                resp = client.get("/api/user")
                self.assertEqual(resp.text, "hi")

                # trigger ctx.authlib_client_oauth_token
                resp = client.get("/api/user")
                self.assertEqual(resp.text, "hi")

    async def test_request_with_refresh_token(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth()

        expired_token = {
            "token_type": "Bearer",
            "access_token": "expired-a",
            "refresh_token": "expired-b",
            "expires_in": "3600",
            "expires_at": 1566465749,
        }
        oauth.init_app(app, fetch_token=lambda name: expired_token)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            refresh_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
        )

        def fake_send(sess, req, **kwargs):
            if req.url == "https://i.b/token":
                auth = req.headers["Authorization"]
                self.assertIn("Basic", auth)
                resp = MagicMock()
                resp.json = get_bearer_token
                resp.status_code = 200
                return resp

            resp = MagicMock()
            resp.text = "hi"
            resp.status_code = 200
            return resp

        async with app.test_request_context("/"):
            with mock.patch("requests.sessions.Session.send", fake_send):
                resp = client.get("/api/user", token=expired_token)
                self.assertEqual(resp.text, "hi")

    async def test_request_without_token(self):
        app = Quart(__name__)
        app.secret_key = "!"
        oauth = OAuth(app)
        client = oauth.register(
            "dev",
            client_id="dev",
            client_secret="dev",
            api_base_url="https://i.b/api",
            access_token_url="https://i.b/token",
            authorize_url="https://i.b/authorize",
        )

        def fake_send(sess, req, **kwargs):
            auth = req.headers.get("Authorization")
            self.assertIsNone(auth)
            resp = MagicMock()
            resp.text = "hi"
            resp.status_code = 200
            return resp

        async with app.test_request_context("/"):
            with mock.patch("requests.sessions.Session.send", fake_send):
                resp = client.get("/api/user", withhold_token=True)
                self.assertEqual(resp.text, "hi")
                self.assertRaises(OAuthError, client.get, "https://i.b/api/user")
