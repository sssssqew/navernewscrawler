### 몰트 위스키(mod_wsgi) 를 이용한 장고서버 셋팅 -> 가장 손쉬운 셋팅방법

```
...
0. 가상환경 생성 및 필요모듈 설치하기 
1. sudo pip install mod_wsgi-httpd 
2. sudo pip install mod_wsgi 
3. pip freeze 로 전역환경에 설치되었음을 확인하기 
4. settings.py에 INSTALLED_APPS 설정에 'mod_wsgi.server' 추가하기
5. 정적(static)파일 생성하기 
-> python manage.py collectstatic
5. manage.py 파일이 위치한 곳에서 mod_wsgi 실행하기 
-> python manage.py runmodwsgi --setup-only --user sylee --group sylee --server-root=/tmp/mod_wsgi-localhost:8000:1012
6. 아파치 실행 또는 재실행하기 
-> /tmp/mod_wsgi-localhost:8000:1012/apachectl start(restart)
...
```

### 참고 사이트 

* [https://github.com/GrahamDumpleton/mod_wsgi](Link URL)
* [http://ggilrong.tistory.com/entry/Django-Apache-%EC%89%AC%EC%9A%B4-%EC%97%B0%EB%8F%99%EB%B0%A9%EB%B2%95-How-to-use-Django-with-Apache-and-modwsgi](Link URL)
* [http://stackoverflow.com/questions/24760872/how-can-run-django-on-centos-using-wsgi](Link URL)