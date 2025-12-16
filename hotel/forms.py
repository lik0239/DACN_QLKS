from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Khachhang, Phong, Datphong

class RegistrationForm(forms.Form):
    # ---- Khachhang ----
    tenkhachhang = forms.CharField(label="Tên khách hàng", max_length=255)
    cccd         = forms.CharField(label="CCCD", max_length=50)
    sdt          = forms.CharField(label="Số điện thoại", max_length=50)
    email        = forms.EmailField(label="Email", required=True)
    diachi       = forms.CharField(label="Địa chỉ", max_length=255)
    ngaysinh     = forms.DateField(label="Ngày sinh", input_formats=["%Y-%m-%d"])

    # ---- Taikhoan / auth_user ----
    tentaikhoan  = forms.CharField(label="Tên tài khoản", max_length=150)
    matkhau      = forms.CharField(label="Mật khẩu", widget=forms.PasswordInput)
    vaitro       = forms.CharField(label="Vai trò", max_length=50, required=False, initial="khach_hang")

    # --- Validate trùng ---
    def clean_tentaikhoan(self):
        u = self.cleaned_data["tentaikhoan"]
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Tên tài khoản đã tồn tại.")
        return u

    def clean_email(self):
        e = self.cleaned_data["email"]
        # Nếu bạn muốn email là duy nhất:
        if User.objects.filter(email=e).exists():
            raise forms.ValidationError("Email đã được sử dụng.")
        return e

    def clean_cccd(self):
        c = self.cleaned_data["cccd"]
        if Khachhang.objects.filter(cccd=c).exists():
            raise forms.ValidationError("CCCD đã tồn tại.")
        return c

class PhongImageForm(forms.ModelForm):
    class Meta:
        model = Phong
        fields = ['anh']

    def clean_anh(self):
        f = self.cleaned_data.get('anh')
        if not f:
            return f
        # Giới hạn 3MB
        if f.size > 3 * 1024 * 1024:
            raise forms.ValidationError("Ảnh quá lớn (>3MB).")
        # Kiểm tra MIME cơ bản
        valid_mime = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
        ctype = getattr(f, 'content_type', None)
        if ctype not in valid_mime:
            raise forms.ValidationError("Chỉ chấp nhận JPG, PNG, WEBP, GIF.")

class DatPhongForm(forms.ModelForm):
    class Meta:
        model = Datphong
        fields = ['ngaynhan', 'ngaytra']
        widgets = {
            'ngaynhan': forms.DateInput(attrs={'type': 'date'}),
            'ngaytra' : forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
                'ngaynhan': 'Ngày nhận',
                'ngaytra': 'Ngày trả',
            }

    def clean(self):
        cleaned = super().clean()
        nhan = cleaned.get('ngaynhan')
        tra  = cleaned.get('ngaytra')
        today = timezone.localdate()
        if nhan and tra:
            if nhan < today:
                raise forms.ValidationError("Ngày nhận phải từ hôm nay trở đi.")
            if tra <= nhan:
                raise forms.ValidationError("Ngày trả phải sau ngày nhận.")
        return cleaned

class KhachHangUpdateForm(forms.ModelForm):
    class Meta:
        model = Khachhang
        fields = ['tenkhachhang', 'sdt', 'email', 'diachi', 'ngaysinh']
        widgets = {
            'tenkhachhang': forms.TextInput(attrs={
                'placeholder': 'Nhập họ tên'
            }),
            'sdt': forms.TextInput(attrs={
                'placeholder': 'Nhập số điện thoại'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Nhập email'
            }),
            'diachi': forms.TextInput(attrs={
                'placeholder': 'Nhập địa chỉ'
            }),
            'ngaysinh': forms.DateInput(attrs={
                'type': 'date'
            }),
        }
    def __init__(self, *args, **kwargs):
        # giữ instance hiện tại để không báo trùng với chính mình
        self.instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = Khachhang.objects.filter(email__iexact=email)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Email này đã được sử dụng bởi khách khác.")
        return email

    def clean_sdt(self):
        sdt = self.cleaned_data.get('sdt')
        if sdt:
            qs = Khachhang.objects.filter(sdt__iexact=sdt)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Số điện thoại này đã tồn tại.")
        return sdt
    
class KhachHangPasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        label="Mật khẩu hiện tại",
        widget=forms.PasswordInput
    )
    new_password = forms.CharField(
        label="Mật khẩu mới",
        widget=forms.PasswordInput
    )
    confirm_password = forms.CharField(
        label="Xác nhận mật khẩu mới",
        widget=forms.PasswordInput
    )

    def __init__(self, *args, **kwargs):
        self.tai_khoan = kwargs.pop('tai_khoan', None)
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        cur = self.cleaned_data.get('current_password')
        if self.tai_khoan and (self.tai_khoan.matkhau or "") != cur:
            raise forms.ValidationError("Mật khẩu hiện tại không đúng.")
        return cur

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get('new_password')
        cf  = cleaned.get('confirm_password')

        if new and cf and new != cf:
            raise forms.ValidationError("Mật khẩu mới và xác nhận không khớp.")
        if new and len(new) < 6:
            raise forms.ValidationError("Mật khẩu mới phải có ít nhất 6 ký tự.")
        return cleaned