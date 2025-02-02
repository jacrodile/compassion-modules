##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Quentin Gigon <gigon.quentin@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging
from datetime import date

from odoo import fields
from odoo.addons.sponsorship_compassion.tests.test_sponsorship_compassion import (
    BaseSponsorshipTest,
)

logger = logging.getLogger(__name__)


class TestGifts(BaseSponsorshipTest):
    def setUp(cls):
        super(TestGifts, cls).setUp()
        child = cls.create_child("AB123456789")
        sp_group = cls.create_group({"partner_id": cls.thomas.id})

        cls.sponsorship = cls.create_contract(
            {
                "partner_id": cls.thomas.id,
                "group_id": sp_group.id,
                "child_id": child.id,
                "correspondent_id": sp_group.partner_id.id,
            },
            [{"amount": 50.0}],
        )

    def test_normal_case(self):
        """ create a gift and verify it's correct """
        gift = self._create_birthday_gift()

        # test gift eligibility based on amount
        self.assertTrue(gift.is_eligible()[0])
        gift.write({"amount": 200})
        self.assertFalse(gift.is_eligible()[0])

        # tests for gift types changes
        product = self.env.ref(
            "sponsorship_compassion.product_template_gift_birthday").product_variant_id
        self.assertEqual(
            gift.get_gift_types(product),
            {
                "gift_type": "Beneficiary Gift",
                "attribution": "Sponsorship",
                "sponsorship_gift_type": "Birthday",
            },
        )

        product.write({"name": "General Gift", "default_code": "gift_gen"})
        self.assertEqual(
            gift.get_gift_types(product),
            {
                "gift_type": "Beneficiary Gift",
                "attribution": "Sponsorship",
                "sponsorship_gift_type": "General",
            },
        )

        product.write({"name": "Family Gift", "default_code": "gift_family"})
        self.assertEqual(
            gift.get_gift_types(product),
            {"gift_type": "Family Gift", "attribution": "Sponsored Child Family", },
        )

        # test for on_connect
        self.assertEqual(gift.state, "draft")
        gift.on_send_to_connect()
        self.assertEqual(gift.state, "open")

    def test_gift_creation_with_account_invoice_line(self):
        """ Data creation """
        product = self.env.ref(
            "sponsorship_compassion.product_template_gift_birthday").product_variant_id

        sponsorship = self.sponsorship

        account = self.env["account.account"].create(
            {
                "name": "test_account",
                "code": "0D",
                "user_type_id": self.env.ref("account.data_account_type_liquidity").id,
            }
        )

        self.thomas.write(
            {
                "property_account_receivable_id": account.id,
                "property_account_payable_id": account.id,
            }
        )

        journal = self.env["account.journal"].create(
            {"name": "test_journal", "code": "test_code", "type": "sale"}
        )

        acc_inv_line = self.env["account.move.line"].create(
            {
                "contract_id": sponsorship.id,
                "product_id": product.id,
                "state": "draft",
                "price_unit": 50.0,
                "account_id": account.id,
                "name": "test",
            }
        )

        today = date.today()
        account_invoice = self.env["account.move"].create(
            {
                "name": "test_account_invoice",
                "invoice_date": "%s-07-01" % str(today.year),
                "move_type": "out_invoice",
                "state": "draft",
                "account_id": account.id,
                "journal_id": journal.id,
                "partner_id": self.thomas.id,
                "invoice_line_ids": [(4, acc_inv_line.id)],
            }
        )

        # Tests

        # before gift creation
        gift = self.env["sponsorship.gift"].search(
            [("sponsorship_id", "=", sponsorship.id)]
        )
        self.assertFalse(gift)

        account_invoice.action_post()

        # after gift creation
        gift = self.env["sponsorship.gift"].search(
            [("sponsorship_id", "=", sponsorship.id)]
        )
        self.assertTrue(gift)
        self.assertTrue(gift.is_eligible()[0])

        # gift information
        self.assertEqual(gift.name, "Birthday Gift [" + gift.sponsorship_id.name + "]")
        # it's a birthday gift, so due_date is 2 month before the birthday
        self.assertEqual(fields.Date.to_string(gift.gift_date),
                         "%s-11-28" % str(today.year))
        self.assertEqual(gift.amount, 50)
        self.assertEqual(gift.gift_type, "Beneficiary Gift")
        self.assertEqual(gift.state, "verify")

        sponsorship.contract_active()

        self.assertEqual(gift.state, "draft")

        # test create from invoice line function
        self.env["sponsorship.gift"].create_from_invoice_line(acc_inv_line)
        self.assertEqual(gift.message_id.state, "new")

        acc_inv_line.write({"price_unit": 200})
        self.env["sponsorship.gift"].create_from_invoice_line(acc_inv_line)
        self.assertEqual(gift.message_id.state, "postponed")
        self.assertEqual(gift.state, "verify")

    def test_multiple_birthday_gifts_aggregation(self):
        gift1 = self._create_birthday_gift(50)
        gift2 = self._create_birthday_gift(80)

        self.assertEqual(gift1, gift2)
        self.assertEqual(gift2.amount, 130)
        self.assertEqual(gift2.instructions.count("Take these"), 2)

    def _create_birthday_gift(self, amount=50):
        return self.env["sponsorship.gift"].create(
            {
                "gift_date": "2018-08-08",
                "sponsorship_id": self.sponsorship.id,
                "gift_type": "Beneficiary Gift",
                "attribution": "Sponsorship",
                "sponsorship_gift_type": "Birthday",
                "instructions": "Take these ${}".format(amount),
                "amount": amount,
            }
        )
