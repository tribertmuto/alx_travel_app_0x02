# ALX Travel App 0x02 - Chapa Payment Integration

A Django-based travel booking application with integrated Chapa payment processing system.

## Features

- **Payment Processing**: Secure payment handling using Chapa API
- **Booking Management**: Complete booking and payment workflow
- **Email Notifications**: Automated payment confirmation emails via Celery
- **Payment Verification**: Real-time payment status verification
- **Admin Interface**: Django admin for managing bookings and payments

## Project Structure

```
alx_travel_app/
├── alx_travel_app/          # Django project settings
│   ├── __init__.py
│   ├── settings.py          # Main configuration
│   ├── urls.py             # URL routing
│   ├── wsgi.py             # WSGI configuration
│   └── celery.py           # Celery configuration
├── listings/               # Main application
│   ├── models.py           # Booking and Payment models
│   ├── views.py            # Payment API endpoints
│   ├── admin.py            # Admin configuration
│   ├── tasks.py            # Celery tasks for emails
│   └── urls.py             # App URL routing
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── test_chapa_integration.py # Test script
```

## Setup Instructions

### 1. Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd alx_travel_app_0x02/alx_travel_app
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Chapa API Configuration

1. Create account at [Chapa Developer Portal](https://developer.chapa.co/)
2. Obtain your API keys (Secret and Public keys)
3. Copy `.env.example` to `.env` and configure:

```env
# Chapa API Configuration
CHAPA_SECRET_KEY=your-chapa-secret-key-here
CHAPA_PUBLIC_KEY=your-chapa-public-key-here

# Django Settings
SECRET_KEY=your-django-secret-key
DEBUG=True

# Email Configuration (for notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@alxtravelapp.com

# Celery Configuration (Redis required)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Database Setup

1. Create and apply migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

2. Create superuser:
```bash
python manage.py createsuperuser
```

### 4. Background Task Setup

1. Install and start Redis:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Windows
# Download and install Redis from official website
```

2. Start Celery worker (in a separate terminal):
```bash
celery -A alx_travel_app worker --loglevel=info
```

### 5. Run Development Server

```bash
python manage.py runserver
```

## API Endpoints

### Payment Initiation
**POST** `/api/payments/initiate/`

Initiates a payment transaction with Chapa.

**Request Body:**
```json
{
    "booking_id": 1,
    "amount": "100.00",
    "phone_number": "+251912345678",
    "return_url": "https://yourapp.com/payment-success/"
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Payment initiated successfully",
    "data": {
        "checkout_url": "https://checkout.chapa.co/checkout/payment/...",
        "transaction_id": "tx_abc123456789",
        "payment_id": 1
    }
}
```

### Payment Verification
**GET** `/api/payments/verify/<transaction_id>/`

Verifies payment status with Chapa and updates local database.

**Response:**
```json
{
    "status": "success",
    "data": {
        "transaction_id": "tx_abc123456789",
        "payment_status": "completed",
        "amount": "100.00",
        "chapa_reference": "chapa_ref_123",
        "payment_method": "telebirr",
        "completed_at": "2024-01-15T10:30:00Z"
    }
}
```

### Payment Status
**GET** `/api/payments/status/<payment_id>/`

Retrieves current payment status from local database.

### Payment Callback
**POST** `/api/payments/callback/`

Webhook endpoint for Chapa to send payment status updates.

## Models

### Booking Model
```python
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Payment Model
```python
class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=255, unique=True)
    chapa_reference = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='ETB')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES)
    payment_method = models.CharField(max_length=50, blank=True)
    checkout_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
```

## Payment Workflow

1. **Booking Creation**: User creates a booking
2. **Payment Initiation**: 
   - POST to `/api/payments/initiate/` with booking details
   - System creates Payment record with 'pending' status
   - Chapa returns checkout URL
3. **User Payment**: User completes payment on Chapa's platform
4. **Status Update**: 
   - Chapa sends callback to `/api/payments/callback/`
   - OR manual verification via `/api/payments/verify/<tx_id>/`
5. **Email Notification**: 
   - Celery task sends confirmation email on successful payment
   - Failure email sent if payment fails

## Testing

### Unit Tests
```bash
python manage.py test
```

### Integration Test
```bash
python test_chapa_integration.py
```

### Sandbox Testing

1. Use Chapa sandbox environment for testing
2. Test payment initiation with sample data
3. Verify webhook callbacks work correctly
4. Check email notifications are sent

### Test Payment Data
```json
{
    "booking_id": 1,
    "amount": "10.00",
    "phone_number": "+251912345678",
    "return_url": "http://localhost:8000/payment-success/"
}
```

## Security Features

- Environment variable configuration for sensitive data
- CSRF protection on Django views
- Request timeout handling
- Proper error handling and logging
- Transaction ID uniqueness enforcement
- User permission checks on payment operations

## Error Handling

The system handles various error scenarios:
- Invalid Chapa API credentials
- Network timeouts
- Duplicate payment attempts
- Invalid booking references
- Payment verification failures

## Deployment Considerations

1. **Environment Variables**: Ensure all required environment variables are set
2. **HTTPS**: Use HTTPS in production for webhook callbacks
3. **Database**: Use PostgreSQL or similar in production
4. **Celery**: Use production message broker (Redis/RabbitMQ)
5. **Logging**: Implement comprehensive logging for payment transactions
6. **Monitoring**: Set up monitoring for payment failures and webhook issues

## Dependencies

- Django 4.2.7
- Django REST Framework 3.14.0
- python-decouple 3.8
- requests 2.31.0
- celery 5.3.4
- redis 5.0.1

## Support

For issues and questions:
1. Check Chapa documentation: https://developer.chapa.co/
2. Review Django REST Framework docs: https://www.django-rest-framework.org/
3. File issues in the project repository

## License

This project is part of the ALX Software Engineering program.

