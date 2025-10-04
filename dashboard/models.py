from django.db import models
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO

class SchoolDetails(models.Model):
    name = models.CharField(max_length=150)
    sub_name = models.CharField(max_length=150)
    place = models.CharField(max_length=100)
    image_1 = models.ImageField(upload_to='school-images', null=True, blank=True)
    image_2 = models.ImageField(upload_to='school-images', null=True, blank=True)
    adress = models.TextField()
    phone_number = models.CharField(max_length=12)
    history = models.TextField()
    educational_board = models.CharField(max_length=200, blank=True, null=True)
    reg_number = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name}-{self.place}"

    def save(self, *args, **kwargs):
        # Only one instance allowed
        if SchoolDetails.objects.exists() and not self.pk:
            raise ValidationError("Only one instance of SchoolDetails is allowed.")

        # Compress image_1
        if self.image_1:
            self.image_1 = self.compress_image(self.image_1)

        # Compress image_2
        if self.image_2:
            self.image_2 = self.compress_image(self.image_2)

        super().save(*args, **kwargs)

    def compress_image(self, image_field):
        """Compress image if size > 200KB"""
        if image_field.size > 200 * 1024:  # 200KB
            img = Image.open(image_field)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img_io = BytesIO()
            img.save(img_io, format="JPEG", quality=70, optimize=True)
            new_image = ContentFile(img_io.getvalue(), name=image_field.name)
            return new_image
        return image_field

    def delete(self, *args, **kwargs):
        raise ValidationError("Deleting SchoolDetails is not allowed.")

    class Meta:
        verbose_name = "School Detail"
        verbose_name_plural = "School Details"


class Gallery(models.Model):
    image = models.ImageField(upload_to='gallery')
    title = models.CharField(max_length=200, default='no title')

    def _str_(self):
        return self.title

    def save(self, *args, **kwargs):
        # ❌ Removed self.name = self.title (since name is not a field)

        if self.image and self.image.size > 200 * 1024:  # > 200KB
            img = Image.open(self.image)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img_io = BytesIO()
            img.save(img_io, format="JPEG", quality=70, optimize=True)
            new_image = ContentFile(img_io.getvalue(), name=self.image.name)
            self.image = new_image

        super().save(*args, **kwargs)


class Notice(models.Model):
    event = models.CharField(max_length=200)
    date = models.DateField()
    time = models.CharField(max_length=200 ,null=True,blank=True)
    posters = models.ImageField(upload_to='notice_posters/', blank=True, null=True)

    def _str_(self):
        return self.event if self.event else "Poster Only Notice"

    def save(self, *args, **kwargs):
        # Convert event to title case
        if self.event:
            self.event = self.event.title()

        # Compress poster image if it's larger than 200KB
        if self.posters and self.posters.size > 200 * 1024:
            img = Image.open(self.posters)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img_io = BytesIO()
            img.save(img_io, format="JPEG", quality=70, optimize=True)
            new_image = ContentFile(img_io.getvalue(), name=self.posters.name)
            self.posters = new_image

        super().save(*args, **kwargs)


class TopScorer(models.Model):

    std = models.CharField(max_length=20, )
    exam_name = models.CharField(max_length=50)  # Default value added

    first_name = models.CharField(max_length=50)
    first_father_name = models.CharField(max_length=50)
    first_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    second_name = models.CharField(max_length=50)
    second_father_name = models.CharField(max_length=50)
    second_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    third_name = models.CharField(max_length=50)
    third_father_name = models.CharField(max_length=50)
    third_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def _str_(self):
        return f"{self.std} - {self.exam_name} - Top Scorers"

    class Meta:
        ordering = ['std', 'exam_name']


class SchoolCommittee(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='committee')
    place = models.CharField(max_length=50)
    position = models.CharField(max_length=50)
    number = models.CharField(max_length=12)

    def _str_(self):
        return f"{self.name} - {self.position}"

    def save(self, *args, **kwargs):
        # Convert text fields to title case
        self.name = self.name.title()
        self.place = self.place.title()
        self.position = self.position.title()

        # Compress image if it's larger than 200KB
        if self.image and self.image.size > 200 * 1024:
            img = Image.open(self.image)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img_io = BytesIO()
            img.save(img_io, format="JPEG", quality=70, optimize=True)
            new_image = ContentFile(img_io.getvalue(), name=self.image.name)
            self.image = new_image

        super().save(*args, **kwargs)


class Parents(models.Model):
    name = models.CharField(max_length=50)
    place = models.CharField(max_length=50)
    age = models.PositiveIntegerField()
    job = models.CharField(max_length=50)
    number = models.CharField(max_length=15)
    position = models.CharField(max_length=50, default="Parent")  # Add default or required input

    def __str__(self):
        return f"{self.name} - {self.position}"

    def save(self, *args, **kwargs):
        # Convert text fields to title case
        self.name = self.name.title()
        super().save(*args, **kwargs)


class Member(models.Model):
    parent = models.ForeignKey(Parents, on_delete=models.CASCADE, related_name='members')
    name = models.CharField(max_length=50)
    number = models.CharField(max_length=12)
    job = models.CharField(max_length=50)
    age = models.PositiveIntegerField()
    relation = models.CharField(max_length=20)  # e.g., Son, Daughter
    martial_status=models.CharField(max_length=50, null=True,blank=True)

    def __str__(self):
        return f"{self.name} ({self.relation}) of {self.parent.name}"


class Memorial(models.Model):
    name=models.CharField(max_length=50)
    place=models.CharField(max_length=100)
    image=models.ImageField(upload_to='memorial')
    date_of_death=models.CharField(max_length=100,null=True,blank=True)

    def __str__(self):
       return f"{self.name} - {self.place}"

    def save(self, *args, **kwargs):

        # Compress image if larger than 200KB
        if self.image and self.image.size > 200 * 1024:
            img = Image.open(self.image)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img_io = BytesIO()
            img.save(img_io, format="JPEG", quality=70, optimize=True)
            new_image = ContentFile(img_io.getvalue(), name=self.image.name)
            self.image = new_image

        super().save(*args, **kwargs)

