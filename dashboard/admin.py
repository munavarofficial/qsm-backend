from django.contrib import admin
from .models import SchoolDetails,Notice,Gallery,TopScorer,SchoolCommittee,Parents,Member,Memorial
# Register your models here.


admin.site.register(SchoolDetails)
admin.site.register(Gallery)
admin.site.register(Notice)
admin.site.register(TopScorer)
admin.site.register(SchoolCommittee)
admin.site.register(Parents)
admin.site.register(Member)
admin.site.register(Memorial)