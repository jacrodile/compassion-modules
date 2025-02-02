from odoo import models, fields, _


class LogOtherInteractionWizard(models.TransientModel):
    _name = "partner.log.other.interaction.wizard"
    _description = "Logging wizard for other interactions"

    partner_id = fields.Many2one(
        "res.partner", "Partner", default=lambda self: self.env.context.get("active_id")
    )
    subject = fields.Char(required=True)
    other_type = fields.Char(required=True)
    date = fields.Datetime(default=fields.Datetime.now)
    direction = fields.Selection(
        [("in", "Incoming"), ("out", "Outgoing")], required=True
    )
    body = fields.Html()

    def log_interaction(self):
        data = {
            "partner_id": self.partner_id.id,
            "subject": self.subject,
            "other_type": self.other_type,
            "direction": self.direction,
            "body": self.body,
            "date": self.date,
        }
        other_interaction = self.env["partner.log.other.interaction"].create(data)
        self.partner_id.message_post(body=_(
            "Your new interaction has been created! Click the link to access it: "
            f"<a href=# data-oe-model={other_interaction._name} data-oe-id={other_interaction.id}>"
            f"{other_interaction.subject + ' ' + other_interaction.other_type}</a>"
        ))

class OtherInteractions(models.Model):
    _name = "partner.log.other.interaction"
    _inherit = [
        "mail.activity.mixin",
        "mail.thread",
        "partner.log.other.interaction.wizard",
    ]
    _description = "Logging for other interactions"
    _rec_name = "subject"
    _transient = False
