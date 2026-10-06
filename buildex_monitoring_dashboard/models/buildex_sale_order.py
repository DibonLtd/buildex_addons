from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    buildex_project_id = fields.Many2one(
        'buildex.project',
        string='Buildex Project',
        tracking=True,
        index=True,
    )
    buildex_outlet_location_id = fields.Many2one(
        'buildex.outlet',
        string='Outlet Location',
        tracking=True,
    )
    buildex_fundi_id = fields.Many2one(
        'res.partner',
        string='Fundi / Installer',
        domain=[('is_fundi', '=', True)],
        tracking=True,
    )
    buildex_followup_ids = fields.One2many('buildex.followup', 'sale_order_id', string='Follow-ups')
    buildex_fundi_request_ids = fields.One2many(
        'buildex.fundi.request',
        'sale_order_id',
        string='Fundi Requests',
    )
    buildex_followup_count = fields.Integer(
        compute='_compute_buildex_monitoring',
        string='Follow-up Count',
    )
    buildex_last_activity_date = fields.Date(
        compute='_compute_buildex_monitoring',
        string='Last Activity',
    )

    @api.depends(
        'buildex_followup_ids.state',
        'buildex_followup_ids.due_date',
        'date_order',
    )
    def _compute_buildex_monitoring(self):
        for order in self:
            order.buildex_followup_count = len(order.buildex_followup_ids.filtered(
                lambda followup: followup.state not in ('done', 'cancelled')
            ))
            due_dates = [date for date in order.buildex_followup_ids.mapped('due_date') if date]
            order.buildex_last_activity_date = max(due_dates) if due_dates else (
                order.date_order.date() if order.date_order else False
            )

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    buildex_intended_use_id = fields.Many2one(
        'buildex.intended.use',
        string='Intended Use',
    )
