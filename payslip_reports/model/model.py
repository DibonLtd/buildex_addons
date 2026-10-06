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
    _name = 'report.payslip_reports.payslip_template_document'
    _description = 'Report'

    def _get_report_values(self, docids, data):
        try:
            if  data:
                _logger.info("Using context data: %s", data)
            employee_ids = data.get('employee_ids')
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            company = self.env.company
              # Collect all rows here
            all_data = []
            if employee_ids is not None:
                _logger.error("Processing employee records for IDs: %s", employee_ids)
                employees = self.env['hr.employee'].search([('id', 'in', employee_ids.ids)])
    
                for employee in employees:
                    p9_data = self.env["hr.payslip"].search(
                        [('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('employee_id', '=', employee.id), ('state', 'in', ['paid', 'done'])], order='date_from asc')
                    
                    for tremos in p9_data:
                        dating = datetime.strptime(str(tremos.date_from), '%Y-%m-%d')
                        values = [
                            sum(line.total for line in tremos.line_ids if line.category_id.code == 'BASIC') * 0.30,
                            20000,
                            sum(line.total for line in tremos.line_ids if line.category_id.code == 'DEDB4TAX')
                        ]
                        basic_pay = sum(line.total for line in tremos.line_ids if line.category_id.code == 'BASIC')
                        row = [
                            dating.strftime('%B'),
                            basic_pay,
                            0.00,
                            0.00,
                            sum(line.total for line in tremos.line_ids if line.category_id.code == 'GROSS'),
                            round((basic_pay * 0.30), 4),
                            sum(line.total for line in tremos.line_ids if line.category_id.code == 'DEDB4TAX'),
                            20000,
                            0.00,
                            min(values),
                            sum(line.total for line in tremos.line_ids if line.category_id.code == 'TXPAY'),
                            sum(line.total for line in tremos.line_ids if line.code == 'PAYEB4R') + 
                            sum(line.total for line in tremos.line_ids if line.code in ['PRLF', 'PERS_RELIEF']),
                            sum(line.total for line in tremos.line_ids if line.code in ['PRLF', 'PERS_RELIEF']),
                            sum(line.total for line in tremos.line_ids if line.code == 'PAYEB4R')
                        ]
                        all_data.append(row)
    
                # Calculate the sums for each column
                if all_data:
                    sums = [0] * len(all_data[0])
                    for row in all_data:
                        for i in range(1, len(row)):  # Start from 1 to skip the month name
                            sums[i] += row[i]
                    _logger.error("Sum of records: %s", sums)
                else:
                    sums = []
    
                return {
                    'doc_ids': docids,
                    'doc_model': 'hr.employee',
                    'docs': employees,
                    'company_id': company,
                    'date_from': date_from,
                    'date_to': date_to,
                    'data': all_data,
                    'sums': sums,
                }
            
        except Exception as e:
            _logger.exception("An error occurred while generating the report: %s", str(e))
            raise

        return  employee_ids or []

