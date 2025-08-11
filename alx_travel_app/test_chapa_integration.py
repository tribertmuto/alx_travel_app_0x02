#!/usr/bin/env python
"""
Test script to demonstrate Chapa payment integration
Run this after setting up the environment and running migrations
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')
django.setup()

from django.contrib.auth.models import User
from listings.models import Booking, Payment


def create_test_data():
    """Create test user and booking"""
    # Create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")
    else:
        print(f"Test user already exists: {user.username}")
    
    # Create test booking
    booking, created = Booking.objects.get_or_create(
        reference='BK-TEST-001',
        defaults={
            'user': user,
            'amount': Decimal('100.00'),
        }
    )
    if created:
        print(f"Created test booking: {booking.reference}")
    else:
        print(f"Test booking already exists: {booking.reference}")
    
    return user, booking


def test_payment_model():
    """Test Payment model creation"""
    user, booking = create_test_data()
    
    # Create payment
    payment = Payment.objects.create(
        booking=booking,
        transaction_id='test_tx_123456789',
        amount=booking.amount,
        status='pending'
    )
    
    print(f"Created payment: {payment}")
    print(f"Payment status: {payment.get_status_display()}")
    
    return payment


if __name__ == '__main__':
    print("=== ALX Travel App - Chapa Integration Test ===")
    print()
    
    try:
        # Test model creation
        payment = test_payment_model()
        
        # Test status update
        payment.status = 'completed'
        payment.save()
        print(f"Updated payment status to: {payment.get_status_display()}")
        
        print()
        print("✅ All tests passed!")
        print()
        print("Next steps:")
        print("1. Set up your .env file with Chapa credentials")
        print("2. Run: python manage.py makemigrations")
        print("3. Run: python manage.py migrate")
        print("4. Start the development server: python manage.py runserver")
        print("5. Start Celery worker: celery -A alx_travel_app worker --loglevel=info")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()