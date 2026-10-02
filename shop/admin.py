from django.contrib import admin
from django.db.models import Sum
from django import forms
from .models import Category, Product, Order, OrderItem, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


# Product admin sathi custom form (checkboxes sathi)
class ProductAdminForm(forms.ModelForm):
    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]

    # Multiple checkboxes sathi field define keli
    size = forms.MultipleChoiceField(
        choices=SIZE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Jar aadhi data madhe size asel, tila comma-separated madhun list madhe convert karun form madhe daakhva
        if self.instance and self.instance.size:
            self.initial['size'] = [s.strip() for s in self.instance.size.split(',')]

    def clean_size(self):
        # Checkboxes che values comma-separated string madhe store karnyasathi
        sizes = self.cleaned_data.get('size')
        if sizes:
            return ", ".join(sizes)
        return ""


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm  # He custom form aapan product admin la dila
    list_display = ['name', 'category', 'price', 'stock', 'available', 'created']
    list_filter = ['available', 'created', 'category']
    list_editable = ['price', 'stock', 'available']
    inlines = [ProductImageInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'phone_number', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    list_editable = ['status']
    inlines = [OrderItemInline]

    def changelist_view(self, request, extra_context=None):
        total_earnings = Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_orders = Order.objects.count()
        extra_context = extra_context or {}
        extra_context['total_earnings'] = total_earnings
        extra_context['total_orders'] = total_orders
        return super().changelist_view(request, extra_context=extra_context)