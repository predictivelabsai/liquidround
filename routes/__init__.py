from routes.auth import ar as auth_router
from routes.home import ar as home_router
from routes.deals import ar as deals_router
from routes.market import ar as market_router
from routes.upload import ar as upload_router
from routes.research import ar as research_router
from routes.api import ar as api_router

all_routers = [auth_router, home_router, deals_router, market_router, upload_router, research_router, api_router]
