# 🤖 AI-Powered E-Commerce Platform

A modern, full-stack e-commerce application integrated with an autonomous AI shopping assistant. This project demonstrates how a Large Language Model (LLM) can safely and deterministically interact with a relational database to drive conversational sales, manage shopping carts, and handle post-purchase operations like tracking and cancellations.

## ✨ Key Features

* **13-Tool Agentic Function Calling:** Powered by Meta's Llama 3.3 70B, the AI acts as an intent router. It executes specific database actions—like dynamic product searches, in-chat checkouts, and bulk order cancellations—without generating raw conversational filler.
* **90%+ Token & Cost Optimization:** The LLM is strictly constrained from generating heavy HTML markup. It outputs tiny, structured JSON payloads (10–30 tokens) that the Python backend parses and renders into deterministic UI components.
* **Sub-Second Performance:** Combining Groq's LPU inference acceleration with FastAPI's asynchronous event loop yields total end-to-end latency (User Prompt ➔ LLM Tool Call ➔ SQL Execution ➔ UI Render) of just **~300–600ms**.
* **Zero-Trust Security:** Mitigates prompt injection and cross-account manipulation ("Ghost Carts") by blinding the AI to user IDs. The backend extracts JWT tokens and injects verified authentication states directly into the SQL queries.
* **Atomic Database Transactions:** Complex operations, such as entire cart checkouts and inventory restocking, are executed via atomic MySQL transaction loops (`commit`/`rollback`) to guarantee inventory synchronization.

## 🛠️ Tech Stack

* **Frontend:** Vanilla JavaScript, HTML5, Bootstrap 5
* **Backend API:** Python, FastAPI, Uvicorn
* **Database:** MySQL 
* **AI Engine:** Meta Llama 3.3 70B (via Groq API)
* **Cloud Architecture:** Vercel (Edge CDN), Render (Backend Compute), Aiven (Managed MySQL)

## 🏗️ Architecture Flow

1. **Client Request:** The user interacts with the chat widget; frontend sends payload + JWT to the backend.
2. **Intent Routing:** FastAPI sends the conversational context and a strict 13-tool JSON schema to the Groq API.
3. **Parameter Extraction:** The LLM bypasses text generation, selecting the appropriate tool and extracting structured arguments (e.g., `product_name`, `quantity`).
4. **Deterministic Execution:** Python parses the JSON, validates arguments, runs parameterized SQL queries against MySQL, and safely formats the response.
5. **UI Update:** The backend returns raw HTML snippets or Markdown strings to update the client's chat interface.

## 🚀 Local Setup & Installation

### Prerequisites
* Python 3.9+
* MySQL Server
* Groq API Key

### 1. Clone the Repository
```bash
git clone [https://github.com/the-vinitjadhav/ai-ecommerce.git](https://github.com/the-vinitjadhav/ai-ecommerce.git)
cd ai-ecommerce
