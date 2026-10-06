from odoo import fields, models, tools


class BuildexProductDemandReport(models.Model):
    _name = 'buildex.product.demand.report'
    _description = 'Buildex Product Demand Insight'
    _auto = False
    _rec_name = 'product_id'
    _order = 'ordered_qty desc'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    project_id = fields.Many2one('buildex.project', string='Project', readonly=True)
    project_stage_id = fields.Many2one('buildex.project.stage', string='Project Stage', readonly=True)
    delivery_county = fields.Selection(selection=lambda self: self.env['res.partner']._fields['county'].selection, readonly=True)
    buildex_town = fields.Char(readonly=True)
    buildex_area = fields.Char(readonly=True)
    intended_use_id = fields.Many2one('buildex.intended.use', string='Intended Use', readonly=True)
    order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    order_date = fields.Datetime(readonly=True)
    ordered_qty = fields.Float(readonly=True)
    subtotal = fields.Monetary(currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)

    def init(self):
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'sale_order'
              AND column_name IN ('buildex_project_id')
        """)
        sale_order_columns = {row[0] for row in self.env.cr.fetchall()}

        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'sale_order_line'
              AND column_name IN ('buildex_intended_use_id')
        """)
        sale_order_line_columns = {row[0] for row in self.env.cr.fetchall()}

        project_sql = (
            'so.buildex_project_id'
            if 'buildex_project_id' in sale_order_columns
            else 'NULL::integer'
        )
        intended_use_sql = (
            'sol.buildex_intended_use_id'
            if 'buildex_intended_use_id' in sale_order_line_columns
            else 'NULL::integer'
        )
        project_join_sql = (
            f'LEFT JOIN buildex_project bp ON bp.id = {project_sql}'
            if 'buildex_project_id' in sale_order_columns
            else 'LEFT JOIN buildex_project bp ON FALSE'
        )

        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    sol.id AS id,
                    sol.product_id AS product_id,
                    so.partner_id AS partner_id,
                    {project_sql} AS project_id,
                    bp.stage_id AS project_stage_id,
                    rp.county AS delivery_county,
                    rp.buildex_town AS buildex_town,
                    rp.buildex_area AS buildex_area,
                    {intended_use_sql} AS intended_use_id,
                    so.id AS order_id,
                    so.date_order AS order_date,
                    sol.product_uom_qty AS ordered_qty,
                    sol.price_subtotal AS subtotal,
                    so.currency_id AS currency_id
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                {project_join_sql}
                LEFT JOIN res_partner rp ON rp.id = so.partner_shipping_id
                WHERE sol.display_type IS NULL
            )
        """)
