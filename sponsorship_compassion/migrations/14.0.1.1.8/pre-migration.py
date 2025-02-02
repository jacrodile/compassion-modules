import logging
from openupgradelib import openupgrade
from odoo.addons.message_center_compassion.tools.onramp_connector import OnrampConnector

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, [('recurring.contract', 'recurring_contract', 'global_id', 'gmc_commitment_id')])
