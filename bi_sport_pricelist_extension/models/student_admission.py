import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class StudentAdmission(models.Model):
    _inherit = 'student.admission'

    pricelist_id = fields.Many2one('product.pricelist', string='جهة الانتماء', required=True)

    def action_make_student(self):
        for admission in self:
            _logger.debug("Processing action_make_student for admission %s", admission.name)
            if not admission.is_invoiced:
                return {
                    'name': 'Create Invoice',
                    'view_mode': 'form',
                    'res_model': 'create.invoice',
                    'type': 'ir.actions.act_window',
                    'context': {
                        'default_pricelist_id': admission.pricelist_id.id,
                        **self._context
                    },
                    'target': 'new',
                }
            # Update student account
            if admission.student_id:
                admission.student_id.update({
                    'is_student': True,
                    'sport_id': [(6, 0, admission.activity_ids.ids)] if admission.activity_ids else [(5, 0, 0)],
                    'trainer_id': admission.trainer_id.id if admission.trainer_id else False,
                })
            # Create or link parent account
            if admission.p_name and admission.parent_mobile:
                parent = self.env['res.partner'].sudo().search([
                    ('mobile', '=', admission.parent_mobile),
                    ('is_parent', '=', True)
                ], limit=1)
                if not parent:
                    parent_vals = {
                        'name': admission.p_name,
                        'mobile': admission.parent_mobile,
                        'email': admission.email,
                        'is_parent': True,
                    }
                    parent = self.env['res.partner'].sudo().create(parent_vals)
                admission.parent_id = parent
                admission.student_id.parent_id = parent
            admission.state = 'student'
        return True
