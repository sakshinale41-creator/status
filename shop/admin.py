from django.contrib import admin
from django.db.models import Sum
from .models import Category, Product, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'available', 'created']
    list_filter = ['available', 'created']
    list_editable = ['price', 'stock', 'available']
    prepopulated_fields = {'slug': ('name',)}


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Live Order Details & Single-click Status Update
    list_display = ['id', 'full_name', 'phone_number', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    list_editable = ['status']  # Pending -> Processing -> Shipped -> Delivered
    inlines = [OrderItemInline]

    # Simple Sales Analytics on Admin Dashboard
    def changelist_view(self, request, extra_context=None):
        total_earnings = Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_orders = Order.objects.count()
        extra_context = extra_context or {}
        extra_context['total_earnings'] = total_earnings
        extra_context['total_orders'] = total_orders
        return super().changelist_view(request, extra_context=extra_context)