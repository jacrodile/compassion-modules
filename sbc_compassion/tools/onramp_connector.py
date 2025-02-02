##############################################################################
#
#    Copyright (C) 2015-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64

from odoo.addons.message_center_compassion.tools.onramp_connector import OnrampConnector

from odoo import _
from odoo.exceptions import UserError


class SBCConnector(object):
    def __init__(self, env):
        self.connector = OnrampConnector(env)

    def send_letter_image(self, image_data, image_type, base64encoded=True):
        """ Sends an image of a Letter to Onramp U.S. Image Upload Service.
        See http://developer.compassion.com/docs/read/compassion_connect2/
            service_catalog/Image_Submission

        Returns the uploaded image URL.
        """
        if image_type == "pdf":
            content_type = "application"
        else:
            content_type = "image"
        headers = {f"Content-type": f"{content_type}/{image_type}"}
        params = {"doctype": "s2bletter"}
        url = "images/documents"
        if base64encoded:
            data = base64.b64decode(image_data)
        else:
            data = image_data
        r = self.connector.send_message(url, "POST", params=params, headers=headers, data=data)
        status = r.get("code")
        letter_url = r.get("content")
        if status != 201:
            raise UserError(_("[%s] %s") % (str(status), letter_url))
        return letter_url

    def get_letter_image(self, letter_url, img_type="jpeg", pages=0, dpi=96):
        """ Calls Letter Image Service from Onramp U.S. and get the data
        http://developer.compassion.com/docs/read/compassion_connect2/service_catalog/Image_Retrieval
        """
        params = {"format": img_type, "pg": pages, "dpi": dpi}
        return base64.b64encode(self.connector.send_message(letter_url, "GET_RAW", params=params, full_url=True))
