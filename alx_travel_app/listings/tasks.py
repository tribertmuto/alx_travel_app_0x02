from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Payment, Booking


@shared_task
def send_payment_confirmation_email(payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)
        booking = payment.booking
        user = booking.user
        
        subject = f'Payment Confirmation - Booking {booking.reference}'
        
        context = {
            'user': user,
            'booking': booking,
            'payment': payment,
        }
        
        html_message = f"""
        <html>
        <body>
            <h2>Payment Confirmation</h2>
            <p>Dear {user.first_name or user.username},</p>
            
            <p>Your payment has been successfully processed!</p>
            
            <h3>Payment Details:</h3>
            <ul>
                <li><strong>Transaction ID:</strong> {payment.transaction_id}</li>
                <li><strong>Booking Reference:</strong> {booking.reference}</li>
                <li><strong>Amount:</strong> {payment.amount} {payment.currency}</li>
                <li><strong>Payment Method:</strong> {payment.payment_method or 'N/A'}</li>
                <li><strong>Status:</strong> {payment.get_status_display()}</li>
                <li><strong>Date:</strong> {payment.completed_at.strftime('%Y-%m-%d %H:%M:%S') if payment.completed_at else 'N/A'}</li>
            </ul>
            
            <p>Thank you for choosing ALX Travel App!</p>
            
            <p>Best regards,<br>
            ALX Travel App Team</p>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Payment confirmation email sent to {user.email}"
        
    except Payment.DoesNotExist:
        return f"Payment with ID {payment_id} not found"
    except Exception as e:
        return f"Error sending payment confirmation email: {str(e)}"


@shared_task
def send_payment_failed_email(payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)
        booking = payment.booking
        user = booking.user
        
        subject = f'Payment Failed - Booking {booking.reference}'
        
        html_message = f"""
        <html>
        <body>
            <h2>Payment Failed</h2>
            <p>Dear {user.first_name or user.username},</p>
            
            <p>Unfortunately, your payment could not be processed.</p>
            
            <h3>Payment Details:</h3>
            <ul>
                <li><strong>Transaction ID:</strong> {payment.transaction_id}</li>
                <li><strong>Booking Reference:</strong> {booking.reference}</li>
                <li><strong>Amount:</strong> {payment.amount} {payment.currency}</li>
                <li><strong>Status:</strong> {payment.get_status_display()}</li>
            </ul>
            
            <p>Please try again or contact our support team for assistance.</p>
            
            <p>Best regards,<br>
            ALX Travel App Team</p>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Payment failed email sent to {user.email}"
        
    except Payment.DoesNotExist:
        return f"Payment with ID {payment_id} not found"
    except Exception as e:
        return f"Error sending payment failed email: {str(e)}"