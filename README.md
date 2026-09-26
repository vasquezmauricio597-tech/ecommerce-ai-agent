E-commerce AI Agent
Intelligent e-commerce agent built with Python, FastAPI, Gemini, and SQLite.

The project combines a conversational agent with business tools to query products, manage a shopping cart, and execute a transactional checkout.

The goal is to demonstrate the construction of a backend application with AI integration, data persistence, business logic, agent tools, conversational sessions, and automated testing.

🚀 Key Features
🤖 Conversational agent powered by Gemini

🔎 Tool-based product search

🛒 Complete cart management

📦 Stock control

💳 Transactional checkout

🧾 Order creation and querying

💾 Data persistence with SQLite

🧠 Conversational sessions

🔧 Specialized tools for the agent

🌐 REST API with FastAPI

📊 Metrics for Gemini and tool calls

🧪 Automated test suite

🔒 Data validations and business rules

⚡ Optimization to avoid unnecessary model calls

🏗️ Architecture
The application is organized by responsibilities:
┌──────────────────────┐
                        │        Client        │
                        │   CLI / HTTP / Docs  │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │       FastAPI        │
                        │       REST API       │
                        └──────────┬───────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │                              │
                    ▼                              ▼
             ┌──────────────────┐           ┌──────────────────┐
             │    AI Agent      │           │   Business API   │
             │                  │           │                  │
             │      Gemini      │           │ Cart / Checkout  │
             │        +         │           │ Orders           │
             │      Tools       │           │                  │
             └────────┬─────────┘           └────────┬─────────┘
                      │                              │
                      ▼                              ▼
             ┌──────────────────┐           ┌──────────────────┐
             │  CatalogService  │           │   CartService    │
             │                  │           │                  │
             │ Product search   │           │ Cart operations  │
             │ Product lookup   │           │ Validation       │
             │ Stock            │           │ Persistence      │
             └────────┬─────────┘           └────────┬─────────┘
                      │                              │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                        ┌──────────────────────┐
                        │   CheckoutService    │
                        │                      │
                        │ Transaction          │
                        │ Stock update         │
                        │ Order creation       │
                        │ Cart cleanup         │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │        SQLite        │
                        │                      │
                        │ products             │
                        │ carts                │
                        │ cart_items           │
                        │ orders               │
                        │ order_items          │
                        └──────────────────────┘
                        ┘
🧩 Main Components
AI Agent

The agent uses Gemini to interpret user requests and decide when it needs to use system tools.

Available tools include:

product search
stock inquiry
add products to cart
view cart
update quantities
remove products
execute checkout

This separates the model's reasoning capability from the application's business logic.

The model does not modify the database directly.

Instead:

User
   │
   ▼
Gemini
   │
   ▼
Tool
   │
   ▼
Service
   │
   ▼
Repository
   │
   ▼
SQLite
🔎 Product Catalog

The catalog is located at:

data/products.json

Products contain information such as:

ID
name
category
price
stock
description
tags

The catalog is initially loaded into SQLite.

The application includes a CatalogService responsible for centralizing product-related operations.

Its responsibilities include:

get products
search products
query products by ID
check stock
decrease stock
increase stock
🛒 Shopping Cart

The CartService manages the persistent state of the shopping cart.

Each cart is associated with a:

session_id

This allows maintaining independent carts across different sessions.

Available operations:

Add product
        │
        ▼
Update quantity
        │
        ▼
View cart
        │
        ├── Remove product
        │
        └── Clear cart

Rules validated include:

mandatory session_id
valid product_id
positive quantity
existing product
requested quantity within available stock
📦 Stock Control

Stock is part of the persistent state of each product.

Available quantity is validated before adding products to the cart.

Stock is checked again inside a transaction during checkout.

This avoids relying solely on the previous validation performed in the cart.

Flow:

Cart
   │
   ▼
Checkout
   │
   ▼
Check stock
   │
   ├── Insufficient → rollback
   │
   └── Available
         │
         ▼
     Create order
         │
         ▼
     Decrease stock
         │
         ▼
      Clear cart
💳 Transactional Checkout

The CheckoutService processes the purchase using a SQLite transaction.

During checkout:

Gets the products from the cart.
Verifies that the cart is not empty.
Checks that the products exist.
Verifies stock again.
Calculates the total.
Creates the order.
Creates order items.
Decreases the stock.
Clears the cart.
Commits the transaction.

If an error occurs during the process, the transaction rolls back.

This maintains consistency across:

Cart
Stock
Order
Order Items
🧠 Sessions and Memory

Conversations use a session_id.

The API maintains the conversational history associated with each session:

session_id
     │
     ▼
chat history
     │
     ├── message 1
     ├── response 1
     ├── message 2
     └── response 2

Additionally, the same session_id can be used to link the conversation with the cart and orders.

This allows an interaction to evolve from:

"I'm looking for headphones"
        ↓
"add them to the cart"
        ↓
"show me my cart"
        ↓
"checkout"
🌐 REST API

The application uses FastAPI.

Root Endpoint
GET /

Verifies that the API is running.

Health Check
GET /health

Response:

{
  "status": "healthy"
}
Chat
POST /chat

Example:

{
  "session_id": "demo-session",
  "message": "I'm looking for wireless headphones"
}

The response includes:

{
  "session_id": "demo-session",
  "response": "...",
  "gemini_calls": 0,
  "tool_calls": 1
}

Metrics allow observing how much work the model performed versus local tools.

🛒 Cart Endpoints
Get cart
GET /cart/{session_id}
Add product
POST /cart/{session_id}/items

Body:

{
  "product_id": "PROD-003",
  "quantity": 1
}
Update quantity
PUT /cart/{session_id}/items/{product_id}

Body:

{
  "quantity": 2
}
Remove product
DELETE /cart/{session_id}/items/{product_id}
Clear cart
DELETE /cart/{session_id}
💳 Checkout Endpoints
Create order
POST /checkout/{session_id}
Get order
GET /orders/{order_id}
Get orders for a session
GET /orders/session/{session_id}
🗄️ Persistence

The application uses SQLite.

Database:

data/ecommerce.db

Main schema:

products
   │
   ├── id
   ├── name
   ├── category
   ├── price
   ├── stock
   ├── description
   └── tags

carts
   │
   └── session_id

cart_items
   │
   ├── session_id
   ├── product_id
   └── quantity

orders
   │
   ├── id
   ├── session_id
   ├── total
   └── created_at

order_items
    │
    ├── order_id
    ├── product_id
    ├── product_name
    ├── unit_price
    ├── quantity
    └── subtotal

The application uses repositories to separate data access from business logic.

📁 Project Structure
ecommerce-ai-agent/
│
├── app/
│   │
│   ├── agent/
│   │   └── agent.py
│   │
│   ├── api/
│   │   └── main.py
│   │
│   ├── cart/
│   │   └── cart_service.py
│   │
│   ├── catalog/
│   │   └── catalog_service.py
│   │
│   ├── checkout/
│   │   └── checkout_service.py
│   │
│   ├── database/
│   │   ├── database.py
│   │   └── repositories/
│   │       ├── cart_repository.py
│   │       ├── order_repository.py
│   │       └── product_repository.py
│   │
│   └── tools/
│       └── tools.py
│
├── data/
│   ├── products.json
│   └── ecommerce.db
│
├── scripts/
│   └── init_vector_db.py
│
├── tests/
│   ├── test_api.py
│   ├── test_cart.py
│   ├── test_cart_checkout.py
│   ├── test_data.py
│   └── test_search.py
│
├── .env
├── requirements.txt
└── README.md
🧪 Testing

The project features an automated test suite.

Last validated run:

61 passed, 3 warnings

Approximate time:

14.57s

Tests cover different layers of the application.

Catalog
product lookup
search
stock
non-existent products
Cart
add products
add repeatedly
update quantities
remove products
clear cart
subtotal calculation
persistence
validations
Checkout
order creation
total calculation
stock update
cart clearing
empty cart
insufficient stock
non-existent products
invalid quantities
API
endpoints
sessions
chat
cart
checkout
orders
HTTP validations
Agent
tool usage
local search
model calls
metrics
integration between agent and services
📊 Model Call Optimization

One of the project's design decisions is to avoid using Gemini when an operation can be resolved locally.

For instance, a direct product search can be handled via the catalog without sending a request to the model.

This allows:

User request
        │
        ▼
Can it be resolved locally?
        │
    ┌───┴───┐
   Yes      No
    │       │
    ▼       ▼
Local     Gemini
Tool        │
            ▼
          Tools

The API exposes metrics per request:

{
  "gemini_calls": 0,
  "tool_calls": 1
}

These metrics allow observing system behavior and serve as a baseline for future cost and latency optimizations.

⚙️ Installation
1. Clone the repository
git clone <REPOSITORY_URL>
cd ecommerce-ai-agent
2. Create virtual environment

In Windows PowerShell:

python -m venv .venv

Activate:

.\.venv\Scripts\Activate.ps1
3. Install dependencies
pip install -r requirements.txt
4. Configure environment variables

Create a file:

.env

with your Gemini API key:

GOOGLE_API_KEY=your_api_key
▶️ Running the API

From the project root:

uvicorn app.api.main:app --reload

The API will be available at:

http://127.0.0.1:8000

FastAPI interactive documentation is available at:

http://127.0.0.1:8000/docs

You can also check:

http://127.0.0.1:8000/redoc
💬 Running the Agent from Console

The agent can be run directly via:

python -m app.agent.agent

The flow allows interacting with the agent from the terminal.

Example:

E-COMMERCE AI AGENT

User: looking for noise-canceling wireless headphones

Assistant:
...

To exit:

salir (or exit)
🔬 Complete Flow Example

A typical interaction follows this flow:

User
 │
 │ "I'm looking for wireless headphones"
 ▼
Agent
 │
 ▼
search_products_catalog
 │
 ▼
CatalogService
 │
 ▼
Product found
 │
 │
 ▼
User
 │
 │ "Add them to the cart"
 ▼
add_product_to_cart
 │
 ▼
CartService
 │
 ▼
SQLite
 │
 ▼
Cart updated
 │
 │
 ▼
User
 │
 │ "Checkout"
 ▼
checkout_cart
 │
 ▼
CheckoutService
 │
 ├── validate stock
 ├── create order
 ├── update stock
 └── clear cart
        │
        ▼
     SQLite
🛡️ Error Handling

The application validates errors at both the business logic and API layers.

Handled cases include:

empty session
non-existent product
invalid quantity
insufficient stock
empty cart
non-existent order
non-existent product during checkout

Business errors translate into appropriate HTTP responses when accessed via FastAPI.

🧱 Design Principles

The project seeks to maintain separated responsibilities:

API
 │
 ▼
Services
 │
 ▼
Repositories
 │
 ▼
Database

While the agent integrates via tools:

Agent
 │
 ├── search_products_catalog
 ├── check_product_stock
 ├── add_product_to_cart
 ├── get_cart
 ├── update_product_in_cart
 ├── remove_product_from_cart
 └── checkout_cart

This allows each part of the system to evolve independently.

🛠️ Technologies
Technology	Usage
Python	Main language
FastAPI	REST API
Pydantic	Data validation
SQLite	Persistence
Gemini	Language model
LangChain	Agent and tool integration
ChromaDB	Vector search infrastructure
Pytest	Testing
Uvicorn	ASGI server
📈 Upcoming Improvements

Planned enhancements for future versions:

conversational memory persistence
user authentication
payment gateway integration
PostgreSQL for production
Redis for sessions/cache
advanced observability
latency metrics
distributed tracing
Docker
cloud deployment
asynchronous workers
systematic evaluation of agent responses

These improvements are part of a potential evolution of the project toward a production architecture.

🎯 Project Goal

This project was built as a demonstration of backend engineering applied to AI-driven systems.

Beyond integrating an LLM, the objective is to demonstrate:

modular design
separation of responsibilities
tool integration with agents
data persistence
transactions
stock control
REST APIs
validation
automated testing
model call optimization
basic observability
integration between AI and business logic

AI is a part of the system, not the entire system.

📌 Current Status
[✓] Catalog
[✓] SQLite
[✓] Repository pattern
[✓] Product search
[✓] AI Agent
[✓] Tools
[✓] Cart
[✓] Stock control
[✓] Checkout
[✓] Orders
[✓] Sessions
[✓] FastAPI
[✓] Error handling
[✓] Automated tests
[✓] Basic metrics
[✓] Call optimization
[ ] Advanced documentation
[ ] Deployment
[ ] Advanced observability
👨‍💻 Portfolio Project

Project developed to demonstrate software backend engineering capabilities and AI-driven application development.

The focus is on building a functional end-to-end system with real business logic, persistence, testing, and the integration of an AI agent with external tools.
