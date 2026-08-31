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
        "is_admin": bool(user.get("is_admin")),
    }


_GOOGLE_SVG = '<svg width="18" height="18" viewBox="0 0 18 18"><path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/><path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/><path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9s.38 1.572.957 3.042l3.007-2.332z" fill="#FBBC05"/><path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/></svg>'


def _google_btn(label: str):
    return A(
        NotStr(_GOOGLE_SVG), label,
        href="/login",
        cls="flex items-center justify-center gap-2 w-full text-white py-2.5 rounded-lg font-semibold text-sm transition-colors no-underline",
        style="background:#3B82F6;",
    )


def _auth_layout(title: str, card_parts: list):
    return (
        Title(f"{title} — LiquidRound"),
        Script(src="https://cdn.tailwindcss.com"),
        Style("html,body{margin:0;} input::placeholder{color:#64748b;}"),
        Main(
            Div(
                Div(
                    Span("◈", cls="text-3xl", style="color:#F59E0B;"),
                    P("LiquidRound", cls="text-xl font-bold mt-2", style="color:#E5E7EB;"),
                    P("M&A Research Platform", cls="text-xs", style="color:#94A3B8;"),
                    cls="text-center mb-6",
                ),
                Div(*card_parts, cls="w-full max-w-sm rounded-xl p-8 shadow-lg", style="background:#111A2E; border:1px solid #1E293B;"),
                P("Predictive Labs Ltd", cls="text-xs mt-6", style="color:#475569;"),
                cls="flex flex-col items-center justify-center min-h-screen",
            ),
            style="background:#0B1220;",
        ),
    )


def _pw_input(name: str, placeholder: str, **kw):
    return Input(
        type="password", name=name, placeholder=placeholder, required=True,
        cls="w-full rounded-lg px-3 py-2.5 text-sm focus:outline-none",
        style="background:#0B1220; color:#E5E7EB; border:1px solid #1E293B;",
        **kw,
    )


def _text_input(name: str, placeholder: str, input_type: str = "text", **kw):
    return Input(
        type=input_type, name=name, placeholder=placeholder,
        cls="w-full rounded-lg px-3 py-2.5 text-sm focus:outline-none",
        style="background:#0B1220; color:#E5E7EB; border:1px solid #1E293B;",
        **kw,
    )


def _submit_btn(label: str):
    return Button(
        label, type="submit",
        cls="w-full text-white py-2.5 rounded-lg font-semibold text-sm cursor-pointer",
        style="background:#F59E0B;",
    )


def _error_msg(msg: str):
    return Div(msg, cls="text-sm px-3 py-2 rounded-lg text-center", style="color:#EF4444; background:rgba(239,68,68,0.1);") if msg else ""


def _success_msg(msg: str):
    return Div(msg, cls="text-sm px-3 py-2 rounded-lg text-center", style="color:#10B981; background:rgba(16,185,129,0.1);") if msg else ""


def _divider():
    return Div(
        Div(cls="flex-1 h-px", style="background:#1E293B;"),
        Span("or", cls="px-3 text-xs", style="color:#64748b;"),
        Div(cls="flex-1 h-px", style="background:#1E293B;"),
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
        return RedirectResponse("/app", status_code=303)

    # GET
    if session.get("user"):
        return RedirectResponse("/app")
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
    parts.append(Div("Already have an account? ", A("Sign in", href="/signin", style="color:#F59E0B;"), cls="text-center text-sm", style="color:#94A3B8; mt-4"))
    return _auth_layout("Register", parts)


@ar("/signin")
def signin(session, request, email: str = "", password: str = "", role: str = "", error: str = "", msg: str = "", next: str = ""):
    next_url = next or request.query_params.get("next", "")
    redirect_to = next_url if next_url.startswith("/app") else (f"/app?role={role}" if role else "/app")
    # POST
    if email and password:
        from utils.auth import authenticate
        user = authenticate(email, password)
        if not user:
            qs = f"error=Invalid+email+or+password&role={role}" if role else "error=Invalid+email+or+password"
            if next_url:
                qs += f"&next={next_url}"
            return RedirectResponse(f"/signin?{qs}", status_code=303)
        _session_login(session, user)
        return RedirectResponse(redirect_to, status_code=303)

    # GET
    if session.get("user"):
        return RedirectResponse(redirect_to)
    parts = [H2("Sign In", cls="text-xl font-bold text-center mb-4")]
    if msg:
        parts.append(_success_msg(msg))
    if error:
        parts.append(_error_msg(error))
    if _oauth_enabled:
        parts.append(_google_btn("Sign in with Google"))
        parts.append(_divider())
    action_params = []
    if role:
        action_params.append(f"role={role}")
    if next_url:
        action_params.append(f"next={next_url}")
    action = "/signin?" + "&".join(action_params) if action_params else "/signin"
    parts.append(
        Form(
            _text_input("email", "Email", input_type="email", required=True, autofocus=True,
                        autocomplete="username"),
            _pw_input("password", "Password", autocomplete="current-password"),
            _submit_btn("Sign In"),
            method="post", action=action, cls="flex flex-col gap-3",
        )
    )
    parts.append(Div(A("Forgot password?", href="/forgot", style="color:#F59E0B;"), cls="text-center text-sm mt-3"))
    parts.append(Div("Don't have an account? ", A("Sign up", href="/register", style="color:#F59E0B;"), cls="text-center text-sm", style="color:#94A3B8; mt-3"))
    return _auth_layout("Sign In", parts)


@ar("/forgot")
def forgot(request, session, email: str = "", error: str = "", msg: str = ""):
    if email:
        from utils.auth import create_password_reset_token, send_password_reset_email
        token = create_password_reset_token(email)
        if token:
            from utils.security import public_base_url
            send_password_reset_email(email, token, public_base_url())
        return RedirectResponse("/forgot?msg=If+that+email+is+registered+you+will+receive+a+reset+link", status_code=303)

    if session.get("user"):
        return RedirectResponse("/")
    parts = [H2("Forgot Password", cls="text-xl font-bold text-center mb-4")]
    if msg:
        parts.append(_success_msg(msg))
    if error:
        parts.append(_error_msg(error))
    parts.append(P("Enter your email and we'll send you a reset link.", cls="text-sm text-center mb-3", style="color:#94A3B8;"))
    parts.append(
        Form(
            _text_input("email", "Enter your email", input_type="email", required=True, autofocus=True),
            _submit_btn("Send Reset Link"),
            method="post", action="/forgot", cls="flex flex-col gap-3",
        )
    )
    parts.append(Div(A("Back to sign in", href="/signin", style="color:#F59E0B;"), cls="text-center text-sm mt-4"))
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
def profile(session, msg: str = "", error: str = ""):
    user = session.get("user")
    if not user:
        return RedirectResponse("/signin")

    from utils.preferences import get_preferences
    prefs = get_preferences(user["user_id"]) or {}

    return _profile_page(user, prefs, msg=msg, error=error)


# ---------------------------------------------------------------------------
# Profile page builder
# ---------------------------------------------------------------------------
SECTORS = [
    "Technology", "Healthcare", "Financial Services", "Industrials",
    "Energy / Cleantech", "Consumer / Retail", "Real Estate",
    "Media / Entertainment", "Business Services", "Education / EdTech",
]
GEOGRAPHIES = [
    "UK & Ireland", "Nordics", "DACH", "Benelux", "Baltics",
    "Southern Europe", "CEE", "North America", "Rest of World",
]
DEAL_TYPES = [
    "Acquisition", "Divestiture", "Merger", "IPO / Listing",
    "Growth Equity", "Secondary / Buyout", "Recapitalization",
]
CURRENCIES = [("EUR", "EUR €"), ("GBP", "GBP £"), ("USD", "USD $")]
LANGUAGES = [
    ("en", "English"), ("de", "Deutsch"), ("fr", "Français"),
    ("es", "Español"), ("et", "Eesti"), ("lv", "Latviešu"),
    ("lt", "Lietuvių"), ("pl", "Polski"), ("sv", "Svenska"),
]


def _profile_page(user, prefs, msg="", error=""):
    uid = user["user_id"]
    email = user.get("email", "")
    name = user.get("display_name", "")

    def _pill_checks(name, options, selected):
        selected = selected or []
        return Div(
            *[Label(
                Input(type="checkbox", name=name, value=opt, checked=(opt in selected), cls="hidden peer"),
                Span(opt, cls="inline-block px-3 py-1.5 text-xs rounded-full border border-gray-300 cursor-pointer peer-checked:bg-blue-600 peer-checked:text-white peer-checked:border-blue-600 transition-colors"),
            ) for opt in options],
            cls="flex flex-wrap gap-2",
        )

    def _toggle(name, label, checked=True):
        return Label(
            Div(
                Input(type="checkbox", name=name, value="1", checked=checked, cls="sr-only peer"),
                Div(cls="w-9 h-5 bg-gray-300 rounded-full peer-checked:bg-blue-600 transition-colors relative after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:w-4 after:h-4 after:bg-white after:rounded-full after:transition-transform peer-checked:after:translate-x-4"),
                cls="relative",
            ),
            Span(label, cls="text-sm text-gray-700"),
            cls="flex items-center gap-3 cursor-pointer",
        )

    def _section(title, *children):
        return Div(
            H3(title, cls="text-sm font-semibold text-gray-800 mb-3 pb-2 border-b border-gray-200"),
            *children,
            cls="bg-white rounded-xl border border-gray-200 p-5 mb-4",
        )

    def _field(label_text, inp):
        return Div(Label(label_text, cls="text-xs font-medium text-gray-500 mb-1 block"), inp)

    def _inp(name, value="", placeholder="", **kw):
        return Input(type="text", name=name, value=value or "", placeholder=placeholder,
                     cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none", **kw)

    def _num(name, value=None, placeholder=""):
        return Input(type="number", name=name, value=str(value) if value else "", placeholder=placeholder,
                     cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none")

    def _select(name, options, selected=""):
        return Select(
            *[Option(lbl, value=val, selected=(val == selected)) for val, lbl in options],
            name=name, cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none",
        )

    account = _section("Account",
        Div(
            Div(user.get("display_name", "U")[0].upper(),
                cls="w-12 h-12 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-lg font-bold"),
            Div(P(name, cls="text-sm font-semibold text-gray-800"), P(email, cls="text-xs text-gray-500")),
            cls="flex items-center gap-3 mb-4",
        ),
        Form(
            Div(
                _field("Display Name", _inp("display_name", name, "Your name")),
                _field("Email", Input(type="email", value=email, disabled=True, cls="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500")),
                cls="grid grid-cols-2 gap-3",
            ),
            Div(
                _field("Company", _inp("company_name", prefs.get("company_name", ""), "Firm name")),
                _field("Job Title", _inp("job_title", prefs.get("job_title", ""), "e.g. Managing Director")),
                cls="grid grid-cols-2 gap-3 mt-3",
            ),
            Div(
                _field("Phone", _inp("phone", prefs.get("phone", ""), "+44 ...")),
                _field("Country", _inp("country", prefs.get("country", ""), "e.g. UK")),
                _field("City", _inp("city", prefs.get("city", ""), "e.g. London")),
                cls="grid grid-cols-3 gap-3 mt-3",
            ),
            Div(
                _field("Currency", _select("currency", CURRENCIES, prefs.get("currency", "EUR"))),
                _field("Language", _select("language", LANGUAGES, prefs.get("language", "en"))),
                cls="grid grid-cols-2 gap-3 mt-3",
            ),
            Div(
                Button("Save Account", type="submit",
                       cls="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"),
                Span(id="account-status", cls="text-xs ml-3"),
                cls="flex items-center mt-4",
            ),
            id="account-form", hx_post="/profile/account", hx_target="#account-status", hx_swap="innerHTML",
        ),
        Div(
            H4("Change Password", cls="text-xs font-semibold text-gray-700 mb-2 mt-4 pt-3 border-t border-gray-100"),
            Form(
                Div(
                    Input(type="password", name="current_password", placeholder="Current password",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"),
                    Input(type="password", name="new_password", placeholder="New password (min 8)", minlength="8",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"),
                    cls="grid grid-cols-2 gap-3",
                ),
                Div(
                    Button("Update Password", type="submit",
                           cls="bg-gray-700 text-white px-4 py-2 rounded-lg text-xs font-semibold hover:bg-gray-800 transition-colors"),
                    Span(id="pw-status", cls="text-xs ml-3"),
                    cls="flex items-center mt-3",
                ),
                id="pw-form", hx_post="/profile/password", hx_target="#pw-status", hx_swap="innerHTML",
            ),
        ),
    )

    deal_prefs = _section("Deal Preferences",
        Form(
            Div(
                _field("Deal Size Min (EUR)", _num("deal_size_min", prefs.get("deal_size_min_eur"), "e.g. 1000000")),
                _field("Deal Size Max (EUR)", _num("deal_size_max", prefs.get("deal_size_max_eur"), "e.g. 50000000")),
                cls="grid grid-cols-2 gap-3",
            ),
            Div(
                P("Preferred Sectors", cls="text-xs font-medium text-gray-500 mt-4 mb-2"),
                _pill_checks("sectors", SECTORS, prefs.get("preferred_sectors")),
            ),
            Div(
                P("Preferred Geographies", cls="text-xs font-medium text-gray-500 mt-4 mb-2"),
                _pill_checks("geographies", GEOGRAPHIES, prefs.get("preferred_geographies")),
            ),
            Div(
                P("Deal Types", cls="text-xs font-medium text-gray-500 mt-4 mb-2"),
                _pill_checks("deal_types", DEAL_TYPES, prefs.get("preferred_deal_types")),
            ),
            Div(
                _field("Target Revenue Min (EUR)", _num("rev_min", prefs.get("target_revenue_min_eur"), "e.g. 500000")),
                _field("Target Revenue Max (EUR)", _num("rev_max", prefs.get("target_revenue_max_eur"), "e.g. 20000000")),
                cls="grid grid-cols-2 gap-3 mt-4",
            ),
            Div(
                _field("Target EBITDA Min (EUR)", _num("ebitda_min", prefs.get("target_ebitda_min_eur"), "e.g. 100000")),
                _field("Target EBITDA Max (EUR)", _num("ebitda_max", prefs.get("target_ebitda_max_eur"), "e.g. 5000000")),
                cls="grid grid-cols-2 gap-3 mt-3",
            ),
            Div(
                Button("Save Deal Preferences", type="submit",
                       cls="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"),
                Span(id="deal-status", cls="text-xs ml-3"),
                cls="flex items-center mt-4",
            ),
            id="deal-form", hx_post="/profile/deals", hx_target="#deal-status", hx_swap="innerHTML",
        ),
    )

    notifs = _section("Notifications",
        Form(
            Div(
                _toggle("notify_new_deals", "New deals matching my criteria", prefs.get("notify_new_deals", True)),
                _toggle("notify_price_changes", "Valuation changes on tracked companies", prefs.get("notify_price_changes", True)),
                _toggle("notify_weekly_digest", "Weekly market digest email", prefs.get("notify_weekly_digest", True)),
                cls="flex flex-col gap-4",
            ),
            Div(
                Button("Save Notifications", type="submit",
                       cls="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"),
                Span(id="notif-status", cls="text-xs ml-3"),
                cls="flex items-center mt-4",
            ),
            id="notif-form", hx_post="/profile/notifications", hx_target="#notif-status", hx_swap="innerHTML",
        ),
    )

    return (
        Title("Profile & Preferences — LiquidRound"),
        Script(src="https://cdn.tailwindcss.com"),
        Style("html, body { background: #F9FAFB !important; }"),
        Main(
            Div(
                Div(
                    A("← Back to app", href="/app", cls="text-xs text-blue-600 hover:underline"),
                    H1("Profile & Preferences", cls="text-xl font-bold text-gray-800 mt-2"),
                    P("Manage your account, deal criteria, and notification settings.", cls="text-sm text-gray-500 mt-1 mb-5"),
                    cls="mb-2",
                ),
                *(([_success_msg(msg)] if msg else []) + ([_error_msg(error)] if error else [])),
                account,
                deal_prefs,
                notifs,
                Div(
                    A("Sign Out", href="/logout", cls="text-sm text-red-500 hover:underline"),
                    cls="text-center py-4",
                ),
                cls="max-w-2xl mx-auto w-full px-4 py-8",
            ),
            cls="bg-gray-50 min-h-screen",
        ),
    )


# ---------------------------------------------------------------------------
# Profile POST endpoints (HTMX)
# ---------------------------------------------------------------------------
@ar("/profile/account")
def profile_account(session, display_name: str = "", company_name: str = "",
                    job_title: str = "", phone: str = "", country: str = "",
                    city: str = "", currency: str = "EUR", language: str = "en"):
    user = session.get("user")
    if not user:
        return Span("Not signed in", cls="text-red-600")
    uid = user["user_id"]

    if display_name and display_name != user.get("display_name"):
        from utils.auth import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE liquidround.users SET display_name = %s, updated_at = NOW() WHERE user_id = %s",
                        (display_name, uid))
        session["user"]["display_name"] = display_name

    from utils.preferences import upsert_account
    ok = upsert_account(uid, company_name=company_name, job_title=job_title,
                        phone=phone, country=country, city=city,
                        currency=currency, language=language)
    if ok:
        return Span("Saved ✓", cls="text-green-600")
    return Span("Error saving", cls="text-red-600")


@ar("/profile/password")
def profile_password(session, current_password: str = "", new_password: str = ""):
    user = session.get("user")
    if not user:
        return Span("Not signed in", cls="text-red-600")
    if not current_password or not new_password:
        return Span("Both fields required", cls="text-red-600")
    if len(new_password) < 8:
        return Span("Min 8 characters", cls="text-red-600")

    from utils.auth import authenticate, update_password
    authed = authenticate(user["email"], current_password)
    if not authed:
        return Span("Current password incorrect", cls="text-red-600")
    update_password(user["user_id"], new_password)
    return Span("Password updated ✓", cls="text-green-600")


@ar("/profile/deals")
async def profile_deals(request, session):
    user = session.get("user")
    if not user:
        return Span("Not signed in", cls="text-red-600")

    form = await request.form()

    def _float(key):
        v = form.get(key, "")
        try:
            return float(v) if v else None
        except ValueError:
            return None

    from utils.preferences import upsert_deal_prefs
    ok = upsert_deal_prefs(
        user["user_id"],
        deal_size_min=_float("deal_size_min"),
        deal_size_max=_float("deal_size_max"),
        sectors=form.getlist("sectors"),
        geographies=form.getlist("geographies"),
        deal_types=form.getlist("deal_types"),
        rev_min=_float("rev_min"),
        rev_max=_float("rev_max"),
        ebitda_min=_float("ebitda_min"),
        ebitda_max=_float("ebitda_max"),
    )
    if ok:
        return Span("Saved ✓", cls="text-green-600")
    return Span("Error saving", cls="text-red-600")


@ar("/profile/notifications")
async def profile_notifications(request, session):
    user = session.get("user")
    if not user:
        return Span("Not signed in", cls="text-red-600")

    form = await request.form()
    from utils.preferences import upsert_notifications
    ok = upsert_notifications(
        user["user_id"],
        notify_new_deals="notify_new_deals" in form,
        notify_price_changes="notify_price_changes" in form,
        notify_weekly_digest="notify_weekly_digest" in form,
    )
    if ok:
        return Span("Saved ✓", cls="text-green-600")
    return Span("Error saving", cls="text-red-600")


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
        from utils.security import public_base_url
        redirect_uri = f"{public_base_url()}/auth/callback"
        return await _authlib_oauth.google.authorize_redirect(request, redirect_uri)

    @ar("/auth/callback")
    async def auth_callback(request, session):
        try:
            token = await _authlib_oauth.google.authorize_access_token(request)
        except Exception:
            return RedirectResponse("/signin?error=Google+login+failed")

        userinfo = token.get("userinfo", {})
        if not userinfo:
            userinfo = await _authlib_oauth.google.userinfo(token=token)

        google_id = userinfo.get("sub", "")
        email = userinfo.get("email", "")
        name = userinfo.get("name", "")
        email_verified = userinfo.get("email_verified")

        from utils.auth import resolve_google_user
        try:
            user = resolve_google_user(
                google_id=google_id,
                email=email,
                display_name=name,
                email_verified=email_verified,
            )
        except ValueError as exc:
            error = str(exc).replace(" ", "+")
            return RedirectResponse(f"/signin?error={error}")
        if user:
            _session_login(session, user)
        else:
            return RedirectResponse("/signin?error=Could+not+create+account")

        return RedirectResponse("/app")
else:
    @ar("/login")
    def google_login_stub():
        return RedirectResponse("/signin")


# ---------------------------------------------------------------------------
# JSON API endpoints for the landing-page sign-in modal
# ---------------------------------------------------------------------------

@ar("/auth/login")
def api_login(session, email: str = "", password: str = ""):
    if not email or not password:
        return {"ok": False, "error": "Email and password required"}
    from utils.auth import authenticate
    user = authenticate(email, password)
    if not user:
        return {"ok": False, "error": "Invalid email or password"}
    _session_login(session, user)
    return {"ok": True}


@ar("/auth/register")
def api_register(session, email: str = "", password: str = "", display_name: str = ""):
    if not email or not password:
        return {"ok": False, "error": "Email and password required"}
    if len(password) < 8:
        return {"ok": False, "error": "Password must be at least 8 characters"}
    from utils.auth import create_user
    user = create_user(email=email, password=password, display_name=display_name or None)
    if not user:
        return {"ok": False, "error": "Email already registered"}
    _session_login(session, user)
    return {"ok": True}


@ar("/auth/forgot")
def api_forgot(request, email: str = ""):
    if not email:
        return {"ok": False, "error": "Email required"}
    from utils.auth import create_password_reset_token, send_password_reset_email
    token = create_password_reset_token(email)
    if token:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("host", request.url.netloc)
        send_password_reset_email(email, token, f"{scheme}://{host}")
    return {"ok": True, "message": "Reset link sent if account exists"}
