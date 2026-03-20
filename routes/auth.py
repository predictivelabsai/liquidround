"""
Authentication routes — sign up, sign in, Google OAuth, logout, password reset, profile.
"""
import os
from fasthtml.common import *
from starlette.responses import RedirectResponse

ar = APIRouter()

# ---------------------------------------------------------------------------
# Google OAuth setup
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
_oauth_enabled = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

_authlib_oauth = None
if _oauth_enabled:
    from authlib.integrations.starlette_client import OAuth as AuthlibOAuth
    _authlib_oauth = AuthlibOAuth()
    _authlib_oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _session_login(session, user: dict):
    session["user"] = {
        "user_id": str(user["user_id"]),
        "email": user["email"],
        "display_name": user.get("display_name") or user["email"].split("@")[0],
    }


_GOOGLE_SVG = '<svg width="18" height="18" viewBox="0 0 18 18"><path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/><path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/><path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9s.38 1.572.957 3.042l3.007-2.332z" fill="#FBBC05"/><path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/></svg>'


def _google_btn(label: str):
    return A(
        NotStr(_GOOGLE_SVG), label,
        href="/login",
        cls="flex items-center justify-center gap-2 w-full bg-blue-600 text-white py-2.5 rounded-lg font-semibold text-sm hover:bg-blue-700 transition-colors no-underline",
    )


def _auth_layout(title: str, card_parts: list):
    return (
        Title(f"{title} — LiquidRound"),
        Script(src="https://cdn.tailwindcss.com"),
        Main(
            Div(
                Div(
                    Div("LR", cls="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-600 to-blue-400 text-white flex items-center justify-center text-xl font-extrabold mx-auto"),
                    P("LiquidRound", cls="text-xl font-bold text-blue-800 mt-2"),
                    P("M&A Research Platform", cls="text-xs text-gray-500"),
                    cls="text-center mb-6",
                ),
                Div(*card_parts, cls="w-full max-w-sm bg-white border border-gray-200 rounded-xl p-8 shadow-lg"),
                P("Predictive Labs Ltd", cls="text-xs text-gray-400 mt-6"),
                cls="flex flex-col items-center justify-center min-h-screen",
            ),
            cls="bg-gray-50",
        ),
    )


def _pw_input(name: str, placeholder: str, **kw):
    return Input(
        type="password", name=name, placeholder=placeholder, required=True,
        cls="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none",
        **kw,
    )


def _text_input(name: str, placeholder: str, input_type: str = "text", **kw):
    return Input(
        type=input_type, name=name, placeholder=placeholder,
        cls="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none",
        **kw,
    )


def _submit_btn(label: str):
    return Button(
        label, type="submit",
        cls="w-full bg-blue-600 text-white py-2.5 rounded-lg font-semibold text-sm hover:bg-blue-700 transition-colors",
    )


def _error_msg(msg: str):
    return Div(msg, cls="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg text-center") if msg else ""


def _success_msg(msg: str):
    return Div(msg, cls="text-sm text-green-600 bg-green-50 px-3 py-2 rounded-lg text-center") if msg else ""


def _divider():
    return Div(
        Div(cls="flex-1 h-px bg-gray-200"),
        Span("or", cls="px-3 text-xs text-gray-400"),
        Div(cls="flex-1 h-px bg-gray-200"),
        cls="flex items-center my-4",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@ar("/register")
def register(session, email: str = "", password: str = "", display_name: str = "", error: str = ""):
    # POST
    if email and password:
        if len(password) < 8:
            return RedirectResponse("/register?error=Password+must+be+at+least+8+characters", status_code=303)
        from utils.auth import create_user
        user = create_user(email=email, password=password, display_name=display_name or None)
        if not user:
            return RedirectResponse("/register?error=Email+already+registered", status_code=303)
        _session_login(session, user)
        return RedirectResponse("/", status_code=303)

    # GET
    if session.get("user"):
        return RedirectResponse("/")
    parts = [H2("Create Account", cls="text-xl font-bold text-center mb-4")]
    if error:
        parts.append(_error_msg(error))
    if _oauth_enabled:
        parts.append(_google_btn("Sign up with Google"))
        parts.append(_divider())
    parts.append(
        Form(
            _text_input("email", "Email", input_type="email", required=True, autofocus=True),
            _pw_input("password", "Password (min 8 characters)", minlength="8"),
            _text_input("display_name", "Display name (optional)"),
            _submit_btn("Create Account"),
            method="post", action="/register", cls="flex flex-col gap-3",
        )
    )
    parts.append(Div("Already have an account? ", A("Sign in", href="/signin", cls="text-blue-600 hover:underline"), cls="text-center text-sm text-gray-500 mt-4"))
    return _auth_layout("Register", parts)


@ar("/signin")
def signin(session, email: str = "", password: str = "", error: str = "", msg: str = ""):
    # POST
    if email and password:
        from utils.auth import authenticate
        user = authenticate(email, password)
        if not user:
            return RedirectResponse("/signin?error=Invalid+email+or+password", status_code=303)
        _session_login(session, user)
        return RedirectResponse("/", status_code=303)

    # GET
    if session.get("user"):
        return RedirectResponse("/")
    parts = [H2("Sign In", cls="text-xl font-bold text-center mb-4")]
    if msg:
        parts.append(_success_msg(msg))
    if error:
        parts.append(_error_msg(error))
    if _oauth_enabled:
        parts.append(_google_btn("Sign in with Google"))
        parts.append(_divider())
    parts.append(
        Form(
            _text_input("email", "Email", input_type="email", required=True, autofocus=True),
            _pw_input("password", "Password"),
            _submit_btn("Sign In"),
            method="post", action="/signin", cls="flex flex-col gap-3",
        )
    )
    parts.append(Div(A("Forgot password?", href="/forgot", cls="text-blue-600 hover:underline"), cls="text-center text-sm mt-3"))
    parts.append(Div("Don't have an account? ", A("Sign up", href="/register", cls="text-blue-600 hover:underline"), cls="text-center text-sm text-gray-500 mt-3"))
    return _auth_layout("Sign In", parts)


@ar("/forgot")
def forgot(session, email: str = "", error: str = "", msg: str = ""):
    if email:
        from utils.auth import create_password_reset_token
        create_password_reset_token(email)
        return RedirectResponse("/forgot?msg=If+that+email+is+registered+you+will+receive+a+reset+link", status_code=303)

    if session.get("user"):
        return RedirectResponse("/")
    parts = [H2("Forgot Password", cls="text-xl font-bold text-center mb-4")]
    if msg:
        parts.append(_success_msg(msg))
    if error:
        parts.append(_error_msg(error))
    parts.append(P("Enter your email and we'll send you a reset link.", cls="text-sm text-gray-500 text-center mb-3"))
    parts.append(
        Form(
            _text_input("email", "Enter your email", input_type="email", required=True, autofocus=True),
            _submit_btn("Send Reset Link"),
            method="post", action="/forgot", cls="flex flex-col gap-3",
        )
    )
    parts.append(Div(A("Back to sign in", href="/signin", cls="text-blue-600 hover:underline"), cls="text-center text-sm mt-4"))
    return _auth_layout("Forgot Password", parts)


@ar("/reset")
def reset(session, token: str = "", password: str = "", confirm_password: str = "", error: str = ""):
    if token and password:
        if len(password) < 8:
            return RedirectResponse(f"/reset?token={token}&error=Password+must+be+at+least+8+characters", status_code=303)
        if password != confirm_password:
            return RedirectResponse(f"/reset?token={token}&error=Passwords+do+not+match", status_code=303)
        from utils.auth import verify_and_consume_reset_token, update_password
        user = verify_and_consume_reset_token(token)
        if not user:
            return RedirectResponse("/forgot?error=Reset+link+is+invalid+or+expired", status_code=303)
        update_password(user["user_id"], password)
        return RedirectResponse("/signin?msg=Password+reset+successful", status_code=303)

    if not token:
        return RedirectResponse("/forgot")
    parts = [H2("Set New Password", cls="text-xl font-bold text-center mb-4")]
    if error:
        parts.append(_error_msg(error))
    parts.append(
        Form(
            Input(type="hidden", name="token", value=token),
            _pw_input("password", "New password (min 8)", minlength="8", autofocus=True),
            _pw_input("confirm_password", "Confirm new password", minlength="8"),
            _submit_btn("Reset Password"),
            method="post", action="/reset", cls="flex flex-col gap-3",
        )
    )
    return _auth_layout("Reset Password", parts)


@ar("/profile")
def profile(session):
    user = session.get("user")
    if not user:
        return RedirectResponse("/signin")
    from components.layout import Shell
    return Shell(
        H1("Profile", cls="text-2xl font-bold text-gray-800 mb-6"),
        Div(
            Div(
                Div(user.get("display_name", "U")[0].upper(), cls="w-16 h-16 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-2xl font-bold"),
                Div(
                    P(user.get("display_name", ""), cls="text-lg font-semibold text-gray-800"),
                    P(user.get("email", ""), cls="text-sm text-gray-500"),
                    cls="ml-4",
                ),
                cls="flex items-center mb-6",
            ),
            Div(
                Div(P("User ID", cls="text-xs text-gray-500"), P(user.get("user_id", ""), cls="text-sm font-mono text-gray-700")),
                cls="bg-gray-50 rounded-lg p-4 mb-4",
            ),
            A("Sign Out", href="/logout", cls="text-sm text-red-600 hover:underline"),
            cls="bg-white rounded-lg p-6 border border-gray-200 max-w-lg",
        ),
    )


@ar("/logout")
def logout(session):
    session.pop("user", None)
    return RedirectResponse("/signin")


# ---------------------------------------------------------------------------
# Google OAuth routes
# ---------------------------------------------------------------------------
if _oauth_enabled:
    @ar("/login")
    async def google_login(request):
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("host", request.url.netloc)
        redirect_uri = f"{scheme}://{host}/auth/callback"
        return await _authlib_oauth.google.authorize_redirect(request, redirect_uri)

    @ar("/auth/callback")
    async def auth_callback(request, session):
        try:
            token = await _authlib_oauth.google.authorize_access_token(request)
        except Exception as e:
            return RedirectResponse(f"/signin?error=Google+login+failed:+{e}")

        userinfo = token.get("userinfo", {})
        if not userinfo:
            userinfo = await _authlib_oauth.google.userinfo(token=token)

        google_id = userinfo.get("sub", "")
        email = userinfo.get("email", "")
        name = userinfo.get("name", "")

        if not email:
            return RedirectResponse("/signin?error=Google+did+not+provide+email")

        from utils.auth import get_user_by_google_id, get_user_by_email, create_user, link_google_id

        user = get_user_by_google_id(google_id) if google_id else None
        if not user:
            user = get_user_by_email(email)
            if user and google_id:
                link_google_id(email, google_id)
            elif not user:
                user = create_user(email=email, google_id=google_id, display_name=name)

        if user:
            _session_login(session, user)
        else:
            return RedirectResponse("/signin?error=Could+not+create+account")

        return RedirectResponse("/")
else:
    @ar("/login")
    def google_login_stub():
        return RedirectResponse("/signin")
