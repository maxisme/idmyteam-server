#!/bin/bash
python manage.py collectstatic
exec "$@"