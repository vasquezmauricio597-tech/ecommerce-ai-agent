# E-commerce AI Agent

AI-powered e-commerce backend built with Python, FastAPI, Google Gemini, LangChain, ChromaDB, and SQLite.

The project combines a conversational AI agent with real business logic for product discovery, semantic search, inventory management, persistent shopping carts, transactional checkout, and order management.

The main engineering goal is to demonstrate that an LLM can be integrated into a reliable backend system without making the model responsible for deterministic business operations.

---

## Overview

The system provides an AI shopping assistant capable of understanding natural-language requests, searching a product catalog, checking inventory, managing a persistent shopping cart, and completing purchases.

Instead of sending every request to an LLM, the system uses a hybrid architecture:

```text
                         +----------------------+
                         |      User Query      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     Query Layer      |
                         | Recommendation /     |
                         | Request Detection    |
                         +----------+-----------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
          +-------------------+          +-------------------+
          | Deterministic     |          | Complex Reasoning |
          | Local Logic       |          | Google Gemini     |
          +---------+---------+          +---------+---------+
                    |                              |
                    |                              v
                    |                       +--------------+
                    |                       | Tool Calling |
                    |                       +------+-------+
                    |                              |
                    +--------------+---------------+
                                   |
                                   v
                         +----------------------+
                         |  Application Layer  |
                         +----------+-----------+
                                    |
                    +---------------+---------------+
                    |               |               |
                    v               v               v
                Catalog           Cart          Checkout
                    |               |               |
                    +---------------+---------------+
                                    |
                                    v
                         +----------------------+
                         |        SQLite        |
                         +----------------------+
```

This architecture allows the application to use an LLM when reasoning is useful while keeping predictable operations inside the backend.

---

## Key Features

### AI Shopping Assistant

* Natural-language product queries
* Google Gemini integration
* Tool calling
* Context-aware conversations
* Product recommendations
* Inventory-aware responses
* Session-based conversations

### Semantic Product Search

The product catalog is indexed using ChromaDB and vector embeddings.

The search layer combines:

* Semantic similarity
* Direct product matching
* Categories
* Product tags
* User intent
* Availability
* Distance thresholds

This allows queries to retrieve relevant products even when the user does not use the exact terminology stored in the catalog.

Example:

```text
"I need headphones that help me focus in a noisy environment."
```

The system can identify relevant products based on their semantic meaning rather than relying exclusively on exact keyword matches.

---

## Intelligent LLM Usage

One of the main engineering decisions in the project was to avoid treating Gemini as the entire application.

Requests that can be resolved deterministically are handled locally.

For example:

```text
User Request
     |
     v
Product-related request
     |
     v
Local Recommendation Engine
     |
     +-- Semantic Search
     +-- Product Tags
     +-- User Intent
     +-- Availability
     |
     v
Recommendation
```

No Gemini call is required for this deterministic path.

More complex requests can instead be routed to Gemini for reasoning and natural-language generation.

This architecture helps reduce:

* API calls
* Token consumption
* Latency
* Rate-limit pressure
* Operational cost

---

## E-commerce Operations

### Product Catalog

Products are persisted in SQLite and indexed into ChromaDB for semantic retrieval.

Each product contains information such as:

* Product ID
* Name
* Category
* Price
* Stock
* Description
* Tags

The original catalog is stored in:

```text
data/products.json
```

---

### Shopping Cart

The application implements a persistent, session-based shopping cart.

Each cart is associated with a `session_id`.

Supported operations include:

* Add product
* Update quantity
* Remove product
* Clear cart
* Retrieve cart
* Calculate subtotal

Cart state is persisted in the database rather than existing only inside the LLM conversation.

---

### Stock Control

Inventory is treated as persistent application state.

Stock is validated when products are added to the cart and checked again during checkout.

This second validation is important because inventory may have changed between cart creation and purchase.

Example flow:

```text
Cart
 |
 v
Checkout
 |
 v
Validate Stock
 |
 +---- Insufficient ----> Rollback
 |
 +---- Available
          |
          v
      Create Order
          |
          v
      Update Stock
          |
          v
       Clear Cart
          |
          v
        Commit
```

---

### Transactional Checkout

Checkout is implemented using a SQLite transaction.

The checkout process:

1. Retrieves the cart
2. Validates that it is not empty
3. Verifies product existence
4. Checks inventory
5. Calculates the total
6. Creates the order
7. Creates order items
8. Decreases inventory
9. Clears the cart
10. Commits the transaction

If an error occurs, the transaction is rolled back.

This protects consistency across:

```text
Cart
Stock
Order
Order Items
```

---

## Sessions and Conversation State

Conversations use a `session_id`.

The same session can connect conversational history with shopping-cart and order operations.

Example:

```text
User
 |
 | "I'm looking for headphones"
 v
AI Agent
 |
 v
Product Search
 |
 | "Add them to the cart"
 v
Cart
 |
 | "Show me my cart"
 v
Cart State
 |
 | "Checkout"
 v
Transactional Checkout
 |
 v
Order
```

This allows a single interaction to evolve from product discovery into a complete purchase workflow.

---

## Architecture

The project separates the AI layer from application and persistence logic.

```text
app/
|
+-- agent/
|   +-- agent.py
|
+-- api/
|   +-- main.py
|
+-- catalog/
|   +-- catalog_service.py
|
+-- cart/
|   +-- cart_service.py
|
+-- checkout/
|   +-- checkout_service.py
|
+-- database/
|   +-- database.py
|   +-- repositories/
|       +-- cart_repository.py
|       +-- order_repository.py
|       +-- product_repository.py
|
+-- tools/
    +-- tools.py
```

Additional components:

```text
data/
+-- products.json
+-- ecommerce.db

scripts/
+-- init_vector_db.py

tests/
+-- test_api.py
+-- test_cart.py
+-- test_cart_checkout.py
+-- test_data.py
+-- test_search.py
```

The application follows a layered architecture:

```text
API
 |
 v
Services
 |
 v
Repositories
 |
 v
Database
```

The AI agent interacts with the application through tools:

```text
User
 |
 v
LLM
 |
 v
Tool
 |
 v
Business Logic
 |
 v
Repository
 |
 v
SQLite
```

The model never modifies the database directly.

---

## AI Architecture

The AI layer uses Google Gemini through LangChain.

The agent can access application tools such as:

```text
search_products_catalog(query)
check_product_stock(product_id)
add_product_to_cart(session_id, product_id, quantity)
get_cart(session_id)
update_product_in_cart(session_id, product_id, quantity)
remove_product_from_cart(session_id, product_id)
checkout_cart(session_id)
```

This separation keeps model reasoning independent from business operations.

The backend remains responsible for:

* Validation
* Inventory rules
* Cart state
* Transactions
* Persistence
* Error handling

---

## REST API

The backend is exposed through FastAPI.

### Root

```text
GET /
```

Verifies that the API is running.

### Health Check

```text
GET /health
```

Example response:

```json
{
  "status": "healthy"
}
```

### Chat

```text
POST /chat
```

Example request:

```json
{
  "session_id": "demo-session",
  "message": "I'm looking for wireless headphones"
}
```

Example response structure:

```json
{
  "session_id": "demo-session",
  "response": "...",
  "gemini_calls": 0,
  "tool_calls": 1
}
```

The response metrics make it possible to observe whether a request was handled locally or required model interaction.

---

## Cart Endpoints

### Get Cart

```text
GET /cart/{session_id}
```

### Add Product

```text
POST /cart/{session_id}/items
```

Example:

```json
{
  "product_id": "PROD-003",
  "quantity": 1
}
```

### Update Quantity

```text
PUT /cart/{session_id}/items/{product_id}
```

Example:

```json
{
  "quantity": 2
}
```

### Remove Product

```text
DELETE /cart/{session_id}/items/{product_id}
```

### Clear Cart

```text
DELETE /cart/{session_id}
```

---

## Checkout Endpoints

### Create Order

```text
POST /checkout/{session_id}
```

### Get Order

```text
GET /orders/{order_id}
```

### Get Orders for Session

```text
GET /orders/session/{session_id}
```

---

## Persistence

The application uses SQLite for persistent relational data.

Database:

```text
data/ecommerce.db
```

Main entities:

```text
products
 |
 +-- id
 +-- name
 +-- category
 +-- price
 +-- stock
 +-- description
 +-- tags

carts
 |
 +-- session_id

cart_items
 |
 +-- session_id
 +-- product_id
 +-- quantity

orders
 |
 +-- id
 +-- session_id
 +-- total
 +-- created_at

order_items
 |
 +-- order_id
 +-- product_id
 +-- product_name
 +-- unit_price
 +-- quantity
 +-- subtotal
```

Repositories are used to separate data access from business logic.

---

## LLM Cost Optimization

A major objective of the project was optimizing LLM usage.

A naive architecture might send every request through Gemini:

```text
Request
   |
   v
Gemini
   |
   v
Tools
   |
   v
Gemini
   |
   v
Response
```

This can result in unnecessary model calls and token consumption.

The implemented architecture introduces a local decision and recommendation layer:

```text
Request
   |
   +-- Deterministic / Product-related
   |          |
   |          v
   |      Local Logic
   |
   +-- Complex Reasoning
              |
              v
           Gemini
```

During optimization, measured token consumption was reduced from:

```text
2,962 tokens
      |
      v
1,092 tokens
```

This represents approximately a **63% reduction in token usage for the measured scenario**.

The optimization also eliminated an unnecessary tool loop in that scenario.

The result is an architecture where the LLM acts as a reasoning component rather than as the application's entire control layer.

---

## Example Interaction

### Local Recommendation Path

```text
User:
"I need headphones for working remotely and blocking background noise."

System:
1. Detects product-related intent
2. Performs semantic catalog search
3. Applies recommendation logic
4. Checks availability
5. Returns relevant products

Gemini:
Not required for the deterministic recommendation path.
```

### Reasoning Path

```text
User:
"Which laptop would you recommend for software development and why?"

System:
1. Identifies the need for reasoning
2. Retrieves relevant product context
3. Uses Gemini for explanation
4. Returns a natural-language response
```

This distinction is one of the main architectural characteristics of the project.

---

## Testing

The project includes an automated test suite covering multiple application layers.

The validated project state reached:

```text
61 passed, 3 warnings
Approximate execution time: 14.57 seconds
```

Tests cover areas including:

### Catalog

* Product lookup
* Product search
* Stock management
* Non-existent products

### Cart

* Adding products
* Adding products repeatedly
* Updating quantities
* Removing products
* Clearing carts
* Subtotal calculation
* Persistence
* Validation

### Checkout

* Order creation
* Total calculation
* Stock updates
* Cart clearing
* Empty carts
* Insufficient stock
* Invalid products
* Invalid quantities

### API

* Endpoints
* Sessions
* Chat
* Cart
* Checkout
* Orders
* HTTP validation

### Agent

* Tool usage
* Local search
* Model calls
* Metrics
* Agent/service integration

---

## Error Handling

Validation is implemented at both the business-logic and API layers.

Handled cases include:

* Empty sessions
* Non-existent products
* Invalid quantities
* Insufficient stock
* Empty carts
* Non-existent orders
* Invalid checkout operations

Business errors are translated into appropriate HTTP responses by the API layer.

---

## Engineering Principles

The project was built around several practical AI engineering principles.

### 1. Do not use an LLM for deterministic work

Database queries, inventory checks, cart calculations, and other predictable operations belong in application code.

### 2. Keep business logic outside the model

The LLM can request operations through tools, but the backend remains responsible for executing and validating them.

### 3. Optimize unnecessary model usage

Reducing unnecessary model calls can improve:

* Cost
* Latency
* Reliability
* Rate-limit resilience

### 4. Keep persistent state in the backend

Cart, inventory, and orders are persisted independently from conversational context.

### 5. Use transactions for critical workflows

Checkout operations are performed atomically to avoid partially completed purchases.

### 6. Separate responsibilities

The application separates:

```text
AI
API
Business Logic
Persistence
```

This makes individual components easier to test, maintain, and extend.

---

## Technology Stack

| Technology    | Purpose                              |
| ------------- | ------------------------------------ |
| Python        | Core application                     |
| FastAPI       | REST API                             |
| Pydantic      | Data validation                      |
| LangChain     | LLM orchestration and tool calling   |
| Google Gemini | Natural-language reasoning           |
| ChromaDB      | Vector search and semantic retrieval |
| SQLite        | Persistent relational data           |
| Pytest        | Automated testing                    |
| Uvicorn       | ASGI server                          |

---

## Installation

### 1. Clone the repository

```bash
git clone <REPOSITORY_URL>
cd ecommerce-ai-agent
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```text
GOOGLE_API_KEY=your_api_key
```

---

## Running the API

From the project root:

```powershell
uvicorn app.api.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative documentation:

```text
http://127.0.0.1:8000/redoc
```

---

## Running the Agent from the Console

The agent can also be executed directly:

```powershell
python -m app.agent.agent
```

Example:

```text
E-COMMERCE AI AGENT

User: looking for noise-canceling wireless headphones

Assistant:
...
```

To exit:

```text
salir
```

or:

```text
exit
```

---

## Complete Purchase Flow

A typical end-to-end interaction can follow this architecture:

```text
User
 |
 | "I'm looking for wireless headphones"
 v
AI Agent
 |
 v
search_products_catalog
 |
 v
CatalogService
 |
 v
Product Found
 |
 | "Add them to the cart"
 v
add_product_to_cart
 |
 v
CartService
 |
 v
SQLite
 |
 v
Cart Updated
 |
 | "Checkout"
 v
checkout_cart
 |
 v
CheckoutService
 |
 +-- Validate stock
 +-- Create order
 +-- Create order items
 +-- Update stock
 +-- Clear cart
 |
 v
SQLite
```

The complete flow combines AI interaction, application services, persistence, validation, and transactional business logic.

---

## Project Goals

This project was built to demonstrate practical experience with:

* LLM application architecture
* AI agents
* Tool calling
* RAG and semantic search
* Vector databases
* Backend development
* REST APIs
* Persistent state
* Transactional workflows
* Inventory management
* AI cost optimization
* Token optimization
* Automated testing
* Separation of concerns

Rather than building a simple chatbot, the objective was to build an **AI-enabled application where the model is one component of a larger software system**.

---

## Future Improvements

Potential future extensions include:

* Streaming responses
* Authentication and user accounts
* Payment integration
* PostgreSQL for production workloads
* Redis for caching and sessions
* Advanced observability
* Distributed tracing
* Background job processing
* Docker
* Cloud deployment
* More advanced recommendation models
* Systematic evaluation of agent responses

---

## Current Status

```text
[✓] Product Catalog
[✓] SQLite Persistence
[✓] Repository Pattern
[✓] Product Search
[✓] Semantic Search
[✓] AI Agent
[✓] Agent Tools
[✓] Session Management
[✓] Persistent Shopping Cart
[✓] Stock Control
[✓] Transactional Checkout
[✓] Orders
[✓] FastAPI
[✓] Error Handling
[✓] Automated Tests
[✓] Request Metrics
[✓] LLM Call Optimization
[ ] Production Deployment
[ ] Advanced Observability
```

---

## Author

Built as an AI engineering portfolio project focused on combining **LLMs with reliable backend engineering, persistent business state, transactional workflows, and efficient system design**.
