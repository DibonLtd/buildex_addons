from odoo import fields, models, tools


class InfluencerLinkPerformanceReport(models.Model):
    _name = "influencer.link.performance.report"
    _description = "Influencer Link Performance Report"
    _auto = False
    _order = "visit_count desc, order_count desc"

    partner_id = fields.Many2one("res.partner", string="Influencer", readonly=True)
    referral_code = fields.Char(string="Referral Code", readonly=True)
    referral_url = fields.Char(
        string="Referral Link",
        related="partner_id.referral_url",
        readonly=True,
    )
    visit_count = fields.Integer(string="Visits", readonly=True)
    order_count = fields.Integer(string="Converted Orders", readonly=True)
    conversion_rate = fields.Float(
        string="Conversion Rate (%)",
        readonly=True,
        digits=(16, 2),
        group_operator="avg",
    )

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS
            SELECT
                p.id AS id,
                p.id AS partner_id,
                p.referral_code AS referral_code,
                COALESCE(v.visit_count, 0)::int AS visit_count,
                COALESCE(o.order_count, 0)::int AS order_count,
                CASE
                    WHEN COALESCE(v.visit_count, 0) > 0 THEN
                        ROUND((COALESCE(o.order_count, 0)::numeric / v.visit_count::numeric) * 100, 2)
                    ELSE 0
                END AS conversion_rate
            FROM res_partner p
            LEFT JOIN (
                SELECT
                    partner_id,
                    SUM(visit_count) AS visit_count
                FROM influencer_referral_visit_stat
                GROUP BY partner_id
            ) v
                ON v.partner_id = p.id
            LEFT JOIN (
                SELECT
                    referral_partner_id AS partner_id,
                    COUNT(*) AS order_count
                FROM sale_order
                WHERE referral_partner_id IS NOT NULL
                  AND state IN ('sale', 'done')
                GROUP BY referral_partner_id
            ) o
                ON o.partner_id = p.id
            WHERE p.is_referrer = TRUE
              AND p.referral_code IS NOT NULL
            """
        )
