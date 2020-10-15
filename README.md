[![Build Status](https://github.com/maxisme/idmyteam-server/workflows/ID%20My%20Team%20Server/badge.svg)](https://github.com/maxisme/idmyteam-server/actions)

[Client Code](https://github.com/maxisme/idmyteam-server)

```
$ git config core.hooksPath .githooks/
$ chmod +x .githooks/*
```

## Local setup
### .env
1. `$ cd web; cp .env.example .env`
2. https://djecrety.ir/ add to SECRET_KEY
3. DEBUG=True

### Full
Make sure the `.env` contains `DATABASE_HOST=db`
```
$ docker-compose up
```
Then access at `http://localhost/`.

### Web
Make sure the .env contains `DATABASE_HOST=127.0.0.1`
```
$ docker-compose up -d db redis
$ cd web
$ python3 manage.py migrate
$ python3 manage.py loaddata test-user.json
$ python3 manage.py runserver
```
You can then login with the credentials `testuser`:`testuser`

____

### Helpers
When editing the models files run:
 - `python manage.py makemigrations`


#### sass
 - `sass source/stylesheets/index.scss build/stylesheets/index.css`
 - `$FilePath$ $FileNameWithoutExtension$.css` (intelij)