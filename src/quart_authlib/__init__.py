#!/usr/bin/env python
# -*- coding: utf-8 -*-

from werkzeug.local import LocalProxy
from authlib.integrations.base_client import BaseOAuth
from authlib.integrations.base_client import OAuthError

from .integration import QuartIntegration
from .integration import token_update
from .apps import QuartOAuth1App
from .apps import QuartOAuth2App

__version__ = "0.0.2"


class OAuth(BaseOAuth):
    oauth1_client_cls = QuartOAuth1App
    oauth2_client_cls = QuartOAuth2App
    framework_integration_cls = QuartIntegration

    def __init__(self, app=None, cache=None, fetch_token=None, update_token=None):
        super().__init__(
            cache=cache, fetch_token=fetch_token, update_token=update_token
        )
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app, cache=None, fetch_token=None, update_token=None):
        """
        Initialize lazy for Quart app.
        """

        self.app = app
        if cache is not None:
            self.cache = cache

        if fetch_token:
            self.fetch_token = fetch_token
        if update_token:
            self.update_token = update_token

        app.extensions = getattr(app, "extensions", {})
        app.extensions["quart_authlib"] = self

    def create_client(self, name):
        if not self.app:
            raise RuntimeError("OAuth is not init with Quart app.")
        return super().create_client(name)

    def register(self, name, overwrite=False, **kwargs):
        self._registry[name] = (overwrite, kwargs)
        if self.app:
            return self.create_client(name)
        return LocalProxy(lambda: self.create_client(name))


__all__ = [
    "OAuth",
    "FlaskIntegration",
    "QuartOAuth1App",
    "QuartOAuth2App",
    "token_update",
    "OAuthError",
]
