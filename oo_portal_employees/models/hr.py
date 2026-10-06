# -*- coding: utf-8 -*-
import logging
from odoo import service, api, models, fields


_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'portal.mixin', 'mail.thread', 'mail.activity.mixin']

    def _get_report_base_filename(self):
        self.ensure_one()
        return f'{self.employee_id.name} - {self.name}'


class HrHoliday(models.Model):
    _inherit = 'hr.leave'

    access_token = fields.Char(string='Access Token')

    def _get_report_base_filename(self):
        self.ensure_one()
        return f'{self.employee_id.name} - {self.name}'

    def _get_template_with_type(self, notification_type):
        notification_map = {
            'create': 'oo_portal_employees.oo_leave_create_mail',
            'approve': 'oo_portal_employees.oo_leave_approve_mail',
            'refuse': 'oo_portal_employees.oo_leave_refuse_mail',
        }
        return notification_map[notification_type]

    def send_email(self, notification_type='create'):
        template = self.env.ref(self._get_template_with_type(notification_type))
        values = {
            'email_from': self.employee_id.user_id.partner_id.email,
            'email_to': self.employee_id.leave_manager_id.partner_id.email
        }
        template.send_mail(self.id,
                           force_send=True,
                           email_values=values,
                           email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature')

        _logger.info('Sent leave notification email')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.send_email()
        return res

    def action_approve(self):
        res = super().action_approve()
        for rec in self:
            rec.send_email(notification_type='approve')
        return res

    def action_refuse(self):
        res = super().action_refuse()
        for rec in self:
            rec.send_email(notification_type='refuse')
        return res


class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'
    

class AppraisalAskFeedback(models.TransientModel):
    _inherit = 'appraisal.ask.feedback'


    def _prepare_survey_anwers(self, employees):
        answers = self.env['survey.user_input']
        employees_info = employees.mapped(lambda employee: {
            'id': employee.id,
            'email': employee.work_email or employee.user_id.partner_id.email,
            'partner_id': employee.user_id.partner_id or employee.sudo().address_home_id
        })
        emails = [e['email'] for e in employees_info]
        partner_ids = [e['partner_id']['id'] for e in employees_info]

        existing_answers = self.env['survey.user_input'].search([
            '&', '&',
            ('survey_id', '=', self.survey_template_id.id),
            ('appraisal_id', '=', self.appraisal_id.id),
            '|',
            '&', ('partner_id', 'in', partner_ids), ('partner_id', '!=', False),
            '&', ('email', 'in', emails), ('email', '!=', False),
        ])
        employees_done = []
        if existing_answers:
            existing_answer_emails = existing_answers.filtered('email').mapped('email')
            existing_answer_partners_id = existing_answers.filtered('partner_id').mapped('partner_id')
            for employee_data in employees_info:
                if employee_data.get('email') in existing_answer_emails or employee_data.get('partner_id') in existing_answer_partners_id:
                    employees_done.append(employee_data)
            existing_answers = existing_answers.sorted(lambda answer: answer.create_date, reverse=True)
            for employee_done in employees_done:
                answers |= existing_answers\
                    .filtered(lambda a:
                        (a.partner_id and a.partner_id == employee_done.get('partner_id'))
                        or (a.email and a.email == employee_done.get('email'))
                    )[:1]

        for new_employee in employees_info:
            answers = self.survey_template_id.sudo()._create_answer(
                partner=new_employee['partner_id'], email=new_employee['email'], check_attempts=False, deadline=self.deadline)
        return answers