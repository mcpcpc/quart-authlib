from quart import Flask
from quart import url_for
from quart import request
from quart import session
from quart import render_template
from quart import redirect
from quart_authlib import OAuth
from quart_authlib import OAuthError


app = Quart(__name__)
app.secret_key = "!secret"
app.config.from_object("config")

oauth = OAuth(app)
oauth.register(
    name="x",
    api_base_url="https://api.x.com/1.1/",
    request_token_url="https://api.x.com/oauth/request_token",
    access_token_url="https://api.x.com/oauth/access_token",
    authorize_url="https://api.x.com/oauth/authenticate",
    fetch_token=lambda: session.get("token"),  # DON'T DO IT IN PRODUCTION
)


@app.errorhandler(OAuthError)
async def handle_error(error):
    return await render_template("error.html", error=error)


@app.route("/")
async def homepage():
    user = session.get("user")
    return await render_template("home.html", user=user)


@app.route("/login")
async def login():
    redirect_uri = url_for("auth", _external=True)
    return oauth.x.authorize_redirect(redirect_uri)


@app.route("/auth")
async def auth():
    token = oauth.x.authorize_access_token()
    url = "account/verify_credentials.json"
    resp = oauth.x.get(url, params={"skip_status": True})
    user = resp.json()
    # DON'T DO IT IN PRODUCTION, SAVE INTO DB IN PRODUCTION
    session["token"] = token
    session["user"] = user
    return redirect("/")


@app.route("/logout")
async def logout():
    session.pop("token", None)
    session.pop("user", None)
    return redirect("/")


@app.route("/tweets")
async def list_tweets():
    url = "statuses/user_timeline.json"
    params = {"include_rts": 1, "count": 200}
    prev_id = request.args.get("prev")
    if prev_id:
        params["max_id"] = prev_id

    resp = oauth.x.get(url, params=params)
    tweets = resp.json()
    return await render_template("tweets.html", tweets=tweets)
