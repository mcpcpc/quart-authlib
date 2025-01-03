#!/usr/bin/env python
# -*- coding: utf-8 -*-

from json import load
from time import time
from os.path import dirname
from os.path import abspath
from os.path import join
from unittest.mock import MagicMock

from requests import Response

ROOT = abspath(dirname(__file__))


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


def read_key_file(name):
    file_path = join(ROOT, name)
    with open(file_path) as f:
        if name.endswith(".json"):
            return load(f)
        return f.read()
