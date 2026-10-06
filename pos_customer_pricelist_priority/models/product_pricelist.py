from odoo import models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def _extract_pricelist_id(self, value):
        if not value:
            return False
        if isinstance(value, int):
            return value
        if isinstance(value, (list, tuple)):
            return value[0] if value else False
        if isinstance(value, dict):
            return value.get('id')
        return False

    def _get_recursive_base_pricelist_ids(self, pricelist_ids):
        seen_ids = set(pricelist_ids)
        pending_ids = set(pricelist_ids)

        while pending_ids:
            base_pricelist_ids = set(
                self.env['product.pricelist.item'].search([
                    ('pricelist_id', 'in', list(pending_ids)),
                    ('base', '=', 'pricelist'),
                    ('base_pricelist_id', '!=', False),
                ]).mapped('base_pricelist_id').ids
            )
            pending_ids = base_pricelist_ids - seen_ids
            seen_ids |= base_pricelist_ids

        return seen_ids

    def _load_pos_data(self, data):
        result = super()._load_pos_data(data)
        fields = result.get('fields', self._load_pos_data_fields(data['pos.config']['data'][0]['id']))
        loaded_pricelist_ids = {pricelist['id'] for pricelist in result.get('data', [])}
        partner_pricelist_ids = {
            self._extract_pricelist_id(partner.get('property_product_pricelist'))
            for partner in data.get('res.partner', {}).get('data', [])
        }
        partner_pricelist_ids.discard(False)

        required_pricelist_ids = self._get_recursive_base_pricelist_ids(partner_pricelist_ids)
        missing_pricelist_ids = list(required_pricelist_ids - loaded_pricelist_ids)

        if missing_pricelist_ids:
            extra_pricelists = self.search_read([('id', 'in', missing_pricelist_ids)], fields, load=False)
            result['data'].extend(extra_pricelists)

        return result
