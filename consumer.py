import json
import os

import django

from kafka import KafkaConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")
django.setup()

from campaign.models import RetailerCampaign
from django.conf import settings

'''
Consumer for update retailer in microservices.
'''
consumer_update_retailer = KafkaConsumer('update_retailer', bootstrap_servers=settings.EXP_EXAMPLE_USER_KAFKA_SERVER)
for msg in consumer_update_retailer:
    request_data = json.loads(msg.value)
    retailer_campaign = RetailerCampaign.objects.get(user_id=request_data.get('id'))
    retailer_campaign.user_name = '%s %s' % (request_data.get('firstname'), request_data.get('lastname'))
    retailer_campaign.save()
consumer_update_retailer.flush()
