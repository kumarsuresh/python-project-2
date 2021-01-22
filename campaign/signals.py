import base64
import uuid
from io import BytesIO

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from example.core.utility import upload_image

from .models import CampaignMediaAsset


@receiver(post_save, sender=CampaignMediaAsset, dispatch_uid="update-campaign-media-assets-qrimage")
def save_qrcode(sender, instance, created, **kwargs):
    if not instance.qrcode:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=50,
            border=1,
        )
        qr.add_data(instance.pk)
        qr.make(fit=True)

        img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        buffered = BytesIO()
        img.save(buffered)
        qr_image = base64.b64encode(buffered.getvalue())
        qr_image_name = '%s/%s.svg' % (settings.AWS_STORE_CAMPAIGN_PATH, uuid.uuid4())
        upload_image(qr_image, qr_image_name)
        instance.qrcode = qr_image_name
        instance.save()
    return True
