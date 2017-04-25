#!/bin/bash

set -e

cd

rm -rf /home/reduce_slave/*
rm -rf /home/reduce_slave/.pid

echo $$ > .pid

exec > .log
exec 2>&1

echo "<pre>"
unzip -u "$1" -d .
bash -x test.sh
echo "</pre>"
