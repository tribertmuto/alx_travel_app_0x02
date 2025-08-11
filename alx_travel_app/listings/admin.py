from django.contrib import admin
from .models import Booking, Payment


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'amount', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reference', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'booking', 'amount', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'currency', 'created_at', 'completed_at')
    search_fields = ('transaction_id', 'chapa_reference', 'booking__reference', 'booking__user__username')
    readonly_fields = ('transaction_id', 'created_at', 'updated_at', 'completed_at')
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.status == 'completed':
            readonly_fields.extend(['booking', 'amount', 'currency'])
        return readonly_fields