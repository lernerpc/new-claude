from odoo import fields, models

class PartnerTag(models.Model):
    _name = 'partner.tag'
    _description = 'Partner Tags'

    name = fields.Char('Name', required=True)