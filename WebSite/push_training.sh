#!/bin/sh
rsync -av --delete --exclude-from=push-exclude.txt . graham@theatrefestvm.ukwest.cloudapp.azure.com:/home/graham/training/website/
rsync -av --delete ./django_static/* graham@theatrefestvm.ukwest.cloudapp.azure.com:/home/graham/training/website/static

