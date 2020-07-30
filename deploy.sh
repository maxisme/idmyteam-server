#!/bin/bash
git pull
docker stack deploy -c stack.yml idmyteam --prune