# E-commerce AI Agent

Agente inteligente de e-commerce construido con Python, FastAPI, Gemini y SQLite.

El proyecto combina un agente conversacional con herramientas de negocio para consultar productos, gestionar un carrito de compras y ejecutar un checkout transaccional.

El objetivo es demostrar la construcción de una aplicación backend con integración de IA, persistencia de datos, lógica de negocio, herramientas para agentes, sesiones conversacionales y pruebas automatizadas.

---

## 🚀 Características principales

- 🤖 Agente conversacional basado en Gemini
- 🔎 Búsqueda de productos mediante herramientas
- 🛒 Gestión completa del carrito
- 📦 Control de stock
- 💳 Checkout transaccional
- 🧾 Creación y consulta de órdenes
- 💾 Persistencia con SQLite
- 🧠 Sesiones conversacionales
- 🔧 Herramientas especializadas para el agente
- 🌐 API REST con FastAPI
- 📊 Métricas de llamadas a Gemini y herramientas
- 🧪 Suite de pruebas automatizadas
- 🔒 Validaciones de datos y reglas de negocio
- ⚡ Optimización para evitar llamadas innecesarias al modelo

---

# 🏗️ Arquitectura

La aplicación está organizada por responsabilidades:

```text
                         ┌──────────────────────┐
                         │       Cliente        │
                         │  CLI / HTTP / Docs   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │      REST API        │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
          ┌──────────────────┐             ┌──────────────────┐
          │   AI Agent       │             │  Business API    │
          │                  │             │                  │
          │     Gemini       │             │ Cart / Checkout  │
          │       +          │             │ Orders           │
          │     Tools        │             │                  │
          └────────┬─────────┘             └────────┬─────────┘
                   │                                │
                   ▼                                ▼
          ┌──────────────────┐             ┌──────────────────┐
          │ CatalogService   │             │   CartService    │
          │                  │             │                  │
          │ Product search   │             │ Cart operations  │
          │ Product lookup   │             │ Validation       │
          │ Stock            │             │ Persistence      │
          └────────┬─────────┘             └────────┬─────────┘
                   │                                │
                   └───────────────┬────────────────┘
                                   │
                                   ▼
                         ┌──────────────────────┐
                         │    CheckoutService   │
                         │                      │
                         │ Transaction          │
                         │ Stock update         │
                         │ Order creation       │
                         │ Cart cleanup         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       SQLite         │
                         │                      │
                         │ products             │
                         │ carts                │
                         │ cart_items            │
                         │ orders               │
                         │ order_items           │
                         └──────────────────────┘
                         ┘
🧩 Componentes principales
AI Agent

El agente utiliza Gemini para interpretar las solicitudes del usuario y decidir cuándo necesita utilizar herramientas del sistema.

Las herramientas disponibles incluyen:

búsqueda de productos
consulta de stock
agregar productos al carrito
consultar carrito
actualizar cantidades
eliminar productos
ejecutar checkout

Esto permite separar la capacidad de razonamiento del modelo de la lógica de negocio de la aplicación.

El modelo no modifica directamente la base de datos.

En su lugar:

Usuario
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
🔎 Catálogo de productos

El catálogo se encuentra en:

data/products.json

Los productos contienen información como:

ID
nombre
categoría
precio
stock
descripción
tags

El catálogo se carga inicialmente en SQLite.

La aplicación dispone de un CatalogService encargado de centralizar las operaciones relacionadas con productos.

Entre sus responsabilidades:

obtener productos
buscar productos
consultar productos por ID
consultar stock
disminuir stock
aumentar stock
🛒 Carrito de compras

El CartService administra el estado persistente del carrito.

Cada carrito está asociado a un:

session_id

Esto permite mantener carritos independientes entre diferentes sesiones.

Operaciones disponibles:

Agregar producto
       │
       ▼
Actualizar cantidad
       │
       ▼
Consultar carrito
       │
       ├── Eliminar producto
       │
       └── Vaciar carrito

También se validan reglas como:

session_id obligatorio
product_id válido
cantidad positiva
producto existente
cantidad solicitada dentro del stock disponible
📦 Control de stock

El stock forma parte del estado persistente de cada producto.

Antes de agregar productos al carrito se valida la cantidad disponible.

Durante el checkout se vuelve a comprobar el stock dentro de una transacción.

Esto evita confiar únicamente en la validación realizada anteriormente en el carrito.

Flujo:

Carrito
   │
   ▼
Checkout
   │
   ▼
Comprobar stock
   │
   ├── Insuficiente → rollback
   │
   └── Disponible
          │
          ▼
     Crear orden
          │
          ▼
    Disminuir stock
          │
          ▼
      Vaciar carrito
💳 Checkout transaccional

El CheckoutService procesa la compra utilizando una transacción SQLite.

Durante el checkout:

Obtiene los productos del carrito.
Verifica que el carrito no esté vacío.
Comprueba que los productos existan.
Verifica nuevamente el stock.
Calcula el total.
Crea la orden.
Crea las líneas de la orden.
Disminuye el stock.
Vacía el carrito.
Confirma la transacción.

Si ocurre un error durante el proceso, la transacción realiza rollback.

Esto mantiene consistentes:

Carrito
Stock
Orden
Order Items
🧠 Sesiones y memoria

Las conversaciones utilizan un session_id.

La API mantiene el historial conversacional asociado a cada sesión:

session_id
     │
     ▼
chat history
     │
     ├── mensaje 1
     ├── respuesta 1
     ├── mensaje 2
     └── respuesta 2

Además, el mismo session_id puede utilizarse para relacionar la conversación con el carrito y las órdenes.

Esto permite que una interacción pueda evolucionar desde:

"Busco audífonos"
        ↓
"agrégalos al carrito"
        ↓
"muéstrame mi carrito"
        ↓
"comprar"
🌐 API REST

La aplicación utiliza FastAPI.

Endpoint raíz
GET /

Comprueba que la API esté funcionando.

Health check
GET /health

Respuesta:

{
  "status": "healthy"
}
Chat
POST /chat

Ejemplo:

{
  "session_id": "demo-session",
  "message": "Busco audífonos inalámbricos"
}

La respuesta incluye:

{
  "session_id": "demo-session",
  "response": "...",
  "gemini_calls": 0,
  "tool_calls": 1
}

Las métricas permiten observar cuánto trabajo realizó el modelo frente a las herramientas locales.

🛒 Endpoints del carrito
Obtener carrito
GET /cart/{session_id}
Agregar producto
POST /cart/{session_id}/items

Body:

{
  "product_id": "PROD-003",
  "quantity": 1
}
Actualizar cantidad
PUT /cart/{session_id}/items/{product_id}

Body:

{
  "quantity": 2
}
Eliminar producto
DELETE /cart/{session_id}/items/{product_id}
Vaciar carrito
DELETE /cart/{session_id}
💳 Endpoints de checkout
Crear orden
POST /checkout/{session_id}
Obtener orden
GET /orders/{order_id}
Obtener órdenes de una sesión
GET /orders/session/{session_id}
🗄️ Persistencia

La aplicación utiliza SQLite.

Base de datos:

data/ecommerce.db

Esquema principal:

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

La aplicación utiliza repositories para separar el acceso a datos de la lógica de negocio.

📁 Estructura del proyecto
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

El proyecto cuenta con una suite automatizada de pruebas.

Última ejecución validada:

61 passed, 3 warnings

Tiempo aproximado:

14.57s

Las pruebas cubren diferentes capas de la aplicación.

Catálogo
consulta de productos
búsqueda
stock
productos inexistentes
Carrito
agregar productos
agregar repetidamente
actualizar cantidades
eliminar productos
vaciar carrito
cálculo del subtotal
persistencia
validaciones
Checkout
creación de órdenes
cálculo del total
actualización de stock
vaciado del carrito
carrito vacío
stock insuficiente
productos inexistentes
cantidades inválidas
API
endpoints
sesiones
chat
carrito
checkout
órdenes
validaciones HTTP
Agente
uso de herramientas
búsqueda local
llamadas al modelo
métricas
integración entre agente y servicios
📊 Optimización de llamadas al modelo

Una de las decisiones del proyecto es evitar utilizar Gemini cuando una operación puede resolverse localmente.

Por ejemplo, una búsqueda directa de productos puede resolverse mediante el catálogo sin necesidad de enviar una solicitud al modelo.

Esto permite:

Solicitud del usuario
        │
        ▼
¿Puede resolverse localmente?
        │
    ┌───┴───┐
   Sí       No
    │        │
    ▼        ▼
  Tool     Gemini
 local       │
             ▼
           Tools

La API expone métricas por solicitud:

{
  "gemini_calls": 0,
  "tool_calls": 1
}

Estas métricas permiten observar el comportamiento del sistema y sirven como base para futuras optimizaciones de costo y latencia.

⚙️ Instalación
1. Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd ecommerce-ai-agent
2. Crear entorno virtual

En Windows PowerShell:

python -m venv .venv

Activar:

.\.venv\Scripts\Activate.ps1
3. Instalar dependencias
pip install -r requirements.txt
4. Configurar variables de entorno

Crear un archivo:

.env

con la API key de Gemini:

GOOGLE_API_KEY=tu_api_key
▶️ Ejecutar la API

Desde la raíz del proyecto:

uvicorn app.api.main:app --reload

La API estará disponible en:

http://127.0.0.1:8000

La documentación interactiva de FastAPI está disponible en:

http://127.0.0.1:8000/docs

También se puede consultar:

http://127.0.0.1:8000/redoc
💬 Ejecutar el agente desde consola

El agente puede ejecutarse directamente mediante:

python -m app.agent.agent

El flujo permite interactuar con el agente desde la terminal.

Ejemplo:

E-COMMERCE AI AGENT

Usuario: busco audífonos inalámbricos con cancelación de ruido

Asistente:
...

Para finalizar:

salir
🔬 Ejemplo de flujo completo

Una interacción típica puede seguir este flujo:

Usuario
  │
  │ "Busco audífonos inalámbricos"
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
Producto encontrado
  │
  │
  ▼
Usuario
  │
  │ "Agrégalos al carrito"
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
Carrito actualizado
  │
  │
  ▼
Usuario
  │
  │ "Comprar"
  ▼
checkout_cart
  │
  ▼
CheckoutService
  │
  ├── validar stock
  ├── crear orden
  ├── actualizar stock
  └── vaciar carrito
        │
        ▼
      SQLite
🛡️ Manejo de errores

La aplicación valida errores tanto en la capa de negocio como en la API.

Algunos casos contemplados:

sesión vacía
producto inexistente
cantidad inválida
stock insuficiente
carrito vacío
orden inexistente
producto inexistente durante checkout

Los errores de negocio se convierten en respuestas HTTP apropiadas cuando se accede mediante FastAPI.

🧱 Principios de diseño

El proyecto busca mantener responsabilidades separadas:

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

Mientras que el agente se integra mediante herramientas:

Agent
 │
 ├── search_products_catalog
 ├── check_product_stock
 ├── add_product_to_cart
 ├── get_cart
 ├── update_product_in_cart
 ├── remove_product_from_cart
 └── checkout_cart

Esto permite evolucionar cada parte del sistema de manera independiente.

🛠️ Tecnologías
Tecnología	Uso
Python	Lenguaje principal
FastAPI	API REST
Pydantic	Validación de datos
SQLite	Persistencia
Gemini	Modelo de lenguaje
LangChain	Integración del agente y herramientas
ChromaDB	Infraestructura de búsqueda vectorial
Pytest	Testing
Uvicorn	Servidor ASGI
📈 Próximas mejoras

Algunas mejoras previstas para futuras versiones:

persistencia de memoria conversacional
autenticación de usuarios
integración con un sistema de pagos
PostgreSQL para producción
Redis para sesiones/cache
observabilidad avanzada
métricas de latencia
tracing distribuido
Docker
despliegue cloud
workers asíncronos
evaluación sistemática de respuestas del agente

Estas mejoras forman parte de una posible evolución del proyecto hacia una arquitectura de producción.

🎯 Objetivo del proyecto

Este proyecto fue construido como una demostración de ingeniería backend aplicada a sistemas con IA.

Más allá de integrar un LLM, el objetivo es demostrar:

diseño modular
separación de responsabilidades
integración de herramientas con agentes
persistencia de datos
transacciones
control de stock
APIs REST
validación
testing automatizado
optimización de llamadas a modelos
observabilidad básica
integración entre IA y lógica de negocio

La IA es una parte del sistema, no el sistema completo.

📌 Estado actual
[✓] Catálogo
[✓] SQLite
[✓] Repository pattern
[✓] Búsqueda de productos
[✓] Agente IA
[✓] Tools
[✓] Carrito
[✓] Control de stock
[✓] Checkout
[✓] Órdenes
[✓] Sesiones
[✓] FastAPI
[✓] Manejo de errores
[✓] Tests automatizados
[✓] Métricas básicas
[✓] Optimización de llamadas
[ ] Documentación avanzada
[ ] Deployment
[ ] Observabilidad avanzada
👨‍💻 Proyecto de portafolio

Proyecto desarrollado para demostrar capacidades de ingeniería de software backend y desarrollo de aplicaciones basadas en IA.

El foco está en construir un sistema funcional de extremo a extremo, con lógica de negocio real, persistencia, pruebas e integración de un agente de IA con herramientas externas.