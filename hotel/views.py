from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from .forms import RegistrationForm
from .models import Khachhang, Taikhoan

def home(request):
    return render(request, "home.html")

@transaction.atomic
def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                # 1) Tạo user Django với "unusable password" (để chỉ backend plaintext hoạt động)
                user = User(username=cd["tentaikhoan"], email=cd["email"], first_name=cd["tenkhachhang"])
                user.set_unusable_password()  # không hash, vô hiệu hóa đăng nhập qua ModelBackend
                user.save()

                # 2) Tạo Khachhang theo đúng tên cột CSDL
                kh = Khachhang.objects.create(
                    tenkhachhang = cd["tenkhachhang"],
                    cccd         = cd["cccd"],
                    sdt          = cd["sdt"],
                    email        = cd["email"],
                    diachi       = cd["diachi"],
                    ngaysinh     = cd["ngaysinh"],
                )

                # 3) Tạo Taikhoan và LƯU PLAINTEXT vào 'matkhau' (theo yêu cầu)
                Taikhoan.objects.create(
                    makhachhang = kh,
                    manhanvien  = None,
                    tentaikhoan = cd["tentaikhoan"],
                    matkhau     = cd["matkhau"],              # <-- PLAINTEXT
                    vaitro      = cd.get("vaitro") or "khach_hang",
                    email       = cd["email"],
                )

                # 4) Đăng nhập (qua session) và điều hướng
                auth_login(request, user)
                messages.success(request, "Đăng ký thành công!")
                next_url = request.GET.get("next") or "home"
                return redirect(next_url)
            except IntegrityError:
                messages.error(request, "Có lỗi khi ghi dữ liệu. Vui lòng thử lại.")
        # form lỗi -> rơi xuống render form với thông báo
    else:
        form = RegistrationForm()
    return render(request, "register.html", {"form": form})
