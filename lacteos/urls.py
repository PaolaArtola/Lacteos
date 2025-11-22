from django.urls import path, include
from . import views

app_name = "lacteos"
urlpatterns = [
    path("admin", views.index),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("products/", views.product_list, name="product_list"),
    path("products/create/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("purchase/", views.create_sale, name="create_sale"),
    path("sales/", views.my_sales, name="my_sales"),
    path("sales/<int:pk>/", views.sale_detail, name="sale_detail"),
    path("users/", views.user_management, name="user_management"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
]