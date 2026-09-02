# 🛒 AI-Powered E-Commerce Platform & Multi-Agent Assistant

A modern, full-stack e-commerce platform featuring an autonomous, multi-agent AI shopping assistant. Built with FastAPI, LangGraph, and MySQL, this project demonstrates advanced LLM orchestration, highly optimized RAG (Retrieval-Augmented Generation), and real-time Server-Sent Events (SSE) streaming.

Designed to operate within strict PaaS constraints (512MB RAM limits) and third-party API rate limits, this architecture bypasses heavy machine learning dependencies in favor of lightweight, custom-built algorithms.

## ✨ Key Engineering Features

* **Multi-Agent Orchestration (LangGraph):** Utilizes a fast Supervisor model to instantly classify user intent, routing requests to specialized "Sales" or "Support" agents to reduce latency and optimize API token usage.
* **Zero-RAM Lexical RAG Engine:** Replaced resource-heavy vector databases (FAISS/Pinecone) and 3GB PyTorch dependencies with a highly optimized, native-Python lexical search. Dynamically fetches real-time store policies from the MySQL database with zero extra RAM footprint.
* **Intelligent Catalog Search:** Implements a fuzzy-matching search algorithm with synonym expansion. The AI understands informal queries (e.g., "mobiles", "kicks") and maps them to strict database schema categories without hallucinations.
* **Deterministic Autonomous Tools:** Features 14 strict SQL-bound tools (Add to Cart, View Order History, Compare Products, Cancel Order) that the LLM executes autonomously, ensuring safe database interactions without SQL injection vulnerabilities.
* **Asynchronous SSE Streaming:** A decoupled UI streaming architecture that pushes LangGraph "thought processes," natural language text tokens, and rich HTML UI cards to the frontend in real-time, while feeding compressed text summaries back to the LLM to prevent TPM (Tokens Per Minute) rate-limit exhaustion.

## 🛠️ Technology Stack

| Component | Technology |
| --- | --- |
| **Backend Framework** | FastAPI, Uvicorn, Python 3.10+ |
| **AI / LLM Orchestration** | LangGraph, LangChain, Groq API (gpt-oss-120b / gpt-oss-20b) |
| **Database** | MySQL (Aiven), `mysql-connector-python` |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript, Bootstrap 5 |
| **Authentication** | JWT (JSON Web Tokens), bcrypt |
| **Streaming Protocol** | Server-Sent Events (SSE) |

## 🏗️ Multi-Agent Architecture Flow

1. **User Input:** The user types a query in the frontend chat widget.
2. **Supervisor Node:** A fast, low-temperature LLM evaluates the prompt.
* *If shopping/cart/orders:* Routes to **Sales Node**.
* *If policies/greeting/FAQ:* Routes to **Support Node**.


3. **Agent Execution:**
* The **Sales Agent** uses SQL tools to search inventory, compare items, and manage the cart.
* The **Support Agent** uses the Lexical RAG tool to pull live store policies from the database.


4. **Decoupled UI Streaming:** The tool executions generate rich HTML blocks sent directly to the user's screen via SSE, while returning tiny text summaries back to the LLM to maintain conversation memory securely and cheaply.

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/the-vinitjadhav/ai-ecommerce-platform.git
cd ai-ecommerce-platform

```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

```

### 4. Environment Variables

Create a `.env` file in the root directory and add your credentials:

```env
# Database Configuration (Aiven or Local)
DB_HOST=your_mysql_host
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name
DB_PORT=3306

# Groq API Configuration
GROQ_API_KEY=your_groq_api_key

# Authentication
SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256

```

### 5. Database Initialization

Execute the provided SQL schemas in your MySQL database to create the `users`, `products`, `cart`, `orders`, `order_items`, and `store_policies` tables. Make sure to populate the `store_policies` table with initial data.

### 6. Run the Application

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

```

The backend API will be available at `http://localhost:8000`. Serve the frontend `index.html` file using any standard local web server (e.g., Live Server extension or `python -m http.server`).

---

**Author:** [Vinit Jadhav](https://www.google.com/search?q=https://github.com/the-vinitjadhav)
