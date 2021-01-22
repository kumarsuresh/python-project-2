from django.db import models
from example.core.utility import TimestampModel

from .choices import (CampaignStatusType, EvidenceStatusCheckType,
                      EvidenceStatusType)

# Create your models here.

class Campaign(TimestampModel):
    name = models.CharField(max_length=40, null=True, blank=True)
    image = models.CharField(max_length=500, null=True, blank=True)
    image_icon = models.CharField(max_length=500, null=True, blank=True)
    reward = models.FloatField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    cutoff_optin_date = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    status = models.IntegerField(choices=CampaignStatusType.choices, default=CampaignStatusType.NOT_OPTED)
    max_stores = models.IntegerField(null=True, blank=True)
    max_stores_per_retailer = models.IntegerField(null=True, blank=True)
    is_new_product = models.BooleanField(default=False)
    supplier_id = models.IntegerField(null=True, blank=True)
    campaign_notes = models.TextField(max_length=250, null=True, blank=True)
    admin_notes = models.TextField(max_length=500, null=True, blank=True)
    product_notes = models.TextField(max_length=200, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    supplier_purchase_order = models.CharField(max_length=20, null=True, blank=True)
    supplier_name = models.CharField(max_length=500, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return '%s' % self.name

class MediaAsset(TimestampModel):
    name = models.CharField(max_length=150)
    image = models.CharField(max_length=500)
    desc = models.TextField(max_length=1000)

    def __str__(self):
        return '%s' % self.name

class CampaignMediaAsset(TimestampModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    media_asset = models.ForeignKey(MediaAsset, on_delete=models.CASCADE)
    sample_image = models.CharField(max_length=500, null=True, blank=True)
    qrcode = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return '%s' % self.campaign.name


class CampaignBrand(TimestampModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_brand")
    brand_id = models.IntegerField()

    def __str__(self):
        return '%s' % self.campaign.name

class CampaignMediaAssetProduct(TimestampModel):
    campaign_media_asset = models.ForeignKey(CampaignMediaAsset, on_delete=models.CASCADE, related_name="campaign_media")
    product_id = models.IntegerField()
    notes = models.TextField(max_length=500, null=True, blank=True)

    def __str__(self):
        return '%s' % self.campaign_media_asset.campaign.name

class RetailerCampaign(TimestampModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="retailercampaign_campaign")
    user_id = models.IntegerField() #retailer id
    user_name = models.CharField(max_length=244)
    opted_by = models.IntegerField()
    is_opt_out = models.BooleanField(default=False)

    def __str__(self):
        return '%s' % self.campaign.name

    class Meta:
        unique_together = ('campaign', 'user_id')

class RetailerCampaignMediaAsset(TimestampModel):
    retailer_campaign = models.ForeignKey(RetailerCampaign, on_delete=models.CASCADE)
    campaign_media_asset = models.ForeignKey(CampaignMediaAsset, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % self.retailer_campaign.campaign.name

class RetailerCampaignStore(TimestampModel):
    retailer_campaign = models.ForeignKey(RetailerCampaign, on_delete=models.CASCADE, related_name="retailercampaign_store")
    store_id = models.IntegerField()
    store_name = models.CharField(max_length=500)

    def __str__(self):
        return '%s' % self.retailer_campaign.campaign.name

class CampaignEvidence(TimestampModel):
    campaign_media_asset = models.ForeignKey(CampaignMediaAsset, on_delete=models.CASCADE, related_name="campaign_media_evidence")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    reward = models.FloatField()
    
    def __str__(self):
        return '%s' % self.campaign.name

class StoreCampaignEvidence(TimestampModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    store_id = models.IntegerField()
    store_name = models.CharField(max_length=500)  #Keeping this info for sorting and needs to be updated by kafka
    retailer_id = models.IntegerField()
    retailer_name = models.CharField(max_length=500)
    evidence = models.ForeignKey(CampaignEvidence, on_delete=models.CASCADE)
    is_submitted = models.BooleanField(default=False)
    task_status = models.IntegerField(choices=EvidenceStatusType.choices, default=EvidenceStatusType.OUTSTANDING)

    def __str__(self):
        return '%s' % self.campaign.name

class PhotoEvidence(TimestampModel):
    store_campaign_evidence = models.ForeignKey(StoreCampaignEvidence, on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    submitter_message = models.TextField(blank=True)
    submitted_by = models.IntegerField(null=True, blank=True)
    is_choosen = models.BooleanField(default=False)
    is_no_improvement = models.BooleanField(default=False)
    evidence_url = models.CharField(max_length=500, blank=True)
    rate1 = models.IntegerField(null=True, blank=True) # on time
    rate2 = models.IntegerField(null=True, blank=True) # correct product
    rate3 = models.IntegerField(null=True, blank=True) # stock levels
    rate4 = models.IntegerField(null=True, blank=True) # merchandised correctly
    rate5 = models.IntegerField(null=True, blank=True) # price labeled
    is_rate1_highlight = models.BooleanField(default=False)
    is_rate2_highlight = models.BooleanField(default=False)
    is_rate3_highlight = models.BooleanField(default=False)
    is_rate4_highlight = models.BooleanField(default=False)
    is_rate5_highlight = models.BooleanField(default=False)
    avg_rate = models.FloatField(null=True, blank=True)
    evidence_status = models.IntegerField(choices=EvidenceStatusCheckType.choices, default=EvidenceStatusCheckType.AWAITING_APPROVAL)

    def __str__(self):
        return '%s' % self.store_campaign_evidence.campaign.name

class TargetRetailer(TimestampModel):
    '''
    Target Retailer for a campaign
    '''
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_targetretailer")
    retailer_id = models.IntegerField()
    retailer_business = models.IntegerField()

    @property
    def all_stores(self):
        _ = self
        return True


class TargetStores(TimestampModel):
    '''
    Target Stores for a campaign
    '''
    target_retailer = models.ForeignKey(TargetRetailer, on_delete=models.CASCADE)
    store_id = models.IntegerField()


class EvidenceLastAccess(TimestampModel):
    '''
    model to get badge count for evidence listing
    '''
    campaign = models.ForeignKey(Campaign)
    user_id = models.IntegerField()

class LastLoggedInTime(models.Model):
    user = models.IntegerField(unique=True)
    campaign_date = models.DateTimeField(null=True, blank=True)
    task_date = models.DateTimeField(null=True, blank=True)
