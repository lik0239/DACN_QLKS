# hotel/admin.py
from django.contrib import admin
from django.apps import apps
from django.db import models as dj_models   # để nhận diện CharField/TextField

app = apps.get_app_config("hotel")

for model in app.get_models():
    # lấy tất cả field “thật” (không gồm ManyToMany)
    field_names = [f.name for f in model._meta.fields]

    # tạo list các field text để cho phép search
    text_fields = [
        f.name
        for f in model._meta.fields
        if isinstance(f, (dj_models.CharField, dj_models.TextField))
    ]

    # thuộc tính cho ModelAdmin
    attrs = {
        "list_display": field_names,   # HIỆN TẤT CẢ CỘT
    }
    if text_fields:
        attrs["search_fields"] = text_fields  # search theo các cột text

    # tạo class Admin động, vd: PhongAdmin, KhachhangAdmin, ...
    admin_class = type(f"{model.__name__}Admin", (admin.ModelAdmin,), attrs)

    try:
        admin.site.register(model, admin_class)
    except admin.sites.AlreadyRegistered:
        # nếu model nào đã đăng ký trước đó thì bỏ qua
        pass
