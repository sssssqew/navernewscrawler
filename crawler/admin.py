from django.contrib import admin
from .models import Keyword

# Register your models here.
class KeywordAdmin(admin.ModelAdmin):
	search_fields = ['name','category', 'donut', 'created_date']
	
admin.site.register(Keyword, KeywordAdmin)