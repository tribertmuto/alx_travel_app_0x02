from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    path('payments/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payments/verify/<str:transaction_id>/', views.verify_payment, name='verify_payment'),
    path('payments/callback/', views.payment_callback, name='payment_callback'),
    path('payments/status/<int:payment_id>/', views.payment_status, name='payment_status'),
]