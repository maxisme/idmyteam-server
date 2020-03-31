[![Build Status](https://github.com/maxisme/idmyteam-server/workflows/ID%20My%20Team%20Server/badge.svg)](https://github.com/maxisme/idmyteam-server/actions)

[Client Code](https://github.com/maxisme/idmyteam-server)

```
$ git config core.hooksPath .githooks/
$ chmod +x .githooks/*
```

1. Create a database `idmyteamserver`
2. `$ python manage.py migrate`

### Helpers
When editing the models files run:
 - `python manage.py makemigrations idmyteamserver`


#### sass
 - `sass source/stylesheets/index.scss build/stylesheets/index.css`
 - `$FilePath$ $FileNameWithoutExtension$.css` (intelij)