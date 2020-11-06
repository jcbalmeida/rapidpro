from django.utils.translation import ugettext_lazy as _

from temba.channels.models import ChannelType
from temba.channels.types.kaleyra.views import ClaimView
from temba.contacts.models import WHATSAPP_SCHEME

CONFIG_ACCOUNT_SID = "account_sid"
CONFIG_API_KEY = "api_key"


class KaleyraType(ChannelType):
    """
    A Kaleyra Channel Type
    """

    code = "KWA"
    category = ChannelType.Category.SOCIAL_MEDIA

    courier_url = r"^kwa/(?P<uuid>[a-z0-9\-]+)/(?P<action>receive|status)$"

    name = "Kaleyra WhatsApp"
    icon = "icon-whatsapp"

    claim_blurb = _(
        """Activate your own enterprise WhatsApp account in Kaleyra to communicate with your contacts. <a href="https://www.kaleyra.com/whatsapp/">Learn more about Kaleyra WhatsApp"""
    )
    claim_view = ClaimView

    schemes = [WHATSAPP_SCHEME]
    max_length = 4096
    attachment_support = True