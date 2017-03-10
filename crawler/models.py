from __future__ import unicode_literals

from django.db import models
from django.utils import timezone


# Create your models here.
class Keyword(models.Model):
	name = models.CharField(max_length=30)
	relatedKeys = models.TextField(blank=True, null=True)
	numOfNews = models.TextField()
	created_date = models.DateTimeField(blank=True, null=True)

	def publish(self):
		self.created_date = timezone.now()
		self.save()

	def __str__(self):
		return self.name.encode('utf-8')
