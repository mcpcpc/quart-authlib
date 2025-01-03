from quart import Quart
from quart import url_for
from quart import session
from quart import render_template
from quart import redirect
from quart_authlib import OAuth


app = Quart(__name__)
app.secret_key = "!secret"
app.config.from_object("config")

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth = OAuth(app)
oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_kwargs={"scope": "openid email profile"},
)


@app.route("/")
async def homepage():
    user = session.get("user")
    return await render_template("home.html", user=user)


@app.route("/login")
async def login():
    redirect_uri = url_for("auth", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth")
async def auth():
    token = oauth.google.authorize_access_token()
    session["user"] = token["userinfo"]
    return redirect("/")


@app.route("/logout")
async def logout():
    session.pop("user", None)
    return redirect("/")
