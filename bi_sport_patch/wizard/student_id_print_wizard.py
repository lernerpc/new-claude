from odoo import models, fields, api, _

class StudentIdPrintWizard(models.TransientModel):
    _name = 'student.id.print.wizard'
    _description = 'Student ID Print Wizard'

    filter_printed = fields.Selection([
        ('all', 'All'),
        ('printed', 'Printed'),
        ('not_printed', 'Not Printed'),
    ], string='Filter', default='not_printed')

    student_ids = fields.Many2many(
        'student.admission',
        'student_id_print_wizard_rel',
        'wizard_id', 'student_id',
        string='Students',
        domain="[('id', 'in', active_ids)]")

    student_display_names = fields.Char(
        string="Student Names",
        compute="_compute_student_display_names",
        store=False
    )

    @api.depends('student_ids')
    def _compute_student_display_names(self):
        for wizard in self:
            names = []
            for student in wizard.student_ids:
                student_name = student.name or ''
                parent_name = student.p_name or ''
                if parent_name:
                    names.append(f"{student_name} - {parent_name}")
                else:
                    names.append(student_name)
            wizard.student_display_names = ', '.join(names)

    @api.onchange('filter_printed')
    def _onchange_filter_printed(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            self.student_ids = [(5, 0, 0)]
            return {'domain': {'student_ids': []}}

        domain = [('id', 'in', active_ids)]
        if self.filter_printed == 'printed':
            domain.append(('printed', '=', True))
        elif self.filter_printed == 'not_printed':
            domain.append(('printed', '=', False))

        students = self.env['student.admission'].search(domain)
        self.student_ids = [(6, 0, students.ids)]
        return {'domain': {'student_ids': domain}}

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            # Apply default filter (not_printed) to active_ids
            students = self.env['student.admission'].search([
                ('id', 'in', active_ids),
                ('printed', '=', False)
            ])
            res['student_ids'] = [(6, 0, students.ids)]
        res['filter_printed'] = 'not_printed'
        return res

    def action_print_ids(self):
        # Ensure the 'Printed' tag exists
        tag = self.env['student.admission.tag'].search([('name', '=', 'Printed')], limit=1)
        if not tag:
            tag = self.env['student.admission.tag'].create({'name': 'Printed'})

        # Mark students as printed and add the Printed tag
        current_time = fields.Datetime.now()
        for student in self.student_ids:
            vals = {
                'printed': True,
                'tag_ids': [(4, tag.id)],
                'last_print_date': current_time
            }
            
            # Set first print date only if it hasn't been set before
            if not student.first_print_date:
                vals['first_print_date'] = current_time
                
            student.write(vals)

        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/bi_sport_patch.report_student_id_card/%s?auto_print=1' % ','.join(map(str, self.student_ids.ids)),
            'target': 'new',
        }

    def action_preview_ids(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/bi_sport_patch.report_student_id_card/%s' % ','.join(map(str, self.student_ids.ids)),
            'target': 'new',
        }