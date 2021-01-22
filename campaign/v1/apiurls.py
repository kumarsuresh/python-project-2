'''urls configurations for rest api requests'''
from django.conf.urls import url

from .api import *

urlpatterns = [
    url(r'^campaigns/(?P<user_id>\d+)/(?P<timestamp>.+)/$', CampaignListing.as_view(), name="campaigns"),
    url(r'^campaign-brands/(?P<user_id>\d+)/(?P<timestamp>.+)/$', CampaignsBrands.as_view(), name="campaign_brands_ids"),
    url(r'^campaign-global-search/(?P<user_id>\d+)/$', CampaignGlobalSearch.as_view(), name="campaign_global_search"),
    url(r'^campaign/(?P<user_id>\d+)/(?P<campaign_id>\d+)/$', CampaignDetail.as_view(), name="campaign"),
    url(r'^selectedstores/(?P<user_id>\d+)/(?P<campaign_id>\d+)/$', SelectedStoresListing.as_view(), name="selected_stores"),
    url(r'^opt-in/(?P<user_id>\d+)/(?P<campaign_id>\d+)/$', CampaignOptIn.as_view(), name="campaign_opt_in"),
    url(r'^opt-out/(?P<user_id>\d+)/(?P<campaign_id>\d+)/$', CampaignOptOut.as_view(), name="campaign_opt_out"),
    url(r'^targetstores/(?P<user_id>\d+)/(?P<campaign_id>\d+)/$', TargetStoresListing.as_view(), name="selected_stores"),
    url(r'^tasks/(?P<user_id>\d+)/(?P<timestamp>.+)/$', TasksListing.as_view(), name="campaign_tasks"),
    url(r'^taskcampaigns/(?P<user_id>\d+)/$', OptedCampaignsListing.as_view(), name="tasks_campaign"),
    url(r'^taskstores/(?P<user_id>\d+)/$', OptedStoresListing.as_view(), name="tasks_stores"),
    url(r'^prod-notes/(?P<media_asset_id>\d+)/$', CampMediaProdListing.as_view(), name="campaign_media_prod"),
    url(r'^filter/(?P<user_id>\d+)/$', FilterDetails.as_view(), name="filter"),
    url(r'^task/(?P<user_id>\d+)/(?P<task_id>\d+)/$', TaskDetail.as_view(), name="task_detail"),
    url(r'^submit-evidence/(?P<user_id>\d+)/$', SubmitPhotoEvidence.as_view(), name="submit-evidence"),
    url(r'^validate-qrcode/(?P<media_id>\d+)/(?P<campaign_id>\d+)/(?P<campaign_media_id>\d+)/$', ValidateQRCode.as_view(), name="validate-qrcode"),
    url(r'^evidences/(?P<evidence_id>\d+)/$', SubmittedEvidenceListing.as_view(), name="evidences"),
    url(r'^evidence/(?P<user_id>\d+)/(?P<evidence_id>\d+)/$', EvidenceDetail.as_view(), name="evidence"),
    url(r'^write-to-example/(?P<evidence_id>\d+)/$', WriteToexample.as_view(), name="write_example"),
    url(r'^retailer-reward/(?P<retailer_id>\d+)/$', RetailerReward.as_view(), name="retailer_reward"),
]
