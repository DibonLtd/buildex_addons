# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields, api
from werkzeug.urls import url_join

import logging
_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    zkteco_webhook_url = fields.Char(string='Zkteco Attendance Url')

    @api.model
    def get_values(self):
        res = super().get_values()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        path = '/wk/zkteco/attendance' 
        full_url = base_url.rstrip('/') + path
        res.update({
            'zkteco_webhook_url': full_url,
        })
        return res
