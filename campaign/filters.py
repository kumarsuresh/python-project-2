'''filters.py'''
import datetime
import json
import rest_framework_filters as filters
from django.db.models import Q
from django.utils import timezone
from example.core.constants import CAMPAIGN_ARCHIVE_DAYS

from .models import (Campaign, CampaignBrand, PhotoEvidence, RetailerCampaign,
                     RetailerCampaignStore, StoreCampaignEvidence)


class CampaignFilter(filters.FilterSet):
    status = filters.NumberFilter(method='filter_status')
    supplier_id = filters.NumberFilter(method='filter_supplier')
    brand = filters.NumberFilter(field_name='campaign_brand__brand_id')
    state = filters.NumberFilter(field_name='is_published')
    media_type = filters.NumberFilter(field_name='campaignmediaasset__media_asset__id')
    start_date = filters.CharFilter(method='filter_start_date')
    to_date = filters.DateTimeFilter(method='filter_to_date')

    class Meta:
        model = Campaign
        fields = [
            'start_date',
            'end_date',
            'status',
            'supplier_id',
            'state'
        ]

    def filter_supplier(self, queryset, name, value):
        '''
        from turnover filter 
        '''
        _ = self
        return queryset.filter(supplier_id=value)

    def filter_start_date(self, queryset, name, value):
        '''
        from turnover filter  date__range=["2011-01-01", "2011-01-31"]
        '''
        _ = self
        dates = value.split(',')
        if dates[0] is '' and dates[1] is '':
            return queryset
        elif dates[0] is '':
            return queryset.filter(end_date__lte=dates[1])
        elif dates[1] is '':
            return queryset.filter(start_date__gte=dates[0])
        else:
            return queryset.filter(Q(start_date__range=dates) | Q(end_date__range=dates))
    
    def filter_to_date(self, queryset, name, value):
        '''
        to turnover filter 
        '''
        _ = self
        return queryset.filter(end_date__lte=value)

    def filter_status(self, queryset, name, value):
        '''
        to turnover filter 
        '''
        _ = self
        if value == 1:
            return queryset.filter(end_date__lte=timezone.now())
        return queryset.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now())

class TaskFilter(filters.FilterSet):
    store = filters.CharFilter(method='filter_store')
    campaign = filters.CharFilter(method='filter_campaign')
    task_status = filters.CharFilter(method='filter_task_status')

    class Meta:
        model = StoreCampaignEvidence
        fields = [
            'store',
            'campaign',
            'task_status',
        ]

    def filter_store(self, queryset, name, value):
        '''
        from store filter 
        '''
        _ = self
        value = [int(x) for x in value.split(",")]
        return queryset.filter(store_id__in=value)

    def filter_campaign(self, queryset, name, value):
        '''
        from campaign filter 
        '''
        _ = self
        value = [int(x) for x in value.split(",")]
        return queryset.filter(campaign_id__in=value)
        
    def filter_task_status(self, queryset, name, value):
        '''
        from campaign filter 
        '''
        _ = self
        return queryset.filter(task_status=value)


class OptedCampaignsFilter(filters.FilterSet):
    query = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = RetailerCampaign
        fields = [
            'query'
        ]

    def filter_search(self, queryset, name, value):
        '''
        campaign name filter 
        '''
        _ = self
        return queryset.filter(campaign__name__icontains=value)


class OptedStoresFilter(filters.FilterSet):
    query = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = RetailerCampaignStore
        fields = [
            'query'
        ]

    def filter_search(self, queryset, name, value):
        '''
        campaign name filter 
        '''
        _ = self
        return queryset.filter(store_name__icontains=value)

class CampaignTasksFilter(filters.FilterSet):
    retailer = filters.NumberFilter(field_name="retailer_id")
    store = filters.NumberFilter(field_name="store_id")
    media_asset = filters.NumberFilter(field_name="evidence__campaign_media_asset")
    campaign_evidence = filters.NumberFilter(field_name="evidence")

    class Meta:
        model = StoreCampaignEvidence
        fields = [
            'retailer',
            'store',
            'media_asset',
            'campaign_evidence',          
        ]


class PhotoEvidenceFilter(filters.FilterSet):
    retailer = filters.NumberFilter(field_name="store_campaign_evidence__retailer_id")
    store = filters.NumberFilter(field_name="store_campaign_evidence__store_id")
    media_asset = filters.NumberFilter(field_name="store_campaign_evidence__evidence__campaign_media_asset")
    campaign_evidence = filters.NumberFilter(field_name="store_campaign_evidence__evidence")
    evidence_date = filters.CharFilter(method='filter_by_week')
    status = filters.NumberFilter(field_name="evidence_status")
    current_proof_date = filters.DateFilter(method='filter_current_date')

    class Meta:
        model = PhotoEvidence
        fields = [
            'retailer',
            'store',
            'status',
            'media_asset',
            'campaign_evidence',
            'evidence_date',
            'current_proof_date'
            
        ]

    def filter_by_week(self, queryset, name, value):
        '''
        from turnover filter  date__range=["2011-01-01", "2011-01-31"]
        '''
        _ = self
        dates = value.split(',')
        return queryset.filter(Q(created__range=dates))


    def filter_current_date(self, queryset, name, value):
        ''' match all evidence submitted on date '''
        _ = self
        return queryset.filter(created__day=value.day, created__month=value.month, created__year=value.year)

class ApiTaskFilter(filters.FilterSet):
    brand = filters.CharFilter(method='filter_brand')
    is_optin = filters.CharFilter(method='filter_is_optin')
    
    class Meta:
        model = Campaign
        fields = [
            'brand',
            'is_optin',
        ]

    def filter_is_optin(self, queryset, name, value):
        '''
        campaign name filter 
        '''
        _ = self
        if value == '1':
            queryset = queryset.filter(retailercampaign_campaign__is_opt_out=False)
        elif value == '2':
            queryset = queryset.exclude(retailercampaign_campaign__is_opt_out=False)
        return queryset

    def filter_brand(self, queryset, name, value):
        '''
        campaign name filter 
        '''
        _ = self
        return queryset.filter(campaign_brand__brand_id__in=json.loads(value))