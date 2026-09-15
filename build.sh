#!/usr/bin/env bash
# Script de build exécuté par Render à chaque déploiement

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

