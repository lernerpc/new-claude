from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class StudentAdmission(models.Model):
    _inherit = 'student.admission'

    parent_id = fields.Many2one('res.partner', string="Parent", help="Parent account for this admission")
    is_guardian = fields.Boolean('هل ولي الأمر مرافق ', default=False, store=True)
    is_parking = fields.Boolean('هل يحتاج إلى موقف سيارة؟', default=False, store=True)
    parent_image_1920 = fields.Binary("Parent Photo")

    @api.constrains('parent_id')
    def _check_parent_fields(self):
        for record in self:
            if record.parent_id and record.parent_id.is_parent:
                record.parent_id.write({
                    'is_guardian': record.is_guardian,
                    'is_parking': record.is_parking,
                })

    def action_make_student(self):
        for admission in self:
            if not admission.is_invoiced:
                return {
                    'name': 'Create Invoice',
                    'view_mode': 'form',
                    'res_model': 'create.invoice',
                    'type': 'ir.actions.act_window',
                    'context': self._context,
                    'target': 'new',
                }

            # Create or update parent based on national ID
            parent = None
            if admission.p_name and admission.parent_mobile:
                if admission.parent_national_id:
                    parent = self.env['res.partner'].search([
                        ('parent_national_id', '=', admission.parent_national_id),
                        ('is_parent', '=', True)
                    ], limit=1)
                if not parent:
                    parent = self.env['res.partner'].search([
                        ('mobile', '=', admission.parent_mobile),
                        ('is_parent', '=', True)
                    ], limit=1)

                parent_vals = {
                    'name': admission.p_name,
                    'mobile': admission.parent_mobile,
                    'email': admission.email,
                    'is_parent': True,
                    'is_guardian': admission.is_guardian,
                    'is_parking': admission.is_parking,
                    'parent_national_id': admission.parent_national_id,
                }
                if admission.parent_image_1920:
                    parent_vals['parent_image_1920'] = admission.parent_image_1920
                    parent_vals['image_1920'] = admission.parent_image_1920  # sync to avatar

                if parent:
                    parent.write(parent_vals)
                else:
                    parent = self.env['res.partner'].create(parent_vals)

                admission.parent_id = parent.id

            # Update student partner
            if admission.student_id:
                student_vals = {
                    'is_student': True,
                    'sport_id': [(6, 0, admission.activity_ids.ids)] if admission.activity_ids else [(5, 0, 0)],
                    'trainer_id': admission.trainer_id.id if admission.trainer_id else False,
                    'parent_id': admission.parent_id.id if admission.parent_id else False,
                    'is_guardian': admission.is_guardian,
                    'is_parking': admission.is_parking,
                }
                if hasattr(admission, 'student_photo') and admission.student_photo:
                    student_vals['image_1920'] = admission.student_photo

                admission.student_id.write(student_vals)

            admission.write({'state': 'student'})
        return True
