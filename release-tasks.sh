#!/bin/bash

python manage.py migrate --run-syncdb
python manage.py loaddata industry.json
