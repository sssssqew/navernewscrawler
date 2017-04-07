# -*- coding: utf-8 -*- 
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from .forms import KeywordForm
from .models import Keyword
import json
from dateutil.relativedelta import relativedelta
import datetime
import os

import sys
from bs4 import BeautifulSoup
import urllib2
import lxml
import numpy as np 
import multiprocessing
import timeit
import csv
import collections
import logging
import time

from httplib import IncompleteRead

# 데이터 수집기간 설정 
# TERM = 1 # 어제 하루치 데이터 
TERM = 5

# URL 쿼리 설정 
TARGET_URL_BEFORE_QUERY = 'https://search.naver.com/search.naver?where=news&se=0&query='
TARGET_URL_BEFORE_FRONT_DATE = '&ie=utf8&sm=tab_opt&sort=0&photo=0&field=0&reporter_article=&pd=3&ds='
TARGET_URL_BEFORE_BACK_DATE = '&docid=&nso=so%3Ar%2Cp%3Afrom'
TARGET_URL_REST = '%2Ca%3Aall&mynews=0&mson=0&refresh_start=0&related=0'

is_saved = 0
is_deleted = 0
is_updated = 0

# 로깅 모듈 설정
logging.basicConfig(
	filename = ("%s.log" % (datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"))),
	filemode = "a",
	format = "%(levelname)-10s %(asctime)s %(message)s",
	level = logging.DEBUG
)

# 검색할 기간의 날짜 생성  
def createDaysForYear(term):
	start_date = datetime.datetime.now() - relativedelta(days=term)
	end_date = datetime.datetime.now() 
	
	days = []
	d = start_date
	while(d.year != end_date.year or d.month != end_date.month or d.day != end_date.day):
		days.append(d)
		d = d + datetime.timedelta(days=1)

	return days

# 날짜 생성 
def createDaysForPeriod(s_year, s_month, s_day, e_year, e_month, e_day):
	days = []
	d = datetime.date(s_year, s_month, s_day)
	while(d.year != e_year or d.month != e_month or d.day != e_day + 1):
		days.append(d)
		d = d + datetime.timedelta(days=1)
	# print days 
	return days

# URL 쿼리 생성 
def createUrlQuery(keword, day):
	front_date = day.strftime('%Y.%m.%d') # URL 앞부분 날짜 포맷
	back_date = day.strftime('%Y%m%d') # URL 뒷부분 날짜 포맷
	query = TARGET_URL_BEFORE_QUERY \
							+ urllib2.quote(keword.encode('utf-8')) \
							+ TARGET_URL_BEFORE_FRONT_DATE \
							+ front_date + '&de=' \
							+ front_date + TARGET_URL_BEFORE_BACK_DATE \
							+ back_date + 'to' \
							+ back_date \
							+ TARGET_URL_REST
	return query

# 뉴스 건수 추출 
def getNumberOfNews(query):
	# Connection refused error 해결 
	try:
		# 사람이 검색하는 것처럼 속임 
		user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
		headers = { 'User-Agent' : user_agent }
		r = urllib2.Request(query, headers=headers)
		URL_source_FOR_DATE = urllib2.urlopen(r)
		# logging.info("url query success !!")
	except Exception as e:
		logging.error(e)
		URL_source_FOR_DATE.close()
		print e
		return 0
		# pass

	soup = BeautifulSoup(URL_source_FOR_DATE, 'lxml', from_encoding='utf-8')

	# 기사 없음 
	if not soup.find('div', 'title_desc all_my'):
		URL_source_FOR_DATE.close()
		logging.info("no news found")
		print "no news found"
		return 0

	news_num_for_day = soup.find('div', 'title_desc all_my').select('span')[0].text.split('/')
	news_num_for_day_int = int(filter(lambda x: x.isdigit(), news_num_for_day[1])) # 숫자 추출 
	URL_source_FOR_DATE.close()
	return  news_num_for_day_int

def get_content(url):
	print "searching..."
	logging.info("searching...")
	num_news = getNumberOfNews(url)
	return num_news

def delete_spaces(words):
	w_list = []
	words = words.split(',')
	for word in words:
		w_list.append(word.strip())
	return w_list


def make_condition_between_dates(crawled_data, s_date, e_date):
	x = crawled_data[:, 0] # np array (keyword)
	y = crawled_data[:, 1] # np array (date)
	z = crawled_data[:, 2] # np array (number of news)

	x_map = np.array(map(lambda p: p.encode('utf-8'), x)) # np array
	y_map = np.array(map(lambda p: datetime.datetime.strptime(p, "%Y-%m-%d"), y)) # np array

	condi = np.logical_and(y_map >=  s_date, y_map <= e_date)
	return condi, y, z

def divideDate(str_date):
	start_date_arr = str_date.split('-')
	year = int(start_date_arr[0])
	month = int(start_date_arr[1])
	day = int(start_date_arr[2])
	return year, month, day

# 조회 페이지 
def index(request):
	global is_saved
	global is_deleted
	global is_updated
	# json dums : string
	# json loads: list
	print "--------------------------------------"
	print "rendering start..."
	# logging.info("rendering start...")

	isExist = False

	selected_keywords = []
	context = {}

	if request.method == 'POST':
		selected_keywords = delete_spaces(request.POST['selected_keywords'])
		
	if selected_keywords:
		not_exist_keys = []
		day_list = []

		try:
			start_date_search = datetime.datetime.strptime(request.POST['start_date_search'], "%Y-%m-%d")
		except:
			start_date_search = datetime.datetime.strptime('2012-03-02', "%Y-%m-%d")
		try:
			end_date_search = datetime.datetime.strptime(request.POST['end_date_search'], "%Y-%m-%d")
		except:
			end_date_search = datetime.datetime.now()

		columns = []
		
		# DB 조회 
		for selected_keyword in selected_keywords:
			try:
				key_model = Keyword.objects.get(name=selected_keyword)
				if(key_model):
					print "model exist in DB"

				numOfNews = json.loads(key_model.numOfNews)
				np_numOfNews = np.array(numOfNews) # list to np array
				condition, y, z = make_condition_between_dates(np_numOfNews, start_date_search, end_date_search)
				date = y[np.where(condition)].tolist()
				data = z[np.where(condition)].tolist()

				date.insert(0, 'x')
				data.insert(0, selected_keyword)

				columns.append(data) 
				columns.insert(0, date)

			except:
				print "model doesn't exist in DB"
				not_exist_keys.append(selected_keyword)

		# DB 존재하는 경우 
		if len(columns) > 1:
			isExist = True
			context = {"columns":json.dumps(columns), "not_keys":not_exist_keys, "isExistData":isExist}
		else:
			context = {"not_keys":not_exist_keys, "isExistData":isExist}
	else:
		if is_saved:
			context = {"is_saved":is_saved, "isExistData":isExist}
			is_saved = 0
		elif is_deleted :
			context = {"is_deleted":is_deleted, "isExistData":isExist}
			is_deleted = 0
		elif is_updated:
			context = {"is_updated":is_updated, "isExistData":isExist}
			is_updated = 0
			

	return render(request, 'crawler/search.html', context)


# 검색 페이지 
def store(request):

	# is_saved = 0
	start_time = timeit.default_timer()

	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			categories = []
			donuts = []
			keywords = []
			file = request.FILES['file']
			print "-------------------"
			# print request.charset
			csvReader = csv.reader(file)

			for k in csvReader:
				categories.append(k[0].decode('euc-kr'))
				donuts.append(k[1].decode('euc-kr'))
				keywords.append(k[2].decode('euc-kr'))
			keys = keywords
		# 직접 입력 
		else:
			keywords = request.POST['keywords']
			keys = delete_spaces(keywords)

	# 수집할 검색어 및 날짜 배열 만들기 (기간으로 수정함)
	if keys:
		if request.POST['start_date_search']:
			start_date_search = request.POST['start_date_search'].encode('utf-8')
		else:
			start_date_search = '2017-03-01'
		if request.POST['end_date_search']:
			end_date_search = request.POST['end_date_search'].encode('utf-8')
		else:
			end_date_search = datetime.datetime.now().strftime('%Y-%m-%d')

	START_YEAR, START_MONTH, START_DAY = divideDate(start_date_search)
	END_YEAR, END_MONTH, END_DAY = divideDate(end_date_search)
	days = createDaysForPeriod(START_YEAR, START_MONTH, START_DAY, END_YEAR, END_MONTH, END_DAY)
	# print days 
	
	# DB 저장 
	for idx, key in enumerate(keys):
		print str(key.encode('utf-8'))
		try:
			key_model = Keyword.objects.get(name=key)

		except:
			record_data = collections.OrderedDict()
			URLS = []

			# URL 리스트 생성 
			for day in days:
				url = createUrlQuery(key, day)
				URLS.append(url)

			# 데이터 수집 
			pool = multiprocessing.Pool(processes=5)  
			time.sleep(2)
			num_news_list = pool.map(get_content, URLS) 
			pool.close() 
			pool.join()   
		

			record_data[key] = []
			for i in range(len(days)):
				row = []
				row.append(key)
				row.append(days[i].strftime("%Y-%m-%d"))
				row.append(num_news_list[i])
				record_data[key].append(row)


			# 결과 저장 
			key_model = Keyword(
				name=key, 
				category = categories[idx],
				donut = donuts[idx],
				numOfNews=json.dumps(record_data[key])
			)
			key_model.publish()
			key_model.save() 
			
			global is_saved
			is_saved = 1

	# 실행시간 표시 
	elapsed = timeit.default_timer() - start_time
	print "------------------------------------------------------------------"
	print "실행시간(s): " + str(round(elapsed , 3)) + ' s'
	print "실행시간(min) : " + str(round(elapsed / 60 , 3)) + ' min'
	# logging.info("실행시간(s): " + str(round(elapsed , 3)) + ' s')

	return HttpResponseRedirect("/")


def csvWriter(request):
	today = datetime.datetime.now().strftime("%Y-%m-%d")
	# Create the HttpResponse object with the appropriate CSV header.
	response = HttpResponse(content_type='text/csv')
	filename = "navernews_" + today+".csv"
	response['Content-Disposition'] = 'attachment; filename=' + filename
	writer = csv.writer(response)

	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			selected_keywords = []
			file = request.FILES['file']
			print "-------------------"
			csvReader = csv.reader(file)

			for k in csvReader:
				# print k[1].decode('euc-kr') # file encoding에 따라 변경 (aws 에러남)
				selected_keywords.append(k[2].decode('euc-kr'))
			
		# 직접 입력 
		else:
			selected_keywords = delete_spaces(request.POST['selected_keywords'])


	if selected_keywords:
		not_exist_keys = []
		try:
			start_date_search = datetime.datetime.strptime(request.POST['start_date_search'], "%Y-%m-%d")
		except:
			start_date_search = datetime.datetime.strptime('2012-03-02', "%Y-%m-%d")
		try:
			end_date_search = datetime.datetime.strptime(request.POST['end_date_search'], "%Y-%m-%d")
		except:
			end_date_search = datetime.datetime.now()


		# DB 조회 
		for selected_keyword in selected_keywords:
			try:
				
				key_model = Keyword.objects.get(name=selected_keyword)
				if(key_model):
					print "model exist in DB"
				
				numOfNews = json.loads(key_model.numOfNews)
				np_numOfNews = np.array(numOfNews) # list to np array
				condition, y, z = make_condition_between_dates(np_numOfNews, start_date_search, end_date_search)
				date = y[np.where(condition)].tolist()
				data = z[np.where(condition)].tolist()

				suffix = u'(뉴)'
				# print type(suffix.encode('euc-kr'))

				for i in range(len(date)):

					writer.writerow([key_model.name.encode('euc-kr')+suffix.encode('euc-kr'), date[i].encode('euc-kr'), data[i].encode('euc-kr'), data[i].encode('euc-kr'), data[i].encode('euc-kr'), data[i].encode('euc-kr')])
					# print type(key_model.name.encode('utf-8'))

			except:
				print "model doesn't exist in DB"
				not_exist_keys.append(selected_keyword)

	return response


def delete(request):
	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			selected_keywords = []
			file = request.FILES['file']
			print "-------------------"
			csvReader = csv.reader(file)

			for k in csvReader:
				# print k[1].decode('euc-kr') # file encoding에 따라 변경 (aws 에러남)
				selected_keywords.append(k[2].decode('euc-kr'))
			
		# 직접 입력 
		else:
			selected_keywords = delete_spaces(request.POST['selected_keywords'])

	if selected_keywords:
		not_exist_keys = []
		try:
			start_date_search = datetime.datetime.strptime(request.POST['start_date_search'], "%Y-%m-%d")
		except:
			start_date_search = datetime.datetime.strptime('2012-03-02', "%Y-%m-%d")
		try:
			end_date_search = datetime.datetime.strptime(request.POST['end_date_search'], "%Y-%m-%d")
		except:
			end_date_search = datetime.datetime.now()

		# DB 조회 
		for selected_keyword in selected_keywords:
			try:
				
				key_model = Keyword.objects.get(name=selected_keyword)
				if(key_model):
					print "model exist in DB"
				
				numOfNews = json.loads(key_model.numOfNews)
				np_numOfNews = np.array(numOfNews) # list to np array
				condition, y, z = make_condition_between_dates(np_numOfNews, start_date_search, end_date_search)
				np_numOfNews_deleted = np_numOfNews[np.logical_not(condition)] # 특정조건을 만족하는 행 제외 
				# print type(np_numOfNews_deleted.tolist())

				key_model.numOfNews = json.dumps(np_numOfNews_deleted.tolist())
				key_model.save(update_fields=['numOfNews'])
				global is_deleted
				is_deleted = 1

			except:
				print "model doesn't exist in DB"
				not_exist_keys.append(selected_keyword)


	return HttpResponseRedirect("/")


def show(request):
	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			selected_keywords = []
			file = request.FILES['file']
			print "-------------------"
			csvReader = csv.reader(file)

			for k in csvReader:
				# print k[1].decode('euc-kr') # file encoding에 따라 변경 (aws 에러남)
				selected_keywords.append(k[2].decode('euc-kr'))
			
		# 직접 입력 
		else:
			selected_keywords = delete_spaces(request.POST['selected_keywords'])

	if selected_keywords:
		not_exist_keys = []
		try:
			start_date_search = datetime.datetime.strptime(request.POST['start_date_search'], "%Y-%m-%d")
		except:
			start_date_search = datetime.datetime.strptime('2012-03-02', "%Y-%m-%d")
		try:
			end_date_search = datetime.datetime.strptime(request.POST['end_date_search'], "%Y-%m-%d")
		except:
			end_date_search = datetime.datetime.now()

		wanted_json = []

		# DB 조회 
		for i, selected_keyword in enumerate(selected_keywords):
			try:
				key_json = collections.OrderedDict()
				key_model = Keyword.objects.get(name=selected_keyword)
				if(key_model):
					print type(key_model.name.encode('utf-8'))
					print "model exist in DB"
					key_json['id'] = key_model.id
					key_json['name'] = key_model.name.encode('utf-8')
					key_json['category'] = key_model.category
					key_json['donut'] = key_model.donut

					
				
				numOfNews = json.loads(key_model.numOfNews)
				np_numOfNews = np.array(numOfNews) # list to np array
				condition, y, z = make_condition_between_dates(np_numOfNews, start_date_search, end_date_search)
				result = np_numOfNews[condition] # 특정조건을 만족하는 행 제외 
			
				# print result.tolist()
				key_json['history'] = result.tolist()
				wanted_json.append(key_json) 

			except:
				print "model doesn't exist in DB"
				not_exist_keys.append(selected_keyword)

		# print wanted_json
	return HttpResponse(json.dumps(wanted_json, indent=4))


# 선택한 기간에 대한 크롤링 데이터를 추가하고 동시에 도넛명도 변경함 
def update(request):
	global is_updated
	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			categories = []
			donuts = []
			keywords = []
			file = request.FILES['file']
			print "-------------------"
			csvReader = csv.reader(file)

			for k in csvReader:
				categories.append(k[0].decode('euc-kr'))
				donuts.append(k[1].decode('euc-kr'))
				keywords.append(k[2].decode('euc-kr'))
			keys = keywords
		# 직접 입력 
		else:
			keywords = request.POST['keywords']
			keys = delete_spaces(keywords)


	cnt = 0
	if request.POST.get("Category_Only"):
		# 도넛명으로 카테고리 추가 & 변경 하도록 수정 
		for idx, donut in enumerate(donuts):
			try:
				key_models = Keyword.objects.filter(donut=donut)
				if(key_models):
					print "model exist in DB"
					
				for key_model in key_models:
					cnt += 1
					key_model.category = categories[idx]
					key_model.save(update_fields=['category'])
					key_model.change()
				is_updated = 1
			except:
				print "model doesn't exist in DB"

		print "* saved category only *"
		print cnt

	elif request.POST.get("Donut_Only"):
		# DB 조회 
		for idx, key in enumerate(keys):
			try:
				key_model = Keyword.objects.get(name=key)
				if(key_model):
					print "model exist in DB"
				key_model.donut = donuts[idx]
				key_model.save(update_fields=['donut'])
				key_model.change()
				is_updated = 1
			except:
				print "model doesn't exist in DB"

		print "* saved donut name only *"
	else:	
		# 수집할 검색어 및 날짜 배열 만들기 (기간으로 수정함)
		if keys:
			if request.POST['start_date_search']:
				start_date_search = request.POST['start_date_search'].encode('utf-8')
			else:
				start_date_search = '2017-03-01'
			if request.POST['end_date_search']:
				end_date_search = request.POST['end_date_search'].encode('utf-8')
			else:
				end_date_search = datetime.datetime.now().strftime('%Y-%m-%d')


		START_YEAR, START_MONTH, START_DAY = divideDate(start_date_search)
		END_YEAR, END_MONTH, END_DAY = divideDate(end_date_search)
		days = createDaysForPeriod(START_YEAR, START_MONTH, START_DAY, END_YEAR, END_MONTH, END_DAY)
		# print days 

		# DB 조회 
		for idx, key in enumerate(keys):
			try:
				key_model = Keyword.objects.get(name=key)
				if(key_model):
					print "model exist in DB"
					numOfNews = json.loads(key_model.numOfNews)
					# print key_model.name (aws에서 완전히 삭제해야 동작함)

				# record_data = collections.OrderedDict()
				URLS = []

				# URL 리스트 생성 
				for day in days:
					url = createUrlQuery(key, day)
					URLS.append(url)

				# 데이터 수집 
				pool = multiprocessing.Pool(processes=5)  
				time.sleep(2)
				num_news_list = pool.map(get_content, URLS) 
				pool.close()  
				pool.join()   

				# record_data[key] = []
				for i in range(len(days)):
					row = []
					row.append(key)
					row.append(days[i].strftime("%Y-%m-%d"))
					row.append(num_news_list[i])
					numOfNews.append(row)

				# 업데이트 
				key_model.numOfNews = json.dumps(numOfNews)
				key_model.save(update_fields=['numOfNews'])
				key_model.change()
				is_updated = 1

			except:
				print "model doesn't exist in DB"
				not_exist_keys.append(selected_keyword)

		print "* saved keyword only*"

	return HttpResponseRedirect("/")


def checkIfKeyExist(request):
	cnt = 0
	abcent = []
	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			keywords = []
			file = request.FILES['file']
			print "-------------------"
			csvReader = csv.reader(file)

			for k in csvReader:
				keywords.append(k[2].decode('euc-kr'))

	for idx, key in enumerate(keywords):
			try:
				key_model = Keyword.objects.get(name=key)
				if(key_model):
					cnt = cnt + 1
					# print "model exist in DB"
			
			except:
				print "model doesn't exist in DB"
				print abcent.append(key)
	
	li = list(set(keywords))
	# print cnt
	print "csv 리스트 : " + str(len(keywords))
	print "중복 제거 리스트 : " + str(len(li))
	return HttpResponse(json.dumps(abcent))
