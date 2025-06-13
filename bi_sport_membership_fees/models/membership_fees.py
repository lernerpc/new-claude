from odoo import models, fields, api

class MembershipFees(models.Model):
    _name = 'sport.membership.fees'
    _description = 'Membership Extra Fees'
    _order = 'sequence_id asc'

    name = fields.Char(string="Fee Name", required=True)
    sequence_id = fields.Integer(string="Sequence ID", readonly=True, copy=False)
    product_ids = fields.Many2many('product.product', string="Products")
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    @api.model
    def create(self, vals):
        if not vals.get('sequence_id'):
            vals['sequence_id'] = self.env['ir.sequence'].next_by_code('sport.membership.fees') or 1
        return super(MembershipFees, self).create(vals)
