from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pos_shop_referral_qr = fields.Binary(
        related="partner_id.referral_qr",
        string="POS Shop Referral QR",
        readonly=True,
    )
    pos_shop_referral_url = fields.Char(
        related="partner_id.referral_url",
        string="POS Shop Referral URL",
        readonly=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_to_load = list(super()._load_pos_data_fields(config_id))
        for field_name in ("pos_shop_referral_qr", "pos_shop_referral_url"):
            if field_name not in fields_to_load:
                fields_to_load.append(field_name)
        return fields_to_load
