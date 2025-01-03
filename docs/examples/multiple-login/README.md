# Multi-platform OAuth demo with Quart

You can learn multi-platform OAuth 2.0 client (i.e. Google and X) implementation with this demo.

## Install

Install the required dependencies:

    $ pip install -U quart_authlib

## Config

Create your Google OAuth Client at <https://console.cloud.google.com/apis/credentials>, make sure to add `http://127.0.0.1:5000/auth` into Authorized redirect URIs.

Fill the given client IDs and secrets for X and Google into `config.py`.

## Run

Start server with:

    $ export QUART_APP=app.py
    $ quart run

Then visit:

    http://127.0.0.1:5000/
