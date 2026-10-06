from odoo import api, fields, models


class InfluencerReferralVisitStat(models.Model):
    _name = "influencer.referral.visit.stat"
    _description = "Influencer Referral Daily Visit Stats"
    _order = "date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        index=True,
        ondelete="cascade",
    )
    referral_code = fields.Char(
        related="partner_id.referral_code",
        store=True,
        index=True,
        readonly=True,
    )
    date = fields.Date(required=True, default=fields.Date.context_today, index=True)
    visit_count = fields.Integer(default=1)

    _sql_constraints = [
        (
            "uniq_partner_date_visit_stat",
            "unique(partner_id, date)",
            "A daily visit stat already exists for this influencer.",
        ),
    ]

    @api.model
    def log_visit(self, partner):
        if not partner:
            return False

        day = fields.Date.context_today(self)
        stat = self.search(
            [("partner_id", "=", partner.id), ("date", "=", day)],
            limit=1,
        )

        if stat:
            stat.visit_count += 1
            return stat

        return self.create(
            {
                "partner_id": partner.id,
                "date": day,
                "visit_count": 1,
            }
        )
