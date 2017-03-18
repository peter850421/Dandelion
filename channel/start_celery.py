from celery import Celery
import celeryconfig

#Create Celery app from celeryconfig
app = Celery()
app.config_from_object(celeryconfig)

