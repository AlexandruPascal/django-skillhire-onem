release: python manage.py migrate --run-syncdb && python manage.py loaddata industry.json
web: gunicorn skillhire.wsgi --log-file -
