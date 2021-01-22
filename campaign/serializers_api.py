from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.forms import ValidationError
from django.utils import timezone
from rest_framework import serializers

from .choices import (CampaignOptStatusType, CampaignStatusType,
                      EvidenceStatusType)
from .messages import *
from .models import (Campaign, CampaignEvidence, CampaignMediaAsset,
                     CampaignMediaAssetProduct, PhotoEvidence,
                     RetailerCampaign, RetailerCampaignMediaAsset,
                     RetailerCampaignStore, StoreCampaignEvidence,
                     TargetStores)


class CampaignMediaAssetSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    class Meta:
        model = CampaignMediaAsset
        fields = ('id', 'media_url', 'name')

    def get_media_url(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.image

    def get_name(self,obj):
        _ = self.__class__.__name__
        return obj.media_asset.name

class CampaignMiniSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    class Meta:
        model = Campaign
        fields = ('id', 'name')


class CampaignSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    media = serializers.SerializerMethodField()
    days_left = serializers.IntegerField(read_only=True)
    targeted_reward = serializers.IntegerField(read_only=True)
    claimed = serializers.IntegerField(read_only=True)
    class Meta:
        model = Campaign
        fields = ('id', 'name', 'image', 'image_icon', 'reward', 'start_date', 'end_date', 'cutoff_optin_date',
                  'duration', 'status', 'is_new_product', 'days_left', 'media', 'is_deleted', 'claimed', 'targeted_reward')

    def get_media(self, obj):
        _ = self.__class__.__name__
        medias = CampaignMediaAsset.objects.filter(campaign=obj.id)
        return CampaignMediaAssetSerializer(medias, many=True).data

    def __init__(self, *args, **kwargs):
        super(CampaignSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']
    
    def to_representation(self, instance):
        self.diff=0
        self.camp_opt = CampaignOptStatusType.BELOW_80
        if instance.end_date < timezone.now():# if_expired
            setattr(instance, 'status', CampaignStatusType.EXPIRED)
        else:
            if RetailerCampaign.objects.filter(campaign=instance, user_id=self.context['user_id'], is_opt_out=False).first():# if_opted
                setattr(instance, 'status', CampaignStatusType.OPTED)
            else:# days left to opt
                setattr(instance, 'status', CampaignStatusType.NOT_OPTED)
                
                delta = instance.cutoff_optin_date - timezone.now()
                if delta.days > -1:
                    self.diff = (relativedelta(instance.cutoff_optin_date, timezone.now()).days) + 1

        # check how many seats are left
        retailer_count = RetailerCampaignStore.objects.filter(retailer_campaign__campaign=instance).count()
        if instance.max_stores is not None and instance.max_stores > 0:
            self.per = (retailer_count / instance.max_stores) * 100
            if self.per == 100:
                self.camp_opt=CampaignOptStatusType.CLAIMED
            elif self.per >= 80:
                self.camp_opt=CampaignOptStatusType.ABOVE_80
            else:
                self.camp_opt=CampaignOptStatusType.BELOW_80

        # calculate reward value for one or for all basis on toggle
        total_amount = 0
        targeted_store_count = 0
        if self.context['isall'] == 'True':
            if instance.status == CampaignStatusType.OPTED:
                targeted_store_count = RetailerCampaignStore.objects.filter(retailer_campaign__user_id=self.context['user_id'], retailer_campaign__campaign_id=instance.id, retailer_campaign__is_opt_out=False).count()
            else:
                targeted_store_count = TargetStores.objects.filter(target_retailer__retailer_id=self.context['user_id'], target_retailer__campaign_id=instance.id).count()
        else:
            targeted_store_count = 1
        evidence_objs = CampaignEvidence.objects.filter(campaign_id=instance.id)
        for evidence_obj in evidence_objs:
            total_amount += evidence_obj.reward
        total_amount = total_amount * targeted_store_count

        result = super(CampaignSerializer, self).to_representation(instance)
        result['days_left'] = self.diff
        result['claimed'] = self.camp_opt
        result['targeted_reward'] = total_amount
        return result

class CampaignMediaAssetProductSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    campaign_media_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    sample_image = serializers.SerializerMethodField()
    desc = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    thumb_image = serializers.SerializerMethodField()
    is_selected = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignMediaAsset
        fields = ('id', 'campaign_media_id', 'name', 'sample_image', 'desc', 'url', 'thumb_image', 'is_selected', 'products', 'evidence')

    def get_evidence(self, obj):
        _ = self.__class__.__name__
        evidences = CampaignEvidence.objects.filter(campaign_media_asset=obj.pk).values('start_date', 'end_date', 'reward', 'name').order_by('name')
        return evidences

    def get_products(self, obj):
        _ = self.__class__.__name__
        return CampaignMediaAssetProduct.objects.filter(campaign_media_asset=obj.pk).values_list('product_id',flat=True)

    def get_id(self, obj):
        _ = self.__class__.__name__
        return obj.media_asset.id

    def get_campaign_media_id(self, obj):
        _ = self.__class__.__name__
        return obj.id

    def get_name(self, obj):
        _ = self.__class__.__name__
        return obj.media_asset.name

    def get_sample_image(self, obj):
        _ = self.__class__.__name__
        return obj.sample_image

    def get_desc(self, obj):
        _ = self.__class__.__name__
        return obj.media_asset.desc

    def get_thumb_image(self, obj):
        _ = self.__class__.__name__
        return obj.media_asset.image

    def get_url(self, obj):
        _ = self.__class__.__name__
        return obj.media_asset.image

    def get_is_selected(self, obj):
        _ = self.__class__.__name__
        objs = obj.retailercampaignmediaasset_set.values().filter(campaign_media_asset_id=obj.id, retailer_campaign__user_id=self.context['user_id'])
        if objs:
            return True
        return False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.context:
            self._context = getattr(self.Meta, 'context', {})
        try:
            self.user = self.context['user_id']
        except KeyError:
            self.user = None

class CampaignDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    opted_stores = serializers.SerializerMethodField()
    media_asset = serializers.SerializerMethodField('get_media_asset_serializer')
    targeted_store_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = ('media_asset', 'opted_stores' , 'id', 'name', 'start_date', 'end_date', 'cutoff_optin_date', 'duration',
                  'max_stores', 'max_stores_per_retailer', 'product_notes', 'campaign_notes', 'supplier_id', 'targeted_store_count')

    def get_opted_stores(self, obj):
        _ = self.__class__.__name__
        try:
            obj = RetailerCampaign.objects.get(campaign_id=self.context['campaign_id'], user_id=self.context['user_id'])
            return RetailerCampaignStore.objects.filter(retailer_campaign=obj).values_list('store_id', flat=True)
        except RetailerCampaign.DoesNotExist:
            return []
    def get_targeted_store_count(self, obj):
        _ = self.__class__.__name__
        return TargetStores.objects.filter(target_retailer__retailer_id=self.context['user_id'], target_retailer__campaign_id=self.context['campaign_id']).count()

    def get_media_asset_serializer(self, obj):
        serializer_context = {'user_id': self.context['user_id'] }
        children = CampaignMediaAsset.objects.filter(campaign=obj)
        serializer = CampaignMediaAssetProductSerializer(children, many=True, context=serializer_context)
        return serializer.data

    def __init__(self, *args, **kwargs):
        super(CampaignDetailSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def validate(self, data):
        selected_stores = self.request.data.get('stores')
        store_ids = [x['id'] for x in selected_stores ]

        try:
            obj = RetailerCampaign.objects.get(campaign_id=self.context['campaign_id'], user_id=self.context['user_id'])
        except RetailerCampaign.DoesNotExist:
            raise ValidationError("Retailer Campaign not exist")
        
        local_store_ids = RetailerCampaignStore.objects.filter(retailer_campaign=obj).values_list('store_id', flat=True)
        campaign_store_count = RetailerCampaignStore.objects.filter(~Q(store_id__in=local_store_ids), Q(retailer_campaign__campaign=self.context['campaign_id'])).count()

        retailer_store_count = RetailerCampaignStore.objects.filter(~Q(store_id__in=local_store_ids),Q(retailer_campaign=obj)).count()
        store_len = len(store_ids)
        if self.instance.max_stores_per_retailer is not None and (store_len > self.instance.max_stores_per_retailer):
            raise ValidationError("Store limit per retailer is : %s"%(self.instance.max_stores_per_retailer))
        elif self.instance.max_stores_per_retailer is not None and (retailer_store_count == self.instance.max_stores_per_retailer):
            raise ValidationError("Per retailer seats exhausted @%s"%seats_left)
        elif self.instance.max_stores is not None and ((self.instance.max_stores - campaign_store_count) < store_len):
            raise ValidationError('Sorry, by the time you were doing store selection, few other retailers have opted for store(s). We just have %s stores left for opting-in. Please hurry@%s'%(seats_left, seats_left))
        else:
            return data

    def update(self, instance, validated_data):
        obj = RetailerCampaign.objects.get(campaign_id=self.context['campaign_id'], user_id=self.context['user_id'])
        media_asset = self.request.data.get('media_asset')
        
        stores = self.request.data.get('stores')
        RetailerCampaignMediaAsset.objects.filter(retailer_campaign=obj).delete()
        if len(media_asset)>0:
            for m_asset in media_asset:
                RetailerCampaignMediaAsset.objects.create(retailer_campaign=obj, campaign_media_asset_id=m_asset)

        RetailerCampaignStore.objects.filter(retailer_campaign=obj).delete()
        StoreCampaignEvidence.objects.filter(campaign_id=int(self.context['campaign_id'])).delete()
        if len(stores)>0:
            for r_store in stores:
                RetailerCampaignStore.objects.create(retailer_campaign=obj, store_id=r_store['id'], store_name=r_store['name'])
            evidence_objs = CampaignEvidence.objects.filter(campaign_id=int(self.context['campaign_id']), campaign_media_asset_id__in=media_asset)
            for evidence in evidence_objs:
                for store in stores:
                    StoreCampaignEvidence.objects.create(campaign_id=int(self.context['campaign_id']), store_id=store['id'], store_name=store['name'], 
                        retailer_id=self.context['user_id'], retailer_name=self.request.data['user_name'], evidence=evidence)
        return self.instance

class CampaignOptInSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = Campaign
        fields = ('id',)

    def __init__(self, *args, **kwargs):
        super(CampaignOptInSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def validate(self, data):
        campaign_store_count = RetailerCampaignStore.objects.filter(retailer_campaign__campaign=self.context['campaign_id']).count()

        store_len = len(self.request.data.get('stores'))
        if self.instance.max_stores is not None and (campaign_store_count >= self.instance.max_stores):
            raise ValidationError("you can opt for maximum %s!@%s"%(seats_left, seats_left))
        elif self.instance.max_stores_per_retailer is not None and (store_len > self.instance.max_stores_per_retailer):
            raise ValidationError("Store limit per retailer is : %s"%self.instance.max_stores_per_retailer)
        elif self.instance.max_stores is not None and ((self.instance.max_stores - campaign_store_count) < store_len):
            raise ValidationError('Sorry, by the time you were doing store selection, few other retailers have opted for stores. We just have %s stores left for opting-in. Please hurry@%s'%(seats_left, seats_left))
        else:
            return data

    def update(self, instance, validated_data):
        obj, _ = RetailerCampaign.objects.update_or_create(campaign_id=self.context['campaign_id'],
                                                           user_id=self.request.data['retailer_id'],
                                                           defaults={"is_opt_out": False, "opted_by":self.context['user_id'], "user_name":self.request.data['user_name']})

        media_asset = self.request.data.get('media_asset')
        stores = self.request.data.get('stores')
        for m_asset in media_asset:
            RetailerCampaignMediaAsset.objects.create(retailer_campaign=obj, campaign_media_asset_id=m_asset)
        
        for store in stores:
            RetailerCampaignStore.objects.get_or_create(retailer_campaign=obj, store_id=store['id'], store_name=store['name'])
        
        evidence_objs = CampaignEvidence.objects.filter(campaign_id=int(self.context['campaign_id']), campaign_media_asset_id__in=media_asset)
        
        for evidence in evidence_objs:
            for store in stores:
                StoreCampaignEvidence.objects.create(campaign_id=int(self.context['campaign_id']), store_id=store['id'], store_name=store['name'], \
                retailer_id=self.request.data['retailer_id'], retailer_name=self.request.data['user_name'], evidence=evidence)
        return self.instance

    def to_representation(self, *args, **kwargs):
        _ = self.__class__
        return {
            MESSAGE: REQUEST_SUCCESSFULL
        }

class CampaignOptOutSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = Campaign
        fields = ('id',)

    def __init__(self, *args, **kwargs):
        super(CampaignOptOutSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def update(self, instance, validated_data):
        obj = RetailerCampaign.objects.filter(campaign_id=self.context['campaign_id'], user_id=self.context['user_id']).first()
        obj.is_opt_out=True
        obj.save()
        RetailerCampaignMediaAsset.objects.filter(retailer_campaign=obj).delete()
        RetailerCampaignStore.objects.filter(retailer_campaign=obj).delete()
        StoreCampaignEvidence.objects.filter(campaign_id=self.context['campaign_id'], retailer_id=self.context['user_id']).delete()
        return self.instance

    def to_representation(self, *args, **kwargs):
        _ = self.__class__
        return {
            MESSAGE: REQUEST_SUCCESSFULL
        }
class OptedStoresSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """    
    class Meta:
        model = RetailerCampaignStore
        fields = ('store_id', 'store_name')

class OptedCampaignsSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    reward = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = RetailerCampaign
        fields = ('id', 'name', 'image', 'reward', 'start_date', 'end_date', 'duration')

    def get_id(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.id

    def get_name(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.name

    def get_image(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.image

    def get_reward(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.reward

    def get_start_date(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.start_date

    def get_end_date(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.end_date

    def get_duration(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.duration

class SelectedStoresListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        if type(data) == dict:
            count = 0
            data = []
        else:
            count = data.count()
        data = super(SelectedStoresListSerializer, self).to_representation(data)
        return [{'data': data}, {'selected_stores_count': count}]

class TargettedStoresListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        # get count for stores left for opt in
        campaign = Campaign.objects.get(pk=self.context['campaign_id'])
        campaign_max_stores = campaign.max_stores
        campaign_max_stores_retailer = campaign.max_stores_per_retailer or 0
        campaign_stores = 0
        if getattr(campaign, 'retailercampaign_set', None):
            campaign_retailers = campaign.retailercampaign_set.values_list('pk',flat=True)
            campaign_stores = RetailerCampaignStore.objects.filter(retailer_campaign__in=campaign_retailers).count()
        count = campaign_max_stores_retailer
        
        if campaign_max_stores_retailer != 0:
            if (campaign_max_stores_retailer - campaign_stores) < campaign_max_stores_retailer:
                count = (campaign_max_stores_retailer or 0) - campaign_stores
        else:
            count = (campaign_max_stores or 0) - campaign_stores
        
        data = super(TargettedStoresListSerializer, self).to_representation(data)
        
        
        return [{'data': data}, {'stores_remaining_count': count}]

class SelectedStoresSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    class Meta:
        model = RetailerCampaignStore
        list_serializer_class = SelectedStoresListSerializer
        fields = ('store_id',)

class TargetStoresSerializer(serializers.ModelSerializer):
    """
    Serializer to get targeted stores
    """
    class Meta:
        model = TargetStores
        list_serializer_class = TargettedStoresListSerializer
        fields = ('store_id',)

class EvidenceSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    campaign_name = serializers.SerializerMethodField()
    campaign_image = serializers.SerializerMethodField()
    media_name = serializers.SerializerMethodField()
    media_image = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    store_id = serializers.SerializerMethodField()
    class Meta:
        model = CampaignEvidence
        fields = ('id', 'name', 'campaign_name', 'campaign_image', 'media_name', 'media_image', 'reward', 'start_date', 'end_date', 'days_left', 'store_id')

    def get_campaign_name(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.name

    def get_campaign_image(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.image_icon

    def get_media_name(self, obj):
        _ = self.__class__.__name__
        return obj.campaign_media_asset.media_asset.name

    def get_media_image(self, obj):
        _ = self.__class__.__name__
        return obj.campaign_media_asset.media_asset.image

    def get_days_left(self, obj):
        _ = self.__class__.__name__
        return relativedelta(obj.end_date, timezone.now()).days

    def get_store_id(self, obj):
        _ = self.__class__.__name__
        retailer_obj = RetailerCampaign.objects.get(campaign=obj.campaign, user_id=self.context['user_id'])
        return RetailerCampaignStore.objects.filter(retailer_campaign=retailer_obj).values_list('store_id', flat=True)

    def __init__(self, *args, **kwargs):
        super(EvidenceSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']
    

class TasksSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """
    name = serializers.SerializerMethodField()
    reward = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    campaign_id = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()
    campaign_image = serializers.SerializerMethodField()
    media_id = serializers.SerializerMethodField()
    media_name = serializers.SerializerMethodField()
    media_image = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    sample_image = serializers.SerializerMethodField()

    class Meta:
        model = StoreCampaignEvidence
        fields = ('id', 'name', 'task_status', 'campaign_id', 'campaign_name', 'campaign_image', 'media_id', 'media_name', 'media_image', 'sample_image', 'reward', 'start_date', 'end_date', 'days_left', 'store_id')

    def get_name(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.name

    def get_reward(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.reward

    def get_start_date(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.start_date

    def get_end_date(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.end_date

    def get_campaign_id(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.id

    def get_campaign_name(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.name

    def get_campaign_image(self, obj):
        _ = self.__class__.__name__
        return obj.campaign.image_icon

    def get_sample_image(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.sample_image

    def get_media_id(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.id

    def get_media_name(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.name

    def get_media_image(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.image

    def get_days_left(self, obj):
        _ = self.__class__.__name__
        number_of_days = obj.evidence.end_date.date() - timezone.now().date()
        return number_of_days.days

    def __init__(self, *args, **kwargs):
        super(TasksSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']
    
class CampMediaProdSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = CampaignMediaAssetProduct
        fields = ('product_id', 'notes')

class FilterStatusSerializer(serializers.Serializer):
    key = serializers.IntegerField()
    name = serializers.CharField()
    count = serializers.IntegerField()

class ValidateQRSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = CampaignMediaAsset
        fields = "__all__"

class SubmitEvidenceSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = PhotoEvidence
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(SubmitEvidenceSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def create(self, validated_data):
        instance = super(SubmitEvidenceSerializer,
                         self).create(validated_data)
        if self.context['task_status']==EvidenceStatusType.AWAITING_APPROVAL:
            instance.store_campaign_evidence.task_status=self.context['task_status']
            instance.store_campaign_evidence.save()
        instance.evidence_status = self.context['task_status']
        instance.submitted_by = self.context['user_id']
        instance.save()
        return instance

    def to_representation(self, *args, **kwargs):
        _ = self.__class__
        return {
            MESSAGE: REQUEST_SUCCESSFULL
        }

class SubmittedEvidenceSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = PhotoEvidence
        fields = ('id', 'evidence_url', 'is_choosen', 'evidence_status', 'avg_rate', 'comment')

class WriteToexampleSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign List
    """

    class Meta:
        model = StoreCampaignEvidence
        fields = "__all__"

class EvidenceDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = PhotoEvidence
        fields = "__all__"

class RatingSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    class Meta:
        model = PhotoEvidence
        fields = ('evidence_status', 'is_choosen', 'avg_rate', 'rate1', 'rate2', 'rate3', 'rate4', 'rate5', 'is_rate1_highlight', 
        'is_rate2_highlight', 'is_rate3_highlight', 'is_rate4_highlight', 'is_rate5_highlight', 'comment')

class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign Detail
    """
    photos_count = serializers.SerializerMethodField()
    media_id = serializers.SerializerMethodField()
    media_name = serializers.SerializerMethodField()
    media_image = serializers.SerializerMethodField()
    sample_image = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField('get_evidence_serializer')

    class Meta:
        model = StoreCampaignEvidence
        fields = ('media_id', 'media_name', 'media_image', 'sample_image', 'task_status', 'photos_count', 'evidence') 

    def get_evidence_serializer(self, obj):
        serializer_context = {'user_id': self.context['user_id'] }
        children = obj.photoevidence_set.order_by('-is_choosen', '-avg_rate').first()
        serializer = RatingSerializer(children, many=False, context=serializer_context)
        return serializer.data

    def get_photos_count(self, obj):
        _ = self.__class__.__name__
        try:
            return PhotoEvidence.objects.filter(store_campaign_evidence=obj).count()
        except PhotoEvidence.DoesNotExist:
            return 0

    def get_sample_image(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.sample_image

    def get_media_id(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.id

    def get_media_name(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.name

    def get_media_image(self, obj):
        _ = self.__class__.__name__
        return obj.evidence.campaign_media_asset.media_asset.image

    def __init__(self, *args, **kwargs):
        super(TaskDetailSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']
