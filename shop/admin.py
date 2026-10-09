import csv
from django.contrib import admin
from django.db.models import Sum
from django import forms
from django.http import HttpResponse
from .models import Category, Product, Order, OrderItem, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


class ProductAdminForm(forms.ModelForm):
    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]

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
        if self.instance and self.instance.size:
            self.initial['size'] = [s.strip() for s in self.instance.size.split(',')]

    def clean_size(self):
        sizes = self.cleaned_data.get('size')
        if sizes:
            return ", ".join(sizes)
        return ""


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ['name', 'category', 'price', 'original_price', 'stock', 'available', 'created']
    search_fields = ('name',)
    list_filter = ['available', 'created', 'category']
    list_editable = ['price', 'original_price', 'stock', 'available']
    inlines = [ProductImageInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


# ==========================================
# EXPORT TO CSV FUNCTION FOR OWNER
# ==========================================
def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    content_type = 'text/csv'
    response = HttpResponse(content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename={opts.verbose_name_plural}-export.csv'

    writer = csv.writer(response)
    fields = ['id', 'full_name', 'phone_number', 'address', 'pincode', 'total_amount', 'status', 'is_paid',
              'created_at']

    writer.writerow([field.replace('_', ' ').capitalize() for field in fields])

    for obj in queryset:
        row = []
        for field in fields:
            value = getattr(obj, field)
            row.append(str(value))
        writer.writerow(row)

    return response


export_to_csv.short_description = "Download Selected Orders (CSV)"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'full_name', 'phone_number', 'address', 'pincode',
        'get_sizes', 'total_amount', 'status', 'is_paid', 'created_at'
    ]
    list_filter = ['status', 'is_paid', 'created_at']
    search_fields = ['full_name', 'phone_number', 'address', 'pincode']
    inlines = [OrderItemInline]
    actions = [export_to_csv, 'mark_paid', 'mark_shipped', 'mark_delivered']
    ordering = ['-created_at']

    def mark_paid(self, request, queryset):
        queryset.update(is_paid=True, status='Paid')
    mark_paid.short_description = 'Mark selected as PAID (payment received)'

    def mark_shipped(self, request, queryset):
        queryset.update(status='Shipped')
    mark_shipped.short_description = 'Mark selected as SHIPPED'

    def mark_delivered(self, request, queryset):
        queryset.update(status='Delivered')
    mark_delivered.short_description = 'Mark selected as DELIVERED'

    def get_sizes(self, obj):
        sizes = [item.size for item in obj.items.all() if item.size]
        return ", ".join(sizes) if sizes else "N/A"

    get_sizes.short_description = 'Size'