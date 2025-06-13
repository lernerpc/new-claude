# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CenterCertificate(models.Model):
    _name = "center.certificate"
    _description = "Sport Center Certificate"

    name = fields.Char('No', required=True,
                       readonly=True, default=lambda self: _('New'))
    user_name = fields.Char("Name")
    title = fields.Char('Title', required=True)
    user_id = fields.Many2one('res.users', string="Issued By", required=True, default=lambda self: self.env.user) 
    user_type = fields.Selection(
        string='User Type',
        selection=[('participant', 'Participant'), ('student', 'Student'), ('teacher', 'Teacher')]
    )
    description = fields.Text("Description")
    date = fields.Date('Date', default=fields.Date.today())
    content = fields.Html('Content')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'center.certificate') or _('New')
        return super(CenterCertificate, self).create(vals_list)
