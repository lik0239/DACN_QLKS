from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Min, Q
from functools import wraps
from django.core.paginator import Paginator

from .forms import RegistrationForm, PhongImageForm, DatPhongForm, KhachHangUpdateForm, KhachHangPasswordChangeForm
from .models import Khachhang, TaiKhoanKhachHang, TaiKhoanNhanVien, Phong, Datphong

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
            return redirect(request.GET.get('next') or 'internal_room_board')

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

@login_required
@transaction.atomic
def datphong_view(request, maphong: int):
    # lấy phòng theo khóa chính hiện tại: maphong (chữ thường)
    phong_obj = get_object_or_404(Phong, pk=maphong)

    # chỉ KH mới được đặt
    auth = request.session.get('auth', {})
    if auth.get('loai') != 'KH':
        messages.error(request, "Bạn cần đăng nhập bằng tài khoản KH để đặt phòng.")
        return redirect('login')

    # kiểm tra trạng thái phòng
    if (phong_obj.trangthai or '').strip().lower() != 'trống':
        messages.error(request, "Phòng này không còn trống để đặt.")
        return redirect('room_list')  # đổi 'posts:room_list' -> 'room_list' theo urls bạn dùng

    # lấy hồ sơ khách hàng từ session
    kh_id = auth.get('profile_id')
    khach = get_object_or_404(Khachhang, pk=kh_id)

    if request.method == 'POST':
        form = DatPhongForm(request.POST)
        if form.is_valid():
            ngaynhan = form.cleaned_data['ngaynhan']
            ngaytra  = form.cleaned_data['ngaytra']

            conflict = Datphong.objects.filter(
                maphong_id=phong_obj.maphong,
                ngaynhan__lt=ngaytra,
                ngaytra__gt=ngaynhan,
                trangthai='xacnhan'
            ).exists()

            if conflict:
                messages.error(request, "Khoảng thời gian này đã có người đặt.")
            else:
                dat = form.save(commit=False)
                dat.makhachhang_id = khach.makhachhang
                dat.maphong_id     = phong_obj.maphong
                dat.trangthai      = 'dangcho'          # 👈 KHÔNG đổi trạng thái phòng ở đây
                dat.save()
                messages.success(request, "Gửi yêu cầu đặt phòng thành công! Đang chờ nhân viên xác nhận.")
                return redirect('room_list')
    else:
        form = DatPhongForm()

    return render(request, 'datphong.html', {
        'form'      : form,
        'phong'     : phong_obj,
        'khachhang' : khach,
    })

def require_nv(viewfunc):
    @wraps(viewfunc)
    def _wrapped(request, *args, **kwargs):
        if request.session.get('auth', {}).get('loai') != 'NV':
            return redirect('home')
        return viewfunc(request, *args, **kwargs)
    return _wrapped

@login_required
def internal_room_board(request):
    auth = request.session.get('auth', {})
    if auth.get('loai') != 'NV':
        return redirect('home')

    today = timezone.localdate()

    stats = (Phong.objects.values('trangthai')
             .annotate(count=Count('maphong')).order_by('trangthai'))

    rooms = (Phong.objects.select_related('maloaiphong')
             .annotate(next_booking_date=Min('datphong__ngaynhan',
                     filter=Q(datphong__ngaynhan__gte=today) & ~Q(datphong__trangthai='huy')))
             .order_by('sophong'))

    pending = (Datphong.objects.select_related('maphong','makhachhang')
               .filter(trangthai='dangcho').order_by('ngaynhan'))

    staying = (Datphong.objects.select_related('maphong','makhachhang')
               .filter(trangthai='xacnhan',
                       ngaynhan__lte=today, ngaytra__gt=today)
               .order_by('ngaytra'))

    return render(request, 'internal_room_board.html', {
        'stats': stats, 'rooms': rooms, 'pending': pending, 'staying': staying, 'today': today
    })

@login_required
@transaction.atomic
def booking_update_status(request, madatphong: int, action: str):
    auth = request.session.get('auth', {})
    if auth.get('loai') != 'NV':
        return redirect('home')

    dp = get_object_or_404(Datphong.objects.select_related('maphong'), pk=madatphong)

    if action == 'xacnhan':
        dp.trangthai = 'xacnhan'
        # (tuỳ quy ước) cập nhật trạng thái phòng
        dp.maphong.trangthai = 'Đã đặt'
        dp.maphong.save(update_fields=['trangthai'])
        dp.save(update_fields=['trangthai'])
        messages.success(request, f'Đã xác nhận đơn #{dp.madatphong}.')

    elif action == 'huy':
        dp.trangthai = 'huy'
        dp.save(update_fields=['trangthai'])
        # Có thể mở phòng nếu đơn này là đơn duy nhất giữ phòng hiện tại
        messages.warning(request, f'Đã hủy đơn #{dp.madatphong}.')

    elif action == 'hoanthanh':
        dp.trangthai = 'hoanthanh'
        dp.save(update_fields=['trangthai'])
        # (tuỳ quy ước) khi khách trả phòng => mở phòng
        dp.maphong.trangthai = 'Trống'
        dp.maphong.save(update_fields=['trangthai'])
        messages.success(request, f'Đã hoàn thành đơn #{dp.madatphong}.')

    else:
        messages.error(request, 'Hành động không hợp lệ.')

    return redirect('internal_room_board')

@login_required
@require_nv
@transaction.atomic
def booking_checkin(request, madatphong: int):
    dp = get_object_or_404(Datphong.objects.select_related('maphong'), pk=madatphong)
    today = timezone.localdate()

    # Chỉ cho check-in trong/đúng khoảng thời gian ở, và đơn chưa huỷ/hoàn thành
    if dp.trangthai == 'huy':
        messages.error(request, f'Đơn #{dp.madatphong} đã huỷ.')
        return redirect('internal_room_board')
    if dp.trangthai == 'hoanthanh':
        messages.error(request, f'Đơn #{dp.madatphong} đã hoàn thành.')
        return redirect('internal_room_board')
    if not (dp.ngaynhan <= today < dp.ngaytra):
        messages.warning(request, 'Chỉ check-in đúng ngày nhận (tới trước ngày trả).')
        return redirect('internal_room_board')

    # Xác nhận đơn & đánh dấu phòng Đang ở
    dp.trangthai = 'xacnhan'
    dp.save(update_fields=['trangthai'])
    dp.maphong.trangthai = 'Đang ở'
    dp.maphong.save(update_fields=['trangthai'])
    messages.success(request, f'Check-in thành công đơn #{dp.madatphong} (phòng {dp.maphong.sophong}).')
    return redirect('internal_room_board')


@login_required
@require_nv
@transaction.atomic
def booking_checkout(request, madatphong: int):
    dp = get_object_or_404(Datphong.objects.select_related('maphong'), pk=madatphong)
    if dp.trangthai == 'huy':
        messages.error(request, f'Đơn #{dp.madatphong} đã huỷ.')
        return redirect('internal_room_board')

    # Hoàn thành đơn & mở phòng
    dp.trangthai = 'hoanthanh'
    dp.save(update_fields=['trangthai'])
    dp.maphong.trangthai = 'Trống'
    dp.maphong.save(update_fields=['trangthai'])
    messages.success(request, f'Check-out thành công đơn #{dp.madatphong}. Phòng {dp.maphong.sophong} đã mở.')
    return redirect('internal_room_board')


@login_required
@require_nv
@transaction.atomic
def booking_cancel(request, madatphong: int):
    dp = get_object_or_404(Datphong.objects.select_related('maphong'), pk=madatphong)
    dp.trangthai = 'huy'
    dp.save(update_fields=['trangthai'])

    # Nếu phòng đang “Đã đặt”/“Đang ở” do đơn này, bạn có thể cân nhắc mở phòng.
    # Ở đây mình KHÔNG tự mở phòng để tránh huỷ nhầm giữa nhiều đơn; NV tự xử lý ở dashboard.
    messages.warning(request, f'Đã huỷ đơn #{dp.madatphong}.')
    return redirect('internal_room_board')


@login_required
@require_nv
@transaction.atomic
def room_set_status(request, maphong: int, status: str):
    """Đổi trạng thái phòng thủ công: Trống/Đã đặt/Đang ở/Đang dọn/Bảo trì..."""
    p = get_object_or_404(Phong, pk=maphong)
    allowed = {'Trống', 'Đã đặt', 'Đang ở', 'Đang dọn', 'Bảo trì'}
    if status not in allowed:
        messages.error(request, f'Trạng thái không hợp lệ: {status}')
        return redirect('internal_room_board')
    p.trangthai = status
    p.save(update_fields=['trangthai'])
    messages.success(request, f'Phòng {p.sophong} → {status}.')
    return redirect('internal_room_board')

@login_required
@require_nv
def internal_booking_search(request):
    q = (request.GET.get('q') or '').strip()
    results = []
    if q:
        results = (
            Datphong.objects
            .select_related('maphong', 'makhachhang')
            .filter(
                Q(makhachhang__tenkhachhang__icontains=q) |
                Q(makhachhang__cccd__icontains=q) |
                Q(makhachhang__sdt__icontains=q) |
                Q(maphong__sophong__icontains=q)
            )
            .order_by('-madatphong')[:100]
        )
    return render(request, 'internal_booking_search.html', {'q': q, 'results': results})

@login_required
@require_nv
@transaction.atomic
def booking_confirm(request, madatphong: int):
    """Đang chờ -> Đã đặt; đồng thời set phòng 'Đã đặt'."""
    dp = get_object_or_404(Datphong.objects.select_related('maphong'), pk=madatphong)
    if dp.trangthai == 'huy':
        messages.error(request, 'Đơn đã hủy.')
        return redirect('internal_room_board')
    if dp.trangthai == 'hoanthanh':
        messages.error(request, 'Đơn đã hoàn thành.')
        return redirect('internal_room_board')

    dp.trangthai = 'xacnhan'
    dp.save(update_fields=['trangthai'])
    dp.maphong.trangthai = 'Đã đặt'
    dp.maphong.save(update_fields=['trangthai'])

    messages.success(request, f'Đã xác nhận đơn #{dp.madatphong} và giữ phòng {dp.maphong.sophong}.')
    return redirect('internal_room_board')

@login_required
@require_nv
def booking_detail(request, madatphong: int):
    """Xem chi tiết đơn + thông tin khách & phòng; cung cấp nút Hành động."""
    dp = get_object_or_404(
        Datphong.objects.select_related('maphong', 'makhachhang'),
        pk=madatphong
    )
    today = timezone.localdate()
    can_checkin = (dp.trangthai != 'huy' and dp.trangthai != 'hoanthanh' and dp.ngaynhan <= today < dp.ngaytra)
    return render(request, 'internal_booking_detail.html', {
        'dp': dp,
        'can_checkin': can_checkin,
        'today': today,
    })

@login_required
@require_nv
def room_booking_info(request, maphong: int):
    """
    Xem khách gắn với phòng:
      - nếu đang ở: đơn 'xacnhan' mà today ∈ [nhan, tra)
      - nếu không: lấy đơn 'xacnhan' gần nhất trong tương lai
      - nếu vẫn không có: hiển thị đơn 'dangcho' gần nhất
    """
    today = timezone.localdate()
    p = get_object_or_404(Phong, pk=maphong)

    cur = (Datphong.objects.select_related('makhachhang')
           .filter(maphong_id=maphong, trangthai='xacnhan',
                   ngaynhan__lte=today, ngaytra__gt=today)
           .order_by('ngaynhan').first())

    nxt = None
    pend = None
    if not cur:
        nxt = (Datphong.objects.select_related('makhachhang')
               .filter(maphong_id=maphong, trangthai='xacnhan',
                       ngaynhan__gte=today)
               .order_by('ngaynhan').first())
        if not nxt:
            pend = (Datphong.objects.select_related('makhachhang')
                    .filter(maphong_id=maphong, trangthai='dangcho')
                    .order_by('ngaynhan').first())

    return render(request, 'internal_room_booking_info.html', {
        'phong': p, 'current': cur, 'upcoming': nxt, 'pending': pend, 'today': today
    })

def quy_dinh(request):
    return render(request, "quydinh.html")

@login_required
def profile(request):
    username = request.user.get_username()

    tk = get_object_or_404(TaiKhoanKhachHang, tentaikhoan=username)
    kh = tk.makhachhang

    qs = (Datphong.objects
          .select_related('maphong', 'makhachhang')
          .filter(makhachhang=kh)
          .order_by('-ngaydat', '-madatphong'))

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # ====== ĐỔI MẬT KHẨU ======
        if form_type == 'password':
            info_form = KhachHangUpdateForm(instance=kh)
            password_form = KhachHangPasswordChangeForm(
                request.POST,
                tai_khoan=tk
            )
            if password_form.is_valid():
                tk.matkhau = password_form.cleaned_data['new_password']
                tk.save(update_fields=['matkhau'])
                messages.success(request, 'Đổi mật khẩu thành công.')
                return redirect('profile')
            else:
                messages.error(request, 'Vui lòng kiểm tra lại thông tin đổi mật khẩu.')

        # ====== CẬP NHẬT THÔNG TIN CÁ NHÂN ======
        else:
            info_form = KhachHangUpdateForm(request.POST, instance=kh)
            password_form = KhachHangPasswordChangeForm(tai_khoan=tk)
            if info_form.is_valid():
                kh = info_form.save()
                tk.email = info_form.cleaned_data.get('email') or tk.email
                tk.save(update_fields=['email'])
                messages.success(request, 'Cập nhật thông tin thành công.')
                return redirect('profile')
            else:
                messages.error(request, 'Vui lòng kiểm tra lại các trường.')
    else:
        info_form = KhachHangUpdateForm(instance=kh)
        password_form = KhachHangPasswordChangeForm(tai_khoan=tk)

    return render(request, 'profile.html', {
        'khach': kh,
        'taikhoan': tk,
        'form': info_form,
        'password_form': password_form,
        'page_obj': page_obj,
    })