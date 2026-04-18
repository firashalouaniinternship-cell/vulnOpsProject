import os
from celery import Celery

# Dfinit le module de rglages par dfaut de Django pour Celery.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('vulnops')

# Utilise une chane pour que le worker n'ait pas  sérialiser
# l'objet de configuration lors de l'utilisation de Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Charge les tches de toutes les applications Django enregistres.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
