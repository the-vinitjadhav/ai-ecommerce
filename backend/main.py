from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.mcp_server import mcp
from backend.routers import auth, cart, chat, orders, products  # match your existing router imports

# Streamable HTTP MCP sub-app (stateless_http=True avoids stale session state on single-instance Render)
mcp_app = mcp.http_app(path="/", transport="streamable-http", stateless_http=True)

app = FastAPI(title="AI E-Commerce Platform", lifespan=mcp_app.lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing REST + SSE routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(chat.router)

# Mount MCP server at /mcp (single process, single $PORT on Render)
app.mount("/mcp", mcp_app)