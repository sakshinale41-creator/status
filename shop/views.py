from django.shortcuts import render, redirect, get_object_or_404
from .models import Category, Product
from .models import Order, OrderItem
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .models import CustomerProfile
import random
import requests


# Simple Session-based Cart Helpers
def get_cart(request):
    cart = request.session.get('cart', {})
    return cart


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.filter(parent__isnull=True)
    products = Product.objects.all()

    # Search query filter
    query = request.GET.get('q')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        # Hya category che ani tichya subcategories che products fetch kara
        subcategories = category.subcategories.all()
        if subcategories.exists():
            # Jar parent category asel tar tiche ani subcategories che sagale products dakhav
            category_list = [category] + list(subcategories)
            products = products.filter(category__in=category_list)
        else:
            # Jar subcategory asel tar fakt tya category che products dakhav
            products = products.filter(category=category)

    return render(request, 'shop/product_list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query,
    })


def product_detail(request, pk):    # इथे pk किंवा id असणे गरजेचे आहे
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'shop/product_detail.html', {'product': product})


def add_to_cart(request, product_id):
  product = get_object_or_404(Product, id=product_id)

  # URL madhun size get kara (default 'S' samja)
  selected_size = request.GET.get('size', 'S')

  cart = request.session.get('cart')
  if not isinstance(cart, dict):
    cart = {}

  # Unique key banva tyamule vegveglya size che items cart madhe alag rahatil
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
    p_id = str(product_id)
    if p_id in cart:
        del cart[p_id]
        save_cart(request, cart)
    return redirect('shop:cart_detail')


def cart_detail(request):
    cart_data = get_cart(request)
    cart_items = []
    total_price = 0

    for p_id, item in cart_data.items():
        try:
            # Clean p_id to handle formats like '2_S'
            clean_id = int(str(p_id).split('_')[0])
            product = Product.objects.get(id=clean_id)
            item_total = float(item['price']) * item['quantity']
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'price': item['price'],
                'total_price': item_total,
            })
        except (Product.DoesNotExist, ValueError):
            continue

    context = {
        'cart': cart_items,
        'total_price': total_price,
    }
    return render(request, 'shop/cart.html', context)


def checkout(request):
    cart = request.session.get('cart', {})

    if request.method == 'POST':
        full_name = request.POST.get('first_name')
        phone_number = request.POST.get('phone')
        address = request.POST.get('address')
        pincode = request.POST.get('pincode')  # Pincode get kela
        payment_method = request.POST.get('payment_method', 'Online')

        total_amount = sum(float(item['price']) * item['quantity'] for item in cart.values())

        # Order create kara
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

            OrderItem.objects.create(
                order=order,
                product=product,
                price=item_data['price'],
                quantity=item_data['quantity']
            )

        # Cart clear kara
        request.session['cart'] = {}
        request.session.modified = True

        # Online payment sathi payment page var redirect kru shakta (kinva direct success jar QR/Mock payment asel)
        return redirect('shop:payment', order_id=order.id)

    return render(request, 'shop/checkout.html', {'cart': cart})


def track_order(request):
    return render(request, 'shop/track_order.html')


def profile(request):
    orders = []
    # Jar user login asel tar tyache orders fetch kartil, nasel tar phone varun
    if request.user.is_authenticated:
        # User account sobat link zalele orders (jar user_id field asel) kinva phone varun
        orders = Order.objects.filter(full_name=request.user.username).order_by('-created_at')

    phone = request.GET.get('phone') or request.session.get('customer_phone')
    if phone and not orders.exists():
        request.session['customer_phone'] = phone
        orders = Order.objects.filter(phone_number=phone).order_by('-created_at')

    return render(request, 'shop/profile.html', {
        'orders': orders,
        'phone': phone
    })


def customer_signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('shop:product_list')
    else:
        form = UserCreationForm()
    return render(request, 'shop/signup.html', {'form': form})


def customer_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('shop:product_list')
    else:
        form = AuthenticationForm()
    return render(request, 'shop/login.html', {'form': form})


def customer_logout(request):
    logout(request)
    return redirect('shop:product_list')


def phone_signup_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone_number')
        request.session['temp_phone'] = phone

        # Random 4-digit OTP generate kara ani session madhe store kara
        otp = str(random.randint(1000, 9999))
        request.session['otp'] = otp

        # Demo
        print("====================")
        print(f"DEMO OTP FOR {phone}: {otp}")
        print("====================")

        # --- Real SMS API Integration (Fast2SMS) ---
        url = 'https://www.fast2sms.com/dev/bulkV2'
        querystring = {
            'authorization': 'TUZI_FAST2SMS_API_KEY_ITHE_TAK',
            'variables_values': otp,
            'route': 'otp',
            'numbers': phone,
        }
        headers = {'cache-control': 'no-cache'}

        try:
            response = requests.request(
                'GET', url, headers=headers, params=querystring
            )
        except Exception as e:
            print('SMS Error (Demo mode fallback active):', e)

        return redirect('shop:verify_otp')
    return render(request, 'shop/phone_signup.html')

def verify_otp_view(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        saved_otp = request.session.get('otp')

        # Demo
        if entered_otp == saved_otp or entered_otp == '1234':
            phone = request.session.get('temp_phone', '9403561352')

            profile = CustomerProfile.objects.filter(phone_number=phone).first()
            if profile:
                user = profile.user
            else:
                username = f'user_{phone}'
                user, created = User.objects.get_or_create(username=username)
                CustomerProfile.objects.get_or_create(user=user, phone_number=phone)

            login(request, user)
            return redirect('shop:product_list')
        else:
            error_message = "Chukaicha OTP ahe! Punha try kara."
            return render(request, 'shop/verify_otp.html', {'error': error_message})

    return render(request, 'shop/verify_otp.html')


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
    return render(request, 'shop/order_success.html', {'order': order})


def payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        # Ithe order status update karun pudhe redirect karayche
        return redirect('shop:order_success', order_id=order.id)

    context = {'order': order}
    return render(request, 'shop/payment.html', context)