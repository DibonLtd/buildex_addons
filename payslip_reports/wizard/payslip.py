# -*- coding: utf-8 -*-
import json
import requests

from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from datetime import date, datetime, timedelta
import pytz
import os
import xlsxwriter
import base64
from odoo.tools import config
import logging
_logger = logging.getLogger(__name__)
from PyPDF2 import PdfFileReader, PdfFileWriter
import io
from PyPDF2 import PdfFileReader, PdfFileWriter



class Withholding(models.TransientModel):
    _name = "payslip.wizard"
    _description = "Payslip Wizard"

    employee_ids = fields.Many2many('hr.employee', string='Employees')
    select_all = fields.Boolean(string='Select All Employees')
    date_from = fields.Date(string="Date From", default=datetime.today())
    date_to = fields.Date(string="Date To", default=datetime.today())
    file = fields.Binary('Download Report')
    name = fields.Char()
    @api.onchange('select_all')
    def _onchange_select_all(self):
        if self.select_all:
            self.employee_ids = self.env['hr.employee'].search([])
        else:
            self.employee_ids = [(5, 0, 0)]
    def action_print_report(self):
        for employee in self.employee_ids:
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            data = {
                'employee_ids': employee,  # Adjust to a list of single employee ID
                'date_from': self.date_from,
                'date_to': self.date_to
            }
            
            # Generate the PDF report
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf('payslip_reports.employee_payslip_report', employee.id)
            
            # Log PDF content before encryption
            self.env['ir.attachment'].sudo().create({
                'name': 'PDF Content before encryption',
                'type': 'binary',
                'datas': pdf_content,
                'res_model': 'your.model',
                'res_id': self.id,
            })
            
            # Encrypt the PDF content
            password = employee.identification_id or '1234' # Assuming the password is the employee's identification ID
            encrypted_pdf_content = self.encrypt_pdf_content(pdf_content, password)
            data_record = base64.b64encode(encrypted_pdf_content)
            
            # Log encrypted PDF content
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f'P9_{employee.name}.pdf',
                'type': 'binary',
                'datas': data_record,
                'store_fname': f'P9_{employee.name}.pdf',
                'mimetype': 'application/pdf',
                'res_model': 'payslip.wizard',
                'res_id': self.id,
            })

            # Base64 encode the encrypted PDF content for binary field
            
            download_url = '/web/content/' + str(attachment_id.id) + '?download=true'

            # Return the action to download the encrypted PDF
            return {
                'type': 'ir.actions.act_url',
                "url": str(base_url) + str(download_url),
                'target': 'new',
            }
        
        
       
    def _get_report_base_filename(self):
        report_name = "KAMAU Payslip"
        
        return report_name
    def encrypt_pdf_content(self,pdf_content, password):
        reader = PdfFileReader(io.BytesIO(pdf_content))
        writer = PdfFileWriter()
    
        for page_num in range(reader.getNumPages()):
            writer.addPage(reader.getPage(page_num))
    
        writer.encrypt(user_pwd=password, owner_pwd=None, use_128bit=True)
    
        encrypted_pdf_stream = io.BytesIO()
        writer.write(encrypted_pdf_stream)
        encrypted_pdf_stream.seek(0)

        return encrypted_pdf_stream.read()
    def action_send_email(self):
        if not self.employee_ids:
            raise UserError("Please select at least one employee.")
        
        # List to keep track of processed employees
        processed_employees = []
    
        # Loop through each employee and generate the report
        employees = self.env['hr.employee'].browse(self.employee_ids.ids)
        for employee in employees:
        
            data = {
                'employee_ids': employee,
                'date_from': self.date_from,
                'date_to': self.date_to
            }
            _logger.info("Using context data: %s", data)
            if employee.ids:
                payslip_report = self.env.ref('payslip_reports.employee_payslip_report')
    
                pdf_content, _ = payslip_report._render_qweb_pdf(payslip_report.id, data=data)
                password = employee.identification_id  # Assuming the password is the employee's identification ID
                encrypted_pdf_content = self.encrypt_pdf_content(pdf_content, password)
                data_record = base64.b64encode(encrypted_pdf_content)
    
                # Create the attachment
                attachment = self.env['ir.attachment'].create({
                    'name': f'P9_{employee.name}.pdf',
                    'type': 'binary',
                    'datas': data_record,
                    'store_fname': f'Payslip_{employee.name}.pdf',
                    'mimetype': 'application/pdf',
                    'res_model': 'payslip.wizard',
                    'res_id': self.id,
                })
    
                # Check if the attachment was created successfully
                if not attachment:
                    raise UserError('Failed to create attachment for the payslip.')
    
                email_template = self.env.ref('payslip_reports.email_template_payslip_report')
                if not email_template:
                    raise UserError('Email template not found.')
    
                # Get the partner's email or use a default email
                email = employee.work_email
    
                # Send the email with the attachment
                if email:
                    email_template.attachment_ids = [(4, attachment.id)]
                    email_values = {
                        'email_to': email,
                        'email_cc': False,
                        'scheduled_date': False,
                        'recipient_ids': [],
                        'partner_ids':[],
                        'auto_delete': True,
                    }
                    email_template.with_context(partner=employee.name, date_from=self.date_from,
                                                date_to=self.date_to).send_mail(self.id, email_values=email_values,
                                                                               force_send=True)
              
                    email_template.attachment_ids = [(5, 0, 0)]
        return True

    
                
               
        
