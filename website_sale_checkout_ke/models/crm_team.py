from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    delivery_town_ids = fields.Many2many(
        "res.country.state",
        "crm_team_delivery_town_rel",
        "team_id",
        "state_id",
        string="Delivery Towns",
        domain="[('country_id.code', '=', 'KE')]",
        help="Orders delivered to these towns can be filtered/assigned to this team.",
    )
