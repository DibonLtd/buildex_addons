from odoo import models, fields, api

DEFAULT_TERMS = """
<ol>
  <li>All information provided is accurate and truthful.</li>
  <li>You will promote the company's products ethically and professionally.</li>
  <li>Commissions are paid upon verified and completed sales only.</li>
  <li>The company reserves the right to approve or reject any application.</li>
  <li>Your personal data will be used solely for programme administration.</li>
  <li>You must not engage in any misleading or fraudulent promotional activity.</li>
</ol>
"""


class InfluencerProgramConfig(models.Model):
    _name = 'influencer.program.config'
    _description = 'Influencer Programme Configuration'

    name = fields.Char(default='Influencer Programme Terms', required=True)
    terms_html = fields.Html(string="Terms & Conditions", sanitize=False, default=DEFAULT_TERMS)

    @api.model
    def get_terms(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Influencer Programme Terms'})
        return config.terms_html or DEFAULT_TERMS
