from django.shortcuts import render, redirect, get_object_or_404
from .models import Category, Product
from .models import Order, OrderItem
from django.db.models import Q, F
from django.db.models.functions import Greatest
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
import requests
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from .models import CustomerProfile
from django.contrib.auth import authenticate, login


# ---------- Order helpers (notification + access control) ----------
def _can_view_order(request, order):
    """Only the browser that placed the order (or staff) may open its pages."""
    if request.user.is_authenticated and request.user.is_staff:
        return True
    return order.id in request.session.get('my_orders', [])


def _order_summary(order):
    lines = [f"Order #{order.id}", f"Name: {order.full_name}", f"Phone: {order.phone_number}",
             f"Address: {order.address} - {order.pincode}", "Items:"]
    for it in order.items.all():
        lines.append(f"  - {it.product.name} | Size {it.size or '-'} | Qty {it.quantity} | Rs {it.price}")
    lines.append(f"Total: Rs {order.total_amount}")
    return "\n".join(lines)


def notify_owner(order):
    """Tell the shop owner about an order. Works only if env vars are set; never breaks the order."""
    text = "NEW ORDER - customer says PAID (please verify in GPay/PhonePe)\n\n" + _order_summary(order)
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
    if token and chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={'chat_id': chat_id, 'text': text}, timeout=5)
        except Exception:
            pass
    to = getattr(settings, 'ORDER_NOTIFY_EMAIL', '')
    if to:
        try:
            send_mail(f"New order #{order.id} - Status", text, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)
        except Exception:
            pass


# Simple Session-based Cart Helpers
def get_cart(request):
    cart = request.session.get('cart', {})
    return cart


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.filter(parent=None)  # Parent categories sathi
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)

        subcategories = category.subcategories.all()
        if subcategories.exists():
            products = products.filter(Q(category=category) | Q(category__in=subcategories))
        else:
            products = products.filter(category=category)

    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    # Cover photo for each category card (latest product in it or in its subcategories)
    categories = list(categories)
    for c in categories:
        cover = Product.objects.filter(available=True).exclude(image='').filter(
            Q(category=c) | Q(category__parent=c)).order_by('-created').first()
        c.cover = cover.image.url if cover else None

    context = {
        'category': category,
        'categories': categories,
        'products': products,
    }
    return render(request, 'shop/product_list.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    saving = None
    if product.original_price and product.original_price > product.price:
        saving = int(product.original_price - product.price)
    return render(request, 'shop/product_detail.html', {'product': product, 'saving': saving})


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    selected_size = request.GET.get('size', 'S')

    cart = request.session.get('cart')
    if not isinstance(cart, dict):
        cart = {}

    cart_item_key = f"{product.id}_{selected_size}"

    if cart_item_key in cart and isinstance(cart[cart_item_key], dict):
        cart[cart_item_key]['quantity'] += 1
    else:
        cart[cart_item_key] = {
            'product_id': product.id,
            'quantity': 1,
            'price': str(product.price),
            'name': product.name,
            'size': selected_size,
        }

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('shop:cart_detail')


def remove_from_cart(request, product_id):
    cart = get_cart(request)
    keys_to_delete = []

    for key in cart.keys():
        if key == str(product_id) or key.startswith(f"{product_id}_"):
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del cart[key]

    save_cart(request, cart)
    return redirect('shop:cart_detail')


def cart_detail(request):
    cart_data = get_cart(request)
    cart_items = []
    total_price = 0

    for p_id, item in cart_data.items():
        try:
            clean_id = int(str(p_id).split('_')[0])
            product = Product.objects.get(id=clean_id)
            item_total = float(item['price']) * item['quantity']
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'price': item['price'],
                'total_price': item_total,
                'size': item.get('size'),
            })
        except (Product.DoesNotExist, ValueError):
            continue

    context = {
        'cart': cart_items,
        'total_price': total_price,
    }
    return render(request, 'shop/cart.html', context)


def checkout(request):
    # 1. Check if user is logged in before allowing checkout (with next parameter redirect)
    if not request.user.is_authenticated:
        return redirect('/login/?next=/checkout/')

    cart = request.session.get('cart', {})

    # 2. Prevent checkout with empty cart
    if not cart:
        return redirect('shop:cart_detail')

    if request.method == 'POST':
        full_name = request.POST.get('first_name')
        phone_number = request.POST.get('phone')
        address = request.POST.get('address')
        pincode = request.POST.get('pincode')
        payment_method = request.POST.get('payment_method', 'Online')

        total_amount = sum(float(item['price']) * item['quantity'] for item in cart.values())

        with transaction.atomic():
            order = Order.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                address=address,
                pincode=pincode,
                total_amount=total_amount,
                payment_method=payment_method
            )

            for item_key, item_data in cart.items():
                product_id = item_data.get('product_id')
                product = get_object_or_404(Product, id=product_id)
                item_size = item_data.get('size')

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=item_data['price'],
                    quantity=item_data['quantity'],
                    size=item_size
                )
                Product.objects.filter(id=product.id).update(stock=Greatest(F('stock') - item_data['quantity'], 0))


        my_orders = request.session.get('my_orders', [])
        my_orders.append(order.id)
        request.session['my_orders'] = my_orders
        request.session['cart'] = {}
        request.session.modified = True

        return redirect('shop:payment', order_id=order.id)

    return render(request, 'shop/checkout.html', {'cart': cart})


def track_order(request):
    return render(request, 'shop/track_order.html')


def profile(request):
    orders = []
    if request.user.is_authenticated:
        orders = Order.objects.filter(full_name=request.user.username).order_by('-created_at')

    phone = request.GET.get('phone') or request.session.get('customer_phone')
    if phone and not orders.exists():
        request.session['customer_phone'] = phone
        orders = Order.objects.filter(phone_number=phone).order_by('-created_at')

    return render(request, 'shop/profile.html', {
        'orders': orders,
        'phone': phone
    })


def customer_login(request):
    if request.method == 'POST':
        username_or_email = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        # Match username or email, ignoring capital/small letters and extra spaces
        if '@' in username_or_email:
            candidates = User.objects.filter(email__iexact=username_or_email)
        else:
            candidates = User.objects.filter(username__iexact=username_or_email)
        user = None
        for candidate in candidates:
            user = authenticate(request, username=candidate.username, password=password)
            if user is not None:
                break

        if user is not None:
            login(request, user)

            # **Flow Fix:** Login zalyanantar 'next' URL check karun tithhe redirect karne
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)

            return redirect('shop:profile')
        else:
            return render(request, 'shop/login.html', {'error': 'Invalid username/email or password.'})

    # GET request sathi 'next' value template la pass karne
    next_url = request.GET.get('next', '')
    return render(request, 'shop/login.html', {'next': next_url})


def customer_logout(request):
    logout(request)
    return redirect('shop:product_list')


def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    selected_size = request.GET.get('size', 'S')

    cart = request.session.get('cart', {})
    if not isinstance(cart, dict):
        cart = {}

    cart_item_key = f"{product.id}_{selected_size}"
    cart[cart_item_key] = {
        'product_id': product.id,
        'quantity': 1,
        'price': str(product.price),
        'name': product.name,
        'size': selected_size,
    }
    request.session['cart'] = cart
    request.session.modified = True

    return redirect('shop:checkout')


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not _can_view_order(request, order):
        return redirect('shop:product_list')
    wa_text = "Hello Status Clothing Line, I have placed and paid for my order.\n\n" + _order_summary(order)
    return render(request, 'shop/order_success.html', {'order': order, 'wa_text': wa_text})


def payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not _can_view_order(request, order):
        return redirect('shop:product_list')
    if request.method == 'POST':
        first_time = not order.payment_method.startswith('UPI QR')
        order.payment_method = 'UPI QR (GPay/PhonePe)'
        order.save()
        if first_time:
            notify_owner(order)
        return redirect('shop:order_success', order_id=order.id)

    context = {'order': order}
    return render(request, 'shop/payment.html', context)


def landing_page(request):
    return render(request, 'shop/landing.html')


def register(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        confirm_password = request.POST.get('confirm_password') or ''

        if password != confirm_password:
            return render(request, 'shop/register.html', {'error': 'Passwords do not match!'})

        if User.objects.filter(username__iexact=username).exists():
            return render(request, 'shop/register.html', {'error': 'Username already taken!'})

        if User.objects.filter(email__iexact=email).exists():
            return render(request, 'shop/register.html', {'error': 'This email is already registered. Please login.'})

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
        except Exception as e:
            return render(request, 'shop/register.html', {'error': str(e)})

        # Log the new customer in straight away (no second login step)
        login(request, user)
        if request.session.get('cart'):
            return redirect('shop:cart_detail')
        return redirect('shop:product_list')

    return render(request, 'shop/register.html')
