from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.contrib import messages
from django.forms import modelform_factory, formset_factory
from django.forms.models import inlineformset_factory
from datetime import timedelta
from decimal import Decimal
from .models import Lacteo, Sale, SaleItem, PriceHistory, UserProfile
from .decorators import admin_or_employee_required, admin_required


@login_required
def index(request):
    return render(request, "admin/index.html", {})


@login_required
@admin_required
def dashboard(request):
    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Latest sales (last 10)
    latest_sales = Sale.objects.select_related('created_by').prefetch_related('saleitem_set__lacteo')[:10]
    
    # Sales statistics
    total_sales = Sale.objects.count()
    total_revenue = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_profit = Sale.objects.aggregate(total=Sum('total_profit'))['total'] or Decimal('0')
    total_cost = Sale.objects.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')
    
    # Calculate overall ROI
    overall_roi = 0
    if total_cost > 0:
        overall_roi = (total_profit / total_cost) * 100
    
    # Recent sales (last 7 days)
    recent_sales_count = Sale.objects.filter(sale_date__date__gte=week_ago).count()
    recent_revenue = Sale.objects.filter(sale_date__date__gte=week_ago).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    recent_profit = Sale.objects.filter(sale_date__date__gte=week_ago).aggregate(
        total=Sum('total_profit')
    )['total'] or Decimal('0')
    
    # Monthly sales (last 30 days)
    monthly_sales_count = Sale.objects.filter(sale_date__date__gte=month_ago).count()
    monthly_revenue = Sale.objects.filter(sale_date__date__gte=month_ago).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    monthly_profit = Sale.objects.filter(sale_date__date__gte=month_ago).aggregate(
        total=Sum('total_profit')
    )['total'] or Decimal('0')
    
    # Today's sales
    today_sales = Sale.objects.filter(sale_date__date=today)
    today_count = today_sales.count()
    today_revenue = today_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    today_profit = today_sales.aggregate(total=Sum('total_profit'))['total'] or Decimal('0')
    
    # Average sale amount
    avg_sale_amount = Sale.objects.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')
    avg_profit_per_sale = Sale.objects.aggregate(avg=Avg('total_profit'))['avg'] or Decimal('0')
    avg_roi = Sale.objects.aggregate(avg=Avg('roi'))['avg'] or Decimal('0')
    
    # Top selling products
    top_products = SaleItem.objects.values('lacteo__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('subtotal'),
        total_profit=Sum('profit')
    ).order_by('-total_quantity')[:10]
    
    # Sales by day (last 7 days)
    sales_by_day = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        day_sales = Sale.objects.filter(sale_date__date=date)
        sales_by_day.append({
            'date': date,
            'count': day_sales.count(),
            'revenue': day_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
            'profit': day_sales.aggregate(total=Sum('total_profit'))['total'] or Decimal('0'),
        })
    
    # Calculate max revenue for chart scaling
    max_revenue = max([day['revenue'] for day in sales_by_day], default=Decimal('1'))
    
    # Low stock products
    low_stock_products = Lacteo.objects.filter(stock__lt=10).order_by('stock')[:5]
    
    context = {
        'latest_sales': latest_sales,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'overall_roi': overall_roi,
        'recent_sales_count': recent_sales_count,
        'recent_revenue': recent_revenue,
        'recent_profit': recent_profit,
        'monthly_sales_count': monthly_sales_count,
        'monthly_revenue': monthly_revenue,
        'monthly_profit': monthly_profit,
        'today_count': today_count,
        'today_revenue': today_revenue,
        'today_profit': today_profit,
        'avg_sale_amount': avg_sale_amount,
        'avg_profit_per_sale': avg_profit_per_sale,
        'avg_roi': avg_roi,
        'top_products': top_products,
        'sales_by_day': sales_by_day,
        'max_revenue': max_revenue,
        'low_stock_products': low_stock_products,
    }
    
    return render(request, 'dashboard.html', context)


def product_list(request):
    """Display all available products"""
    category = request.GET.get('category', '')
    search_query = request.GET.get('search', '')
    
    products = Lacteo.objects.filter(stock__gt=0)
    
    if category:
        products = products.filter(category__icontains=category)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Get unique categories for filter
    categories = Lacteo.objects.values_list('category', flat=True).distinct()
    
    context = {
        'products': products,
        'categories': categories,
        'selected_category': category,
        'search_query': search_query,
    }
    return render(request, 'products/list.html', context)


def product_detail(request, pk):
    """Display product details"""
    product = get_object_or_404(Lacteo, pk=pk)
    context = {
        'product': product,
    }
    return render(request, 'products/detail.html', context)


@login_required
def create_sale(request):
    """Create a new sale with items"""
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '')
        notes = request.POST.get('notes', '')
        
        # Get items from POST data
        item_ids = request.POST.getlist('item_id')
        quantities = request.POST.getlist('quantity')
        
        if not item_ids or not any(quantities):
            messages.error(request, 'Please select at least one item to purchase.')
            return redirect('lacteos:product_list')
        
        # Create sale
        sale = Sale.objects.create(
            customer_name=customer_name,
            total_amount=Decimal('0'),
            created_by=request.user,
            notes=notes
        )
        
        # Create sale items
        total_items = 0
        for item_id, quantity in zip(item_ids, quantities):
            try:
                lacteo = Lacteo.objects.get(pk=item_id)
                qty = int(quantity)
                
                if qty <= 0:
                    continue
                
                if qty > lacteo.stock:
                    messages.warning(
                        request, 
                        f'Only {lacteo.stock} units available for {lacteo.name}. Adjusted quantity.'
                    )
                    qty = lacteo.stock
                
                if qty > 0:
                    cost_price = lacteo.cost_price if lacteo.cost_price > 0 else lacteo.price * Decimal('0.6')
                    SaleItem.objects.create(
                        sale=sale,
                        lacteo=lacteo,
                        quantity=qty,
                        unit_price=lacteo.price,
                        cost_price=cost_price
                    )
                    
                    # Update stock
                    lacteo.stock -= qty
                    lacteo.save()
                    
                    total_items += qty
            except (Lacteo.DoesNotExist, ValueError):
                continue
        
        if total_items == 0:
            sale.delete()
            messages.error(request, 'No valid items were added to the sale.')
            return redirect('lacteos:product_list')
        
        # Recalculate totals
        sale.calculate_totals()
        
        messages.success(
            request, 
            f'Sale #{sale.id} created successfully! Total: ${sale.total_amount:.2f}'
        )
        return redirect('lacteos:sale_detail', pk=sale.id)
    
    return redirect('lacteos:product_list')


@login_required
def sale_detail(request, pk):
    """View details of a sale"""
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.saleitem_set.select_related('lacteo').all()
    
    context = {
        'sale': sale,
        'items': items,
    }
    return render(request, 'sales/detail.html', context)


@login_required
def my_sales(request):
    """View user's sales history"""
    sales = Sale.objects.filter(created_by=request.user).order_by('-sale_date')
    
    context = {
        'sales': sales,
    }
    return render(request, 'sales/list.html', context)


@login_required
@admin_required
def user_management(request):
    """Admin view to manage users"""
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.all().select_related('profile')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(profile__role=role_filter)
    
    users = users.order_by('-date_joined')
    
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'role_choices': UserProfile.ROLE_CHOICES,
    }
    return render(request, 'users/list.html', context)


@login_required
@admin_required
def user_detail(request, pk):
    """Admin view to view/edit user details"""
    user = get_object_or_404(User, pk=pk)
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Update user
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.is_active = request.POST.get('is_active') == 'on'
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.save()
        
        # Update profile
        profile.role = request.POST.get('role', profile.role)
        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        profile.save()
        
        messages.success(request, f'Usuario {user.username} actualizado exitosamente.')
        return redirect('lacteos:user_management')
    
    context = {
        'user_obj': user,
        'profile': profile,
        'role_choices': UserProfile.ROLE_CHOICES,
    }
    return render(request, 'users/detail.html', context)


@login_required
@admin_required
def user_delete(request, pk):
    """Admin view to delete a user"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Usuario {username} eliminado exitosamente.')
        return redirect('lacteos:user_management')
    
    context = {
        'user_obj': user,
    }
    return render(request, 'users/delete.html', context)


@login_required
@admin_or_employee_required
def product_create(request):
    """Create a new product (admin and employee only)"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', '').strip()
        price = request.POST.get('price', '0')
        cost_price = request.POST.get('cost_price', '0')
        stock = request.POST.get('stock', '0')
        unit = request.POST.get('unit', '').strip()
        expiration_date = request.POST.get('expiration_date', '')
        description = request.POST.get('description', '').strip()
        
        if not name or not category or not price or not stock or not unit:
            messages.error(request, 'Por favor completa todos los campos requeridos.')
            return render(request, 'products/create.html')
        
        try:
            product = Lacteo.objects.create(
                name=name,
                category=category,
                price=Decimal(price),
                cost_price=Decimal(cost_price) if cost_price else Decimal('0'),
                stock=int(stock),
                unit=unit,
                expiration_date=expiration_date if expiration_date else None,
                description=description
            )
            messages.success(request, f'Producto "{product.name}" creado exitosamente.')
            return redirect('lacteos:product_detail', pk=product.pk)
        except (ValueError, Exception) as e:
            messages.error(request, f'Error al crear el producto: {str(e)}')
    
    return render(request, 'products/create.html')


@login_required
@admin_or_employee_required
def product_edit(request, pk):
    """Edit an existing product (admin and employee only)"""
    product = get_object_or_404(Lacteo, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', '').strip()
        price = request.POST.get('price', '0')
        cost_price = request.POST.get('cost_price', '0')
        stock = request.POST.get('stock', '0')
        unit = request.POST.get('unit', '').strip()
        expiration_date = request.POST.get('expiration_date', '')
        description = request.POST.get('description', '').strip()
        
        if not name or not category or not price or not stock or not unit:
            messages.error(request, 'Por favor completa todos los campos requeridos.')
            return render(request, 'products/edit.html', {'product': product})
        
        try:
            product.name = name
            product.category = category
            product.price = Decimal(price)
            product.cost_price = Decimal(cost_price) if cost_price else Decimal('0')
            product.stock = int(stock)
            product.unit = unit
            product.expiration_date = expiration_date if expiration_date else None
            product.description = description
            product.save()
            
            messages.success(request, f'Producto "{product.name}" actualizado exitosamente.')
            return redirect('lacteos:product_detail', pk=product.pk)
        except (ValueError, Exception) as e:
            messages.error(request, f'Error al actualizar el producto: {str(e)}')
    
    context = {
        'product': product,
    }
    return render(request, 'products/edit.html', context)


@login_required
@admin_or_employee_required
def product_delete(request, pk):
    """Delete a product (admin and employee only)"""
    product = get_object_or_404(Lacteo, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Producto "{product_name}" eliminado exitosamente.')
        return redirect('lacteos:product_list')
    
    context = {
        'product': product,
    }
    return render(request, 'products/delete.html', context)