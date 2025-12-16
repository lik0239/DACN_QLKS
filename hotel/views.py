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
from decimal import Decimal
from django.db.models.functions import Coalesce
from django.db.models import Sum, OuterRef, Subquery, DecimalField, Value, F, ExpressionWrapper
from itertools import groupby

from .forms import RegistrationForm, PhongImageForm, DatPhongForm, KhachHangUpdateForm, KhachHangPasswordChangeForm
from .models import Khachhang, TaiKhoanKhachHang, TaiKhoanNhanVien, Phong, Datphong, Dichvu, Sudungdichvu, Hoadon, Thanhtoan

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
        password = request.POST.get('password') or ''

        # ---- ĐĂNG NHẬP NHÂN VIÊN / QUẢN LÝ ----
        nv = TaiKhoanNhanVien.objects.filter(
            tentaikhoan__iexact=username,
            matkhau=password
        ).first()

        if nv:
            user = _get_or_create_shadow_user(username=nv.tentaikhoan)
            auth_login(request, user)
            request.session['auth'] = {
                'loai'        : 'NV',                         # nhân viên (bao gồm cả quản lý)
                'ma_tai_khoan': nv.mataikhoan,
                'profile_id'  : getattr(nv, 'manhanvien_id', None),
                'vaitro'      : getattr(nv, 'vaitro', None),  # 👈 dùng 'vaitro' thống nhất
                'email'       : getattr(nv, 'email', None),
                'ten'         : nv.tentaikhoan,
            }
            return redirect(request.GET.get('next') or 'internal_room_board')

        # ---- ĐĂNG NHẬP KHÁCH ----
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
    phong_qs = (
        Phong.objects
        .select_related('maloaiphong')
        .order_by('maloaiphong__tenloaiphong', 'sophong')
    )

    room_groups = []
    for loai, rooms in groupby(phong_qs, key=lambda p: p.maloaiphong):
        room_groups.append({
            "loai": loai,
            "rooms": list(rooms),
        })

    return render(request, 'room_list.html', {
        'room_groups': room_groups,
    })

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
    # lấy phòng theo khóa chính hiện tại
    phong_obj = get_object_or_404(Phong, pk=maphong)

    # chỉ KH mới được đặt
    auth = request.session.get('auth', {})
    if auth.get('loai') != 'KH':
        messages.error(request, "Bạn cần đăng nhập bằng tài khoản KH để đặt phòng.")
        return redirect('login')

    # chỉ phòng 'trống' mới bắt đầu quy trình
    if (phong_obj.trangthai or '').strip().lower() != 'trống':
        messages.error(request, "Phòng này không còn trống để đặt.")
        return redirect('room_list')

    # hồ sơ khách
    kh_id = auth.get('profile_id')
    khach = get_object_or_404(Khachhang, pk=kh_id)

    # dịch vụ để render checkbox
    services = Dichvu.objects.all().order_by('madichvu')

    if request.method == 'POST':
        form = DatPhongForm(request.POST)
        if form.is_valid():
            ngaynhan = form.cleaned_data['ngaynhan']
            ngaytra  = form.cleaned_data['ngaytra']

            # chỉ chặn trùng với đơn đã xác nhận (nhân viên đã chốt)
            conflict = Datphong.objects.filter(
                maphong_id=phong_obj.maphong,
                ngaynhan__lt=ngaytra,
                ngaytra__gt=ngaynhan,
                trangthai='xacnhan'
            ).exists()

            if conflict:
                messages.error(request, "Khoảng thời gian này đã có người đặt.")
            else:
                # tạo đơn NHÁP: khách mới chọn ngày + dịch vụ,
                # CHƯA gửi đến nhân viên
                dat = form.save(commit=False)
                dat.makhachhang_id = khach.makhachhang
                dat.maphong_id     = phong_obj.maphong
                dat.trangthai      = 'chuathanhtoan'
                dat.ngaydat = timezone.now().date()
                # dat.phuongthucthanhtoan_du_kien = None (chưa chọn)
                dat.save()

                # lưu dịch vụ đã chọn vào sudungdichvu
                service_ids = request.POST.getlist('services')
                for sid in service_ids:
                    try:
                        dv = Dichvu.objects.get(madichvu=sid)
                    except Dichvu.DoesNotExist:
                        continue

                    Sudungdichvu.objects.create(
                        madatphong=dat,
                        madichvu=dv,
                        soluong=1,
                        tongtien=dv.gia
                    )

                messages.info(
                    request,
                    "Đã ghi nhận thông tin đặt phòng. "
                    "Vui lòng chọn hình thức thanh toán để gửi yêu cầu tới nhân viên."
                )
                return redirect('payment', madatphong=dat.madatphong)
    else:
        form = DatPhongForm()

    return render(request, 'datphong.html', {
        'form': form,
        'phong': phong_obj,
        'khachhang': khach,
        'services': services,
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
    is_manager = (auth.get('vaitro') == 'QuanLy')
    if auth.get('loai') != 'NV':
        return redirect('home')

    today = timezone.localdate()

    stats = (
        Phong.objects.values('trangthai')
        .annotate(count=Count('maphong'))
        .order_by('trangthai')
    )

    status_filter = request.GET.get('status')

    rooms = (
        Phong.objects.select_related('maloaiphong')
        .annotate(
            next_booking_date=Min(
                'datphong__ngaynhan',
                filter=Q(datphong__ngaynhan__gte=today) & ~Q(datphong__trangthai='huy')
            )
        )
        .order_by('sophong')
    )

    if status_filter:
        rooms = rooms.filter(trangthai=status_filter)

    return render(request, 'internal_room_board.html', {
        'stats': stats,
        'rooms': rooms,
        'today': today,
        'status_filter': status_filter,
        'is_manager': is_manager,
    })

@login_required
def internal_booking_board(request):
    auth = request.session.get('auth', {})
    is_manager = (auth.get('vaitro') == 'QuanLy')
    if auth.get('loai') != 'NV':
        return redirect('home')

    today = timezone.localdate()

    pending = (
        Datphong.objects.select_related('maphong', 'makhachhang')
        .filter(trangthai='dangcho')
        .order_by('ngaydat', 'madatphong')
    )

    staying = (
        Datphong.objects.select_related('maphong', 'makhachhang')
        .filter(trangthai='xacnhan', ngaynhan__lte=today, ngaytra__gt=today)
        .order_by('ngaytra')
    )

    return render(request, 'internal_booking_board.html', {
        'pending': pending,
        'staying': staying,
        'today': today,
        'is_manager': is_manager,
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
    # Đơn đặt phòng + phòng + khách
    booking = get_object_or_404(
        Datphong.objects.select_related('maphong', 'makhachhang'),
        pk=madatphong
    )

    # Tính số đêm
    so_dem = (booking.ngaytra - booking.ngaynhan).days
    if so_dem <= 0:
        so_dem = 1

    gia_phong_moi_dem = booking.maphong.maloaiphong.gia
    tien_phong = gia_phong_moi_dem * so_dem

    # Tiền dịch vụ
    services_used = Sudungdichvu.objects.filter(madatphong=booking.madatphong)
    tien_dichvu = sum((s.tongtien or Decimal('0')) for s in services_used)

    tong_tien = tien_phong + tien_dichvu

    # Lấy / tạo hóa đơn
    invoice, created = Hoadon.objects.get_or_create(
        madatphong=booking,
        defaults={
            'ngayphathanh': timezone.localdate(),
            'tongtien': tong_tien,
        }
    )
    # Nếu hóa đơn đã có nhưng tổng tiền thay đổi thì cập nhật lại
    if not created and invoice.tongtien != tong_tien:
        invoice.tongtien = tong_tien
        invoice.save(update_fields=['tongtien'])

    # Tổng tiền đã thu từ bảng THANHTOAN
    da_thu = (
        Thanhtoan.objects.filter(
            mahoadon=invoice,          # FK tới Hoadon
            trangthai='DaThu'          # nếu bạn chưa dùng trạng thái thì bỏ điều kiện này cũng được
        )
        .aggregate(total=Sum('sotien'))['total']
        or Decimal('0')
    )

    need_pay = tong_tien - da_thu
    if need_pay < 0:
        need_pay = Decimal('0')

    if request.method == 'POST':
        method = request.POST.get('hinhthucthanhtoan')

        if need_pay > 0:
            if method not in ('TienMat', 'The', 'ChuyenKhoan'):
                messages.error(request, "Vui lòng chọn hình thức thanh toán hợp lệ.")
                return redirect(request.path)

            # Ghi nhận lần thanh toán cuối cùng (thực tế) vào bảng THANHTOAN
            Thanhtoan.objects.create(
                mahoadon=invoice,
                hinhthucthanhtoan=method,
                sotien=need_pay,
                thoigian=timezone.localtime().time(),
                trangthai='DaThu',
            )

        # Hoàn tất đơn & cập nhật trạng thái phòng
        booking.trangthai = 'hoanthanh'
        booking.save(update_fields=['trangthai'])

        room = booking.maphong
        if room.trangthai == 'Đang ở':
            room.trangthai = 'Đang dọn'  # hoặc 'Trống' tùy quy ước của bạn
            room.save(update_fields=['trangthai'])

        messages.success(request, f"Đã check-out đơn #{booking.madatphong}.")
        return redirect('internal_room_board')

    return render(request, 'internal_booking_checkout.html', {
        'booking': booking,
        'tien_phong': tien_phong,
        'tien_dichvu': tien_dichvu,
        'tong_tien': tong_tien,
        'da_thu': da_thu,
        'need_pay': need_pay,
    })

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
      - nếu phòng đang ở: đơn 'xacnhan' mà today ∈ [nhan, tra)
      - nếu không: lấy đơn 'xacnhan' gần nhất trong tương lai (Đã đặt)
      - nếu vẫn không có: hiển thị đơn 'dangcho' gần nhất
    """
    today = timezone.localdate()
    p = get_object_or_404(Phong, pk=maphong)

    # chỉ khi phòng đang ở mới tìm "current"
    cur = None
    if p.trangthai == 'Đang ở':
        cur = (
            Datphong.objects
            .select_related('makhachhang')
            .filter(
                maphong_id=maphong,
                trangthai='xacnhan',
                ngaynhan__lte=today,
                ngaytra__gt=today,
            )
            .order_by('ngaynhan')
            .first()
        )

    # nếu không có current thì tìm booking ĐÃ XÁC NHẬN trong tương lai (Đã đặt)
    nxt = None
    pend = None
    if not cur:
        nxt = (
            Datphong.objects
            .select_related('makhachhang')
            .filter(
                maphong_id=maphong,
                trangthai='xacnhan',
                ngaynhan__gte=today,
            )
            .order_by('ngaynhan')
            .first()
        )

        # nếu không có xác nhận nào thì lấy đơn đang chờ
        if not nxt:
            pend = (
                Datphong.objects
                .select_related('makhachhang')
                .filter(
                    maphong_id=maphong,
                    trangthai='dangcho',
                )
                .order_by('ngaynhan')
                .first()
            )

    return render(request, 'internal_room_booking_info.html', {
        'phong': p,
        'current': cur,
        'upcoming': nxt,
        'pending': pend,
        'today': today,
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

def services_view(request):
    services = Dichvu.objects.all().order_by('madichvu')
    return render(request, 'services.html', {
        'services': services,
    })

@login_required
@transaction.atomic
def payment_view(request, madatphong: int):
    # Chỉ KH mới được vào trang thanh toán
    auth = request.session.get('auth', {})
    if auth.get('loai') != 'KH':
        messages.error(request, "Bạn cần đăng nhập bằng tài khoản KH để xem thanh toán.")
        return redirect('login')

    kh_id = auth.get('profile_id')
    khach = get_object_or_404(Khachhang, pk=kh_id)

    booking = get_object_or_404(
        Datphong.objects.select_related('maphong', 'makhachhang'),
        madatphong=madatphong,
        makhachhang=khach
    )

    # ===== TÍNH TIỀN PHÒNG =====
    so_dem = (booking.ngaytra - booking.ngaynhan).days
    if so_dem <= 0:
        so_dem = 1

    gia_phong_moi_dem = booking.maphong.maloaiphong.gia
    tien_phong = gia_phong_moi_dem * so_dem

    # ===== TÍNH TIỀN DỊCH VỤ =====
    services_used = Sudungdichvu.objects.select_related('madichvu').filter(
        madatphong=booking.madatphong
    )

    tien_dichvu = sum((s.tongtien or Decimal('0')) for s in services_used)
    tong_tien = tien_phong + tien_dichvu

    if request.method == 'POST':
        action = request.POST.get('action')  # 'pay' hoặc 'change_room'

        # --- KH chọn "Chọn phòng khác" -> hủy đơn, trả về danh sách phòng ---
        if action == 'change_room':
            booking.trangthai = 'huy'
            booking.save(update_fields=['trangthai'])
            Sudungdichvu.objects.filter(madatphong=booking).delete()
            messages.info(request, "Đơn đặt phòng đã được hủy. Bạn có thể chọn phòng khác.")
            return redirect('room_list')

        # --- KH xác nhận thanh toán / đặt phòng ---
        payment_method = request.POST.get('payment_method')  # later / vietqr / card

        # Giá trị hợp lệ đúng theo template
        VALID_METHODS = ('later', 'vietqr', 'card')

        if payment_method not in VALID_METHODS:
            messages.error(request, "Vui lòng chọn hình thức thanh toán hợp lệ.")
        else:
            # Map sang code lưu trong DB (bảng DATPHONG / THANHTOAN)
            METHOD_MAP = {
                'later': 'KhiNhanPhong',
                'vietqr': 'VietQR',
                'card':  'The',
            }
            method_code = METHOD_MAP[payment_method]

            # Lưu phương thức thanh toán dự kiến trên DATPHONG
            booking.phuongthucthanhtoan_du_kien = method_code
            booking.ngaydat = booking.ngaydat or timezone.localdate()
            booking.trangthai = 'dangcho'   # chờ NV kiểm tra & xác nhận
            booking.save(update_fields=['phuongthucthanhtoan_du_kien', 'ngaydat', 'trangthai'])

            # Nếu khách chọn thanh toán ONLINE → tạo HÓA ĐƠN + THANHTOAN ngay
            if payment_method in ('vietqr', 'card'):
                invoice, created = Hoadon.objects.get_or_create(
                    madatphong=booking,
                    defaults={
                        'ngayphathanh': timezone.localdate(),
                        'tongtien': tong_tien,
                    }
                )
                if (not created) and invoice.tongtien != tong_tien:
                    invoice.tongtien = tong_tien
                    invoice.save(update_fields=['tongtien'])

                Thanhtoan.objects.create(
                    mahoadon=invoice,
                    thoigian=timezone.now().time(),
                    sotien=tong_tien,
                    hinhthucthanhtoan=method_code,  # dùng 'VietQR' hoặc 'The'
                    trangthai='DaThu',
                )

            # Nếu later (KhiNhanPhong) thì chỉ lưu dự kiến, thu thật lúc checkout
            messages.success(
                request,
                "Đã ghi nhận yêu cầu đặt phòng. Nhân viên sẽ kiểm tra và xác nhận cho bạn."
            )
            return redirect('room_list')

    # GET hoặc POST lỗi -> render lại form
    return render(request, 'payment.html', {
        'booking': booking,
        'khach': khach,
        'tien_phong': tien_phong,
        'tien_dichvu': tien_dichvu,
        'tong_tien': tong_tien,
        'so_dem': so_dem,
        'gia_phong_moi_dem': gia_phong_moi_dem,
        'services_used': services_used,
    })

def is_manager(request) -> bool:
    auth = request.session.get('auth', {})
    return auth.get('vaitro') == 'QuanLy'

@login_required
@require_nv
def internal_dashboard(request):
    """
    Trang báo cáo doanh thu – chỉ cho tài khoản vaitro='QuanLy'
    """
    if not is_manager(request):
        messages.error(request, "Bạn không có quyền xem báo cáo doanh thu.")
        return redirect('internal_room_board')

    today = timezone.localdate()

    # Lấy from / to từ GET, mặc định: từ đầu tháng đến hôm nay
    from_str = request.GET.get('from')
    to_str   = request.GET.get('to')

    try:
        from_date = timezone.datetime.strptime(from_str, "%Y-%m-%d").date() if from_str else today.replace(day=1)
    except ValueError:
        from_date = today.replace(day=1)

    try:
        to_date = timezone.datetime.strptime(to_str, "%Y-%m-%d").date() if to_str else today
    except ValueError:
        to_date = today

    # Hóa đơn trong khoảng thời gian
    hoadon_qs = (
        Hoadon.objects
        .select_related('madatphong__makhachhang', 'madatphong__maphong__maloaiphong')
        .filter(ngayphathanh__gte=from_date, ngayphathanh__lte=to_date)
    )

    # Hóa đơn được tính doanh thu (loại bỏ "Chưa phát hành" nếu có)
    hoadon_doanhthu = hoadon_qs.exclude(trangthai="Chưa phát hành")

    # Tổng doanh thu, phòng, dịch vụ
    agg = hoadon_doanhthu.aggregate(
        total_revenue=Coalesce(Sum('tongtien'), Decimal('0')),
        room_revenue=Coalesce(Sum('tienphong'), Decimal('0')),
        service_revenue=Coalesce(Sum('tiendichvu'), Decimal('0')),
    )
    total_revenue   = agg['total_revenue']
    room_revenue    = agg['room_revenue']
    service_revenue = agg['service_revenue']

    # Tổng tiền đã thu thực tế từ bảng THANHTOAN (ThanhCong)
    payments_qs = Thanhtoan.objects.filter(
        mahoadon__in=hoadon_qs.values('mahoadon'),
        trangthai='ThanhCong'
    )
    total_paid = payments_qs.aggregate(
        total_paid=Coalesce(Sum('sotien'), Decimal('0'))
    )['total_paid']

    # Doanh thu còn nợ = tổng doanh thu hóa đơn - tổng đã thu
    # (cách nhìn tổng thể, không chính xác từng hóa đơn nếu trả một phần,
    #  nhưng đủ cho dashboard; chi tiết sẽ xem ở bảng dưới.)
    total_debt = total_revenue - total_paid

    # Doanh thu theo ngày
    revenue_by_day = (
        hoadon_doanhthu
        .values('ngayphathanh')
        .annotate(tong=Sum('tongtien'))
        .order_by('ngayphathanh')
    )

    # Top loại phòng theo doanh thu phòng
    top_room_types = (
        hoadon_doanhthu
        .values('madatphong__maphong__maloaiphong__tenloaiphong')
        .annotate(tien=Sum('tienphong'))
        .order_by('-tien')[:5]
    )

    # Doanh thu dịch vụ theo loại dịch vụ (dựa trên sudungdichvu trong các đặt phòng thuộc hóa đơn trong khoảng)
    service_usage_qs = (
        Sudungdichvu.objects
        .select_related('madichvu', 'madatphong')
        .filter(madatphong__hoadon__in=hoadon_qs)
        .values('madichvu__tendichvu')
        .annotate(tong=Sum('tongtien'))
        .order_by('-tong')
    )

    # Annotate từng hóa đơn với số tiền đã thanh toán
    paid_sub = (
        Thanhtoan.objects
        .filter(mahoadon=OuterRef('pk'), trangthai='ThanhCong')
        .values('mahoadon')
        .annotate(total=Sum('sotien'))
        .values('total')
    )

    invoices = (
        hoadon_qs
        .annotate(
            da_thu=Coalesce(
                Subquery(paid_sub, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(Decimal('0')),
            ),
        )
        .annotate(
            con_no=ExpressionWrapper(
                F('tongtien') - F('da_thu'),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .order_by('-ngayphathanh', '-mahoadon')
    )

    # Tổng kết vài số đếm
    count_paid      = hoadon_qs.filter(trangthai='Đã thanh toán').count()
    count_partial   = hoadon_qs.filter(trangthai='Thanh toán một phần').count()
    count_unpaid    = hoadon_qs.filter(trangthai='Chưa thanh toán').count()
    count_unissued  = hoadon_qs.filter(trangthai='Chưa phát hành').count()

    context = {
        'from_date': from_date,
        'to_date': to_date,
        'total_revenue': total_revenue,
        'room_revenue': room_revenue,
        'service_revenue': service_revenue,
        'total_paid': total_paid,
        'total_debt': total_debt,
        'revenue_by_day': revenue_by_day,
        'top_room_types': top_room_types,
        'service_usage': service_usage_qs,
        'invoices': invoices,
        'count_paid': count_paid,
        'count_partial': count_partial,
        'count_unpaid': count_unpaid,
        'count_unissued': count_unissued,
        'is_manager': True,  # để template ít phải kiểm tra lại
    }
    return render(request, 'internal_dashboard.html', context)

@login_required
@transaction.atomic
def booking_cancel_request(request, madatphong: int):
    # Chỉ KH mới được gửi yêu cầu hủy
    auth = request.session.get("auth", {})
    if auth.get("loai") != "KH":
        messages.error(request, "Bạn cần đăng nhập bằng tài khoản khách hàng.")
        return redirect("login")

    khach_id = auth.get("profile_id")

    # Đảm bảo đơn thuộc về đúng khách
    booking = get_object_or_404(
        Datphong,
        madatphong=madatphong,
        makhachhang_id=khach_id,
    )

    # Không cho gửi yêu cầu nếu đơn đã hủy / hoàn thành / đã yêu cầu trước đó
    if booking.trangthai in ["huy", "hoanthanh", "yeucauhuy"]:
        messages.error(
            request,
            "Đơn này đã hoàn thành, đã hủy hoặc đã gửi yêu cầu trước đó."
        )
        return redirect("profile") 

    if request.method != "POST":
        messages.error(request, "Yêu cầu không hợp lệ.")
        return redirect("profile")

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "Vui lòng nhập lý do hủy phòng.")
        return redirect("profile")

    # Ghi lý do vào ghichu, giữ lại nội dung cũ nếu có
    prefix = "[YÊU CẦU HỦY] "
    if booking.ghichu:
        booking.ghichu = booking.ghichu + "\n" + prefix + reason
    else:
        booking.ghichu = prefix + reason

    # Đánh dấu trạng thái để nhân viên dễ nhận biết
    booking.trangthai = "yeucauhuy"
    booking.save(update_fields=["ghichu", "trangthai"])

    messages.success(
        request,
        "Đã gửi yêu cầu hủy phòng. Nhân viên sẽ kiểm tra và xử lý trong thời gian sớm nhất."
    )
    return redirect("profile")

@login_required
def internal_cancel_requests(request):
    """
    Trang cho nhân viên xem các đơn khách đã gửi yêu cầu hủy
    (trangthai = 'yeucauhuy').
    """
    auth = request.session.get("auth", {})
    if auth.get("loai") != "NV":
        messages.error(request, "Bạn không có quyền truy cập trang này.")
        return redirect("home")

    is_manager = (auth.get("vaitro") == "QuanLy")

    # Lấy các đơn đang ở trạng thái 'yeucauhuy'
    requests_qs = (
        Datphong.objects
        .select_related("maphong", "makhachhang")
        .filter(trangthai="yeucauhuy")
        .order_by("-ngaydat")
    )

    return render(request, "internal_cancel_requests.html", {
        "requests": requests_qs,
        "is_manager": is_manager,
        "messages": messages.get_messages(request),
    })
