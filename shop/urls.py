from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
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

]