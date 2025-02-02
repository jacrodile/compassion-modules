##############################################################################
#
#    Copyright (C) 2016-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError

logger = logging.getLogger(__name__)


class CommunicationDefaults(models.AbstractModel):
    """ Abstract class to share config settings between communication config
    and communication job. """

    _name = "partner.communication.defaults"

    user_id = fields.Many2one(
        "res.users", "From", domain=[("share", "=", False)]
    )
    need_call = fields.Selection(
        "get_need_call",
        help="Indicates we should have a personal contact with the partner",
    )
    print_if_not_email = fields.Boolean(
        help="Should we print the communication if the sponsor don't have "
             "an e-mail address"
    )
    report_id = fields.Many2one(
        "ir.actions.report",
        "Print report",
        domain=[("model", "=", "partner.communication.job")],
        readonly=False,
    )
    # printer_input_tray_id = fields.Many2one("printing.tray.input", "Paper Source")
    # printer_output_tray_id = fields.Many2one("printing.tray.output", "Output Bin")

    @api.model
    def get_need_call(self):
        return [
            ("before_sending", _("Before the communication is sent")),
            ("after_sending", _("After the communication is sent")),
        ]


class CommunicationDefaultConfig(models.Model):

    _name = "partner.communication.default.config"
    _inherit = "partner.communication.defaults"
    _description = "Communication Default Config"

    config_id = fields.Many2one("partner.communication.config", "Communication type")
    lang_id = fields.Many2one(
        "res.lang", "Language",
        help="This config will only apply to communications in selected language.")
    user_id = fields.Many2one(
       string="User", help="This config will only apply for communications from this user")

    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("user_id") and not vals.get("lang_id"):
                raise UserError(_(
                    "The config should apply at least for a user or a language, otherwise you can "
                    "simply change the settings in the general configuration."))
        return super().create(vals_list)


class CommunicationConfig(models.Model):
    """ This class allows to configure if and how we will inform the
    sponsor when a given event occurs. """

    _name = "partner.communication.config"
    _inherit = "partner.communication.defaults"
    _inherits = {"utm.source": "source_id"}
    _rec_name = "source_id"
    _description = "Communication Configuration"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    source_id = fields.Many2one(
        "utm.source", "UTM Source", required=True, ondelete="restrict", readonly=False
    )
    model_id = fields.Many2one(
        "ir.model",
        "Applies to",
        required=True,
        help="The kind of document with this communication can be used",
        readonly=False,
        ondelete="cascade",
    )
    model = fields.Char(related="model_id.model", store=True, readonly=True)
    send_mode = fields.Selection("get_send_mode", required=True)
    send_mode_pref_field = fields.Char(
        "Partner preference field",
        help="Name of the field in res.partner in which to find the "
        "delivery preference",
    )
    email_template_id = fields.Many2one(
        "mail.template",
        "Email template",
        domain=[
            "|",
            ("model", "=", "partner.communication.job"),
            ("model", "=", "crm.claim"),
        ],
        readonly=False,
    )
    attachments_function = fields.Char(
        help="Define a function in the communication_job model that will "
        "return all the attachment information for the communication in a "
        "dict of following format: {attach_name: [report_name, b64_data]}"
        "where attach_name is the name of the file generated,"
        "report_name is the name of the report used for printing,"
        "b64_data is the binary of the attachment"
    )
    default_config_ids = fields.One2many(
        comodel_name="partner.communication.default.config",
        inverse_name="config_id",
        string="Custom Configuration",
        readonly=False
    )
    active = fields.Boolean(default=True)

    ##########################################################################
    #                             FIELDS METHODS                             #
    ##########################################################################
    @api.constrains("send_mode_pref_field")
    def _validate_config(self):
        """ Test if the config is valid. """
        for config in self.filtered("send_mode_pref_field"):
            valid = hasattr(self.env["res.partner"], config.send_mode_pref_field)
            if not valid:
                raise ValidationError(
                    _(
                        "Following field does not exist in res.partner: %s."
                    ) % config.send_mode_pref_field
                )

    @api.constrains("report_id")
    def _validate_attached_reports(self):
        for config in self:
            if (
                config.report_id
                and config.report_id.model != "partner.communication.job"
            ):
                raise ValidationError(
                    _(
                        "Attached report templates should be linked to "
                        "partner.communication.job objects!"
                    )
                )

    @api.constrains("attachments_function")
    def _validate_attachment_function(self):
        job_obj = self.env["partner.communication.job"]
        for config in self.filtered("attachments_function"):
            if not hasattr(job_obj, config.attachments_function):
                raise ValidationError(
                    _("partner.communication.job has no function called ")
                    + config.attachments_function
                )

    ##########################################################################
    #                             PUBLIC METHODS                             #
    ##########################################################################
    def get_default_config(self, lang):
        default_config = self.default_config_ids.filtered(lambda c: not c.lang_id)[:1]
        for config in self.default_config_ids:
            if config.lang_id == lang:
                default_config = config
        return default_config

    @api.model
    def get_send_mode(self):
        send_modes = self.get_delivery_preferences()
        send_modes.append(("partner_preference", _("Partner specific")))
        return send_modes

    @api.model
    def get_delivery_preferences(self):
        return [
            ("none", _("Don't inform sponsor")),
            ("auto_digital_only", _("only by e-mail (send automatically)")),
            ("digital_only", _("only by e-mail (send manually)")),
            ("auto_digital", _("Send e-mail automatically")),
            ("digital", _("Send e-mail manually")),
            ("physical", _("Print letter")),
            ("both", _("Send e-mail + print letter")),
        ]

    def get_inform_mode(self, partner):
        self.ensure_one()
        return self.build_inform_mode(
            partner, self.send_mode, self.print_if_not_email, self.send_mode_pref_field
        )

    @api.model
    def build_inform_mode(
        self, partner, communication_send_mode, print_if_not_email, send_mode_pref_field
    ):
        """ Returns how the partner should be informed for the given
        communication (digital, physical or False).
        It makes the product of the communication preference and the partner
        preference :

        comm_pref       partner_pref        result
        ---------------------------------------------------
        physical        digital             physical
        physical        digital_only        digital
        digital         physical            physical if "print if no e-mail"
                                                     else none
        digital         digital_only        digital
        digital_only    physical            digital if e-mail is set else none
        digital_only    digital             digital
        digital_only    both                digital
        both            digital_only        digital


        auto            manual              manual
        manual          auto                manual

        :param partner: res.partner record
        :param communication_send_mode: string
        :param print_if_not_email: boolean
        :param send_mode_pref_field string
        :returns: send_mode (physical/digital/False), auto_mode (True/False)
        """
        # First key is the comm send_mode, second key is the partner send_mode
        # value is the send_mode that should be selected.
        send_priority = {
            "physical": {
                "none": "none",
                "physical": "physical",
                "digital": "physical",
                "digital_only": "digital",
                "both": "physical",
            },
            "digital": {
                "none": "none",
                "physical": "physical" if print_if_not_email else "none",
                "digital": "digital",
                "digital_only": "digital",
                "both": "both" if print_if_not_email else "digital",
            },
            "digital_only": {
                "none": "none",
                "physical": "digital" if partner.email else "none",
                "digital": "digital",
                "digital_only": "digital",
                "both": "digital",
            },
            "both": {
                "none": "none",
                "physical": "physical",
                "digital": "both",
                "digital_only": "digital",
                "both": "both",
            },
        }

        if communication_send_mode != "partner_preference":
            partner_mode = getattr(
                partner,
                send_mode_pref_field or "global_communication_delivery_preference",
                partner.global_communication_delivery_preference,
            )
            if communication_send_mode == partner_mode:
                send_mode = communication_send_mode
                auto_mode = "auto" in send_mode or send_mode == "both"
                digital_only = "digital_only" in partner_mode
            else:
                auto_mode = (
                    "auto" in partner_mode
                    and "auto" in communication_send_mode
                    or "auto" in partner_mode
                    and communication_send_mode == "both"
                    or "auto" in communication_send_mode
                    and partner_mode == "both"
                )
                comm_mode = communication_send_mode.replace("auto_", "")
                partner_mode = partner_mode.replace("auto_", "")
                send_mode = send_priority.get(comm_mode, {}).get(partner_mode, "none")
                digital_only = (
                    "digital_only" in partner_mode or "digital_only" in comm_mode
                )
        else:
            send_mode = getattr(partner, send_mode_pref_field, "none")
            auto_mode = "auto" in send_mode or send_mode == "both"
            digital_only = "digital_only" in send_mode

        send_mode = send_mode.replace("auto_", "").replace("_only", "")

        if send_mode == "none":
            send_mode = False

        # missing email
        removed_digital = False
        if send_mode in ["digital", "both"] and not partner.email:
            removed_digital = True
            if (print_if_not_email or send_mode == "both") and not digital_only:
                send_mode = "physical"
                auto_mode = False
            else:
                send_mode = False

        # missing address
        if send_mode in ["physical", "both"] and not (partner.zip or partner.city):
            if send_mode == "both" and not removed_digital:
                send_mode = "digital"
            else:
                send_mode = False

        return send_mode, auto_mode
