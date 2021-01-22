import os
import uuid
from datetime import datetime, timedelta
from example.core.utility import intializekafka

import requests

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core import serializers as s
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.utils import timezone
from example.core.utility import upload_image
from rest_framework import serializers

from .choices import (CampaignStatusType, EvidenceStatusCheckType,
                      EvidenceStatusType)
from .messages import *
from .models import (Campaign, CampaignBrand, CampaignEvidence,
                     CampaignMediaAsset, CampaignMediaAssetProduct,
                     EvidenceLastAccess, MediaAsset, PhotoEvidence,
                     RetailerCampaign, RetailerCampaignMediaAsset,
                     RetailerCampaignStore, StoreCampaignEvidence,
                     TargetRetailer, TargetStores)


class RetailerCampaignStoreSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = RetailerCampaignStore
        fields = "__all__"

class RetailerCampaignSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = RetailerCampaign
        fields = "__all__"

class CampaignMediaAssetEvidenceSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CampaignEvidence
        fields = "__all__"

class CampaignMediaAssetProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampaignMediaAssetProduct
        fields = "__all__"

class MediaAssetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = ('id', 'name', 'image', 'desc')

class CampaignMediaAssetSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = CampaignMediaAsset
        fields = ('id', 'media_url')

    def get_media_url(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.image

class CreateCampaignSerializer(serializers.ModelSerializer):
    '''
    Serializer for create Session
    '''
    class Meta:
        '''
        meta for create Session
        '''
        model = Campaign
        fields = ('id', 'name', 'image', 'image_icon', 'reward', 'start_date', 'end_date', 'cutoff_optin_date',
                  'duration', 'status', 'is_new_product', 'max_stores', 'max_stores_per_retailer', 'campaign_notes', 
                  'supplier_id', 'admin_notes', 'product_notes', 'supplier_purchase_order', 'is_published', 'supplier_name')

    def __init__(self, *args, **kwargs):
        super(CreateCampaignSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']
            image_obj = self.request.data.get('image', '')
            if image_obj:
                image_name = '%s/%s.jpeg' % (settings.AWS_STORE_CAMPAIGN_PATH, uuid.uuid4())
                self.request.data['image'] = image_name
                upload_image(image_obj, image_name)

            image_icon_obj = self.request.data.get('image_icon', '')
            if image_icon_obj:
                image_name = '%s/%s.jpeg' % (settings.AWS_STORE_CAMPAIGN_PATH, uuid.uuid4())
                self.request.data['image_icon'] = image_name
                upload_image(image_icon_obj, image_name)

    def update_sample_image(self, media, obj):
        _ = self
        if media['sample_image']:
            image_name = '%s/%s.jpeg' % (settings.AWS_STORE_CAMPAIGN_PATH, uuid.uuid4())
            upload_image(media['sample_image'], image_name)
            return image_name
        elif media['sample_image']=="":
            return None

    def create(self, validated_data):
        instance = super(CreateCampaignSerializer, self).create(validated_data)
        if settings.ENABLE_KAFKA:
            intializekafka('create_campaign', self.request.data)
        for i in self.request.data['brands']:
            CampaignBrand.objects.create(campaign=instance, brand_id=i)

        for media in self.request.data['media']:
            if media:
                obj = CampaignMediaAsset.objects.create(campaign=instance, media_asset_id=media['media_asset_id'])

                if 'sample_image' in media:
                    img = self.update_sample_image(media, obj)
                    obj.sample_image = img
                    obj.save()
                for product in media['product']:
                    CampaignMediaAssetProduct.objects.create(campaign_media_asset=obj, product_id=product['product_id'], notes=product['notes'])
                for i in media['evidence']:
                    CampaignEvidence.objects.create(campaign_media_asset=obj, campaign=instance, start_date=i.get('start_date', None) ,
                                                    end_date=i.get('end_date', None), reward=i.get('reward', None), name=i['name'])
        return instance


class PublishCampaignSerializer(CreateCampaignSerializer):
    '''
    Serializer for Publish Campaign
    '''
    name = serializers.CharField(required=True, max_length=100)
    reward = serializers.FloatField(required=True)
    start_date = serializers.DateTimeField(required=True)
    end_date = serializers.DateTimeField(required=True,)
    cutoff_optin_date = serializers.DateTimeField(required=True)
    duration = serializers.IntegerField(required=True)
    supplier_id = serializers.IntegerField(required=True)
    campaign_notes = serializers.CharField(required=True, max_length=250)
    product_notes = serializers.CharField(required=True, max_length=200)
    supplier_purchase_order = serializers.CharField(required=True, max_length=20)

    class Meta:
        '''
        meta for Publish
        '''
        model = Campaign
        fields = ('id', 'name', 'image', 'image_icon', 'reward', 'start_date', 'end_date', 'cutoff_optin_date',
                  'duration', 'status', 'is_new_product', 'max_stores', 'max_stores_per_retailer', 'campaign_notes', 
                  'supplier_id', 'admin_notes', 'product_notes', 'supplier_purchase_order', 'is_published', 'supplier_name')


class CampaignMediaAssetProductSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    desc = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    thumb_image = serializers.SerializerMethodField()
    is_selected = serializers.SerializerMethodField()
    media_asset_id = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignMediaAssetProduct
        fields = ('id', 'media_asset_id', 'name', 'desc', 'url', 'products', 'thumb_image', 'is_selected', 'evidence')

    def get_products(self,obj):
        ''' Get Campaign Media Assests products list '''
        _ = self.__class__.__name__
        return CampaignMediaAssetProduct.objects.filter(campaign_media_asset=obj.campaign_media_asset_id).values('id', 'product_id', 'notes').order_by('-id')

    def get_evidence(self, obj):
        _ = self.__class__.__name__
        evidences = CampaignEvidence.objects.filter(campaign_media_asset=obj.campaign_media_asset_id).values('id', 'name', 'start_date', 'end_date', 'reward').order_by('-id')
        return evidences

    def get_id(self,obj):
        _ = self.__class__.__name__
        return obj.campaign_media_asset.id

    def get_name(self,obj):
        ''' Return media assets name'''
        _ = self.__class__.__name__
        return obj.campaign_media_asset.media_asset.name

    def get_desc(self,obj):
        _ = self.__class__.__name__
        return obj.campaign_media_asset.media_asset.desc

    def get_thumb_image(self,obj):
        ''' Return Media assets thumbnail/image '''
        _ = self.__class__.__name__
        return obj.campaign_media_asset.media_asset.image

    def get_url(self,obj):
        _ = self.__class__.__name__
        return obj.campaign_media_asset.media_asset.image

    def get_media_asset_id(self,obj):
        _ = self.__class__.__name__
        return obj.campaign_media_asset.media_asset.id

    def get_is_selected(self,obj):
        _ = self.__class__.__name__
        objs = obj.campaign_media_asset.retailercampaignmediaasset_set.values().filter(campaign_media_asset_id=obj.campaign_media_asset.id)
        if objs:
            return True
        return False


class CampaignSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    media = serializers.SerializerMethodField()
    days_left = serializers.IntegerField(read_only=True)
    class Meta:
        model = Campaign
        fields = ('id', 'name', 'image', 'image_icon', 'reward', 'start_date', 'end_date', 'cutoff_optin_date',
                  'duration', 'status', 'is_new_product', 'days_left', 'media', 'supplier_id', 'supplier_purchase_order',
                  'is_published', 'supplier_name')

    def __init__(self, *args, **kwargs):
        ''' Add request from context params '''
        super(CampaignSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def get_media(self, obj):
        ''' Return Media assets serialized data/object'''
        _ = self.__class__.__name__
        medias = CampaignMediaAsset.objects.filter(campaign=obj.id)
        return CampaignMediaAssetSerializer(medias, many=True).data

    
    def to_representation(self, instance):
        ''' Modify campaign serialzer response '''
        self.diff=0
        if instance.cutoff_optin_date and instance.cutoff_optin_date < timezone.now():# if_expired
            setattr(instance, 'status', CampaignStatusType.EXPIRED)
        else:
            self.diff = relativedelta(instance.cutoff_optin_date, timezone.now()).days
        result = super(CampaignSerializer, self).to_representation(instance)
        result['days_left']=self.diff
        return result


class CampaignDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    media_asset = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    retailer_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = ('brand', 'media_asset', 'id', 'name', 'start_date', 'end_date', 'cutoff_optin_date', 'duration', 'image',
                  'is_new_product', 'is_published', 'image_icon', 'reward', 'max_stores', 'max_stores_per_retailer', 'supplier_name',
                  'campaign_notes', 'supplier_id', 'admin_notes', 'product_notes', 'supplier_purchase_order', 'is_deleted', 'retailer_count')

    def get_media_asset(self, obj):
        ''' Return Media assets serialized data/object'''
        _ = self.__class__.__name__
        medias = CampaignMediaAsset.objects.filter(campaign_id=obj.id).order_by('id')
        return CampaignDetailsMediaAssetSerializer(medias, many=True).data

    def get_brand(self, obj):
        ''' Return Media assets serialized data/object'''
        _ = self.__class__.__name__
        brands = CampaignBrand.objects.filter(campaign=obj).values('brand_id')
        return brands

    def get_retailer_count(self, obj):
        ''' Return Media assets serialized data/object'''
        _ = self.__class__.__name__
        retailer_count = TargetRetailer.objects.filter(campaign=obj).count()
        return retailer_count

    def __init__(self, *args, **kwargs):
        super(CampaignDetailSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def update(self, instance, validated_data):
        ''' Update data..'''
        obj = RetailerCampaign.objects.get(campaign_id=self.context['campaign_id'], user_id=self.context['user_id'])
        media_asset = self.request.data.get('media')
        stores = self.request.data.get('stores')
        RetailerCampaignMediaAsset.objects.filter(retailer_campaign=obj).delete()
        if len(media_asset)>0:
            for m_asset in media_asset:
                campaign_media_asset = CampaignMediaAsset.objects.get(campaign_id=int(self.context['campaign_id']), media_asset_id=int(m_asset))
                RetailerCampaignMediaAsset.objects.create(retailer_campaign=obj, campaign_media_asset_id=campaign_media_asset.pk)

        RetailerCampaignStore.objects.filter(retailer_campaign=obj).delete()
        if len(stores)>0:
            for r_store in stores:
                RetailerCampaignStore.objects.create(retailer_campaign=obj, store_id=r_store)
        return self.instance

class UpdateCampaignSerializer(serializers.ModelSerializer):
    '''
    Serializer to update campaign
    '''
    class Meta:
        '''
        meta for update campaign
        '''
        model = Campaign
        fields = ('name', 'image', 'image_icon', 'reward', 'start_date', 'end_date', 'cutoff_optin_date', 'supplier_name',
                  'duration', 'status', 'is_new_product', 'max_stores', 'max_stores_per_retailer', 'campaign_notes', 
                  'supplier_id', 'admin_notes', 'product_notes', 'supplier_purchase_order','is_published', 'is_deleted')

    def __init__(self, *args, **kwargs):
        super(UpdateCampaignSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def update_sample_image(self, media, obj):
        _ = self.__class__.__name__
        if media['sample_image']:
            image_name = '%s/%s.jpeg' % (settings.AWS_STORE_CAMPAIGN_PATH, uuid.uuid4())
            upload_image(media['sample_image'], image_name)
            return image_name
        elif media['sample_image']=="":
            return None

    def update_evidence(self, obj, instance, media):
        # get stores for a campaign
        _ = self
        store_obj = RetailerCampaignStore.objects.filter(retailer_campaign__campaign=instance).order_by('-id')
        if 'evidence' in media:
            for i in media['evidence']:
                campaign_evidence_obj, _ = CampaignEvidence.objects.update_or_create(id=i.get('campaign_evidence_id'),
                                                            defaults={'campaign_media_asset':obj, 'campaign':instance,
                                                                    'start_date':i['start_date'], 'end_date':i['end_date'],
                                                                    'reward':i['reward'],
                                                                    'name':i['name']})
                for store in store_obj:
                    store_campaign = {}
                    store_campaign['campaign'] = instance
                    store_campaign['store_id'] = store.store_id
                    store_campaign['store_name'] = store.store_name
                    store_campaign['retailer_id'] = store.retailer_campaign.user_id
                    store_campaign['retailer_name'] = store.retailer_campaign.user_name
                    store_campaign['evidence'] = campaign_evidence_obj
                    StoreCampaignEvidence.objects.create(**store_campaign)

    def update_products(self, obj, media):
        _ = self
        if 'product' in media:
            for product in media['product']:
                CampaignMediaAssetProduct.objects.update_or_create(product_id=product['product_id'],
                                                                campaign_media_asset=obj,
                                                                defaults={'product_id':product['product_id'], 'notes': product['notes']})
        
    def update(self, instance, validated_data):
        ''' Update data..'''
        super(UpdateCampaignSerializer, self).update(instance, validated_data)
        if 'brands' in self._kwargs['data']:
            CampaignBrand.objects.filter(campaign=instance).delete()
            for i in self._kwargs['data']['brands']:
                CampaignBrand.objects.create(campaign=instance, brand_id=i)
        
        #remove store evidences
        StoreCampaignEvidence.objects.filter(campaign=instance).delete()

        if 'deletedProducts' in self._kwargs['data']:
            CampaignMediaAssetProduct.objects.filter(id__in=self._kwargs['data']['deletedProducts']).delete()
        if 'media' in self._kwargs['data']:
            for media in self._kwargs['data']['media']:
                try:
                    obj_temp = CampaignMediaAsset.objects.filter(id=media.get('campaign_media_asset_id')).first()
                except CampaignMediaAssetProduct.DoesNotExist:
                    obj_temp = None
                obj, created = CampaignMediaAsset.objects.update_or_create(id=media.get('campaign_media_asset_id'),
                    defaults={'campaign': instance, 'media_asset_id': media['media_asset_id']})

                if 'sample_image' in media:
                    img = self.update_sample_image(media, obj)
                    obj.sample_image = img
                    obj.save()

                if not created and not obj_temp.media_asset_id==media['media_asset_id']:
                    retailer_ids = RetailerCampaignMediaAsset.objects.filter(campaign_media_asset=obj).values_list('retailer_campaign', flat=True)
                    for retailer_id in retailer_ids:
                        opted_media_count = RetailerCampaignMediaAsset.objects.filter(Q(retailer_campaign_id=retailer_id), ~Q(campaign_media_asset=obj)).count()
                        if opted_media_count < 1:
                            RetailerCampaign.objects.filter(pk=retailer_id).update(is_opt_out=True)
                            RetailerCampaignStore.objects.filter(retailer_campaign=retailer_id).delete()

                self.update_products(obj, media)
                self.update_evidence(obj, instance, media)
        return self.instance

class TargetRetailerStoreSerializer(serializers.ModelSerializer):
    '''
    Serializer to create target retailers store of campaign
    '''
    class Meta:
        model = TargetStores
        fields = ('store_id',)


class TargetRetailerSerializer(serializers.ModelSerializer):
    '''
    Serializer to create target retailers of campaign
    '''
    stores = TargetRetailerStoreSerializer(many=True, allow_null=True)
    all_stores = serializers.BooleanField(required=False)
    
    class Meta:
        model = TargetRetailer
        fields = ('campaign','retailer_id', 'stores', 'retailer_business', 'all_stores')

    def create(self, validated_data):
        
        with transaction.atomic():
            all_stores = validated_data.pop('all_stores')
            stores = validated_data.pop('stores')
            
            obj, created = TargetRetailer.objects.update_or_create(campaign=validated_data['campaign'],
                                                                   retailer_id=validated_data['retailer_id'],
                                                                   retailer_business=validated_data['retailer_business'])
            
            
            if all_stores:
                try:
                    self.add_stores(obj, validated_data)
                except e:
                    raise ConnectionError(e)
            elif not all_stores:
                if not stores:
                    try:
                        self.add_stores(obj, validated_data, self.context['store_filters'])
                    except Exception as e:
                        raise ConnectionError(e)
                else:
                    # add store ids from request
                    for store in stores:
                        store['target_retailer'] = obj
                        TargetStores.objects.update_or_create(**store)
        return obj

    def add_stores(self, target_retailer, validated_data, store_filters=''):
        _ = self
        # get stores with filters
        # get store from other microservice
        # TODO: to be tranferred in background
        
        base_url = os.environ.get('EXP_EXAMPLE_CAMPAIGN_STORE_SERVER')
        url = base_url + ('/store/filter-business-stores/%s?%s') % (validated_data['retailer_business'], store_filters)
        response = requests.get(url)
        
        response_obj = {}
        if response.status_code == requests.codes.ok:
            response = response.json()
            try:
                response_obj["message"] = response["message"]
            except KeyError:
                response_obj = response["response"]
        else:
            raise Exception(
                'Connection failed to the services. (%s)' % response.text)
        
        for store in response_obj:
            store['target_retailer'] = target_retailer
            store['store_id'] = store.pop('id')
            TargetStores.objects.update_or_create(**store)

class CampaignRetailersSerializer(serializers.ModelSerializer):
    has_opt_store = serializers.SerializerMethodField()
    class Meta:
        model = TargetRetailer
        fields = ('id', 'retailer_id', 'retailer_business', 'has_opt_store')


    def get_has_opt_store(self, instance):
        _ = self
        status = False
        count = RetailerCampaignStore.objects.filter(retailer_campaign__campaign=instance.campaign, store_id__in=instance.targetstores_set.values_list('store_id', flat=True)).count()
        if count > 0:
            status = True
        return status


class CampaignStoresSerializer(serializers.ModelSerializer):
    is_opted = serializers.SerializerMethodField()
    class Meta:
        model = TargetStores
        fields = ('id', 'store_id', 'is_opted')

    def get_is_opted(self, instance):
        _ = self
        status = False
        count = RetailerCampaignStore.objects.filter(store_id=instance.store_id, retailer_campaign__campaign=instance.target_retailer.campaign).count()
        if count > 0:
            status = True
        return status

class CampaignMediaAssetsProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignMediaAssetProduct
        fields = fields = ('id', 'product_id', 'notes', 'campaign_media_asset')

class CampaignDetailsMediaAssetSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    desc = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    thumb_image = serializers.SerializerMethodField()
    is_selected = serializers.SerializerMethodField()
    media_asset_id = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignMediaAsset
        fields = ('id', 'media_asset_id', 'name', 'desc', 'url', 'products', 'thumb_image',
                  'is_selected', 'evidence', 'sample_image', 'qrcode')

    def get_products(self,obj):
        ''' Get Campaign Media Assests products list '''
        _ = self.__class__.__name__
        return CampaignMediaAssetProduct.objects.filter(campaign_media_asset=obj.id).values('id', 'product_id', 'notes').order_by('id')

    def get_evidence(self, obj):
        _ = self.__class__.__name__
        evidences = CampaignEvidence.objects.filter(campaign_media_asset=obj.id).values('id', 'name', 'start_date', 'end_date', 'reward').order_by('id')
        return evidences

    def get_name(self,obj):
        ''' Return media assets name'''
        _ = self.__class__.__name__
        return obj.media_asset.name

    def get_desc(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.desc

    def get_thumb_image(self,obj):
        ''' Return Media assets thumbnail/image '''
        _ = self.__class__.__name__
        return obj.media_asset.image

    def get_url(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.image

    def get_media_asset_id(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.id

    def get_is_selected(self,obj):
        _ = self.__class__.__name__
        objs = obj.retailercampaignmediaasset_set.values().filter(campaign_media_asset_id=obj.id)
        if objs:
            return True
        return False

class CampaignRetailerStoresCountSerializer(serializers.ModelSerializer):
    matched_stores = serializers.SerializerMethodField()
    class Meta:
        model = TargetRetailer
        fields = ('campaign_id', 'retailer_id', 'retailer_business', 'matched_stores')

    def get_matched_stores(self, instance):
        _ = self.__class__.__name__
        return instance.matched_stores

class MediaAssetListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    desc = serializers.SerializerMethodField()
    thumb_image = serializers.SerializerMethodField()
    media_asset_id = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignMediaAsset
        fields = ('id', 'media_asset_id', 'name', 'desc', 'thumb_image', 'product_count')

    def get_name(self,obj):
        ''' Return media assets name'''
        _ = self.__class__.__name__
        return obj.media_asset.name

    def get_desc(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.desc

    def get_thumb_image(self,obj):
        ''' Return Media assets thumbnail/image '''
        _ = self.__class__.__name__
        return obj.media_asset.image

    def get_media_asset_id(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.id

    def get_product_count(self,obj):
        _ = self.__class__.__name__
        return obj.campaign_media.count()


class EvidenceMediaAssetListSerializer(MediaAssetListSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = CampaignMediaAsset
        fields = ('id', 'media_asset_id', 'name', 'desc', 'thumb_image', 'product_count')

    def get_product_count(self,obj):
        _ = self.__class__.__name__
        return obj.campaign_media.count()

class CampaignOptedStores(serializers.ModelSerializer):
    class Meta:
        model = RetailerCampaignStore
        fields = ('store_id',)

class EvidencePhotoListSerializer(serializers.ModelSerializer):
    store_id = serializers.SerializerMethodField()
    retailer_id = serializers.SerializerMethodField()
    class Meta:
        model = PhotoEvidence
        fields = ('id', 'created', 'comment', 'submitter_message', 'submitted_by', 'evidence_url', 'rate1', 'rate2',
        'rate3', 'rate4', 'rate5', 'avg_rate', 'is_rate1_highlight', 'is_rate2_highlight', 'is_rate3_highlight'
        , 'is_rate4_highlight', 'is_rate5_highlight', 'evidence_status', 'store_id', 'retailer_id')

    def get_store_id(self, instance):
        _ = self
        return instance.store_campaign_evidence.store_id

    def get_retailer_id(self, instance):
        _ = self
        return instance.store_campaign_evidence.retailer_id

class EvidencePhotoRetrieveUpdateSerializer(serializers.ModelSerializer):
    store_id = serializers.SerializerMethodField()
    retailer_id = serializers.SerializerMethodField()
    previous_rating = serializers.SerializerMethodField()
    prev_record = serializers.SerializerMethodField()
    next_record = serializers.SerializerMethodField()
    
    class Meta:
        model = PhotoEvidence
        fields = ('id', 'created', 'comment', 'submitter_message', 'submitted_by', 'evidence_url', 'rate1', 'rate2',
        'rate3', 'rate4', 'rate5', 'avg_rate', 'is_rate1_highlight', 'is_rate2_highlight', 'is_rate3_highlight', 
        'is_rate4_highlight', 'is_rate5_highlight', 'evidence_status', 'store_id', 'retailer_id', 'previous_rating',
        'is_no_improvement', 'prev_record', 'next_record')

    def get_store_id(self, instance):
        _ = self
        return instance.store_campaign_evidence.store_id

    def get_retailer_id(self, instance):
        _ = self
        return instance.store_campaign_evidence.retailer_id

    def get_previous_rating(self, instance):
        _ = self
        previous_rating = {}
        query_vars = ''
        
        if instance.evidence_status == EvidenceStatusCheckType.AWAITING_APPROVAL:
            status = EvidenceStatusCheckType.REJECTED
            query_vars = Q(evidence_status=status, store_campaign_evidence=instance.store_campaign_evidence)
        elif instance.evidence_status == EvidenceStatusCheckType.RE_SUBMISSION:
            status = EvidenceStatusCheckType.ACCEPTED
            query_vars = Q(evidence_status=status, store_campaign_evidence=instance.store_campaign_evidence, is_choosen=True)
        
        if query_vars != '':
            previous_rating = PhotoEvidence.objects.exclude(pk=instance.pk).filter(query_vars).values('rate1', 'rate2', 'rate3', 'rate4', 'rate5', 'avg_rate',
            'is_rate1_highlight', 'is_rate2_highlight', 'is_rate3_highlight', 'is_rate4_highlight', 'is_rate5_highlight',
            'evidence_status', 'comment', 'evidence_url').order_by('-id').first()
        
        return previous_rating

    def get_next_record(self, instance):
        next_record = 0
        queryset = self.get_queryset()
        next_record_obj = queryset.filter(pk__gt=instance.pk).order_by('id').first()
        
        if next_record_obj:
            next_record = next_record_obj.pk
        
        return next_record

    def get_prev_record(self, instance):
        prev_record = 0
        queryset = self.get_queryset()
        prev_record_obj = queryset.filter(pk__lt=instance.pk).order_by('-id').first()
        
        if prev_record_obj:
            prev_record = prev_record_obj.pk
        
        return prev_record

    def get_queryset(self):
        query_params = {}
        
        if 'query_params' in self.context:
            query_params = self.context['query_params']
        
        retailer = query_params.get('retailer', '')
        store = query_params.get('store', '')
        status = query_params.get('status', '')
        media_asset = query_params.get('media_asset', '')
        campaign_evidence = query_params.get('campaign_evidence', '')
        current_proof_date = query_params.get('current_proof_date', '')
        
        queryset = PhotoEvidence.objects.all()

        if 'campaign_id' in self.context:
            queryset = queryset.filter(store_campaign_evidence__campaign=self.context['campaign_id'])        

        if retailer != '':
            queryset = queryset.filter(store_campaign_evidence__retailer_id=retailer)

        if store != '':
            queryset = queryset.filter(store_campaign_evidence__store_id=store)

        if status != '':
            queryset = queryset.filter(evidence_status=status)

        if media_asset != '':
            queryset = queryset.filter(store_campaign_evidence__evidence__campaign_media_asset=media_asset)
        
        if campaign_evidence != '':
            queryset = queryset.filter(store_campaign_evidence__evidence=campaign_evidence)
        
        if current_proof_date != '':
            date_obj = datetime.strptime(current_proof_date, '%Y-%m-%d')
            queryset = queryset.filter(created__day=date_obj.day, created__month=date_obj.month, created__year=date_obj.year)

        return queryset

    def update(self, instance, validated_data):
        ''' Update data '''
        task_status = None
        if validated_data['evidence_status'] == EvidenceStatusCheckType.ACCEPTED and validated_data['is_no_improvement'] is False:
            PhotoEvidence.objects.filter(store_campaign_evidence=instance.store_campaign_evidence).update(is_choosen=False)
            validated_data['is_choosen'] = True
            task_status = EvidenceStatusType.ACCEPTED
        elif validated_data['evidence_status'] == EvidenceStatusCheckType.REJECTED:
            task_status = EvidenceStatusType.REJECTED
        
        if task_status is not None:
            StoreCampaignEvidence.objects.filter(pk=instance.store_campaign_evidence.pk).update(task_status=task_status)

        super(EvidencePhotoRetrieveUpdateSerializer, self).update(instance, validated_data)

        return self.instance


class EvidenceLastAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceLastAccess
        fields = ('campaign', 'user_id')

    def create(self, validated_data):
        _ = self
        obj, created = EvidenceLastAccess.objects.update_or_create(**validated_data)
        return obj


class CampaignDataSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    class Meta:
        model = Campaign
        fields = '__all__'

class RetailerDetailCampaignSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    media = serializers.SerializerMethodField()
    days_left = serializers.IntegerField(read_only=True)
    activation_percentage = serializers.SerializerMethodField()
    campaign_status = serializers.SerializerMethodField()
    opted_in = serializers.SerializerMethodField()
    class Meta:
        model = Campaign
        fields = ('id', 'name', 'image', 'image_icon', 'reward', 'start_date', 'end_date', 'cutoff_optin_date',
                  'duration', 'status', 'is_new_product', 'days_left', 'media', 'supplier_id', 'supplier_purchase_order',
                  'is_published', 'supplier_name', 'activation_percentage', 'campaign_status', 'opted_in')

    def __init__(self, *args, **kwargs):
        ''' Add request from context params '''
        super(RetailerDetailCampaignSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def get_media(self, obj):
        ''' Return Media assets serialized data/object'''
        _ = self.__class__.__name__
        medias = CampaignMediaAsset.objects.filter(campaign=obj.id)
        return CampaignMediaAssetSerializer(medias, many=True).data

    def get_campaign_status(self, obj):
        _ = self.__class__.__name__
        campaign_status = 0
        if obj.end_date <= timezone.now():
            campaign_status = 2 #completed campaign
        elif obj.end_date >= timezone.now() and obj.start_date <= timezone.now():
            campaign_status = 1 #active campaign
        elif RetailerCampaignStore.objects.filter(retailer_campaign__campaign_id=obj.id).count() > 0 and obj.start_date >= timezone.now():
             campaign_status = 3 #optin campaign
        return campaign_status

    def get_opted_in(self, obj):
        _ = self.__class__.__name__
        optincampaign = RetailerCampaignStore.objects.filter(is_active=True, retailer_campaign__campaign_id=obj.id).aggregate(optin_stores=Count('id'))
        targetcampaign = TargetStores.objects.filter(is_active=True, target_retailer__campaign_id=obj.id).aggregate(optin_stores=Count('id'))
        try:
            optin_percentage = optincampaign['optin_stores'] * 100 / targetcampaign['optin_stores']
        except ZeroDivisionError:
            optin_percentage = 0
        return optin_percentage

    def get_activation_percentage(self, obj):
        _ = self.__class__.__name__
        reward_distributed = StoreCampaignEvidence.objects.filter(campaign_id=obj.id).aggregate(
            total=Sum(Case(When(task_status=EvidenceStatusCheckType.ACCEPTED, then='campaign__reward'), 
                default=Value(0),
                output_field=IntegerField())),
            total_evidence=Count('id'),
            total_accepted_evidence=Sum(
                Case(When(task_status=EvidenceStatusCheckType.ACCEPTED, then=1),
                default=Value(0),
                output_field=IntegerField())),
            )
        try:
            activation_percentage = (100 * reward_distributed['total_accepted_evidence']) / reward_distributed['total_evidence']
        except (ZeroDivisionError, TypeError):
            activation_percentage = 0
        return activation_percentage
    
    def to_representation(self, instance):
        ''' Modify campaign serialzer response '''
        self.diff=0
        if instance.cutoff_optin_date and instance.cutoff_optin_date < timezone.now():# if_expired
            setattr(instance, 'status', CampaignStatusType.EXPIRED)
        else:
            self.diff = relativedelta(instance.cutoff_optin_date, timezone.now()).days
        result = super(RetailerDetailCampaignSerializer, self).to_representation(instance)
        result['days_left']=self.diff
        return result


class StoreCampaignEvidenceSerializer(serializers.ModelSerializer):
    media_assets = serializers.SerializerMethodField()
    evidence_name = serializers.SerializerMethodField()
    media_asset_name = serializers.SerializerMethodField()
    media_asset_image = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    evidence_start_date = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()

    class Meta:
        model = StoreCampaignEvidence
        fields = ('id', 'campaign', 'store_id', 'retailer_id', 'evidence', 'is_submitted', 'task_status', 'store_name', 'campaign_name',
                  'is_active', 'media_assets', 'evidence_name', 'media_asset_name', 'media_asset_image', 'days_left', 'evidence_start_date')

    def get_media_assets(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset_id

    def get_evidence(self, obj):
        _ = self.__class__.__name__
        return obj.evidence_id

    def get_campaign_name(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.name

    def get_evidence_start_date(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.start_date

    def get_evidence_name(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.name

    def get_media_asset_name(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.name

    def get_media_asset_image(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.image

    def get_days_left(self, obj):
        _ = self.__class__.__name__
        return relativedelta(obj.evidence.end_date, timezone.now()).days
