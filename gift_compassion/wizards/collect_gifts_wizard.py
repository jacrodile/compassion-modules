﻿##############################################################################
#
#    Copyright (C) 2014 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class CollectGiftWizard(models.TransientModel):
    """ This wizard generates a Gift Invoice for a given contract. """

    _name = "gift.collect.wizard"
    _description = "Gift Collect Wizard"

    invoice_line_ids = fields.Many2many(
        "account.move.line", string="Invoice lines", readonly=False
    )
    domain = fields.Char(
        default=lambda s: s._get_domain()
    )

    @api.model
    def _get_domain(self):
        category = self.env.ref("sponsorship_compassion.product_category_gift")
        return str([
            ("product_id.categ_id", "=", category.id),
            ("payment_state", "=", "paid"),
            ("gift_id", "=", False)
        ])

    @api.onchange("domain")
    def apply_domain(self):
        return {"domain": {"invoice_line_ids": safe_eval(self.domain)}}

    def collect_invoices(self):
        # Read data in english
        self.ensure_one()
        gift = self.env["sponsorship.gift"].browse(self.env.context["active_id"])
        self.invoice_line_ids.write({"gift_id": gift.id})
        return gift.write(
            {"invoice_line_ids": [(4, id) for id in self.invoice_line_ids.ids]}
        )
