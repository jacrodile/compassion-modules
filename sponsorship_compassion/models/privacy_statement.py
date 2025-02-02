##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Stephane Eicher <seicher@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import models, fields, api


class PrivacyStatement(models.Model):
    _name = "compassion.privacy.statement"
    _description = "Compassion Privacy Statement"
    _order = "date desc"
    _sql_constraints = [
        ("unique_privacy_statement", "unique(version)", 'This "Version" already exists')
    ]

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    name = fields.Char(compute="_compute_name")
    version = fields.Char()
    text = fields.Html(translate=True)
    date = fields.Date()

    @api.model
    def get_current(self):
        return self.env["compassion.privacy.statement"].search(
            [], order="date desc", limit=1
        )

    ##########################################################################
    #                             FIELDS METHODS                             #
    ##########################################################################
    @api.depends("version")
    def _compute_name(self):
        for rd in self:
            rd.name = rd.version


class PrivacyStatementAgreement(models.Model):
    _name = "privacy.statement.agreement"
    _description = "Privacy Statement Agreement"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    partner_id = fields.Many2one("res.partner", "Partner", readonly=False)
    agreement_date = fields.Date()
    privacy_statement_id = fields.Many2one(
        "compassion.privacy.statement", "Privacy statement", readonly=False
    )
    version = fields.Char(related="privacy_statement_id.version", readonly=True)
    origin_signature = fields.Selection(
        [
            ("new_letter", "Website new letter"),
            ("my_account", "Website My Account"),
            ("new_sponsorship", "Website new sponsorship"),
            ("new_gift", "Website new gift"),
            ("first_payment", "First payment"),
        ]
    )

    ##########################################################################
    #                             VIEW CALLBACKS                             #
    ##########################################################################
    def open_contract(self):
        """ Used to bypass opening a contract in popup mode from
        res_partner view. """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Contract",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "current",
        }
