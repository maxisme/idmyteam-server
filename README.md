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
### Web
1. `docker-compose up -d db`
2. `cd web`
3. `$ python manage.py migrate`
4. `$ python manage.py loaddata test-user.json`
You can then login with the credentials `testuser`:`testuser`

____

### Helpers
When editing the models files run:
 - `python manage.py makemigrations idmyteam`


#### sass
 - `sass source/stylesheets/index.scss build/stylesheets/index.css`
 - `$FilePath$ $FileNameWithoutExtension$.css` (intelij)