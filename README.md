[![Build Status](https://github.com/maxisme/idmyteam-server/workflows/ID%20My%20Team%20Server/badge.svg)](https://github.com/maxisme/idmyteam-server/actions)
[![codecov](https://codecov.io/gh/maxisme/idmyteam-server/branch/master/graph/badge.svg?token=3BHMWx6kUO)](https://codecov.io/gh/maxisme/idmyteam-server)
[Client Code](https://github.com/maxisme/idmyteam-server)

# Local environment
## `pre-commit`
```
$ pip install pre-commit
$ pre-commit install
```

to test:
```
$ pre-commit run --all-files
```

## How to run
### Full integration
```
$ docker-compose up --build
```
Then access at `http://localhost/`.

### Custom `runserver`
```
$ docker-compose up -d db redis
$ cd web
$ python3 manage.py migrate
$ python3 manage.py loaddata test-user.json
$ python3 manage.py runserver
```
You can then login with the credentials `testuser`:`testuser`

___

#### requirements.txt
```
pipdeptree | grep -P '^\w+' > web/requirements.txt
```

#### sass
 - `sass source/stylesheets/index.scss build/stylesheets/index.css --style compressed`
 - `$FilePath$ $FileNameWithoutExtension$.css --style compressed` (intelij)
 

### Updating models
```
$ python3 manage.py makemigrations
```

# k8 deployment
```
kubectl create secret generic idmyteam --from-env-file web/.env
helm upgrade idmyteam maxisme/staticweb --install -f 'helm/django-values.yml'
    
```
 
___
# Tests
## TODO
 - [ ] Already in use username when signing up
 - [ ] Already in use email when signing up