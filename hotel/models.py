import uuid, os
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Datphong(models.Model):
    madatphong = models.AutoField(primary_key=True)
    makhachhang = models.ForeignKey('Khachhang', models.DO_NOTHING, db_column='makhachhang')
    maphong = models.ForeignKey('Phong', models.DO_NOTHING, db_column='maphong')
    ngaydat = models.DateField(blank=True, null=True)
    ngaynhan = models.DateField(blank=True, null=True)
    ngaytra = models.DateField(blank=True, null=True)
    trangthai = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'datphong'


class Dichvu(models.Model):
    madichvu = models.AutoField(primary_key=True)
    tendichvu = models.TextField(blank=True, null=True)
    mota = models.TextField(blank=True, null=True)
    gia = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dichvu'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Hoadon(models.Model):
    mahoadon = models.AutoField(primary_key=True)
    madatphong = models.ForeignKey(Datphong, models.DO_NOTHING, db_column='madatphong')
    ngayphathanh = models.DateField(blank=True, null=True)
    tienphong = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    tiendichvu = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    tongtien = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    trangthai = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'hoadon'


class Khachhang(models.Model):
    makhachhang = models.AutoField(primary_key=True)
    tenkhachhang = models.TextField(blank=True, null=True)
    cccd = models.TextField(unique=True, blank=True, null=True)
    sdt = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    diachi = models.TextField(blank=True, null=True)
    ngaysinh = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'khachhang'


class Loaiphong(models.Model):
    maloaiphong = models.AutoField(primary_key=True)
    tenloaiphong = models.TextField(blank=True, null=True)
    mota = models.TextField(blank=True, null=True)
    gia = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'loaiphong'


class Nhanvien(models.Model):
    manhanvien = models.AutoField(primary_key=True)
    hoten = models.TextField(blank=True, null=True)
    sdt = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    chucvu = models.TextField(blank=True, null=True)
    luong = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    ngayvaolam = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'nhanvien'

def room_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"rooms/{instance.sophong}/{uuid.uuid4().hex}{ext}"

class Phong(models.Model):
    maphong = models.AutoField(primary_key=True)
    sophong = models.TextField(blank=True, null=True)
    maloaiphong = models.ForeignKey(Loaiphong, models.DO_NOTHING, db_column='maloaiphong')
    trangthai = models.TextField(blank=True, null=True)
    anh = models.FileField(upload_to=room_upload_path, db_column='anh', blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'phong'


class Sudungdichvu(models.Model):
    masddv = models.AutoField(primary_key=True)
    madatphong = models.ForeignKey(Datphong, models.DO_NOTHING, db_column='madatphong')
    madichvu = models.ForeignKey(Dichvu, models.DO_NOTHING, db_column='madichvu')
    soluong = models.IntegerField(blank=True, null=True)
    tongtien = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sudungdichvu'


class Taikhoan(models.Model):
    mataikhoan = models.AutoField(primary_key=True)
    makhachhang = models.ForeignKey(Khachhang, models.DO_NOTHING, db_column='makhachhang', blank=True, null=True)
    manhanvien = models.ForeignKey(Nhanvien, models.DO_NOTHING, db_column='manhanvien', blank=True, null=True)
    tentaikhoan = models.TextField(blank=True, null=True)
    matkhau = models.TextField(blank=True, null=True)
    vaitro = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'taikhoan'


class Thanhtoan(models.Model):
    mathanhtoan = models.AutoField(primary_key=True)
    mahoadon = models.ForeignKey(Hoadon, models.DO_NOTHING, db_column='mahoadon')
    sotien = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    hinhthucthanhtoan = models.TextField(blank=True, null=True)
    thoigian = models.TimeField(blank=True, null=True)
    trangthai = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'thanhtoan'

class TaiKhoanKhachHang(models.Model):
    mataikhoan  = models.AutoField(db_column='mataikhoan', primary_key=True)
    makhachhang = models.ForeignKey('Khachhang', models.DO_NOTHING, db_column='makhachhang')
    tentaikhoan = models.CharField(db_column='tentaikhoan', max_length=150, unique=True)
    matkhau     = models.CharField(db_column='matkhau', max_length=255)
    email       = models.EmailField(db_column='email', max_length=255, null=True, blank=True, unique=True)

    class Meta:
        managed = False
        db_table = 'taikhoankhachhang'

class TaiKhoanNhanVien(models.Model):
    mataikhoan  = models.AutoField(db_column='mataikhoan', primary_key=True)
    manhanvien  = models.ForeignKey('Nhanvien', models.DO_NOTHING, db_column='manhanvien')
    tentaikhoan = models.CharField(db_column='tentaikhoan', max_length=150, unique=True)
    matkhau     = models.CharField(db_column='matkhau', max_length=255)
    email       = models.EmailField(db_column='email', max_length=255, null=True, blank=True, unique=True)
    vaitro      = models.CharField(db_column='vaitro', max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'taikhoannhanvien'