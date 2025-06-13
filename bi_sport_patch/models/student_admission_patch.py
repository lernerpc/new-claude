from odoo import models, fields

class StudentAdmission(models.Model):
    _inherit = 'student.admission'

    printed = fields.Boolean('Printed', default=False)
    tag_ids = fields.Many2many('student.admission.tag', 'student_admission_tag_rel', 'student_id', 'tag_id', string='Tags')
    first_print_date = fields.Datetime('First Print Date', readonly=True)
    last_print_date = fields.Datetime('Last Print Date', readonly=True)
    membership_number = fields.Char('رقم الاستمارة')

    _sql_constraints = [
        ('membership_number_unique', 'UNIQUE(membership_number)', 'Membership number must be unique.')
    ]


    def action_print_and_mark(self):
        # Ensure the 'Printed' tag exists
        tag = self.env['student.admission.tag'].search([('name', '=', 'Printed')], limit=1)
        if not tag:
            tag = self.env['student.admission.tag'].create({'name': 'Printed'})
        
        current_time = fields.Datetime.now()
        vals = {
            'printed': True,
            'tag_ids': [(4, tag.id)],
            'last_print_date': current_time
        }
        
        # Set first print date only if it hasn't been set before
        if not self.first_print_date:
            vals['first_print_date'] = current_time
            
        self.write(vals)
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/bi_sport_patch.report_student_id_card/%s' % ','.join(map(str, self.ids)),
            'target': 'new',
        }