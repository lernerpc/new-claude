from odoo import models, fields, api, _

class ParentIdPrintWizard(models.TransientModel):
    _name = 'parent.id.print.wizard'
    _description = 'Parent ID Print Wizard'

    filter_printed = fields.Selection([
        ('all', 'All'),
        ('printed', 'Printed'),
        ('not_printed', 'Not Printed'),
    ], string='Filter', default='not_printed')

    parent_ids = fields.Many2many(
        'res.partner',
        'parent_id_print_wizard_rel',
        'wizard_id',
        'parent_id',
        string='Parents',
        domain="[('is_parent', '=', True), ('id', 'in', active_ids)]"
    )

    parent_display_names = fields.Char(
        string="Parent Names",
        compute="_compute_parent_display_names",
        store=False
    )

    @api.depends('parent_ids')
    def _compute_parent_display_names(self):
        for wizard in self:
            names = [parent.name or '' for parent in wizard.parent_ids]
            wizard.parent_display_names = ', '.join(names)

    @api.onchange('filter_printed')
    def _onchange_filter_printed(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            self.parent_ids = [(5, 0, 0)]
            return {'domain': {'parent_ids': [('is_parent', '=', True)]}}

        domain = [('is_parent', '=', True), ('id', 'in', active_ids)]
        if self.filter_printed == 'printed':
            domain.append(('printed', '=', True))
        elif self.filter_printed == 'not_printed':
            domain.append(('printed', '=', False))

        parents = self.env['res.partner'].search(domain)
        self.parent_ids = [(6, 0, parents.ids)]
        return {'domain': {'parent_ids': domain}}

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            parents = self.env['res.partner'].search([
                ('is_parent', '=', True),
                ('id', 'in', active_ids),
                ('printed', '=', False)
            ])
            res['parent_ids'] = [(6, 0, parents.ids)]
        res['filter_printed'] = 'not_printed'
        return res

    def action_print_ids(self):
        tag = self.env['partner.tag'].search([('name', '=', 'Printed')], limit=1)
        if not tag:
            tag = self.env['partner.tag'].create({'name': 'Printed'})

        current_time = fields.Datetime.now()
        for parent in self.parent_ids:
            vals = {
                'printed': True,
                'tag_ids': [(4, tag.id)],
                'last_print_date': current_time,
            }
            if not parent.first_print_date:
                vals['first_print_date'] = current_time
            parent.write(vals)

        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/bi_sport_parent_management.parent_id_card_report/%s?auto_print=1'% ','.join(map(str, self.parent_ids.ids)),
            'target': 'new',
        }

    def action_preview_ids(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/bi_sport_parent_management.parent_id_card_report/%s'% ','.join(map(str, self.parent_ids.ids)),
            'target': 'new',
        }