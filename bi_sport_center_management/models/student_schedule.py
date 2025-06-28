# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StudentSchedule(models.Model):
    _name = 'student.schedule'
    _description = 'Student Sport Schedule Selection'

    admission_id = fields.Many2one('student.admission', string='Admission', required=True, ondelete='cascade')
    sport_id = fields.Many2one('product.product', string='Sport', required=True)
    schedule_id = fields.Many2one('sport.schedule', string='Selected Schedule', required=True)
    day_of_week_ids = fields.Many2many('sport.schedule.day', 'student_schedule_day_rel', 'student_id', 'day_id', related='schedule_id.day_of_week_ids', store=True, readonly=True)
    start_time = fields.Float(related='schedule_id.start_time', store=True, readonly=True)
    end_time = fields.Float(related='schedule_id.end_time', store=True, readonly=True)

    @api.constrains('admission_id', 'schedule_id')
    def _check_schedule_conflicts(self):
        for rec in self:
            if not rec.admission_id or not rec.schedule_id:
                continue
            # Find other schedules for this admission on the same days
            for day in rec.day_of_week_ids:
                conflicts = self.search([
                    ('admission_id', '=', rec.admission_id.id),
                    ('id', '!=', rec.id),
                    ('day_of_week_ids', 'in', [day.id]),
                    '|',
                    '&', ('start_time', '<', rec.end_time), ('end_time', '>', rec.start_time),
                    '&', ('start_time', '<', rec.start_time), ('end_time', '>', rec.start_time)
                ])
                if conflicts:
                    raise ValidationError('Schedule conflict detected: The student already has a schedule that overlaps with this time slot on one of the selected days.')

# Extend student.admission
class StudentAdmission(models.Model):
    _inherit = 'student.admission'
    schedule_details = fields.One2many('student.schedule', 'admission_id', string='Schedule Details')
