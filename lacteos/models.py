from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal


class Lacteo(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    unit = models.CharField(max_length=20)
    expiration_date = models.DateField()
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Purchase cost per unit")

    def __str__(self):
        return self.name

    def get_profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return ((self.price - self.cost_price) / self.cost_price) * 100
        return 0

    def get_profit_per_unit(self):
        """Calculate profit per unit"""
        return self.price - self.cost_price


class Sale(models.Model):
    sale_date = models.DateTimeField(default=timezone.now)
    customer_name = models.CharField(max_length=100, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    roi = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Return on Investment percentage")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-sale_date']

    def __str__(self):
        return f"Sale #{self.id} - {self.sale_date.strftime('%Y-%m-%d %H:%M')}"

    def calculate_totals(self):
        """Recalculate totals based on sale items"""
        items = self.saleitem_set.all()
        self.total_amount = sum(item.subtotal for item in items) or Decimal('0')
        self.total_cost = sum(item.cost_subtotal for item in items) or Decimal('0')
        self.total_profit = self.total_amount - self.total_cost
        if self.total_cost > 0:
            self.roi = (self.total_profit / self.total_cost) * 100
        else:
            self.roi = Decimal('0')
        self.save()


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    lacteo = models.ForeignKey(Lacteo, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost price at time of sale")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    cost_subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    profit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.lacteo.name} x{self.quantity} - Sale #{self.sale.id}"

    def save(self, *args, **kwargs):
        """Calculate subtotals and profit on save"""
        self.subtotal = self.quantity * self.unit_price
        self.cost_subtotal = self.quantity * self.cost_price
        self.profit = self.subtotal - self.cost_subtotal
        super().save(*args, **kwargs)
        # Update parent sale totals
        self.sale.calculate_totals()


class PriceHistory(models.Model):
    lacteo = models.ForeignKey(Lacteo, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    changed_at = models.DateTimeField(default=timezone.now)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = "Price Histories"

    def __str__(self):
        return f"{self.lacteo.name} - {self.price} ({self.changed_at.strftime('%Y-%m-%d')})"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Cliente'),
        ('employee', 'Empleado'),
        ('admin', 'Administrador'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser
    
    def is_employee(self):
        return self.role == 'employee' or self.is_admin()
    
    def is_customer(self):
        return self.role == 'customer'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a User is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)
