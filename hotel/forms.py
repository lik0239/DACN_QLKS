from django import forms
from django.contrib.auth.models import User
from .models import Khachhang, Phong

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