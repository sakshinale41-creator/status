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
        exclude = ('stock',)  # <-- Ithe stock exclude kela

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
    form = ProductAdminForm
    # 'stock' field list_display madhe add keli ahe, mhanje admin madhe stock disel
    list_display = ['name', 'category', 'price', 'stock', 'available', 'created']
    search_fields = ('name',)
    list_filter = ['available', 'created', 'category']
    # list_editable madhe stock pan taku shaktees jyamule direct admin list madhun pan stock badalata yeil
    list_editable = ['price', 'stock', 'available']
    inlines = [ProductImageInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'phone_number', 'get_sizes', 'total_amount', 'status', 'created_at']
    inlines = [OrderItemInline]

    def get_sizes(self, obj):
        # Hya order madhle sagle items chya sizes comma separated print karel
        sizes = [item.size for item in obj.items.all() if item.size]
        return ", ".join(sizes) if sizes else "N/A"

    get_sizes.short_description = 'Size'


admin.site.register(Order, OrderAdmin)