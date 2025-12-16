from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView
from .views import home, login_view, internal_home, register, update_phong_image
from .views import internal_room_board, booking_update_status, booking_checkin, booking_checkout, booking_cancel, room_set_status, internal_booking_search, booking_confirm, booking_detail, room_booking_info

urlpatterns = [
    path("", views.home, name="home"),
    path('login/', login_view, name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path('internal/', internal_home, name='internal_home'),
    path('room-list/', views.room_list_view, name='room_list'),
    path('rooms/<int:maphong>/image/', update_phong_image, name='update_phong_image'),
    path('dat-phong/<int:maphong>/', views.datphong_view, name='datphong'),
    path('internal/rooms/', internal_room_board, name='internal_room_board'),
    path('internal/booking/<int:madatphong>/confirm/', booking_confirm, name='booking_confirm'),
    path('internal/booking/<int:madatphong>/checkin/',  booking_checkin,  name='booking_checkin'),
    path('internal/booking/<int:madatphong>/checkout/', booking_checkout, name='booking_checkout'),
    path('internal/booking/<int:madatphong>/cancel/',   booking_cancel,   name='booking_cancel'),
    path('internal/room/<int:maphong>/status/<str:status>/', room_set_status, name='room_set_status'),
    path('internal/bookings/search/', internal_booking_search, name='internal_booking_search'),
    path('internal/booking/<int:madatphong>/', booking_detail, name='booking_detail'),
    path('internal/room/<int:maphong>/booking/', room_booking_info, name='room_booking_info'),
    path("quy-dinh/", views.quy_dinh, name="policy"),
    path("profile/", views.profile, name="profile"),
    path('services/', views.services_view, name='services'),
    path('thanh-toan/<int:madatphong>/', views.payment_view, name='payment'),
    path('internal/dashboard/', views.internal_dashboard, name='internal_dashboard'),
    path('lich-su-dat-phong/huy/<int:madatphong>/', views.booking_cancel_request, name='booking_cancel_request'),
    path('internal/cancel-requests/', views.internal_cancel_requests, name="internal_cancel_requests"),
    path('internal/bookings/', views.internal_booking_board, name='internal_booking_board'),
]
