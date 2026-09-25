from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('profile/', views.profile, name='profile'),  # He aadhi gheun yaa
    path('cart/', views.cart_detail, name='cart_detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('track/', views.track_order, name='track_order'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
]