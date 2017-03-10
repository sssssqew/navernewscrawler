from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^$', views.index, name='keyword_list'),
	url(r'^store/$', views.store, name='keyword_store'),
	url(r'^csv/$', views.csvWriter, name="download_to_csv"),
]