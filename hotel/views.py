from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required

from .forms import RegistrationForm, PhongImageForm
from .models import Khachhang, TaiKhoanKhachHang, TaiKhoanNhanVien, Phong

def home(request):
    return render(request, "home.html")

@login_required
def internal_home(request):
    auth = request.session.get('auth', {})
    if auth.get('loai') != 'NV':
        return redirect('home')
    return render(request, "internal_home.html")

def _get_or_create_shadow_user(username: str):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_unusable_password()
        user.save()
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    return user

@transaction.atomic
def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                kh = Khachhang.objects.create(
                    tenkhachhang = cd["tenkhachhang"],
                    cccd         = cd["cccd"],
                    sdt          = cd["sdt"],
                    email        = cd["email"],
                    diachi       = cd["diachi"],
                    ngaysinh     = cd["ngaysinh"],
                )
                TaiKhoanKhachHang.objects.create(
                    makhachhang = kh,              
                    tentaikhoan = cd["tentaikhoan"],
                    matkhau     = cd["matkhau"],   
                    email       = cd["email"],
                )
                messages.success(request, "Đăng ký thành công! Vui lòng đăng nhập.")
                return redirect("login")
            except IntegrityError:
                messages.error(request, "Có lỗi khi ghi dữ liệu. Vui lòng thử lại.")
    else:
        form = RegistrationForm()
    return render(request, "register.html", {"form": form})

def login_view(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password   = request.POST.get('password') or ''

        nv = TaiKhoanNhanVien.objects.filter(
            tentaikhoan__iexact=username,
            matkhau=password
        ).first()

        if nv:
            user = _get_or_create_shadow_user(username=nv.tentaikhoan)
            auth_login(request, user)
            request.session['auth'] = {
                'loai'        : 'NV',
                'ma_tai_khoan': nv.mataikhoan,
                'profile_id'  : getattr(nv, 'manhanvien_id', None),
                'vaiTro'      : getattr(nv, 'vaitro', None),
                'email'       : getattr(nv, 'email', None),
                'ten'         : nv.tentaikhoan,
            }
            return redirect(request.GET.get('next') or 'internal_home')

        kh = TaiKhoanKhachHang.objects.filter(
            tentaikhoan__iexact=username,
            matkhau=password
        ).first()

        if kh:
            user = _get_or_create_shadow_user(username=kh.tentaikhoan)
            auth_login(request, user)
            request.session['auth'] = {
                'loai'        : 'KH',
                'ma_tai_khoan': kh.mataikhoan,
                'profile_id'  : getattr(kh, 'makhachhang_id', None),
                'email'       : getattr(kh, 'email', None),
                'ten'         : kh.tentaikhoan,
            }
            return redirect(request.GET.get('next') or 'home')
        messages.error(request, 'Sai tên đăng nhập hoặc mật khẩu.')
        return render(request, 'login.html')
    return render(request, 'login.html')

def room_list_view(request):
    phong_list = Phong.objects.all()
    return render(request, 'room_list.html', {'phong_list': phong_list})

def update_phong_image(request, maphong):
    phong = get_object_or_404(Phong, pk=maphong)
    if request.method == 'POST':
        form = PhongImageForm(request.POST, request.FILES, instance=phong)
        if form.is_valid():
            form.save()
            return redirect('room_list')  # đổi theo tên url của bạn
    else:
        form = PhongImageForm(instance=phong)
    return render(request, 'update_phong_image.html', {'form': form, 'phong': phong})