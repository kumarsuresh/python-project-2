import json
from datetime import datetime, timedelta
from itertools import chain

import django_filters
from django.conf import settings
from django.core.mail.message import EmailMessage
from django.db.models import Case, Count, FloatField, Q, Sum, Value, When
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import ugettext_lazy as __
from example.core.constants import HTTP_200_SUCCESS, HTTP_API_ERROR
from example.core.utility import CustomPagination
from rest_framework import filters, generics, status
from rest_framework.response import Response

from ..choices import EvidenceStatusCheckType, EvidenceStatusType
from ..constants import LAST_OPT_IN_DATE
from ..filters import OptedCampaignsFilter, OptedStoresFilter, TaskFilter, ApiTaskFilter
from ..messages import *
from ..models import *
from ..serializers_api import *


def get_retailer_campaign(retailer_id, query_params):
    queryset = Campaign.objects.filter(is_active=True, end_date__gt=timezone.now() - timedelta(LAST_OPT_IN_DATE), is_published=True).order_by('-id')
    target_campaigns = TargetRetailer.objects.filter(retailer_id=retailer_id)
    if 'store_ids' in query_params.keys():            
        target_retailer_ids = target_campaigns.values_list('id', flat=True)
        staff_campaign = TargetStores.objects.filter(target_retailer__in=target_retailer_ids, 
                                                        store_id__in=json.loads(query_params['store_ids'])
                                                        ).values_list('target_retailer__campaign', flat=True)
        target_campaigns = target_campaigns.filter(campaign_id__in=staff_campaign)
        
    target_campaign_ids = target_campaigns.values_list('campaign', flat=True).distinct()

    optout_campaigns = RetailerCampaign.objects.filter(is_opt_out=False, user_id=retailer_id).values_list('campaign', flat=True)
    queryset = queryset.filter(id__in=target_campaign_ids)

    opted_out_deleted = ''
    
    if optout_campaigns:
        opted_out_deleted = queryset.filter(pk__in=optout_campaigns, is_deleted=True)
    
    queryset = queryset.filter(is_deleted=False)
    
    if opted_out_deleted != '':
        queryset = queryset | opted_out_deleted
    
    return queryset

class CampaignListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = CampaignSerializer
    pagination_class = CustomPagination
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filter_class = ApiTaskFilter
    ordering_fields = ('id', 'reward')
    search_fields = ('name',)

    def get_serializer_context(self):
        context = super(CampaignListing, self).get_serializer_context()
        context.update({'user_id': self.kwargs['user_id']})
        context.update({'isall': self.request.query_params.get('isall', False)})
        return context

    def get_queryset(self):
        return get_retailer_campaign(self.kwargs['user_id'], self.request.query_params)

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)
        queryset = self.get_queryset()
        obj = LastLoggedInTime.objects.filter(user=self.kwargs['user_id']).first()
        if not obj or obj.campaign_date is None:
            last_visited_timestamp = timezone.now()
            LastLoggedInTime.objects.update_or_create(user=self.kwargs['user_id'], defaults={"campaign_date": timezone.now()})
            response.data['badge_count'] = queryset.filter(created__gt=last_visited_timestamp).count()
        else:
            response.data['badge_count'] = queryset.filter(created__gt=obj.campaign_date).count()
            LastLoggedInTime.objects.update_or_create(user=self.kwargs['user_id'], defaults={"campaign_date": timezone.now()})

        return Response(response.data)


class CampaignGlobalSearch(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = CampaignMiniSerializer
    pagination_class = CustomPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)

    def get_queryset(self):
        return get_retailer_campaign(self.kwargs['user_id'], self.request.query_params)



class CampaignsBrands(generics.RetrieveAPIView):
    '''
    API for campaign listing
    '''
    def get_queryset(self):
        return get_retailer_campaign(self.kwargs['user_id'], self.request.query_params)

    def get(self, request, *args, **kwargs):
        campaign_list = self.get_queryset()
        campaign_ids = [campaign.id for campaign in campaign_list]
        brand_ids = CampaignBrand.objects.filter(campaign_id__in=campaign_ids).distinct('brand_id').values_list('brand_id')
        brand_ids = [brand[0] for brand in brand_ids]
        return Response({'brand_ids': brand_ids})


class CampaignDetail(generics.RetrieveUpdateAPIView):
    serializer_class = CampaignDetailSerializer

    def get_object(self):
        return Campaign.objects.get(pk=self.kwargs['campaign_id'])

    def get_serializer_context(self):
        context = super(CampaignDetail, self).get_serializer_context()
        context.update({'campaign_id': self.kwargs['campaign_id']})
        context.update({'user_id': self.kwargs['user_id']})
        return context

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        response = super(CampaignDetail, self).update(
            request, *args, **kwargs)
        return Response({MESSAGE: REQUEST_SUCCESSFULL})

    def retrieve(self, *args, **kwargs):
        '''Retrieve'''
        try:
            return super(CampaignDetail, self).retrieve(*args, **kwargs)
        except Campaign.DoesNotExist:
            return Response({MESSAGE: CAMPAIGN_NOT_FOUND}, status=HTTP_API_ERROR)

class CampaignOptIn(generics.UpdateAPIView):
    serializer_class = CampaignOptInSerializer

    def get_object(self):
        return Campaign.objects.get(pk=self.kwargs['campaign_id'])

    def get_serializer_context(self):
        context = super(CampaignOptIn, self).get_serializer_context()
        context.update({'campaign_id': self.kwargs['campaign_id']})
        context.update({'user_id': self.kwargs['user_id']})
        return context

class CampaignOptOut(generics.UpdateAPIView):
    serializer_class = CampaignOptOutSerializer

    def get_object(self):
        return Campaign.objects.get(pk=self.kwargs['campaign_id'])

    def get_serializer_context(self):
        context = super(CampaignOptOut, self).get_serializer_context()
        context.update({'campaign_id': self.kwargs['campaign_id']})
        context.update({'user_id': self.kwargs['user_id']})
        return context

class OptedCampaignsListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = OptedCampaignsSerializer
    pagination_class = CustomPagination
    filter_class = OptedCampaignsFilter

    def get_queryset(self):
        try:
            campaign_ids = StoreCampaignEvidence.objects.filter(is_active=True, 
                retailer_id=self.kwargs['user_id'],
                is_submitted=False,
                evidence__start_date__lte=timezone.now(),
                evidence__end_date__gte=timezone.now(),
            ).distinct('campaign_id').values_list('campaign_id', flat=True)
            return RetailerCampaign.objects.filter(user_id=self.kwargs['user_id'], campaign_id__in=campaign_ids, is_opt_out=False)
        except RetailerCampaign.DoesNotExist:
            return {}

class SelectedStoresListing(generics.ListAPIView):
    '''
    API for campaign stores listing
    '''
    
    serializer_class = SelectedStoresSerializer

    def get_queryset(self):
        response = {}
        try:
            obj = RetailerCampaign.objects.filter(campaign_id=self.kwargs['campaign_id'], user_id=self.kwargs['user_id'])
            if obj:
                response = RetailerCampaignStore.objects.filter(retailer_campaign=obj)
        except RetailerCampaign.DoesNotExist:
            pass
        return response

class TargetStoresListing(generics.ListAPIView):
    '''
    API for campaign targeted stores listing
    '''
    
    serializer_class = TargetStoresSerializer

    def get_serializer_context(self):
        return {'campaign_id': self.kwargs['campaign_id'], 'retailer_id':self.kwargs['user_id']}

    def get_queryset(self):
        response = {}
        try:
            response = TargetStores.objects.filter(target_retailer__campaign_id=self.kwargs['campaign_id'], target_retailer__retailer_id=self.kwargs['user_id'])
        except RetailerCampaign.DoesNotExist:
            pass
        return response

class OptedStoresListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = OptedStoresSerializer
    pagination_class = CustomPagination
    filter_class = OptedStoresFilter
    def get_queryset(self):
        try:
            return RetailerCampaignStore.objects.filter(retailer_campaign__user_id=self.kwargs['user_id'], retailer_campaign__is_opt_out=False).distinct('store_id')
        except RetailerCampaign.DoesNotExist:
            return {}

class TasksListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = TasksSerializer
    filter_class = TaskFilter
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter)
    pagination_class = CustomPagination
    search_fields = ('campaign__name',)

    def get_serializer_context(self):
        context = super(TasksListing, self).get_serializer_context()
        context.update({'user_id': self.kwargs['user_id']})
        return context

    def get_queryset(self):
        queryset = StoreCampaignEvidence.objects.filter(is_active=True, 
            retailer_id=self.kwargs['user_id'], 
            is_submitted=False, 
            evidence__start_date__lte=timezone.now(),
            evidence__end_date__gte=timezone.now(),
        ).order_by('evidence__end_date')
        
        sort = self.request.query_params.get('sort', 'date')
        if sort == 'date':
            queryset = queryset.order_by('evidence__end_date')
        elif sort == 'campaign_name':
            queryset = queryset.order_by('campaign__name', 'evidence__end_date')
        elif sort == 'store_name':
            queryset = queryset.order_by('store_name', 'evidence__end_date')

        if 'store_ids' in self.request.query_params.keys():      
            queryset = queryset.filter(store_id__in=json.loads(self.request.query_params['store_ids']))
        return queryset

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)
        obj = LastLoggedInTime.objects.filter(user=self.kwargs['user_id']).first()
        if not obj or obj.task_date is None:
            last_visited_timestamp = timezone.now()
            LastLoggedInTime.objects.update_or_create(user=self.kwargs['user_id'], defaults={"task_date": timezone.now()})
            response.data['badge_count'] = self.get_queryset().filter(evidence__created__gt=last_visited_timestamp).count()
        else:
            response.data['badge_count'] = self.get_queryset().filter(evidence__created__gt=obj.task_date).count()
            LastLoggedInTime.objects.update_or_create(user=self.kwargs['user_id'], defaults={"task_date": timezone.now()})
        return Response(response.data)

class CampMediaProdListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = CampMediaProdSerializer
    def get_queryset(self):
        try:
            return CampaignMediaAssetProduct.objects.filter(campaign_media_asset_id=self.kwargs['media_asset_id'])
        except CampaignMediaAssetProduct.DoesNotExist:
            return {}

class FilterDetails(generics.RetrieveAPIView):
    '''
    API for campaign listing
    '''
    def get_queryset(self):
        queryset = StoreCampaignEvidence.objects.filter(is_active=True, 
            retailer_id=self.kwargs['user_id'], 
            evidence__start_date__lte=timezone.now(),
            evidence__end_date__gte=timezone.now(),
            # evidence__start_date__year__lte=timezone.now().year,
            # evidence__start_date__month__lte=timezone.now().month,
            # evidence__start_date__day__lte=timezone.now().day,
            # evidence__end_date__year__gte=timezone.now().year,
            # evidence__end_date__month__gte=timezone.now().month,
            # evidence__end_date__day__gte=timezone.now().day
        ).order_by('evidence__end_date')
        return queryset

    def get(self, request, *args, **kwargs):
        filter_data = []
        query_set = self.get_queryset()
        if 'store_ids' in self.request.query_params.keys():      
            query_set = query_set.filter(store_id__in=json.loads(self.request.query_params['store_ids']))
        for data in EvidenceStatusType.choices:
            filter_data.append({"key": data.__getitem__(0), "name": data.__getitem__(1), "count": query_set.filter(task_status=data.__getitem__(0)).count()})
        results = FilterStatusSerializer(filter_data, many=True).data
        return Response(results)

class SubmitPhotoEvidence(generics.CreateAPIView):
    '''API to submit Photo evidence'''

    serializer_class = SubmitEvidenceSerializer

    def get_serializer_context(self):
        context = super(SubmitPhotoEvidence, self).get_serializer_context()
        context.update({'user_id': self.kwargs['user_id']})
        context.update({'task_status': self.request.data['task_status']})
        return context

class ValidateQRCode(generics.RetrieveAPIView):
    '''API to validate QR code'''
    serializer_class = ValidateQRSerializer

    def get_object(self):
        obj = CampaignMediaAsset.objects.get(id=self.kwargs['campaign_media_id'])
        return obj

    def get(self, request, *args, **kwargs):
        try:
            obj = self.get_object()
        except CampaignMediaAsset.DoesNotExist:
            return Response({MESSAGE: MEDIA_ASSEST_NOT_FOUND}, status=HTTP_API_ERROR)
        if obj.campaign.id == int(self.kwargs['campaign_id']) and obj.media_asset.id == int(self.kwargs['media_id']):
            return Response({MESSAGE: SUCCESS}, status=HTTP_200_SUCCESS)
        return Response({MESSAGE: MEDIA_ASSEST_NOT_FOUND}, status=HTTP_API_ERROR)

class SubmittedEvidenceListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = SubmittedEvidenceSerializer
    def get_queryset(self):
        try:
            return PhotoEvidence.objects.filter(store_campaign_evidence_id=self.kwargs['evidence_id']).order_by('-created')
        except PhotoEvidence.DoesNotExist:
            return {}

class WriteToexample(generics.UpdateAPIView):
    serializer_class = WriteToexampleSerializer

    def get_object(self):
        return StoreCampaignEvidence.objects.get(pk=self.kwargs['evidence_id'])

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        response = super(WriteToexample, self).update(
            request, *args, **kwargs)
        return Response({MESSAGE: REQUEST_SUCCESSFULL})

class EvidenceDetail(generics.RetrieveAPIView):
    serializer_class = EvidenceDetailSerializer

    def get_object(self):
        return PhotoEvidence.objects.get(pk=self.kwargs['evidence_id'])

    def get_serializer_context(self):
        context = super(EvidenceDetail, self).get_serializer_context()
        context.update({'evidence_id': self.kwargs['evidence_id']})
        context.update({'user_id': self.kwargs['user_id']})
        return context

    def retrieve(self, *args, **kwargs):
        '''Retrieve'''
        try:
            return super(EvidenceDetail, self).retrieve(*args, **kwargs)
        except PhotoEvidence.DoesNotExist:
            return Response({MESSAGE: EVIDENCE_NOT_FOUND}, status=HTTP_API_ERROR)

class TaskDetail(generics.RetrieveAPIView):
    serializer_class = TaskDetailSerializer

    def get_object(self):
        return StoreCampaignEvidence.objects.get(pk=self.kwargs['task_id'])

    def get_serializer_context(self):
        context = super(TaskDetail, self).get_serializer_context()
        context.update({'task_id': self.kwargs['task_id']})
        context.update({'user_id': self.kwargs['user_id']})
        return context

    def retrieve(self, *args, **kwargs):
        '''Retrieve'''
        try:
            return super(TaskDetail, self).retrieve(*args, **kwargs)
        except StoreCampaignEvidence.DoesNotExist:
            return Response({MESSAGE: TASK_NOT_FOUND}, status=HTTP_API_ERROR)

class RetailerReward(generics.RetrieveAPIView):
    '''
    API for campaign Statistics
    total_reward - Sum of the rewards for each of the campaigns for all Targeted stores, so can be maximum possible rewards.
    '''
    def get(self, request, *args, **kwargs):
        _ = self   
        reward_distributed = StoreCampaignEvidence.objects.filter(retailer_id=self.kwargs['retailer_id']).aggregate(
            total=Sum(Case(When(task_status=EvidenceStatusCheckType.ACCEPTED, then='evidence__reward'), 
                default=Value(0),
                output_field=FloatField())))
        reward_obj = {"reward_distributed": reward_distributed['total'] or 0}
        return Response(reward_obj)
