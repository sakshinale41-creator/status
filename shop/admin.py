from django.contrib import admin
from django.db.models import Sum
from django import forms
from django.template.response import TemplateResponse
from .models import Category, Product, Order, OrderItem, ProductImage


# ==========================================
# PYTHON 3.14 COMPATIBILITY BASE ADMIN CLASS
# ==========================================
class Python314AdminMixin:
    """
    Python 3.14 mule Django admin madhe ye nara 'super' object has no attribute 'dicts'
    error fix karnyasaathi ha mixin banavla ahe.
    """

    def changelist_view(self, request, extra_context=None):
        try:
            return super().changelist_view(request, extra_context=extra_context)
        except AttributeError:
            Model = self.model
            opts = Model._meta
            app_label = opts.app_label

            changelist = self.get_changelist_instance(request)
            media = self.media
            extra_context = extra_context or {}

            context = {
                **self.admin_site.each_context(request),
                'title': f'Select {opts.verbose_name} to change',
                'cl': changelist,
                'media': media,
                **extra_context,
            }
            request.current_app = self.admin_site.name
            return TemplateResponse(request, self.change_list_template or [
                f"admin/{app_label}/{Model._meta.model_name}/change_list.html",
                f"admin/{app_label}/change_list.html",
                "admin/change_list.html",
            ], context)


@admin.register(Category)
class CategoryAdmin(Python314AdminMixin, admin.ModelAdmin):
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
class ProductAdmin(Python314AdminMixin, admin.ModelAdmin):
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


@admin.register(Order)
class OrderAdmin(Python314AdminMixin, admin.ModelAdmin):
    list_display = ['id', 'full_name', 'phone_number', 'get_sizes', 'total_amount', 'status', 'created_at']
    inlines = [OrderItemInline]

    def get_sizes(self, obj):
        sizes = [item.size for item in obj.items.all() if item.size]
        return ", ".join(sizes) if sizes else "N/A"

    get_sizes.short_description = 'Size'