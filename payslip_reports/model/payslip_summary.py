# -*- coding: utf-8 -*-
import base64
import io
from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import UserError
import xlwt
import logging

today = date.today()

_logger = logging.getLogger(__name__)

class PayslipReport(models.AbstractModel):
    _name = 'report.payslip_reports.report_salary_summary'
    _description = 'Report'
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    def _get_report_values(self, docids, data):
        date_from = data.get('date_start')
        date_to = data.get('date_end')
        structure_id = data.get('structure_id')

        # Fetch payslips within the selected period and structure
        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('struct_id', '=', structure_id)
        ])
        
        rule_data = {}
        category_totals = {}
        for slip in payslips:
            for line in slip.line_ids:
                category = line.salary_rule_id.category_id.name
                rule_name = line.salary_rule_id.name
                structure_name = slip.struct_id.name

                if category not in rule_data:
                    rule_data[category] = {}
                    category_totals[category] = 0

                if rule_name not in rule_data[category]:
                    rule_data[category][rule_name] = 0

                rule_data[category][rule_name] += line.total
                category_totals[category] += line.total
        
        # Log the rule data and category totals
        _logger.info(f"Rule Data: {rule_data}")
        _logger.info(f"Category Totals: {category_totals}")
        
        # Return the report values including the original data passed in
        return {
            'doc_ids': docids,
            'docs': payslips,
            'doc_model': 'hr.payslip',
            'date_start': date_from,
            'date_end': date_to,
            'structure_name': structure_name,
            'rule_data': rule_data,
            'category_totals': category_totals,
            'company_id': self.company_id,
        }
