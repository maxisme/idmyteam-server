#!/bin/bash
# for jenkins ssh:
# $ visudo
# jenk ALL = NOPASSWD: /bin/bash /var/www/idmyteam-server/deploy.sh

cd /var/www/idmyteam-server

git checkout master
git fetch &> /dev/null
diffs=$(git diff master origin/master)

if [ ! -z "$diffs" ]
then
    echo "Pulling code from GitHub..."
    git pull origin master

    supervisorctl restart idmyteamweb:*
else
    echo "Already up to date"
fi