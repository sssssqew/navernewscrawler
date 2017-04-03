from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^$', views.index, name='keyword_list'),
	url(r'^store/$', views.store, name='keyword_store'),
	url(r'^csv/$', views.csvWriter, name="download_to_csv"),
	url(r'^delete/$', views.delete, name='keyword_delete'),
	url(r'^show/$', views.show, name='keyword_show'),
	url(r'^update/$', views.update, name='keyword_update'),
]