from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView
from .views import home, login_view, internal_home, register, update_phong_image

urlpatterns = [
    path("", views.home, name="home"),
    path('login/', login_view, name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path('internal/', internal_home, name='internal_home'),
    path('room-list/', views.room_list_view, name='room_list'),
    path('rooms/<int:maphong>/image/', update_phong_image, name='update_phong_image'),
]
