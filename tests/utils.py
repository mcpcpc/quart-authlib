#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import time
from unittest.mock import MagicMock

from requests import Response


def mock_send_value(body, status_code: int = 200):
    resp = MagicMock(spec=Response)
    resp.cookies = []
    if isinstance(body, dict):
        resp.json = lambda: body
    else:
        resp.text = body
    resp.status_code = status_code
    return resp


def get_bearer_token():
    t = int(time())
    return {
        "token_type": "Bearer",
        "access_token": "a",
        "refresh_token": "b",
        "expires_in": "3600",
        "expires_at": t + 3600,
    }
