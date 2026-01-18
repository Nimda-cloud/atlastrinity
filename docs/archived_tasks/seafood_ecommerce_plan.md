# Seafood E-Commerce Development Plan

## 1. ERD Draft

### Core Entities:

```mermaid
graph TD
    User[User] -->|has_many| Order
    User -->|has_many| Address
    User -->|has_many| PaymentMethod
    
    Product[Product] -->|belongs_to| Category
    Product -->|has_many| ProductVariant
    Product -->|has_many| Review
    
    Order[Order] -->|belongs_to| User
    Order -->|has_many| OrderItem
    Order -->|has_one| Shipping
    Order -->|has_one| Payment
    
    OrderItem[OrderItem] -->|belongs_to| Order
    OrderItem -->|belongs_to| ProductVariant
    
    Category[Category] -->|has_many| Product
    
    Inventory[Inventory] -->|belongs_to| ProductVariant
    
    Shipping[Shipping] -->|belongs_to| Order
    Shipping -->|has_many| ShippingStatus
    
    Payment[Payment] -->|belongs_to| Order
    Payment -->|has_one| PaymentStatus
```

### Entity Details:

**User**
- id: UUID (PK)
- email: string (unique)
- password_hash: string
- first_name: string
- last_name: string
- phone: string
- role: enum (customer, admin, staff)
- created_at: timestamp
- updated_at: timestamp

**Product**
- id: UUID (PK)
- name: string
- description: text
- base_price: decimal
- category_id: UUID (FK)
- is_active: boolean
- is_featured: boolean
- created_at: timestamp
- updated_at: timestamp

**ProductVariant**
- id: UUID (PK)
- product_id: UUID (FK)
- variant_name: string (e.g., "Fresh Salmon Fillet - 1lb")
- sku: string (unique)
- price: decimal
- weight: decimal
- unit: enum (lb, kg, each, dozen)
- image_url: string
- is_available: boolean

**Category**
- id: UUID (PK)
- name: string
- description: text
- parent_id: UUID (FK, nullable for top-level)
- image_url: string

**Order**
- id: UUID (PK)
- user_id: UUID (FK)
- order_number: string (unique)
- status: enum (pending, processing, shipped, delivered, cancelled, refunded)
- subtotal: decimal
- tax: decimal
- shipping_cost: decimal
- total: decimal
- notes: text
- created_at: timestamp
- updated_at: timestamp

**OrderItem**
- id: UUID (PK)
- order_id: UUID (FK)
- product_variant_id: UUID (FK)
- quantity: integer
- unit_price: decimal
- total_price: decimal

**Inventory**
- id: UUID (PK)
- product_variant_id: UUID (FK)
- quantity: integer
- low_stock_threshold: integer
- last_restocked: timestamp
- expires_at: timestamp (for perishable items)

**Shipping**
- id: UUID (PK)
- order_id: UUID (FK)
- address_id: UUID (FK)
- carrier: string
- tracking_number: string
- service_level: enum (standard, express, overnight)
- estimated_delivery: timestamp
- actual_delivery: timestamp (nullable)

**Payment**
- id: UUID (PK)
- order_id: UUID (FK)
- payment_method_id: UUID (FK)
- amount: decimal
- currency: string (default: USD)
- status: enum (pending, completed, failed, refunded)
- transaction_id: string
- gateway_response: jsonb

**Address**
- id: UUID (PK)
- user_id: UUID (FK)
- address_type: enum (home, work, other)
- street: string
- city: string
- state: string
- postal_code: string
- country: string
- is_default: boolean

**PaymentMethod**
- id: UUID (PK)
- user_id: UUID (FK)
- type: enum (credit_card, paypal, bank_transfer)
- card_last_four: string (nullable)
- card_brand: string (nullable)
- card_exp_month: integer (nullable)
- card_exp_year: integer (nullable)
- is_default: boolean

**Review**
- id: UUID (PK)
- product_id: UUID (FK)
- user_id: UUID (FK)
- rating: integer (1-5)
- title: string
- comment: text
- created_at: timestamp

## 2. OpenAPI Contract Skeleton

```yaml
openapi: 3.0.3
info:
  title: Seafood E-Commerce API
  description: API for a full-featured seafood e-commerce platform
  version: 1.0.0
  contact:
    email: support@seafoodmarket.com
    url: https://seafoodmarket.com
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.seafoodmarket.com/v1
    description: Production server
  - url: https://staging.seafoodmarket.com/v1
    description: Staging server
  - url: http://localhost:3000/v1
    description: Local development server

paths:
  /auth:
    post:
      tags: [Authentication]
      summary: User login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoginRequest'
      responses:
        '200':
          description: Successful login
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        '401':
          description: Invalid credentials

  /auth/refresh:
    post:
      tags: [Authentication]
      summary: Refresh access token
      security:
        - refreshToken: []
      responses:
        '200':
          description: Token refreshed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'

  /users:
    post:
      tags: [Users]
      summary: Register new user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreate'
      responses:
        '201':
          description: User created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'

  /users/me:
    get:
      tags: [Users]
      summary: Get current user profile
      security:
        - bearerAuth: []
      responses:
        '200':
          description: User profile
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
    put:
      tags: [Users]
      summary: Update current user profile
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserUpdate'
      responses:
        '200':
          description: User updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'

  /products:
    get:
      tags: [Products]
      summary: List all products
      parameters:
        - $ref: '#/components/parameters/page'
        - $ref: '#/components/parameters/limit'
        - $ref: '#/components/parameters/category'
        - $ref: '#/components/parameters/search'
        - $ref: '#/components/parameters/sort'
      responses:
        '200':
          description: List of products
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/ProductResponse'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

    post:
      tags: [Products]
      summary: Create new product (Admin only)
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ProductCreate'
      responses:
        '201':
          description: Product created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProductResponse'

  /products/{id}:
    get:
      tags: [Products]
      summary: Get product details
      parameters:
        - $ref: '#/components/parameters/productId'
      responses:
        '200':
          description: Product details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProductDetailResponse'

  /categories:
    get:
      tags: [Categories]
      summary: List all categories
      responses:
        '200':
          description: List of categories
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/CategoryResponse'

  /cart:
    get:
      tags: [Cart]
      summary: Get current user's cart
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Cart contents
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CartResponse'

    post:
      tags: [Cart]
      summary: Add item to cart
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CartItemAdd'
      responses:
        '200':
          description: Item added to cart
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CartResponse'

  /cart/items/{itemId}:
    put:
      tags: [Cart]
      summary: Update cart item quantity
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/cartItemId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CartItemUpdate'
      responses:
        '200':
          description: Cart item updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CartResponse'
    delete:
      tags: [Cart]
      summary: Remove item from cart
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/cartItemId'
      responses:
        '200':
          description: Item removed from cart
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CartResponse'

  /checkout:
    post:
      tags: [Checkout]
      summary: Initiate checkout process
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CheckoutRequest'
      responses:
        '200':
          description: Checkout initiated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CheckoutResponse'

  /orders:
    get:
      tags: [Orders]
      summary: List user orders
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/page'
        - $ref: '#/components/parameters/limit'
        - $ref: '#/components/parameters/status'
      responses:
        '200':
          description: List of orders
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/OrderResponse'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

    post:
      tags: [Orders]
      summary: Create new order (from checkout)
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OrderCreate'
      responses:
        '201':
          description: Order created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrderResponse'

  /orders/{orderId}:
    get:
      tags: [Orders]
      summary: Get order details
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/orderId'
      responses:
        '200':
          description: Order details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrderDetailResponse'

  /payments/{paymentId}/capture:
    post:
      tags: [Payments]
      summary: Capture payment
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/paymentId'
      responses:
        '200':
          description: Payment captured
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaymentResponse'

  /shipping/rates:
    post:
      tags: [Shipping]
      summary: Calculate shipping rates
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ShippingRateRequest'
      responses:
        '200':
          description: Shipping rates
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ShippingRateResponse'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    refreshToken:
      type: http
      scheme: bearer
      bearerFormat: JWT

  parameters:
    page:
      name: page
      in: query
      description: Page number
      schema:
        type: integer
        default: 1
    limit:
      name: limit
      in: query
      description: Items per page
      schema:
        type: integer
        default: 20
        maximum: 100
    category:
      name: category
      in: query
      description: Filter by category ID
      schema:
        type: string
        format: uuid
    search:
      name: search
      in: query
      description: Search term
      schema:
        type: string
    sort:
      name: sort
      in: query
      description: Sort field and direction
      schema:
        type: string
        enum: [price_asc, price_desc, name_asc, name_desc, featured]
    productId:
      name: id
      in: path
      description: Product ID
      required: true
      schema:
        type: string
        format: uuid
    cartItemId:
      name: itemId
      in: path
      description: Cart item ID
      required: true
      schema:
        type: string
        format: uuid
    orderId:
      name: orderId
      in: path
      description: Order ID
      required: true
      schema:
        type: string
        format: uuid
    paymentId:
      name: paymentId
      in: path
      description: Payment ID
      required: true
      schema:
        type: string
        format: uuid
    status:
      name: status
      in: query
      description: Filter by order status
      schema:
        type: string
        enum: [pending, processing, shipped, delivered, cancelled, refunded]

  schemas:
    LoginRequest:
      type: object
      required: [email, password]
      properties:
        email:
          type: string
          format: email
        password:
          type: string
          format: password
          minLength: 8

    AuthResponse:
      type: object
      properties:
        access_token:
          type: string
        refresh_token:
          type: string
        expires_in:
          type: integer
        token_type:
          type: string
          example: bearer

    UserCreate:
      type: object
      required: [email, password, first_name, last_name]
      properties:
        email:
          type: string
          format: email
        password:
          type: string
          format: password
          minLength: 8
        first_name:
          type: string
        last_name:
          type: string
        phone:
          type: string

    UserResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        first_name:
          type: string
        last_name:
          type: string
        phone:
          type: string
        role:
          type: string
          enum: [customer, admin, staff]
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    UserUpdate:
      type: object
      properties:
        first_name:
          type: string
        last_name:
          type: string
        phone:
          type: string
        password:
          type: string
          format: password
          minLength: 8

    ProductCreate:
      type: object
      required: [name, description, base_price, category_id]
      properties:
        name:
          type: string
        description:
          type: string
        base_price:
          type: number
          format: decimal
        category_id:
          type: string
          format: uuid
        is_active:
          type: boolean
          default: true
        is_featured:
          type: boolean
          default: false
        images:
          type: array
          items:
            type: string
            format: uri

    ProductResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        base_price:
          type: number
          format: decimal
        category:
          $ref: '#/components/schemas/CategorySimple'
        is_active:
          type: boolean
        is_featured:
          type: boolean
        average_rating:
          type: number
          format: float
        review_count:
          type: integer
        created_at:
          type: string
          format: date-time

    ProductDetailResponse:
      allOf:
        - $ref: '#/components/schemas/ProductResponse'
        - type: object
          properties:
            variants:
              type: array
              items:
                $ref: '#/components/schemas/ProductVariant'
            reviews:
              type: array
              items:
                $ref: '#/components/schemas/Review'
            related_products:
              type: array
              items:
                $ref: '#/components/schemas/ProductResponse'

    ProductVariant:
      type: object
      properties:
        id:
          type: string
          format: uuid
        variant_name:
          type: string
        sku:
          type: string
        price:
          type: number
          format: decimal
        weight:
          type: number
          format: decimal
        unit:
          type: string
          enum: [lb, kg, each, dozen]
        image_url:
          type: string
          format: uri
        is_available:
          type: boolean
        stock_quantity:
          type: integer

    CategoryResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        parent_id:
          type: string
          format: uuid
          nullable: true
        image_url:
          type: string
          format: uri
        product_count:
          type: integer

    CategorySimple:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string

    CartResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        items:
          type: array
          items:
            $ref: '#/components/schemas/CartItem'
        subtotal:
          type: number
          format: decimal
        tax_estimate:
          type: number
          format: decimal
        shipping_estimate:
          type: number
          format: decimal
        total:
          type: number
          format: decimal

    CartItem:
      type: object
      properties:
        id:
          type: string
          format: uuid
        product_variant:
          $ref: '#/components/schemas/ProductVariant'
        quantity:
          type: integer
        unit_price:
          type: number
          format: decimal
        total_price:
          type: number
          format: decimal

    CartItemAdd:
      type: object
      required: [product_variant_id, quantity]
      properties:
        product_variant_id:
          type: string
          format: uuid
        quantity:
          type: integer
          minimum: 1

    CartItemUpdate:
      type: object
      required: [quantity]
      properties:
        quantity:
          type: integer
          minimum: 1

    CheckoutRequest:
      type: object
      required: [shipping_address_id, payment_method_id, shipping_method]
      properties:
        shipping_address_id:
          type: string
          format: uuid
        payment_method_id:
          type: string
          format: uuid
        shipping_method:
          type: string
        notes:
          type: string

    CheckoutResponse:
      type: object
      properties:
        order_id:
          type: string
          format: uuid
        payment_intent_id:
          type: string
        client_secret:
          type: string
        status:
          type: string
          enum: [requires_payment_method, requires_confirmation, requires_action, processing, succeeded, failed]
        total_amount:
          type: number
          format: decimal

    OrderResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        order_number:
          type: string
        status:
          type: string
          enum: [pending, processing, shipped, delivered, cancelled, refunded]
        subtotal:
          type: number
          format: decimal
        tax:
          type: number
          format: decimal
        shipping_cost:
          type: number
          format: decimal
        total:
          type: number
          format: decimal
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    OrderDetailResponse:
      allOf:
        - $ref: '#/components/schemas/OrderResponse'
        - type: object
          properties:
            items:
              type: array
              items:
                $ref: '#/components/schemas/OrderItem'
            shipping_address:
              $ref: '#/components/schemas/Address'
            payment:
              $ref: '#/components/schemas/PaymentResponse'
            shipping:
              $ref: '#/components/schemas/ShippingResponse'

    OrderItem:
      type: object
      properties:
        id:
          type: string
          format: uuid
        product_variant:
          $ref: '#/components/schemas/ProductVariant'
        quantity:
          type: integer
        unit_price:
          type: number
          format: decimal
        total_price:
          type: number
          format: decimal

    OrderCreate:
      type: object
      required: [cart_id, shipping_address_id, payment_method_id, shipping_method]
      properties:
        cart_id:
          type: string
          format: uuid
        shipping_address_id:
          type: string
          format: uuid
        payment_method_id:
          type: string
          format: uuid
        shipping_method:
          type: string
        notes:
          type: string

    Address:
      type: object
      properties:
        id:
          type: string
          format: uuid
        address_type:
          type: string
          enum: [home, work, other]
        street:
          type: string
        city:
          type: string
        state:
          type: string
        postal_code:
          type: string
        country:
          type: string
        is_default:
          type: boolean

    PaymentResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        amount:
          type: number
          format: decimal
        currency:
          type: string
          default: USD
        status:
          type: string
          enum: [pending, completed, failed, refunded]
        payment_method:
          type: string
        transaction_id:
          type: string
        created_at:
          type: string
          format: date-time

    ShippingResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        carrier:
          type: string
        tracking_number:
          type: string
        service_level:
          type: string
          enum: [standard, express, overnight]
        estimated_delivery:
          type: string
          format: date-time
        actual_delivery:
          type: string
          format: date-time
          nullable: true
        status:
          type: string

    ShippingRateRequest:
      type: object
      required: [address, items]
      properties:
        address:
          $ref: '#/components/schemas/Address'
        items:
          type: array
          items:
            type: object
            properties:
              product_variant_id:
                type: string
                format: uuid
              quantity:
                type: integer
              weight:
                type: number
                format: decimal
              unit:
                type: string
                enum: [lb, kg]

    ShippingRateResponse:
      type: object
      properties:
        carrier:
          type: string
        service_level:
          type: string
          enum: [standard, express, overnight]
        cost:
          type: number
          format: decimal
        estimated_delivery:
          type: string
          format: date-time
        description:
          type: string

    Review:
      type: object
      properties:
        id:
          type: string
          format: uuid
        user:
          type: object
          properties:
            id:
              type: string
              format: uuid
            first_name:
              type: string
            last_name:
              type: string
        rating:
          type: integer
          minimum: 1
          maximum: 5
        title:
          type: string
        comment:
          type: string
        created_at:
          type: string
          format: date-time

    Pagination:
      type: object
      properties:
        total:
          type: integer
        page:
          type: integer
        limit:
          type: integer
        total_pages:
          type: integer

    ErrorResponse:
      type: object
      properties:
        error:
          type: object
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: object
              additionalProperties: true

  responses:
    BadRequest:
      description: Bad request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    Unauthorized:
      description: Unauthorized
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    Forbidden:
      description: Forbidden
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    InternalServerError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

## 3. Milestone Timeline (6-8 Weeks)

### Week 1-2: Foundation & Core Setup
**Milestone: Project Setup & Basic Functionality**
- **Tech Stack Decision**: Finalize Next.js + NestJS + PostgreSQL
- **Project Setup**: Initialize monorepo with Turborepo
- **Database**: Set up PostgreSQL with Prisma ORM
- **Authentication**: Implement JWT auth with NextAuth.js
- **Basic API**: CRUD for Users, Products, Categories
- **Frontend**: Basic layout, routing, and theme setup
- **CI/CD**: Initial pipeline setup with GitHub Actions
- **Deliverables**: Working dev environment, basic API endpoints, auth flow

### Week 3-4: Product Catalog & Storefront
**Milestone: Complete Product Management & Storefront**
- **Product Management**: Full CRUD with variants, images, categories
- **Search & Filtering**: Implement product search with filters
- **Storefront UI**: Product listing, detail pages, category navigation
- **Admin Panel**: Basic product management interface
- **API**: Complete product endpoints with pagination
- **Testing**: Unit tests for product services
- **Deliverables**: Functional storefront, admin product management

### Week 5: Shopping Cart & Checkout
**Milestone: Complete Purchase Flow**
- **Cart System**: Add/remove items, quantity updates, persistence
- **Checkout Process**: Multi-step checkout with address/payment
- **Shipping Calculation**: Real-time shipping rate API
- **Payment Integration**: Stripe integration for payments
- **Order Creation**: Complete order processing flow
- **Testing**: Integration tests for cart/checkout
- **Deliverables**: End-to-end purchase flow working

### Week 6: Admin Dashboard & Order Management
**Milestone: Complete Admin Functionality**
- **Order Management**: View, process, ship orders
- **Inventory Management**: Stock tracking, low stock alerts
- **User Management**: Admin user CRUD
- **Reports**: Basic sales and inventory reports
- **Testing**: Admin functionality tests
- **Deliverables**: Full admin dashboard with order management

### Week 7: Testing, Optimization & Deployment
**Milestone: Production Ready**
- **Testing**: Comprehensive test suite (unit, integration, e2e)
- **Performance**: Optimize API queries, implement caching
- **Security**: Penetration testing, security hardening
- **Documentation**: Complete API docs, user guides
- **Deployment**: Production deployment with monitoring
- **Deliverables**: Production-ready application with full test coverage

### Week 8: Final Touches & Launch
**Milestone: Launch Preparation**
- **Final Testing**: User acceptance testing
- **Content**: Product data loading, SEO optimization
- **Monitoring**: Set up error tracking and analytics
- **Backup**: Database backup system
- **Launch**: Go-live checklist completion
- **Deliverables**: Fully launched, monitored e-commerce platform

## 4. Tech Stack Decision

### Recommended Stack: Next.js + NestJS + PostgreSQL

**Frontend:**
- **Framework**: Next.js 14 (App Router)
- **UI Library**: Tailwind CSS + ShadCN UI components
- **State Management**: Zustand or React Context
- **Forms**: React Hook Form + Zod validation
- **Animation**: Framer Motion
- **Internationalization**: next-intl

**Backend:**
- **Framework**: NestJS (TypeScript)
- **Database**: PostgreSQL 15+
- **ORM**: Prisma (with migrations)
- **Authentication**: JWT with Passport.js
- **API**: RESTful with OpenAPI/Swagger docs
- **Real-time**: WebSockets for order updates
- **File Storage**: AWS S3 or Cloudinary

**DevOps:**
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Hosting**: Vercel (frontend) + AWS EC2/RDS (backend)
- **Monitoring**: Sentry + Prometheus/Grafana
- **Logging**: Winston + ELK Stack
- **Caching**: Redis

**Testing:**
- **Unit**: Jest + React Testing Library
- **Integration**: Supertest + NestJS Testing Module
- **E2E**: Cypress or Playwright
- **API**: Postman/Newman for contract testing

**Alternative Considered: Django + DRF**
While Django is excellent, the modern JavaScript ecosystem provides better frontend integration and developer experience for full-stack development. The Next.js + NestJS combination offers:
- Better TypeScript support
- Superior frontend performance with React
- More modern developer tooling
- Easier to find full-stack JavaScript developers
- Better ecosystem for real-time features

## 5. File Structure

```bash
seafood-ecommerce/
├── apps/
│   ├── frontend/                  # Next.js application
│   │   ├── public/                 # Static assets
│   │   ├── src/
│   │   │   ├── app/                # Next.js app router
│   │   │   │   ├── (auth)/         # Auth routes
│   │   │   │   ├── (main)/         # Main app routes
│   │   │   │   │   ├── cart/       # Cart pages
│   │   │   │   │   ├── checkout/   # Checkout flow
│   │   │   │   │   ├── products/   # Product pages
│   │   │   │   │   ├── orders/     # Order pages
│   │   │   │   │   └── ...
│   │   │   ├── components/         # Reusable components
│   │   │   ├── hooks/              # Custom hooks
│   │   │   ├── lib/                # Utility functions
│   │   │   ├── providers/          # Context providers
│   │   │   ├── styles/             # Global styles
│   │   │   ├── types/              # TypeScript types
│   │   │   └── ...
│   │   ├── next.config.js
│   │   └── package.json
│   │
│   └── backend/                   # NestJS application
│       ├── src/
│       │   ├── auth/               # Authentication module
│       │   ├── cart/               # Cart module
│       │   ├── categories/         # Categories module
│       │   ├── checkout/           # Checkout module
│       │   ├── common/             # Shared utilities
│       │   ├── config/             # Configuration
│       │   ├── database/           # Database module
│       │   ├── orders/             # Orders module
│       │   ├── payments/           # Payments module
│       │   ├── products/           # Products module
│       │   ├── shipping/           # Shipping module
│       │   ├── users/              # Users module
│       │   ├── app.module.ts
│       │   ├── main.ts
│       │   └── ...
│       ├── prisma/                # Prisma schema & migrations
│       ├── test/                  # Backend tests
│       ├── .env
│       └── package.json
│
├── packages/                     # Shared packages
│   ├── ui/                       # Shared UI components
│   ├── types/                    # Shared TypeScript types
│   ├── constants/                # Shared constants
│   └── ...
│
├── docs/                        # Documentation
│   ├── api/                      # API documentation
│   ├── architecture/             # Architecture decisions
│   ├── deployment/               # Deployment guides
│   └── ...
│
├── scripts/                     # Utility scripts
│   ├── db/                       # Database scripts
│   ├── deploy/                   # Deployment scripts
│   └── ...
│
├── .github/                     # GitHub configuration
│   ├── workflows/                # CI/CD workflows
│   └── ...
│
├── docker/                      # Docker configuration
│   ├── compose.yml
│   ├── Dockerfile.frontend
│   └── Dockerfile.backend
│
├── .eslintrc.json
├── .prettierrc
├── package.json                  # Root package.json
├── turbo.json                    # Turborepo configuration
└── README.md

## 6. CI/CD Design

### GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

env:
  NODE_VERSION: 18
  POSTGRES_VERSION: 15
  DOCKER_COMPOSE_VERSION: v2

jobs:
  setup:
    name: Setup Environment
    runs-on: ubuntu-latest
    outputs:
      cache-key: ${{ steps.cache-key.outputs.value }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Generate cache key
        id: cache-key
        run: echo "value=$(date +%Y-%m-%W)-${{ hashFiles('**/package.json', '**/yarn.lock') }}" >> $GITHUB_OUTPUT

  lint:
    name: Lint & Format
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'yarn'

      - name: Install dependencies
        run: yarn install --frozen-lockfile

      - name: Run ESLint
        run: yarn lint

      - name: Run Prettier
        run: yarn format:check

  test:
    name: Test Suite
    needs: setup
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:${{ env.POSTGRES_VERSION }}
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: seafood_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'yarn'

      - name: Install dependencies
        run: yarn install --frozen-lockfile

      - name: Run database migrations
        run: yarn db:migrate
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/seafood_test

      - name: Run unit tests
        run: yarn test:unit

      - name: Run integration tests
        run: yarn test:integration

      - name: Run E2E tests
        run: yarn test:e2e
        env:
          BASE_URL: http://localhost:3000

  build:
    name: Build Applications
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'yarn'

      - name: Install dependencies
        run: yarn install --frozen-lockfile

      - name: Build frontend
        run: yarn build:frontend

      - name: Build backend
        run: yarn build:backend

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-artifacts
          path: |
            apps/frontend/.next/
            apps/backend/dist/

  docker:
    name: Build Docker Images
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Download build artifacts
        uses: actions/download-artifact@v3
        with:
          name: build-artifacts

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        if: github.ref == 'refs/heads/main'
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_HUB_USERNAME }}
          password: ${{ secrets.DOCKER_HUB_TOKEN }}

      - name: Build and push frontend
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./docker/Dockerfile.frontend
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: seafood-ecommerce/frontend:latest,seafood-ecommerce/frontend:${{ github.sha }}

      - name: Build and push backend
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./docker/Dockerfile.backend
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: seafood-ecommerce/backend:latest,seafood-ecommerce/backend:${{ github.sha }}

  deploy-staging:
    name: Deploy to Staging
    needs: docker
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.seafoodmarket.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install SSH key
        uses: shimataro/ssh-key-action@v2
        with:
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          known_hosts: ${{ secrets.KNOWN_HOSTS }}

      - name: Deploy with Docker Compose
        run: |
          ssh -o StrictHostKeyChecking=no ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }} << 'EOF'
          cd /opt/seafood-ecommerce
          git pull origin develop
          docker-compose -f docker-compose.staging.yml pull
          docker-compose -f docker-compose.staging.yml up -d --build
          docker system prune -f
          EOF

  deploy-production:
    name: Deploy to Production
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://seafoodmarket.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install SSH key
        uses: shimataro/ssh-key-action@v2
        with:
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          known_hosts: ${{ secrets.KNOWN_HOSTS }}

      - name: Deploy with Docker Compose
        run: |
          ssh -o StrictHostKeyChecking=no ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }} << 'EOF'
          cd /opt/seafood-ecommerce
          git pull origin main
          docker-compose -f docker-compose.prod.yml pull
          docker-compose -f docker-compose.prod.yml up -d --build
          docker system prune -f
          EOF

      - name: Notify Slack
        uses: rtCamp/action-slack-notify@v2
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
          SLACK_COLOR: good
          SLACK_TITLE: Production Deployment
          SLACK_MESSAGE: 'Production deployment completed successfully :rocket:'

### Docker Configuration

```yaml
# docker-compose.yml (development)
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: docker/Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:4000
      - NODE_ENV=development
    volumes:
      - ./apps/frontend:/app
      - /app/node_modules
    depends_on:
      - backend
    networks:
      - seafood-network

  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    ports:
      - "4000:4000"
    environment:
      - DATABASE_URL=postgresql://dev:dev@postgres:5432/seafood_dev
      - JWT_SECRET=${JWT_SECRET}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - NODE_ENV=development
    depends_on:
      - postgres
      - redis
    networks:
      - seafood-network

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: seafood_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - seafood-network

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - seafood-network

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@seafood.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres
    networks:
      - seafood-network

volumes:
  postgres-data:
  redis-data:

networks:
  seafood-network:
    driver: bridge
```

### Deployment Strategy

**Blue-Green Deployment:**
- Maintain two identical production environments (Blue and Green)
- Deploy new version to inactive environment
- Switch traffic using load balancer
- Rollback by switching back if issues detected

**Feature Flags:**
- Implement feature toggles for gradual rollouts
- Use LaunchDarkly or custom solution
- Enable A/B testing and canary releases

**Monitoring & Rollback:**
- Automated health checks post-deployment
- Sentry for error tracking
- Prometheus/Grafana for performance monitoring
- Automated rollback on critical failures
```
```
