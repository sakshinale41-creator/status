from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [

    path('', views.product_list, name='product_list'),

    # Baki sagle paths tasech thev
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('profile/', views.profile, name='profile'),

    # --- Mobile OTP Signup URLs ---
    path('signup/', views.phone_signup_view, name='phone_signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.customer_logout, name='logout'),
    path('track-order/', views.profile, name='track_order'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('payment/<int:order_id>/', views.payment_view, name='payment'),
]