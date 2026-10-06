from odoo import models, fields, api
import xlwt
import io
import base64

class PayrollDeductionReportWizard(models.TransientModel):
    _name = 'payroll.deduction.report.wizard'

    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    structure_id = fields.Many2one('hr.payroll.structure', string="Salary Structure", required=True)
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")

    def generate_payment_details_report(self):
        data_obj = self.env['hr.payslip']
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Payroll Salary Rules Report', cell_overwrite_ok=True)
        bold = xlwt.easyxf("font: bold on;")
        total_style = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour yellow;")

        # Company Information
        company_name = self.env.user.company_id.name or "Company Name"
        report_period = f"Report Period: {self.date_start} to {self.date_end}"
        num_employees = data_obj.search_count([
            ("date_from", '>=', self.date_start),
            ("date_to", '<=', self.date_end),
            ("state", 'in', ['paid', 'done']),
            ('struct_id', '=', self.structure_id.id)
        ])

        # Add rows for company name, report period, and employee count
        worksheet.write(0, 0, company_name, bold)
        worksheet.write(1, 0, report_period, bold)
        worksheet.write(2, 0, f"Number of Employees: {num_employees}", bold)

        r = 4  # Start writing the report from row 4

        # Get all distinct salary rule names for the selected structure
        salary_rules = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.structure_id.id)
        ])
        rule_names = [rule.name for rule in salary_rules]

        # Initialize a dictionary to keep track of totals for each rule
        totals = {name: 0.0 for name in rule_names}

        # Domain for payslip search
        domain = [
            ("date_from", '>=', self.date_start),
            ("date_to", '<=', self.date_end),
            ("state", 'in', ['paid', 'done']),
            ('struct_id', '=', self.structure_id.id)
        ]

        # Collect data for each employee and sum totals for each rule
        employee_data = []
        for record in data_obj.search(domain, order='employee_id asc'):
            rule_dict = {name: 0.0 for name in rule_names}
            for line in record.line_ids:
                if line.salary_rule_id.name in rule_dict:
                    rule_dict[line.salary_rule_id.name] += line.total
                    totals[line.salary_rule_id.name] += line.total  # Update the total for the rule

            employee_data.append({
                'employee_name': record.employee_id.name,
                'department': record.employee_id.department_id.name or "N/A",
                'contract_id': record.contract_id.id or '',
                'rule_values': rule_dict
            })

        # Filter out the rule names where the total is 0
        filtered_rule_names = [name for name in rule_names if totals[name] > 0]

        # Write the header with filtered rule names
        header = ["EMPLOYEE NAME", "DEPARTMENT", "PAYROLL NUMBER"] + filtered_rule_names
        c = 0
        for item in header:
            worksheet.write(r, c, item, bold)
            c += 1
        r += 1

        # Write the employee data with filtered columns
        for data in employee_data:
            worksheet.write(r, 0, data['employee_name'])
            worksheet.write(r, 1, data['department'])
            worksheet.write(r, 2, data['contract_id'])

            c = 3
            for name in filtered_rule_names:
                worksheet.write(r, c, data['rule_values'][name])
                c += 1

            r += 1

        # Write the totals for the filtered columns
        worksheet.write(r, 0, "TOTAL", total_style)
        worksheet.write(r, 1, "", total_style)  # Empty cell under "DEPARTMENT"
        worksheet.write(r, 2, "", total_style)  # Empty cell under "PAYROLL NUMBER"
        c = 3
        for name in filtered_rule_names:
            worksheet.write(r, c, totals[name], total_style)
            c += 1

        # Save and create the attachment
        buf = io.BytesIO()
        workbook.save(buf)
        buf.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': f'Payroll_Salary_Rules_Report_{fields.Date.today()}.xls',
            'type': 'binary',
            'datas': base64.b64encode(buf.getvalue()),
            'mimetype': 'application/vnd.ms-excel',
            'res_model': self._name,
            'res_id': self.id,
        })

        self.attachment_id = attachment.id

        # Return the file for download
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }



class PayrollSummaryReportWizard(models.TransientModel):
    _name = 'payroll.summary.report.wizard'

    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    structure_id = fields.Many2one('hr.payroll.structure', string="Salary Structure", required=True)
    def generate_pdf_report(self):
        data = {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'structure_id': self.structure_id.id,
            #'rule_data': self._get_salary_rules_data(),
        }
    
        # Call the report action with the correct report template
        return self.env.ref('payslip_reports.report_salary_summary_pdf').report_action(self, data=data)


    

