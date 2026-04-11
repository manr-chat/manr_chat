#!/usr/bin/sh

cd `dirname $0`
source ~/envs/def/bin/activate
python3 app.py "$@"
