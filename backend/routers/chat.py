import json
import urllib.parse
from typing import Annotated, Literal, TypedDict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain.mcp import MCPAdapter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from backend.database import close_db_connection, get_db_connection
from backend.mcp_server import current_user_id, mcp
from backend.models import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["AI Agent"])

SALES_TOOL_NAMES = {
    "search_catalog",
    "compare_products",
    "view_cart",
    "add_to_cart",
    "get_order_history",
    "cancel_order",
}
SUPPORT_TOOL_NAMES = {"search_knowledge_base"}


# =====================================================================
# 1. HTML CARD RENDERERS (BUILT FROM MCP structured_content ARTIFACTS)
# =====================================================================

def _minify(raw_html: str) -> str:
    return " ".join(line.strip() for line in raw_html.splitlines() if line.strip())


def _avatar_url(name: str) -> str:
    return f"https://ui-avatars.com/api/?name={urllib.parse.quote(name)}&background=random"


def render_ui_block(structured: dict) -> str:
    """Converts compact MCP structured_content JSON into minified HTML cards for the frontend."""
    ui_type = structured.get("ui_type")

    if ui_type == "products":
        cards = ["<div style='display:flex; flex-direction:column; gap:10px; margin-top:8px;'>"]
        for p in structured.get("items", []):
            img = p.get("image_url") or _avatar_url(p["product_name"])
            cards.append(
                f"""<div style="display:flex; gap:12px; padding:12px; background:rgba(255,255,255,0.85); border:1px solid rgba(0,0,0,0.08); border-radius:14px; align-items:center; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
                    <img src="{img}" style="width:65px; height:65px; object-fit:cover; border-radius:10px; flex-shrink:0;">
                    <div style="flex:1; min-width:0;">
                        <div style="font-size:0.75rem; color:#6366f1; font-weight:bold; text-transform:uppercase;">{p.get('category_name', 'Featured')}</div>
                        <h6 style="margin:2px 0 4px 0; font-size:0.92rem; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{p['product_name']}</h6>
                        <div style="font-weight:800; color:#0f172a; font-size:1.05rem; margin-bottom:6px;">₹{p['price']:,.2f}</div>
                        <button style="background:#0f172a; color:white; border:none; padding:6px 14px; border-radius:8px; font-size:0.8rem; font-weight:600; cursor:pointer;" onclick="widgetAddToCart({p['product_id']})">Add to Cart</button>
                    </div>
                </div>"""
            )
        cards.append("</div>")
        return _minify("".join(cards))

    if ui_type == "comparison":
        cards = ["<div style='display:flex; gap:10px; overflow-x:auto; padding:5px 0; margin-top:5px;'>"]
        for p in structured.get("items", []):
            img = p.get("image_url") or _avatar_url(p["product_name"])
            cards.append(
                f"""<div style="flex:1; min-width:140px; background:rgba(255,255,255,0.85); border:1px solid rgba(0,0,0,0.06); border-radius:12px; padding:12px; text-align:center;">
                    <img src="{img}" style="width:70px; height:70px; object-fit:cover; border-radius:8px; margin-bottom:8px;">
                    <h6 style="font-size:0.85rem; font-weight:bold; margin:0 0 5px 0; height:32px; overflow:hidden;">{p['product_name']}</h6>
                    <p style="color:#6366f1; font-weight:800; font-size:1.1rem; margin:0 0 8px 0;">₹{p['price']:,.2f}</p>
                    <div style="font-size:0.75rem; color:#64748b; margin-bottom:10px;">{p.get('category_name', 'Item')}</div>
                    <button style="background:#0f172a; color:white; border:none; padding:6px 10px; border-radius:6px; width:100%; font-size:0.8rem; cursor:pointer;" onclick="widgetAddToCart({p['product_id']})">Add to Cart</button>
                </div>"""
            )
        cards.append("</div>")
        return _minify("".join(cards))

    if ui_type == "cart":
        cards = ["<div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"]
        for item in structured.get("items", []):
            img = item.get("image_url") or _avatar_url(item["product_name"])
            cards.append(
                f"""<div style="display:flex; gap:10px; padding:8px; background:rgba(255,255,255,0.85); border-radius:10px; align-items:center;">
                    <img src="{img}" style="width:45px; height:45px; object-fit:cover; border-radius:6px;">
                    <div style="flex:1;">
                        <b style="font-size:0.85rem;">{item['product_name']}</b>
                        <div style="font-size:0.75rem; color:#64748b;">Qty: {item['quantity']} × ₹{item['price']:,.2f}</div>
                    </div>
                    <div style="font-weight:bold; color:#6366f1;">₹{item['subtotal']:,.2f}</div>
                </div>"""
            )
        total = structured.get("total", 0)
        cards.append(
            f"""<div style="margin-top:6px; padding-top:8px; border-top:1px dashed #cbd5e1; display:flex; justify-content:space-between;">
                <b>Total:</b> <span style="font-weight:800; color:#0f172a;">₹{total:,.2f}</span>
            </div>
            <a href="cart.html" style="display:block; text-align:center; background:#6366f1; color:white; padding:8px; border-radius:8px; text-decoration:none; font-weight:bold; margin-top:8px;">Go to Checkout</a></div>"""
        )
        return _minify("".join(cards))

    if ui_type == "orders":
        cards = ["<div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"]
        for o in structured.get("orders", []):
            cards.append(
                f"""<div style="background:rgba(255,255,255,0.85); border-left:4px solid #6366f1; padding:8px 12px; border-radius:0 8px 8px 0;">
                    <div style="display:flex; justify-content:space-between;">
                        <b>Order #{o['order_id']}</b>
                        <span style="font-size:0.75rem; font-weight:bold;">{o['status'].upper()}</span>
                    </div>
                    <div style="font-size:0.8rem; color:#475569;">Items: {o.get('items_summary', 'Catalog Items')}</div>
                    <div style="color:#6366f1; font-weight:bold; margin-top:2px;">₹{o['total_amount']:,.2f}</div>
                </div>"""
            )
        cards.append("</div>")
        return _minify("".join(cards))

    return ""


# =====================================================================
# 2. LIGHTWEIGHT CONTEXT HELPERS
# =====================================================================

def get_store_metadata() -> dict:
    conn = get_db_connection()
    if not conn:
        return {"categories": []}
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT DISTINCT category_name FROM products WHERE category_name IS NOT NULL")
        return {"categories": [r["category_name"] for r in cursor.fetchall() if r.get("category_name")]}
    except Exception:
        return {"categories": []}
    finally:
        cursor.close()
        close_db_connection(conn)


def db_get_user_context(user_id: int) -> str:
    if user_id == 0:
        return "Customer: Guest User."
    conn = get_db_connection()
    if not conn:
        return ""
    cursor = conn.cursor(dictionary=True)
    try:
        context_str = f"Customer ID: #{user_id}\n"
        cursor.execute(
            """
            SELECT p.product_name, c.quantity, p.price
            FROM cart c JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = %s
            """,
            (user_id,),
        )
        cart_items = cursor.fetchall()
        if cart_items:
            context_str += "ACTIVE CART: " + ", ".join(
                f"{item['quantity']}x {item['product_name']} (₹{item['price']})" for item in cart_items
            ) + "\n"
        else:
            context_str += "ACTIVE CART: Empty\n"

        cursor.execute(
            "SELECT order_id, status FROM orders WHERE user_id = %s ORDER BY order_date DESC LIMIT 1",
            (user_id,),
        )
        last_order = cursor.fetchone()
        if last_order:
            context_str += f"LAST ORDER: #{last_order['order_id']} ({last_order['status']})\n"
        return context_str
    finally:
        cursor.close()
        close_db_connection(conn)


# =====================================================================
# 3. ASYNC MULTI-AGENT GRAPH CONSUMING IN-PROCESS MCP TOOLS
# =====================================================================

class RouteDefinition(BaseModel):
    next_node: Literal["Sales", "Support"] = Field(
        description="Route to 'Sales' for product browsing, search, recommendations, cart, or orders. Route to 'Support' for greetings, store policies, warranties, or shipping."
    )


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_node: str
    user_id: int


async def supervisor_node(state: AgentState):
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    system_prompt = (
        "Classify user message destination:\n"
        "- 'Sales': Finding/recommending products (phones, laptops, accessories), cart, checkout, orders.\n"
        "- 'Support': Greetings ('hi', 'hello', 'hey'), policies, delivery, returns, FAQs."
    )
    # Send only the latest 4 messages to keep supervisor token overhead minimal
    messages = [{"role": "system", "content": system_prompt}] + state["messages"][-4:]
    response = await llm.with_structured_output(RouteDefinition).ainvoke(messages)
    return {"next_node": response.next_node}


async def sales_node(state: AgentState):
    user_ctx = db_get_user_context(state["user_id"])
    store_meta = get_store_metadata()
    categories_str = ", ".join(store_meta["categories"]) or "Electronics, Smartphones, Laptops, Accessories"

    sales_prompt = f"""You are the AI Shopping Advisor at AI Store.
{user_ctx}
DEPARTMENTS: [{categories_str}]

STRICT RULES:
1. Call `search_catalog` AT MOST ONCE per turn. Combine synonyms into `search_keywords` (e.g. search_keywords='phone mobile smartphone'). Never issue duplicate search calls.
2. Product, comparison, cart, and order cards render automatically on the user's screen. Never output raw HTML.
3. Give a concise, helpful summary of the options and offer to add items to their cart."""

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)

    async with MCPAdapter(mcp) as adapter:
        all_tools = await adapter.list_tools()
        sales_tools = [t for t in all_tools if t.name in SALES_TOOL_NAMES]
        agent = create_react_agent(llm, sales_tools)

        input_messages = [SystemMessage(content=sales_prompt)] + state["messages"][-8:]
        result = await agent.ainvoke({"messages": input_messages})

    return {"messages": result["messages"][len(input_messages):]}


async def support_node(state: AgentState):
    support_prompt = """You are the Customer Support Concierge at AI Store.
- If the customer sends a greeting, greet them warmly and suggest what they can browse.
- If they ask about policies, shipping timelines, warranties, or returns, run `search_knowledge_base` and explain the answer conversationally.
- Never output raw HTML; speak naturally in plain text."""

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)

    async with MCPAdapter(mcp) as adapter:
        all_tools = await adapter.list_tools()
        support_tools = [t for t in all_tools if t.name in SUPPORT_TOOL_NAMES]
        agent = create_react_agent(llm, support_tools)

        input_messages = [SystemMessage(content=support_prompt)] + state["messages"][-8:]
        result = await agent.ainvoke({"messages": input_messages})

    return {"messages": result["messages"][len(input_messages):]}


builder = StateGraph(AgentState)
builder.add_node("Supervisor", supervisor_node)
builder.add_node("Sales", sales_node)
builder.add_node("Support", support_node)

builder.add_edge(START, "Supervisor")
builder.add_conditional_edges(
    "Supervisor",
    lambda state: state["next_node"],
    {"Sales": "Sales", "Support": "Support"},
)
builder.add_edge("Sales", END)
builder.add_edge("Support", END)

memory = MemorySaver()
multi_agent_graph = builder.compile(checkpointer=memory)


# =====================================================================
# 4. SSE STREAMING ENDPOINT
# =====================================================================

@router.post("")
async def process_chat(request: ChatRequest):
    safe_user_id = request.user_id if request.user_id else 0

    async def generate_stream():
        ctx_token = current_user_id.set(safe_user_id)
        config = {"configurable": {"thread_id": str(safe_user_id)}}
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "user_id": safe_user_id,
        }

        try:
            async for event in multi_agent_graph.astream_events(initial_state, config, version="v2"):
                kind = event["event"]
                node_name = event.get("metadata", {}).get("langgraph_node", "")

                # Stream conversational tokens (skip Supervisor structured-output noise)
                if kind == "on_chat_model_stream" and node_name != "Supervisor":
                    chunk = event["data"]["chunk"].content
                    if isinstance(chunk, str) and chunk:
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    if tool_name != "RouteDefinition":
                        yield f"data: {json.dumps({'type': 'thought', 'content': f'Running MCP tool: {tool_name}...'})}\n\n"

                # Intercept ToolMessage.artifact["structured_content"] to render HTML cards
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    artifact = getattr(output, "artifact", None)
                    if isinstance(artifact, dict) and isinstance(artifact.get("structured_content"), dict):
                        html_card = render_ui_block(artifact["structured_content"])
                        if html_card:
                            yield f"data: {json.dumps({'type': 'ui_block', 'content': html_card})}\n\n"

        except Exception as e:
            print("Chat Agent Runtime Error:", str(e))
            yield f"data: {json.dumps({'type': 'text', 'content': f'Encountered an issue: {str(e)}'})}\n\n"
        finally:
            current_user_id.reset(ctx_token)
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")