from django.db import models
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password, check_password

class Principal(models.Model):
    name = models.CharField(max_length=50)
    password=models.CharField(max_length=15)
    phone_no=models.CharField(max_length=12)
    image = models.ImageField(upload_to='principal', blank=True, null=True)
    place = models.CharField(max_length=50)
    reg_no = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name}, {self.place}"

    def save(self, *args, **kwargs):
        # Normalize fields to reduce login errors
        if self.name:
            self.name = self.name.strip().title()
        if self.reg_no:
            self.reg_no = self.reg_no.strip().upper()

        # Hash password if not hashed already
        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)

        # Compress image if >200KB
        if self.image and hasattr(self.image, "size") and self.image.size > 200 * 1024:
            img = Image.open(self.image)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img_io = BytesIO()
            img.save(img_io, format="JPEG", quality=70, optimize=True)
            self.image = ContentFile(img_io.getvalue(), name=self.image.name)

        super().save(*args, **kwargs)

    # Check password securely
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
