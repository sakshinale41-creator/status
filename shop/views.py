from django.shortcuts import render, redirect, get_object_or_404
from .models import Category, Product
from .models import Order, OrderItem


# Simple Session-based Cart Helpers
def get_cart(request):
    cart = request.session.get('cart', {})
    return cart


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.all()

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    return render(request, 'shop/product_list.html', {
        'category': category,
        'categories': categories,
        'products': products
    })


def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug)
    return render(request, 'shop/product_detail.html', {'product': product})


def add_to_cart(request, product_id):
    request.session.flush()
    product = get_object_or_404(Product, id=product_id)

    # Session madhun cart ghetaana to dict ahe ka check kara, nasel tar fresh dict banva
    cart = request.session.get('cart')
    if not isinstance(cart, dict):
        cart = {}

    p_id = str(product.id)

    if p_id in cart and isinstance(cart[p_id], dict):
        cart[p_id]['quantity'] += 1
    else:
        cart[p_id] = {
            'quantity': 1,
            'price': str(product.price),
            'name': product.name,
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
            product = Product.objects.get(id=int(p_id))
            item_total = float(item['price']) * item['quantity']
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'price': item['price'],
                'total_price': item_total,
            })
        except Product.DoesNotExist:
            continue

    context = {
        'cart': cart_items,
        'total_price': total_price,
    }
    return render(request, 'shop/cart.html', context)


def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('shop:product_list')

    if request.method == 'POST':
        name = request.POST.get('first_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        pincode = request.POST.get('pincode', '000000')  # Default value format saathi

        # Total Price Calculate kara
        total_price = sum(float(item['price']) * item['quantity'] for item in cart.values())

        # Exact model fields map karun Order create kara:
        order = Order.objects.create(
            full_name=name,
            phone_number=phone,
            address=address,
            pincode=pincode,
            total_amount=total_price,
            status='Pending'
        )

        # Order Items save kara ani Product Stock kam kara
        for item_id, item_data in cart.items():
            product = get_object_or_404(Product, id=item_id)

            OrderItem.objects.create(
                order=order,
                product=product,
                price=item_data['price'],
                quantity=item_data['quantity']
            )

            # Stock automatic minus kara
            if product.stock >= item_data['quantity']:
                product.stock -= item_data['quantity']
                if product.stock == 0:
                    product.available = False
                product.save()

        # Session cart clear kara
        request.session['cart'] = {}
        request.session.modified = True

        return render(request, 'shop/order_success.html', {'order': order})

    return render(request, 'shop/checkout.html')

def track_order(request):
    return render(request, 'shop/track_order.html')