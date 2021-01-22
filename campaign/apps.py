from django.apps import AppConfig

class CampaignConfig(AppConfig):
    name = 'campaign'

    def ready(self):
        _ = self
        from campaign import signals
