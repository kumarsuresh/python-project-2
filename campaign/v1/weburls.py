'''urls configurations for rest api requests'''
from django.conf.urls import url

from .web import *

urlpatterns = [
    url(r'^campaign-data/$', CampaignData.as_view(), name="campaign_data"),
    url(r'^brand-campaign-data/$', BrandCampaignData.as_view(), name="brand_campaign_data"),
    url(r'^stats/$', CampaignStats.as_view(), name="campaign_stats"),
    url(r'^campaign-opted-count/$', CampaignOptedCountView.as_view(), name="campaign_opted_count"),
    url(r'^retailer-stats/(?P<campaign_id>\d+)/$', TargetedRetailerStats.as_view(), name="retailer_stats"),
    url(r'^retailer-campaigns/(?P<retailer_id>\d+)/$', RetailerCampaignListing.as_view(), name="retailer_campaigns"),
    url(r'^campaigns/$', CampaignListing.as_view(), name="campaign_list"),
    url(r'^create-campaign/$', CreateCampaign.as_view(), name="create_campaign"),
    url(r'^publish-campaign/$', PublishCampaignView.as_view(), name="publish_campaign"),

    url(r'^stores-list-data/$', StoresListingData.as_view(), name="store_listing_data"),
    url(r'^update-campaign/(?P<id>\d+)/$', UpdateCampaign.as_view(), name="update_campaign"),
    url(r'^media-assets/$', MediaAssetsListing.as_view(), name="media_assets_list"),
    url(r'^store/(?P<campaign_id>\d+)/$', RemoveCampaignStore.as_view(), name="remove_campaign_store"),
    url(r'^retailer/(?P<campaign_id>\d+)/$', RemoveCampaignRetailers.as_view(), name="remove_campaign_retailer"),
    url(r'^products/(?P<media_asset_id>\d+)/$', CampaignProductsView.as_view(), name="list_campaign_products"),
    url(r'^campaign/(?P<id>\d+)/$', CampaignDetail.as_view(), name="campaign_details"),
    url(r'^media-asset/(?P<pk>\d+)/$', MediaAssetRemove.as_view(), name="campaign_media"),
    url(r'^list-campaign-media-asset/(?P<campaign_id>\d+)/$', CampaignMediaAssetListView.as_view(), name="list_campaign_media_asset"),

    url(r'^evidence-media-asset/(?P<campaign_id>\d+)/$', MediaAssetForEvidenceListView.as_view(), name="campaign_evidence_media_asset"),
    url(r'^media-asset-evidence/(?P<campaign_media_asset_id>\d+)/$', MediaAssetEvidenceListView.as_view(), name="campaign_media_asset_evidence"),
    url(r'^opted-retailer/(?P<campaign_id>\d+)/$', CampaignRetailerListView.as_view(), name="campaign_opted_retailer"),
    url(r'^opted-retailers-store/(?P<retailer_campaign_id>\d+)/$', RetailerCampaignStoreListView.as_view(), name="campaign_opted_retailers_store"),
    url(r'^evidence-proof/(?P<campaign_id>\d+)/$', CampaignEvidencePhotoListView.as_view(), name="campaign_evidence_photo"),
    url(r'^photo-evidence/(?P<campaign_id>\d+)/(?P<photo_evidence_id>\d+)/$', CampaignPhotoEvidenceUpdateView.as_view(), name="campaign_evidence_photo_create"),
    url(r'^evidence-stats/(?P<user_id>\d+)/(?P<campaign_id>\d+)/$', EvidenceStatsView.as_view(), name="campaign_evidence_stats"),
    url(r'^outstanding-stats/(?P<campaign_id>\d+)/$', OutstandingEvidenceStatsView.as_view(), name="campaign_outstanding_stats"),
    url(r'^last-access/$', EvidenceLastAccessView.as_view(), name="task_last_access"),

    url(r'^product/(?P<pk>\d+)/$', MediaAssetProductRemove.as_view(), name="campaign_product"),
    url(r'^evidence/(?P<pk>\d+)/$', EvidenceRemove.as_view(), name="campaign_evidence"),
    url(r'^targetretailers/$', TargetRetailersView.as_view(), name="target_retailers"),
    url(r'^retailers/(?P<campaign_id>\d+)/$', CampaignRetailersView.as_view(), name="campaign_target_retailers"),
    url(r'^stores/(?P<campaign_id>\d+)/$', CampaignStoresView.as_view(), name="campaign_store_retailers"),
    url(r'^retailer-stores/(?P<campaign_id>\d+)/(?P<retailer_business_id>\d+)/$', CampaignRetailerStoresView.as_view(), name="campaign_retailers_store"),
    url(r'^retailer-stores-count/(?P<campaign_id>\d+)/$', CampaignRetailerStoresCountView.as_view(), name="campaign_retailers_store_count"),
    url(r'^retailer-campaign-stats/$', RetailerCampaignStats.as_view(), name="retailer_campaign_stats"),
    url(r'^opted-stores/(?P<campaign_id>\d+)/$', CampaignOptedStoresView.as_view(), name="campaign_stores_list"),
    url(r'^campaigns-retailer-deactivate/(?P<retailer_id>\d+)/$', RetailerCampaignDeactivateView.as_view(), name="campaign_deactivate"),
    url(r'^campaigns-store-deactivate/$', RetailerCampaignDeactivateView.as_view(), name="campaign_store_deactivate"),
    url(r'^campaign-tasks/(?P<campaign_id>\d+)/$', CampaignTaskListView.as_view(), name="campaign_tasks"),
    url(r'^campaign-task/(?P<pk>\d+)/$', CampaignTaskView.as_view(), name="campaign_task_details"),
    url(r'^live-campaign/$', LiveCampaignCount.as_view(), name="supplier_live_campaign"),
]
