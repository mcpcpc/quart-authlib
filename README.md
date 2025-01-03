# Quart-Authlib

A Quart extension for the Authlib library. This is an adoption from the existing Authlib Flask Client.  Since the primary Authlib developer rejected previous client integration attempts, this project will remain under independent development.

**Important**: This project is in *early* development. Most features are considered unstable or non-functioning; thus, I would **strongly** advise against using any version less than 1.0 for production environments.

## Install

### PyPI

Install and update using pip:

```shell
pip install -U quart-authlib
```

### Repository

When using git, clone the repository and change your present working directory.

```shell
git clone http://github.com/mcpcpc/quart-authlib
cd quart_authlib/
```

Create and activate a virtual environment.

```shell
python3 -m venv venv
source venv/bin/activate
```

Install to the virtual environment.

```shell
pip install -e .
```

## Usage

Quart OAuth client can handle OAuth 1 and OAuth 2 services. It shares a similar API with Quart-OAuthlib, you can transfer your code from Quart-Authlib to Authlib with ease.

Create a registry with OAuth object:

```python
from quart_authlib import OAuth

oauth = OAuth(app)
```

You can also initialize it later with `init_app()` method:

```python
oauth = OAuth()
oauth.init_app(app)
```

The common use case for OAuth is authentication, e.g. let your users log in with Twitter, GitHub, Google etc.

## Configuration

Quart-Authlib OAuth registry can load the configuration from Quart `app.config` automatically. Every key-value pair in `.register` can be omitted. They can be configured in your Quart App configuration. Config keys are formatted as `{name}_{key}` in uppercase. If you register your remote app as `oauth.register('example', ...)`, the config keys would look like:

| Name                        | Key                                                        |
| --------------------------- | ---------------------------------------------------------- |
| EXAMPLE_CLIENT_ID           | OAuth Consumer Key                                         |
| EXAMPLE_CLIENT_SECRET       | OAuth Consumer Secret                                      |
| EXAMPLE_ACCESS_TOKEN_URL    | URL to fetch OAuth access token                            |

Here is a full list of the configuration keys:

* {name}_CLIENT_ID: Client key of OAuth 1, or Client ID of OAuth 2
* {name}_CLIENT_SECRET: Client secret of OAuth 2, or Client Secret of OAuth 2
* {name}_REQUEST_TOKEN_URL: Request Token endpoint for OAuth 1
* {name}_REQUEST_TOKEN_PARAMS: Extra parameters for Request Token endpoint
* {name}_ACCESS_TOKEN_URL: Access Token endpoint for OAuth 1 and OAuth 2
* {name}_ACCESS_TOKEN_PARAMS: Extra parameters for Access Token endpoint
* {name}_AUTHORIZE_URL: Endpoint for user authorization of OAuth 1 or OAuth 2
* {name}_AUTHORIZE_PARAMS: Extra parameters for Authorization Endpoint.
* {name}_API_BASE_URL: A base URL endpoint to make requests simple
* {name}_CLIENT_KWARGS: Extra keyword arguments for OAuth1Session or OAuth2Session

We suggest that you keep ONLY `{name}_CLIENT_ID` and `{name}_CLIENT_SECRET` in your Quart application configuration.

### Routes for Authorization

Routes for authorization should look like:

```python
from flask import url_for, redirect

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return oauth.twitter.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = oauth.twitter.authorize_access_token()
    resp = oauth.twitter.get('account/verify_credentials.json')
    resp.raise_for_status()
    profile = resp.json()
    # do something with the token and profile
    return redirect('/')
```

### Accessing OAuth Resources

Just like above example, we don’t need to pass the `request` parameter, everything is handled by Authlib automatically:

```python
from flask import render_template

@app.route('/github')
def show_github_profile():
    resp = oauth.github.get('user')
    resp.raise_for_status()
    profile = resp.json()
    return render_template('github.html', profile=profile)
```

In this case, our `fetch_token` could look like:

```python
from your_project import current_user

def fetch_token(name):
    if name in OAUTH1_SERVICES:
        model = OAuth1Token
    else:
        model = OAuth2Token
    token = model.find(
        name=name,
        user=current_user,
    )
    return token.to_token()

# initialize the OAuth registry with this fetch_token function
oauth = OAuth(fetch_token=fetch_token)
```

### OpenID Connect Client

An OpenID Connect client is no different than a normal OAuth 2.0 client. When registered with `openid` scope, the built-in OAuth client will handle everything automatically:

```python
oauth.register(
    'google',
    ...
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)
```

When we get the returned token:

```python
token = oauth.google.authorize_access_token()
```

There should be a `id_token` in the response. Authlib has called *.parse_id_token* automatically, we can get `userinfo` in the `token`:

```python
userinfo = token['userinfo']
```

## Examples

See the [examples](docs/examples) directory.


## Contributing

Please create a new [Issue](https://github.com/mcpcpc/quart-authlib/issues/new) or [Pull Request](https://github.com/mcpcpc/quart-authlib/compare).

## Resources

* https://authlib.org
* https://quart.palletsprojects.com/en/latest/
* https://github.com/lepture/authlib/issues/429
* https://docs.authlib.org/en/latest/client/flask.html
* https://github.com/authlib/demo-oauth-client/tree/master
