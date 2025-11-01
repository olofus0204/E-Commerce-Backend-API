# E-Commerce Backend API

A production-ready REST API for e-commerce applications built with FastAPI, PostgreSQL, and JWT authentication.

## Features

- **User Authentication**: JWT-based authentication with access and refresh tokens
- **Role-Based Access Control**: Customer and admin roles with permission management
- **Product Management**: Complete CRUD operations for products with categories
- **Hierarchical Categories**: Support for nested categories and subcategories
- **Shopping Cart**: Persistent cart management for authenticated users
- **Order Processing**: Full order lifecycle with status tracking
- **Payment Integration**: Support for Stripe and mock payment providers
- **Database Migrations**: Managed with Alembic
- **Docker Support**: Containerized application with docker-compose
- **Interactive API Documentation**: Auto-generated Swagger UI and ReDoc

## Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0.23
- **Authentication**: JWT (python-jose, passlib with bcrypt)
- **Validation**: Pydantic 2.5.0
- **Migrations**: Alembic 1.12.1
- **Payments**: Stripe 7.4.0
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or Docker)
- Stripe account (optional, for real payments)

## Quick Start with Docker

1. **Clone the repository**
```bash
git clone <repository-url>
cd E-Commerce-Backend-API
```

2. **Start the application**
```bash
docker-compose up -d --build
```

3. **Access the API**
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

The database migrations will run automatically on startup.

## Local Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/ecommerce_db
JWT_SECRET_KEY=your-secure-secret-key-min-32-characters
PAYMENT_PROVIDER=mock  # or 'stripe' for real payments
```

### 4. Create Database

```bash
createdb ecommerce_db
```

### 5. Run Migrations

```bash
alembic upgrade head
```

### 6. Start Server

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

### Base URL

```
http://localhost:8000/api/v1
```

### Authentication

Most endpoints require JWT authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Main Endpoints

#### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and receive tokens
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (revoke refresh token)

#### Users
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update profile
- `DELETE /users/me` - Delete account (soft delete)

#### Categories
- `GET /categories` - List all categories
- `GET /categories/{id}` - Get category details
- `POST /categories` - Create category (admin only)
- `PUT /categories/{id}` - Update category (admin only)
- `DELETE /categories/{id}` - Delete category (admin only)

#### Products
- `GET /products` - List products (with filtering, search, pagination)
- `GET /products/{id}` - Get product details
- `POST /products` - Create product (admin only)
- `PUT /products/{id}` - Update product (admin only)
- `DELETE /products/{id}` - Soft delete product (admin only)

#### Shopping Cart
- `GET /cart` - Get current cart
- `POST /cart/items` - Add item to cart
- `PUT /cart/items/{id}` - Update cart item quantity
- `DELETE /cart/items/{id}` - Remove item from cart
- `DELETE /cart` - Clear entire cart

#### Orders
- `GET /orders` - List orders (own orders or all for admin)
- `GET /orders/{id}` - Get order details
- `POST /orders` - Create order from cart
- `PUT /orders/{id}/status` - Update order status (admin only)
- `POST /orders/{id}/cancel` - Cancel order

#### Payments
- `POST /payments/process` - Process payment for order

For complete API documentation, visit http://localhost:8000/docs

## Database Migrations

### Create a New Migration

```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Creating an Admin User

By default, all registered users have the `customer` role. To create an admin user:

### Option 1: Register then Update (Recommended)

1. Register a new user via the API
2. Update the user's role in the database:

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

### Option 2: Using Docker

```bash
docker-compose exec db psql -U ecommerce_user -d ecommerce_db -c "UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';"
```

## Payment Configuration

### Mock Payment (Default)

Set in `.env`:
```env
PAYMENT_PROVIDER=mock
```

Mock payment always succeeds and is perfect for development and testing.

### Stripe Integration

1. Get your Stripe API keys from https://dashboard.stripe.com/apikeys

2. Configure in `.env`:
```env
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
```

3. For webhooks:
```env
STRIPE_WEBHOOK_SECRET=whsec_your_secret
```

## Project Structure

```
E-Commerce-Backend-API/
├── app/
│   ├── core/              # Core configuration and security
│   ├── models/            # SQLAlchemy database models
│   ├── schemas/           # Pydantic request/response schemas
│   ├── routes/            # API route handlers
│   ├── services/          # Business logic layer
│   ├── middleware/        # Authentication middleware
│   ├── utils/             # Utility functions
│   └── main.py            # FastAPI application entry
├── alembic/               # Database migrations
├── tests/                 # Test suite
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker container definition
├── docker-compose.yml     # Docker orchestration
└── README.md              # This file
```

## Environment Variables

See `.env.example` for all available configuration options:

- **App Settings**: APP_NAME, DEBUG, ENVIRONMENT
- **Server**: HOST, PORT
- **Database**: DATABASE_URL
- **JWT**: JWT_SECRET_KEY, JWT_ALGORITHM, token expiration times
- **CORS**: CORS_ORIGINS (comma-separated or JSON array)
- **Payment**: PAYMENT_PROVIDER, Stripe API keys
- **Logging**: LOG_LEVEL

## Docker Commands

```bash
# Build and start services
docker-compose up -d --build

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes database)
docker-compose down -v

# Run migrations
docker-compose exec api alembic upgrade head

# Access database
docker-compose exec db psql -U ecommerce_user -d ecommerce_db
```

## Testing the API

### Using Swagger UI

1. Navigate to http://localhost:8000/docs
2. Click "Try it out" on any endpoint
3. For authenticated endpoints:
   - First register/login to get tokens
   - Click "Authorize" button at top
   - Enter: `Bearer <your_access_token>`

### Using cURL

Register a user:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

## Security Considerations

### Production Deployment

Before deploying to production:

1. **Generate Strong JWT Secret**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Update Environment Variables**:
```env
DEBUG=False
ENVIRONMENT=production
JWT_SECRET_KEY=<generated-secret-key>
```

3. **Configure CORS**: Set specific allowed origins
```env
CORS_ORIGINS=["https://yourdomain.com"]
```

4. **Use HTTPS**: Always use HTTPS in production

5. **Secure Database**: Use strong passwords and restrict access

6. **Stripe**: Use production keys, not test keys

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Migration Issues

```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Force migration to specific version
alembic upgrade <revision>
```

### Port Already in Use

If port 8000 or 5432 is already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change host port
```

## License

This project is licensed under the terms in the LICENSE file.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (if available)
5. Submit a pull request

## Support

For issues and questions:
- Check the API documentation at `/docs`
- Review this README
- Open an issue on GitHub

---

Built with FastAPI, PostgreSQL, and modern Python best practices.
