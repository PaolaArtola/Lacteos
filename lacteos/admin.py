from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Lacteo, Sale, SaleItem, PriceHistory, UserProfile


@admin.register(Lacteo)
class LacteoAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'cost_price', 'stock', 'unit', 'expiration_date']
    list_filter = ['category', 'expiration_date']
    search_fields = ['name', 'category']
    readonly_fields = ['get_profit_margin', 'get_profit_per_unit']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'cost_price', 'get_profit_margin', 'get_profit_per_unit')
        }),
        ('Inventory', {
            'fields': ('stock', 'unit', 'expiration_date')
        }),
    )


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    readonly_fields = ['subtotal', 'cost_subtotal', 'profit']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'sale_date', 'customer_name', 'total_amount', 'total_profit', 'roi', 'created_by']
    list_filter = ['sale_date', 'created_by']
    search_fields = ['customer_name', 'notes']
    readonly_fields = ['total_amount', 'total_cost', 'total_profit', 'roi']
    inlines = [SaleItemInline]
    date_hierarchy = 'sale_date'


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'sale', 'lacteo', 'quantity', 'unit_price', 'subtotal', 'profit']
    list_filter = ['sale__sale_date', 'lacteo']
    search_fields = ['lacteo__name', 'sale__customer_name']
    readonly_fields = ['subtotal', 'cost_subtotal', 'profit']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['lacteo', 'price', 'cost_price', 'changed_at', 'changed_by', 'reason']
    list_filter = ['changed_at', 'lacteo']
    search_fields = ['lacteo__name', 'reason']
    readonly_fields = ['changed_at']
    date_hierarchy = 'changed_at'


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return 'N/A'
    get_role.short_description = 'Rol'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
