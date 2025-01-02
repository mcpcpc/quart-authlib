from quart import Quart
from quart import url_for
from quart import session
from quart import render_template
from quart import redirect
from quart import abort
from quart_authlib import OAuth


app = Quart(__name__)
app.secret_key = '!secret'
app.config.from_object('config')

CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth = OAuth(app)
oauth.register(
    name='google',
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)


def normalize_twitter_userinfo(client, data):
    # make twitter account data into UserInfo format
    params = {
        'sub': data['id_str'],
        'name': data['name'],
        'email': data.get('email'),
        'locale': data.get('lang'),
        'picture': data.get('profile_image_url_https'),
        'preferred_username': data.get('screen_name'),
    }
    username = params['preferred_username']
    if username:
        params['profile'] = 'https://x.com/{}'.format(username)
    return params


oauth.register(
    name='twitter',
    api_base_url='https://api.x.com/1.1/',
    request_token_url='https://api.x.com/oauth/request_token',
    access_token_url='https://api.x.com/oauth/access_token',
    authorize_url='https://api.x.com/oauth/authenticate',
    userinfo_endpoint='account/verify_credentials.json?include_email=true&skip_status=true',
    userinfo_compliance_fix=normalize_twitter_userinfo,
    fetch_token=lambda: session.get('token'),  # DON'T DO IT IN PRODUCTION
)



@app.route('/')
async def homepage():
    user = session.get('user')
    return await render_template('home.html', user=user)


@app.route('/login/<name>')
async def login(name):
    client = oauth.create_client(name)
    if not client:
        abort(404)

    redirect_uri = url_for('auth', name=name, _external=True)
    return client.authorize_redirect(redirect_uri)


@app.route('/auth/<name>')
async def auth(name):
    client = oauth.create_client(name)
    if not client:
        abort(404)

    token = client.authorize_access_token()
    user = token.get('userinfo')
    if not user:
        user = client.userinfo()

    session['user'] = user
    return redirect('/')


@app.route('/logout')
async def logout():
    session.pop('user', None)
    return redirect('/')
