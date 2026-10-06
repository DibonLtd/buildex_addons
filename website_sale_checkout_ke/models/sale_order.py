from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Payment preference chosen at checkout
    payment_preference = fields.Selection(
        string='Payment Preference',
        selection=[('pay_now', 'Pay on Order'), ('pay_after_delivery', 'Pay on Delivery')],
        default='pay_now',
    )

    bank_till_payment_reference = fields.Char(
        string='Payment Reference',
        help='M-PESA / Equity confirmation code provided by the customer at checkout.',
        copy=False,
        readonly=True,
    )

    # Installation technician information (optional, collected at checkout)
    technician_name = fields.Char(string='Technician Name')
    technician_contact = fields.Char(string='Technician Contact')
    technician_location = fields.Char(string='Technician Location')
    technician_specs = fields.Text(string='Installation Specifications')

    delivery_town_id = fields.Many2one(
        'res.country.state',
        string='Delivery Town',
        related='partner_shipping_id.state_id',
        store=True,
        readonly=True,
        index=True,
    )
    user_team_town_match = fields.Boolean(
        string="My Team Town Order",
        compute="_compute_user_team_town_match",
        search="_search_user_team_town_match",
    )

    def _get_user_team_town_domain(self):
        teams = self.env["crm.team.member"].sudo().search([
            ("user_id", "=", self.env.user.id),
            ("active", "=", True),
        ]).mapped("crm_team_id")
        town_ids = teams.mapped("delivery_town_ids").ids
        if not teams or not town_ids:
            return [("id", "=", 0)]
        return [("team_id", "in", teams.ids), ("delivery_town_id", "in", town_ids)]

    def _compute_user_team_town_match(self):
        if not self:
            return
        matching_ids = set(self.search(self._get_user_team_town_domain()).ids)
        for order in self:
            order.user_team_town_match = order.id in matching_ids

    def _search_user_team_town_match(self, operator, value):
        positive = self._get_user_team_town_domain()
        if operator in ("=", "==") and bool(value):
            return positive
        if operator in ("!=", "<>") and bool(value):
            return [("id", "not in", self.search(positive).ids)]
        return []

    def _assign_team_from_delivery_town(self):
        if self.env.context.get("skip_team_delivery_assign"):
            return
        Team = self.env["crm.team"].sudo()
        for order in self:
            town = order.delivery_town_id
            if not town:
                continue
            if order.team_id and town in order.team_id.delivery_town_ids:
                continue
            team = Team.search(
                [("delivery_town_ids", "in", town.id), ("active", "=", True)],
                order="sequence, id",
                limit=1,
            )
            if team:
                order.with_context(skip_team_delivery_assign=True).team_id = team.id

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._assign_team_from_delivery_town()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if "partner_shipping_id" in vals or "team_id" in vals:
            self._assign_team_from_delivery_town()
        return res
