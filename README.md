[![Build Status](https://github.com/maxisme/idmyteam-server/workflows/ID%20My%20Team%20Server/badge.svg)](https://github.com/maxisme/idmyteam-server/actions)

[Client Code](https://github.com/maxisme/idmyteam-server)

```
$ git config core.hooksPath .githooks/
$ chmod +x .githooks/*
```

To create new migrations run:
```
$ migrate create -ext sql -dir sql/ -seq "description"
```