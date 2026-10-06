from odoo import fields, models


class BuildexNamedConfig(models.AbstractModel):
    _name = 'buildex.named.config'
    _description = 'Buildex Named Configuration'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The code must be unique.'),
    ]


class BuildexCustomerType(models.Model):
    _name = 'buildex.customer.type'
    _description = 'Buildex Customer Type'
    _inherit = 'buildex.named.config'


class BuildexSkillType(models.Model):
    _name = 'buildex.skill.type'
    _description = 'Buildex Skill Type'
    _inherit = 'buildex.named.config'


class BuildexOutlet(models.Model):
    _name = 'buildex.outlet'
    _description = 'Buildex Outlet'
    _inherit = 'buildex.named.config'


class BuildexAgeBracket(models.Model):
    _name = 'buildex.age.bracket'
    _description = 'Buildex Age Bracket'
    _inherit = 'buildex.named.config'


class BuildexAcquisitionSource(models.Model):
    _name = 'buildex.acquisition.source'
    _description = 'Buildex Acquisition Source'
    _inherit = 'buildex.named.config'


class BuildexNextNeed(models.Model):
    _name = 'buildex.next.need'
    _description = 'Buildex Next Need'
    _inherit = 'buildex.named.config'


class BuildexProjectType(models.Model):
    _name = 'buildex.project.type'
    _description = 'Buildex Project Type'
    _inherit = 'buildex.named.config'


class BuildexResidentialUse(models.Model):
    _name = 'buildex.residential.use'
    _description = 'Buildex Residential Use'
    _inherit = 'buildex.named.config'


class BuildexProjectStage(models.Model):
    _name = 'buildex.project.stage'
    _description = 'Buildex Project Stage'
    _inherit = 'buildex.named.config'


class BuildexBudgetRange(models.Model):
    _name = 'buildex.budget.range'
    _description = 'Buildex Budget Range'
    _inherit = 'buildex.named.config'


class BuildexDecisionMaker(models.Model):
    _name = 'buildex.decision.maker'
    _description = 'Buildex Material Decision Maker'
    _inherit = 'buildex.named.config'


class BuildexIntendedUse(models.Model):
    _name = 'buildex.intended.use'
    _description = 'Buildex Intended Use'
    _inherit = 'buildex.named.config'


class BuildexFollowupActivityType(models.Model):
    _name = 'buildex.followup.activity.type'
    _description = 'Buildex Follow-up Activity Type'
    _inherit = 'buildex.named.config'
