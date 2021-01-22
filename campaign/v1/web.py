import json
import uuid
from datetime import datetime, timedelta
from example.core.utility import intializekafka
import django_filters
from django.conf import settings
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When, F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from example.core.constants import HTTP_200_SUCCESS, HTTP_API_ERROR
from example.core.utility import CustomPagination, upload_image
from rest_framework import filters, generics, status
from rest_framework.response import Response

from ..choices import EvidenceStatusCheckType, EvidenceStatusType
from ..constants import LAST_OPT_IN_DATE
from ..filters import CampaignFilter, CampaignTasksFilter, PhotoEvidenceFilter
from ..messages import *
from ..models import *
from ..serializers_web import *


class CampaignListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = CampaignSerializer
    pagination_class = CustomPagination
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.OrderingFilter)
    filter_class = CampaignFilter

    def get_queryset(self):
        _ = self
        query_vars = Q(is_active=True, is_deleted=False)
        queryset = Campaign.objects.filter(query_vars).distinct().order_by('-id')
        return queryset


class CampaignDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CampaignDetailSerializer
    queryset = Campaign.objects.all()

    def get_object(self):
        return Campaign.objects.get(pk=self.kwargs['id'], is_active=True, is_deleted=False)

    def retrieve(self, *args, **kwargs):
        '''Retrieve'''
        try:
            return super(CampaignDetail, self).retrieve(*args, **kwargs)
        except (Http404, Campaign.DoesNotExist):
            return Response({MESSAGE: CAMPAIGN_NOT_FOUND}, status=HTTP_API_ERROR)

    def patch(self, request, *args, **kwargs):
        '''Partialy update object'''
        response_data = {}
        instance = self.get_object()
        
        serializer = UpdateCampaignSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            campaign = serializer.save()
            response = serializer.data
            if settings.ENABLE_KAFKA:
                intializekafka('update_campaign', response)
            response_data[SUCCESS] = REQUEST_SUCCESSFULL
            return Response(response_data, status=HTTP_200_SUCCESS)
        else:
            response_data[MESSAGE] = serializer.errors
            return Response(response_data, status=HTTP_API_ERROR)


class UpdateCampaign(generics.UpdateAPIView):
    serializer_class = UpdateCampaignSerializer

    def get_object(self):
        return Campaign.objects.get(pk=self.kwargs['id'], is_active=True, is_deleted=False)

    def patch(self, request, *args, **kwargs):
        try:
            campaign = self.get_object()
        except Campaign.DoesNotExist:
            return Response({"message": CAMPAIGN_NOT_FOUND}, status=HTTP_API_ERROR)
        response_data = {}

        image_icon_obj = self.request.data.get('image_icon', '')
        if image_icon_obj:
            image_name = '%s/%s.jpeg' % (settings.AWS_STORE_CAMPAIGN_PATH, uuid.uuid4())
            self.request.data['image_icon'] = image_name
            upload_image(image_icon_obj, image_name)

        image_obj = self.request.data.get('image', '')
        if image_obj:
            image_name = '%s/%s.jpeg' % (settings.AWS_STORE_CAMPAIGN_PATH, uuid.uuid4())
            self.request.data['image'] = image_name
            upload_image(image_obj, image_name)

        serializer = UpdateCampaignSerializer(campaign, data=request.data, partial=True)
        if serializer.is_valid():
            campaign = serializer.save()
            response = serializer.data
            if settings.ENABLE_KAFKA:
                intializekafka('update_campaign', response)
            response_data[SUCCESS] = REQUEST_SUCCESSFULL
            return Response(response_data, status=HTTP_200_SUCCESS)
        else:
            response_data[MESSAGE] = serializer.errors
            return Response(response_data, status=HTTP_API_ERROR)


class CreateCampaign(generics.CreateAPIView):
    '''API to add campaign'''
    serializer_class = CreateCampaignSerializer


class PublishCampaignView(generics.CreateAPIView):
    '''API to pusblish camapaign'''
    serializer_class = PublishCampaignSerializer


class MediaAssetsListing(generics.ListAPIView):
    '''
    API for Media Assets Listing
    '''
    serializer_class = MediaAssetsSerializer
    pagination_class = CustomPagination
    queryset = MediaAsset.objects.filter(is_active=True).order_by('name')


class MediaAssetRemove(generics.DestroyAPIView):
    """
    API to  View  User's own Store.
    """
    serializer_class = CampaignMediaAssetSerializer
    queryset = CampaignMediaAsset.objects.all()

    def get_object(self):
        return CampaignMediaAsset.objects.get(id=self.kwargs['pk'])

    def delete(self, *args, **kwargs):
        retailer_ids = RetailerCampaignMediaAsset.objects.filter(campaign_media_asset_id=self.kwargs['pk']).values_list('retailer_campaign', flat=True)
        for retailer_id in retailer_ids:
            opted_media_count = RetailerCampaignMediaAsset.objects.filter(Q(retailer_campaign_id=retailer_id), ~Q(campaign_media_asset_id=self.kwargs['pk'])).count()
            if opted_media_count < 1:
                RetailerCampaign.objects.filter(pk=retailer_id).update(is_opt_out=True)
                RetailerCampaignStore.objects.filter(retailer_campaign=retailer_id).delete()
                
        try:
            return super(MediaAssetRemove,self).delete(*args, **kwargs)
        except CampaignMediaAsset.DoesNotExist:
            return Response({"message": MEDIA_ASSEST_NOT_FOUND}, status=HTTP_API_ERROR)


class MediaAssetProductRemove(generics.DestroyAPIView):
    """
    API to  View  User's own Store.
    """
    serializer_class = CampaignMediaAssetProductSerializer

    def get_object(self):
        return CampaignMediaAssetProduct.objects.get(id=self.kwargs['pk'])

    def delete(self, *args, **kwargs):
        try:
            return super(MediaAssetProductRemove,self).delete(*args, **kwargs)
        except CampaignMediaAssetProduct.DoesNotExist:
            return Response({"message": MEDIA_ASSEST_PRODUCT_NOT_FOUND}, status=HTTP_API_ERROR)


class EvidenceRemove(generics.DestroyAPIView):
    """
    API to  View  User's own Store.
    """
    serializer_class = CampaignMediaAssetEvidenceSerializer

    def get_object(self):
        return CampaignEvidence.objects.get(id=self.kwargs['pk'])
    
    def delete(self, *args, **kwargs):
        try:
            instance = self.get_object()
            StoreCampaignEvidence.objects.filter(evidence=instance).delete()
            return super(EvidenceRemove, self).delete(*args, **kwargs)
        except CampaignEvidence.DoesNotExist:
            return Response({"message": EVIDENCE_NOT_FOUND}, status=HTTP_API_ERROR)


class TargetRetailersView(generics.CreateAPIView):
    '''API to targeted retailers'''
    serializer_class = TargetRetailerSerializer

    def post(self, request, *args, **kwargs):
        _ = self
        response_data = {}
        
        serializer = TargetRetailerSerializer(data=request.data.pop('target_retailers'), many=True,
                                              context={'store_filters': request.data.pop('store_filters')})
        if serializer.is_valid():
            campaign = serializer.save()
            response = serializer.data
            if settings.ENABLE_KAFKA:
                intializekafka('target_retailer', response)
            response_data[SUCCESS] = CREATED_SUCCESSFULL
            status_code = HTTP_200_SUCCESS
        else:
            response_data[MESSAGE] = serializer.errors
            status_code = HTTP_API_ERROR
        return Response(response_data, status=status_code)


class CampaignRetailersView(generics.ListAPIView):
    '''
    get target retailers of campaign
    '''
    serializer_class = CampaignRetailersSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return TargetRetailer.objects.filter(campaign=self.kwargs['campaign_id']).order_by('-id')


class CampaignStoresView(generics.ListAPIView):
    '''
    get target Stores of campaign
    '''
    serializer_class = CampaignStoresSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = TargetStores.objects.filter(target_retailer__campaign=self.kwargs['campaign_id']).order_by('-id')
        return queryset


class CampaignRetailerStoresView(generics.ListAPIView):
    '''
    get target Stores of campaign
    '''
    serializer_class = CampaignStoresSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return TargetStores.objects.filter(target_retailer__campaign=self.kwargs['campaign_id'],
                                           target_retailer__retailer_business=self.kwargs['retailer_business_id']).order_by('-id')


class CampaignRetailerStoresCountView(generics.ListAPIView):
    '''
    get target Stores of campaign
    '''
    serializer_class = CampaignRetailerStoresCountSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        business_ids = self.request.query_params['business_ids']
        business_ids = [int(x) for x in business_ids.split(",")]
        queryset = TargetRetailer.objects.filter(campaign=self.kwargs['campaign_id'],
                                               retailer_business__in=business_ids).annotate(matched_stores=Count('targetstores'))
        return queryset


class RemoveCampaignStore(generics.DestroyAPIView):
    """
    API to  remove campaign stores
    """
    serializer_class = CampaignStoresSerializer

    def get_object(self):
        target_ids = self.request.GET.get('target_ids')
        target_ids = target_ids.split(',')
        return TargetStores.objects.filter(id__in=target_ids)
    
    def destroy(self, request, *args, **kwargs):
        instances = self.get_object()
        message = ''
        try:
            for instance in instances:
                # check store is not opted in, if it is then should not be deleted
                opted_stores = RetailerCampaignStore.objects.filter(store_id=instance.store_id, 
                                                                    retailer_campaign__campaign=instance.target_retailer.campaign
                                                                    ).values_list('store_id', flat=True)
                
                if instance.store_id not in opted_stores:
                    StoreCampaignEvidence.objects.filter(store_id=instance.store_id, 
                                                        campaign=instance.target_retailer.campaign).exclude(
                                                        store_id__in=opted_stores).delete()
                    self.perform_destroy(instance)
            status_code = HTTP_200_SUCCESS
        except:
            message = "Stores does not exist"
            status_code = HTTP_API_ERROR
        return Response({"message":message}, status=status_code)


class RemoveCampaignRetailers(generics.DestroyAPIView):
    """
    API to  remove campaign retailers and stores
    """
    serializer_class = CampaignRetailersSerializer

    def get_object(self):
        target_ids = self.request.GET.get('target_ids')
        target_ids = target_ids.split(',')
        return TargetRetailer.objects.filter(id__in=target_ids, campaign=self.kwargs['campaign_id'])

    def destroy(self, request, *args, **kwargs):
        instances = self.get_object()
        message = ''
        try:
            for instance in instances:
                #remove retailer target stores 
                TargetStores.objects.filter(target_retailer=instance.id).delete()
                #remove retailer target stores evidence if any
                StoreCampaignEvidence.objects.filter(retailer_id=instance.retailer_id, campaign=instance.campaign).delete()
                self.perform_destroy(instance)
            status_code = HTTP_200_SUCCESS
        except:
            message = "Retailer does not exist"
            status_code = HTTP_API_ERROR
        return Response({"message":message}, status=status_code)


class CampaignProductsView(generics.ListAPIView):
    '''
    get target Stores of campaign
    '''
    serializer_class = CampaignMediaAssetsProductSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = CampaignMediaAssetProduct.objects.filter(campaign_media_asset=self.kwargs['media_asset_id']).order_by('-id')
        return queryset


class CampaignMediaAssetListView(generics.ListAPIView):
    '''
    Media Asset List View
    '''
    serializer_class = MediaAssetListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return CampaignMediaAsset.objects.annotate(num_campaign_media=Count('campaign_media')).filter(campaign=self.kwargs['campaign_id'], num_campaign_media__gt=0).order_by('id')


class MediaAssetForEvidenceListView(generics.ListAPIView):
    '''
    Media Asset For Evidence List View
    '''
    serializer_class = EvidenceMediaAssetListSerializer

    def get_queryset(self):
        return CampaignMediaAsset.objects.filter(campaign=self.kwargs['campaign_id'], is_active=True).order_by('id')


class MediaAssetEvidenceListView(generics.ListAPIView):
    '''
    Media Asset For Evidence List View
    '''
    serializer_class = CampaignMediaAssetEvidenceSerializer

    def get_queryset(self):
        return CampaignEvidence.objects.filter(campaign_media_asset=self.kwargs['campaign_media_asset_id'],
                                               start_date__lte=timezone.now(), is_active=True).order_by('id')

class CampaignOptedStoresView(generics.ListAPIView):
    serializer_class = CampaignOptedStores
    
    def get_queryset(self):
        return RetailerCampaignStore.objects.filter(retailer_campaign__campaign=self.kwargs['campaign_id'])


class CampaignRetailerListView(generics.ListAPIView):
    serializer_class = RetailerCampaignSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('user_name',)
    
    def get_queryset(self):
        return RetailerCampaign.objects.filter(campaign=self.kwargs['campaign_id'], is_opt_out=False, is_active=True)


class RetailerCampaignStoreListView(generics.ListAPIView):
    serializer_class = RetailerCampaignStoreSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('store_name',)
    def get_queryset(self):
        return RetailerCampaignStore.objects.filter(retailer_campaign=self.kwargs['retailer_campaign_id'], is_active=True)


class CampaignEvidencePhotoListView(generics.ListAPIView):
    queryset = PhotoEvidence.objects.all()
    serializer_class = EvidencePhotoListSerializer
    pagination_class = CustomPagination
    filter_class = PhotoEvidenceFilter
    ordering = ('-created',)

    def get_queryset(self):
        queryset = self.queryset.filter(store_campaign_evidence__campaign=self.kwargs['campaign_id'])
        return queryset


class CampaignPhotoEvidenceUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = EvidencePhotoRetrieveUpdateSerializer
    queryset = PhotoEvidence.objects.all()

    def get_serializer_context(self):
        context = super(CampaignPhotoEvidenceUpdateView, self).get_serializer_context()
        query_params = self.request.query_params
        context.update({'query_params':query_params, 'campaign_id': self.kwargs['campaign_id']})
        return context

    def get_object(self):
        photo_evidence_id = self.kwargs["photo_evidence_id"]
        return get_object_or_404(PhotoEvidence, id=photo_evidence_id)

    def retrieve(self, *args, **kwargs):
        '''Retrieve'''
        try:
            return super(CampaignPhotoEvidenceUpdateView, self).retrieve(*args, **kwargs)
        except (Http404, Campaign.DoesNotExist):
            return Response({MESSAGE: PHOTO_EVIDENCE_NOT_FOUND}, status=HTTP_API_ERROR)      
    
    def patch(self, request, *args, **kwargs):
        '''Partial update object'''
        response_data = {}
        instance = self.get_object()
        
        serializer = EvidencePhotoRetrieveUpdateSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            photo_evidence = serializer.save()
            response = serializer.data
            response_data[SUCCESS] = REQUEST_SUCCESSFULL
            return Response(response_data, status=HTTP_200_SUCCESS)
        else:
            response_data[MESSAGE] = serializer.errors
            return Response(response_data, status=HTTP_API_ERROR)


class CampaignStats(generics.RetrieveAPIView):
    '''
    API for campaign Statistics
    total_reward - Sum of the rewards for each of the campaigns for all Targeted stores, so can be maximum possible rewards.
    reward_distributed - Sum of Reward value for accepted (chosen) evidences for all campaigns.
    Overall Reward Percentage - Sum of Reward value for accepted (chosen) evidences for all campaigns/Total reward value * 100
    activation_percentage - (Total opted stores for all campaigns * total number of evidences per store) /total accepted evidences
    '''
    def get(self, request, *args, **kwargs):
        _ = self

        total_reward = TargetStores.objects.filter(target_retailer__campaign__is_active=True, target_retailer__campaign__is_deleted=False).aggregate(
            total_reward=Sum('target_retailer__campaign__reward'))

        reward_distributed = StoreCampaignEvidence.objects.filter(campaign__is_active=True, campaign__is_deleted=False).aggregate(
            total=Sum(Case(When(task_status=EvidenceStatusCheckType.ACCEPTED, then='campaign__reward'), 
                default=Value(0),
                output_field=IntegerField())),
            total_evidence=Count('id'),
            total_accepted_evidence=Sum(
                Case(When(task_status=EvidenceStatusCheckType.ACCEPTED, then=1),
                default=Value(0),
                output_field=IntegerField())),
            accepted_evidence_reward=Sum(
                Case(When(task_status=EvidenceStatusCheckType.ACCEPTED, then='campaign__reward'),
                default=Value(0),
                output_field=IntegerField())),
            )
        
        total_opted_stores = RetailerCampaignStore.objects.filter(retailer_campaign__campaign__is_active=True, retailer_campaign__campaign__is_deleted=False).count()
        total_accepted_evidence = StoreCampaignEvidence.objects.filter(campaign__is_active=True, campaign__is_deleted=False, task_status=EvidenceStatusCheckType.ACCEPTED).count()
        
        try:
            activation_percentage = round((reward_distributed['total_accepted_evidence']*100)/reward_distributed['total_evidence'], 2) #total_opted_stores*
        except (ZeroDivisionError, TypeError):
            activation_percentage = 0
        
        try:
            #reward value
            reward_activation=(reward_distributed['accepted_evidence_reward']/total_reward['total_reward'])*100 # Total reward value of target stores
        except (ZeroDivisionError, TypeError):
            reward_activation = 0
        
        stats_obj = Campaign.objects.filter(is_active=True, is_deleted=False).aggregate(
            total_campaign=Count('id'),
            active_campaign=Sum(
                Case(When(end_date__gt=timezone.now(), start_date__lte=timezone.now(), then=1),
                default=Value(0),
                output_field=IntegerField())),
            completed_campaign=Sum(
                Case(When(end_date__lt=timezone.now(), then=1),
                default=Value(0),
                output_field=IntegerField())),
            pending_campaign=Sum(
                Case(When(is_published=False, then=1),
                default=Value(0),
                output_field=IntegerField())),
            expired_campaign=Sum(
                Case(When(end_date__lt=timezone.now() - timedelta(LAST_OPT_IN_DATE), then=1),
                default=Value(0),
                output_field=IntegerField()))
            )
        stats_obj = {"total_campaign": stats_obj['total_campaign'], "active_campaign": stats_obj['active_campaign'], 'pending_campaign': stats_obj['pending_campaign'],
                      "completed_campaign": stats_obj['completed_campaign'], 'expired_campaign': stats_obj['expired_campaign'],
                      "total_reward": total_reward['total_reward'] or 0, "reward_distributed": reward_distributed['total'] or 0,
                      "activation_percentage": activation_percentage, "reward_activation": reward_activation}
        return Response(stats_obj)


class EvidenceStatsView(generics.RetrieveAPIView):
    '''
    API for Evidence Statistics
    '''
    def get(self, request, *args, **kwargs):
        
        outstanding_count = StoreCampaignEvidence.objects.filter(campaign=self.kwargs['campaign_id'], task_status=EvidenceStatusCheckType.OUTSTANDING).count()
        stats_obj = PhotoEvidence.objects.filter(store_campaign_evidence__campaign=self.kwargs['campaign_id']).aggregate(
         awaiting_approval=Sum(
             Case(When(evidence_status=EvidenceStatusCheckType.AWAITING_APPROVAL, then=1),
                default=Value(0),
                output_field=IntegerField())
         ),
         resubmission=Sum(
             Case(When(evidence_status=EvidenceStatusCheckType.RE_SUBMISSION, then=1),
                default=Value(0),
                output_field=IntegerField())
         ),
         accepted=Sum(
             Case(When(evidence_status=EvidenceStatusCheckType.ACCEPTED, then=1),
                default=Value(0),
                output_field=IntegerField())
        ),
         rejected=Sum(
             Case(When(evidence_status=EvidenceStatusCheckType.REJECTED, then=1),
                default=Value(0),
                output_field=IntegerField())
        )
        )

        last_access = EvidenceLastAccess.objects.filter(campaign=self.kwargs['campaign_id'], user_id=self.kwargs['user_id']).order_by('-updated').first()
        
        query_vars = Q(store_campaign_evidence__campaign=self.kwargs['campaign_id'])
        if last_access:
            query_vars = Q(store_campaign_evidence__campaign=self.kwargs['campaign_id'], created__gte=last_access.updated)
        
        badge_count = PhotoEvidence.objects.filter(query_vars).aggregate(
         new_awaiting_approval=Sum(
             Case(When(evidence_status=EvidenceStatusCheckType.AWAITING_APPROVAL, then=1),
                default=Value(0),
                output_field=IntegerField())
         ),
         new_resubmission=Sum(
             Case(When(evidence_status=EvidenceStatusCheckType.RE_SUBMISSION, then=1),
                default=Value(0),
                output_field=IntegerField())
         )
        )
        
        stats_obj = {"outstanding": outstanding_count, "awaiting_approval": stats_obj['awaiting_approval'] or 0, 
                     "resubmission": stats_obj['resubmission'] or 0, "accepted": stats_obj['accepted'] or 0, 
                     "rejected": stats_obj['rejected'] or 0, "new_awaiting_approval": badge_count['new_awaiting_approval'] or 0,
                     "new_resubmission": badge_count['new_resubmission'] or 0}
        
        return Response(stats_obj)


class TargetedRetailerStats(generics.RetrieveAPIView):
    '''
    API for campaign listing
    '''
    def get(self, request, *args, **kwargs):
        retailer_count = TargetRetailer.objects.filter(campaign=self.kwargs['campaign_id'], is_active=True).count()
        stores_count = TargetStores.objects.filter(target_retailer__campaign__id=self.kwargs['campaign_id']).count()
        reward = Campaign.objects.get(id=self.kwargs['campaign_id']).reward
        reward_money = stores_count * reward
        stats_obj = {"retailer_count": retailer_count, "stores_count": stores_count, 'reward_money': reward_money}
        return Response(stats_obj)


class EvidenceLastAccessView(generics.CreateAPIView):
    '''
    API to create or update last access of Evidence
    '''
    serializer_class = EvidenceLastAccessSerializer


class CampaignData(generics.ListAPIView):
    serializer_class = CampaignDataSerializer

    def get(self, request, *args, **kwargs):
            ids = json.loads(self.request.GET.get('supplier_ids'))
            camp_data=[]
            for supplier_id in ids:
                stats = Campaign.objects.filter(is_active=True, is_deleted=False, supplier_id=supplier_id).aggregate(
                    total_campaign=Count('id'),
                    live_campaign=Sum(
                        Case(When(is_published=True, end_date__gt=timezone.now(), start_date__lte=timezone.now(), then=1),
                        default=Value(0),
                        output_field=IntegerField())),
                    completed_campaign=Sum(
                        Case(When(end_date__lt=timezone.now(), then=1),
                        default=Value(0),
                        output_field=IntegerField())))
                stats_obj = {"live_campaign": stats['live_campaign'] or 0, 
                        "completed_campaign": stats['completed_campaign'] or 0, 'supplier_id':supplier_id}
                camp_data.append(stats_obj)
            return Response(camp_data)

class LiveCampaignCount(generics.ListAPIView):
    
    def get(self, request, *args, **kwargs):
        params = {'is_active':True, 'is_deleted':False}
        if 'supplier_id' in self.request.GET.keys():
            params['supplier_id']=self.request.GET.get('supplier_id')
        
        elif 'brand_id' in self.request.GET.keys():
            params['campaign_brand__brand_id'] = self.request.GET.get('brand_id')
        
        elif 'retailer_id' in self.request.GET.keys():
            queryset = RetailerCampaign.objects.filter(user_id=self.request.GET.get('retailer_id'), is_opt_out=False, 
            campaign__is_published=True, campaign__end_date__gt=timezone.now(), campaign__cutoff_optin_date__lte=timezone.now(), 
            campaign__is_active=True, campaign__is_deleted=False).values('campaign__name').annotate(name = F('campaign__name'))

        elif 'store_id' in self.request.GET.keys():
            queryset = RetailerCampaignStore.objects.filter(store_id=self.request.GET.get('store_id'), retailer_campaign__is_opt_out=False, 
            retailer_campaign__campaign__is_published=True, retailer_campaign__campaign__end_date__gt=timezone.now(), 
            retailer_campaign__campaign__cutoff_optin_date__lte=timezone.now(), 
            retailer_campaign__campaign__is_active=True, retailer_campaign__campaign__is_deleted=False).values('retailer_campaign__campaign__name').annotate(name = F('retailer_campaign__campaign__name'))

        elif 'business_id' in self.request.GET.keys():
            queryset = RetailerCampaignStore.objects.filter(store_id__in=json.loads(self.request.GET.get('store_ids')), retailer_campaign__is_opt_out=False, 
            retailer_campaign__campaign__is_published=True, retailer_campaign__campaign__end_date__gt=timezone.now(), 
            retailer_campaign__campaign__cutoff_optin_date__lte=timezone.now(), 
            retailer_campaign__campaign__is_active=True, retailer_campaign__campaign__is_deleted=False).values('retailer_campaign__campaign__name').annotate(name = F('retailer_campaign__campaign__name'))

        if 'supplier_id' in self.request.GET.keys() or 'brand_id' in self.request.GET.keys():
            queryset = Campaign.objects.filter(**params).filter(
                is_published=True, end_date__gt=timezone.now(),
                cutoff_optin_date__lte=timezone.now()).values('name')
          

        data_obj = {"live_campaign": queryset.count() or 0, "results":list(queryset)}
        return Response(data_obj)

class BrandCampaignData(generics.ListAPIView):
    serializer_class = CampaignDataSerializer

    def get(self, request, *args, **kwargs):
        brand_ids = json.loads(self.request.GET.get('brand_ids'))
        data = []
        for brand_id in brand_ids:
            stats = Campaign.objects.filter(is_active=True, is_deleted=False, campaign_brand__brand_id=brand_id).aggregate(
                total_campaign = Count('id'),
                live_campaign = Sum(
                    Case(When(is_published=True, end_date__gt=timezone.now(), start_date__lte=timezone.now(), then=1),
                    default=Value(0),
                    output_field=IntegerField())),
                completed_campaign=Sum(
                    Case(When(end_date__lt=timezone.now(), then=1),
                    default=Value(0),
                    output_field=IntegerField()))
            )
            stats_obj = {"live_campaign": stats['live_campaign'] or 0, 
                        "completed_campaign": stats['completed_campaign'] or 0, 'brand_id':brand_id}
            data.append(stats_obj)
        return Response(data)


class StoresListingData(generics.RetrieveAPIView):
    '''
    Return Retailer Store listing activation and optin percentage
    '''
    def get(self, request, *args, **kwargs):
        _ = self
        store_ids = json.loads(self.request.GET.get('store_ids'))
        data = []
        
        for store_id in store_ids:
            optincampaign = RetailerCampaignStore.objects.filter(is_active=True, store_id=store_id).aggregate(optin_stores=Count('id'))
            targetcampaign = TargetStores.objects.filter(is_active=True, store_id=store_id).aggregate(optin_stores=Count('id'))
            try:
                optin_percentage = optincampaign['optin_stores'] * 100 / targetcampaign['optin_stores']
            except ZeroDivisionError:
                optin_percentage = 0

            accepted_evidence = StoreCampaignEvidence.objects.filter(is_active=True, store_id=store_id, task_status=EvidenceStatusType.ACCEPTED).aggregate(accepted_evidence=Count('id'))
            total_evidence = StoreCampaignEvidence.objects.filter(is_active=True, store_id=store_id).aggregate(total_evidence=Count('id'))
            try:
                activation_percentage = accepted_evidence['accepted_evidence'] * 100 / total_evidence['total_evidence']
            except ZeroDivisionError:
                activation_percentage = 0

            stats_obj = {"optin_percentage": optin_percentage,
                         "activation_percentage": activation_percentage,
                         "optin_stores": optincampaign['optin_stores'],
                         "store_id": store_id,
                        }
            data.append(stats_obj)
        return Response(data)


class RetailerCampaignListing(generics.ListAPIView):
    '''
    API for campaign listing
    '''
    serializer_class = RetailerDetailCampaignSerializer
    pagination_class = CustomPagination
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.OrderingFilter)

    def get_queryset(self):
        '''
        campaign_status == 1 for all
        campaign_status == 2 for active campaigns
        campaign_status == 3 for completed campaigns
        campaign_status == 4 for opted campaigns
        '''
        _ = self
        query_vars = Q(is_active=True, is_deleted=False, retailercampaign_campaign__user_id=self.kwargs['retailer_id'])
        
        if self.request.GET.get('campaign_status', '') == '3':
            query_vars = query_vars & Q(end_date__lt=timezone.now())
        elif self.request.GET.get('campaign_status', '') == '2':
            query_vars = query_vars & Q(is_published=True, end_date__gt=timezone.now(), start_date__lte=timezone.now())
        elif self.request.GET.get('campaign_status', '') == '4':
            campaign_ids = RetailerCampaignStore.objects.filter(is_active=True, 
                                                                retailer_campaign__user_id=self.kwargs['retailer_id'],
                                                                retailer_campaign__is_opt_out=False).values_list('retailer_campaign__campaign')
            query_vars = query_vars & Q(id__in=campaign_ids, start_date__gte=timezone.now())
        return Campaign.objects.filter(query_vars).distinct().order_by('-id')


class RetailerCampaignStats(generics.CreateAPIView):
    '''
    API for campaign Retailer Business campaigns total
    '''
    def post(self, request, *args, **kwargs):
        _ = self
        retailer_ids = self.request.data.get('retailer_ids', '')
        data = []
        for retailer_id in retailer_ids:
            
            campaign_list = RetailerCampaign.objects.filter(user_id=retailer_id, is_opt_out=False).values_list('campaign')
            campaign_ids = [campaign[0] for campaign in campaign_list]

            stats_obj = Campaign.objects.filter(is_active=True, is_deleted=False, id__in=campaign_ids).aggregate(total_campaign=Count('id'),
                active_campaign=Sum(
                    Case(When(end_date__gt=timezone.now(), start_date__lte=timezone.now(), then=1),
                    default=Value(0),
                    output_field=IntegerField())),
                completed_campaign=Sum(
                    Case(When(end_date__lt=timezone.now(), then=1),
                    default=Value(0),
                    output_field=IntegerField()))
                )

            reward_distributed = StoreCampaignEvidence.objects.filter(campaign__is_active=True, campaign__is_deleted=False,
                                                                      campaign__id__in=campaign_ids).aggregate(total_evidence=Count('id'),
                                                                      total_accepted_evidence=Sum(
                                                                          Case(When(task_status=EvidenceStatusCheckType.ACCEPTED, then=1),
                                                                          default=Value(0),
                                                                          output_field=IntegerField())),
                                                                      )
            
            total_target_campaign = TargetRetailer.objects.filter(campaign__is_active=True, 
                                                                  campaign__is_deleted=False, 
                                                                  retailer_id=retailer_id).count()

            opted_campaigns = campaign_list.count()
            
            try:
                activation_percentage = (reward_distributed['total_accepted_evidence']*100)/reward_distributed['total_evidence']
            except (ZeroDivisionError, TypeError):
                activation_percentage = 0

            try:
                opted_percentage = (opted_campaigns*100)/total_target_campaign
            except (ZeroDivisionError, TypeError):
                opted_percentage = 0

            stats_obj = {"total_campaign": stats_obj['total_campaign'] if stats_obj['total_campaign'] else 0,
                         "active_campaign": stats_obj['active_campaign'] if stats_obj['active_campaign'] else 0,
                         "completed_campaign": stats_obj['completed_campaign'] if stats_obj['completed_campaign'] else 0,
                         "opted": total_target_campaign,
                         "opted_stores": opted_campaigns,
                         "opted_percentage": opted_percentage,
                         'retailer_id': retailer_id,
                         "activation_percentage": activation_percentage}
            data.append(stats_obj)
        return Response(data)


class RetailerCampaignDeactivateView(generics.UpdateAPIView):

    def patch(self, request, *args, **kwargs):
        response_data = {}
        
        is_opt_out = True
        if request.data['is_active']:
            is_opt_out = False
        
        stores = self.request.query_params.get('stores', None)

        if stores is not None and stores != '':
            store_ids = [int(x) for x in stores.split(",")]
            RetailerCampaignStore.objects.filter(store_id__in=store_ids).update(is_active=request.data['is_active'])    
        elif stores is None:
            RetailerCampaign.objects.filter(user_id=self.kwargs['retailer_id']).update(is_opt_out=is_opt_out)
            RetailerCampaignStore.objects.filter(retailer_campaign__user_id=self.kwargs['retailer_id']).update(is_active=request.data['is_active'])
        
        response_data[SUCCESS] = REQUEST_SUCCESSFULL
        return Response(response_data, status=HTTP_200_SUCCESS)


class CampaignOptedCountView(generics.CreateAPIView):
    '''
    API for Campaign Opted Count 
    '''
    def post(self, request, *args, **kwargs):
        _ = self
        retailer_ids = self.request.data.get('retailer_ids', '')
        data = []
        for retailer_id in retailer_ids:
            campaign_list = RetailerCampaign.objects.filter(user_id=retailer_id).values_list('campaign')
            campaign_ids = [campaign[0] for campaign in campaign_list]
            opted_count = RetailerCampaignStore.objects.filter(retailer_campaign__campaign__in=campaign_ids).count()
            stats_obj = {"is_opted": opted_count > 0,
                         'retailer_id': retailer_id}
            data.append(stats_obj)
        return Response(data)


class CampaignTaskListView(generics.ListAPIView):
    queryset = StoreCampaignEvidence.objects.all()
    serializer_class = StoreCampaignEvidenceSerializer
    pagination_class = CustomPagination
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.OrderingFilter)
    filter_class = CampaignTasksFilter

    def get_queryset(self):
        return self.queryset.filter(campaign_id=self.kwargs['campaign_id'], task_status=EvidenceStatusType.OUTSTANDING).order_by('-id')


class CampaignTaskView(generics.RetrieveAPIView):
    serializer_class = StoreCampaignEvidenceSerializer

    def get_object(self):
        return StoreCampaignEvidence.objects.get(pk=self.kwargs['pk'], is_active=True)

    def retrieve(self, *args, **kwargs):
        '''Retrieve'''
        try:
            return super(CampaignTaskView, self).retrieve(*args, **kwargs)
        except (Http404, StoreCampaignEvidence.DoesNotExist):
            return Response({MESSAGE: TASK_NOT_FOUND}, status=HTTP_API_ERROR)


class OutstandingEvidenceStatsView(generics.RetrieveAPIView):
    '''
    API for Evidence Statistics
    '''
    def get(self, request, *args, **kwargs):
        
        outstanding_count = StoreCampaignEvidence.objects.filter(campaign=self.kwargs['campaign_id'], task_status=EvidenceStatusCheckType.OUTSTANDING).count()

        store_count = RetailerCampaignStore.objects.filter(retailer_campaign__campaign_id=self.kwargs['campaign_id']).count()
        stats_obj = {"outstanding": outstanding_count, "store_count": store_count}
        return Response(stats_obj)
