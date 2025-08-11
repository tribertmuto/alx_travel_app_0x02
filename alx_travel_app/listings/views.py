import requests
import uuid
import json
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Booking, Payment
from .tasks import send_payment_confirmation_email, send_payment_failed_email


CHAPA_BASE_URL = "https://api.chapa.co/v1"
CHAPA_SANDBOX_URL = "https://api.chapa.co/v1"


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    try:
        data = request.data
        booking_id = data.get('booking_id')
        amount = data.get('amount')
        
        if not booking_id or not amount:
            return Response({
                'error': 'booking_id and amount are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        if hasattr(booking, 'payment'):
            return Response({
                'error': 'Payment already exists for this booking'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        transaction_id = f"tx_{uuid.uuid4().hex[:12]}"
        
        payment_data = {
            'amount': str(amount),
            'currency': 'ETB',
            'email': request.user.email,
            'first_name': request.user.first_name or request.user.username,
            'last_name': request.user.last_name or '',
            'phone_number': data.get('phone_number', ''),
            'tx_ref': transaction_id,
            'callback_url': f"{request.build_absolute_uri('/').rstrip('/')}/api/payments/callback/",
            'return_url': data.get('return_url', f"{request.build_absolute_uri('/').rstrip('/')}/payment-success/"),
            'customization': {
                'title': 'ALX Travel App',
                'description': f'Payment for booking {booking.reference}'
            }
        }
        
        headers = {
            'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            f"{CHAPA_BASE_URL}/transaction/initialize",
            headers=headers,
            json=payment_data,
            timeout=30
        )
        
        if response.status_code == 200:
            chapa_response = response.json()
            
            if chapa_response.get('status') == 'success':
                payment = Payment.objects.create(
                    booking=booking,
                    transaction_id=transaction_id,
                    amount=Decimal(str(amount)),
                    status='pending',
                    checkout_url=chapa_response['data']['checkout_url']
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Payment initiated successfully',
                    'data': {
                        'checkout_url': chapa_response['data']['checkout_url'],
                        'transaction_id': transaction_id,
                        'payment_id': payment.id
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to initialize payment with Chapa',
                    'details': chapa_response.get('message', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': 'Failed to communicate with Chapa API',
                'status_code': response.status_code
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Booking.DoesNotExist:
        return Response({
            'error': 'Booking not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except requests.RequestException as e:
        return Response({
            'error': 'Network error occurred',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment(request, transaction_id):
    try:
        payment = get_object_or_404(Payment, transaction_id=transaction_id)
        
        if payment.booking.user != request.user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        headers = {
            'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        response = requests.get(
            f"{CHAPA_BASE_URL}/transaction/verify/{transaction_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            chapa_response = response.json()
            
            if chapa_response.get('status') == 'success':
                chapa_data = chapa_response.get('data', {})
                chapa_status = chapa_data.get('status', '').lower()
                
                if chapa_status == 'success':
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.chapa_reference = chapa_data.get('reference')
                    payment.payment_method = chapa_data.get('method')
                    payment.save()
                    
                    send_payment_confirmation_email.delay(payment.id)
                elif chapa_status in ['failed', 'cancelled']:
                    payment.status = chapa_status
                    payment.save()
                    
                    send_payment_failed_email.delay(payment.id)
                
                return Response({
                    'status': 'success',
                    'data': {
                        'transaction_id': transaction_id,
                        'payment_status': payment.status,
                        'amount': str(payment.amount),
                        'chapa_reference': payment.chapa_reference,
                        'payment_method': payment.payment_method,
                        'completed_at': payment.completed_at.isoformat() if payment.completed_at else None
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to verify payment with Chapa',
                    'details': chapa_response.get('message', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': 'Failed to communicate with Chapa API',
                'status_code': response.status_code
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Payment.DoesNotExist:
        return Response({
            'error': 'Payment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except requests.RequestException as e:
        return Response({
            'error': 'Network error occurred',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["POST"])
def payment_callback(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST
        
        transaction_id = data.get('tx_ref')
        chapa_status = data.get('status', '').lower()
        
        if not transaction_id:
            return JsonResponse({
                'error': 'Transaction ID not provided'
            }, status=400)
        
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return JsonResponse({
                'error': 'Payment not found'
            }, status=404)
        
        if chapa_status == 'success':
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.chapa_reference = data.get('reference')
            payment.payment_method = data.get('method')
            payment.save()
            
            send_payment_confirmation_email.delay(payment.id)
        elif chapa_status in ['failed', 'cancelled']:
            payment.status = chapa_status
            payment.save()
            
            send_payment_failed_email.delay(payment.id)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Payment status updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, payment_id):
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        
        if payment.booking.user != request.user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'status': 'success',
            'data': {
                'payment_id': payment.id,
                'transaction_id': payment.transaction_id,
                'booking_reference': payment.booking.reference,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'status': payment.status,
                'payment_method': payment.payment_method,
                'created_at': payment.created_at.isoformat(),
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                'checkout_url': payment.checkout_url if payment.status == 'pending' else None
            }
        }, status=status.HTTP_200_OK)
        
    except Payment.DoesNotExist:
        return Response({
            'error': 'Payment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)