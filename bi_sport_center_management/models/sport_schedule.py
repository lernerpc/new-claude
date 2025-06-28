# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SportSchedule(models.Model):
    _name = 'sport.schedule'
    _description = 'Sport Weekly Schedule'
    _rec_name = 'display_name'

    sport_id = fields.Many2one('product.product', string='Sport Activity', required=True, domain=[('is_sportname', '=', True)])
    day_of_week_ids = fields.Many2many(
        'sport.schedule.day',
        'sport_schedule_day_rel',
        'schedule_id',
        'day_id',
        string='Days of Week',
        required=True
    )
    start_time = fields.Float('Start Time', required=True, help="Time in 24-hour format (e.g., 14.5 for 2:30 PM)")
    end_time = fields.Float('End Time', required=True, help="Time in 24-hour format (e.g., 16.0 for 4:00 PM)")
    capacity = fields.Integer('Maximum Capacity', default=20, required=True)
    available_spots = fields.Integer('Available Spots', compute='_compute_available_spots', store=True)
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    student_schedule_ids = fields.One2many('student.schedule', 'schedule_id', string='Student Schedules')
    enrolled_count = fields.Integer('Enrolled Students', compute='_compute_enrolled_count', store=True)

    @api.depends('sport_id', 'day_of_week_ids', 'start_time', 'end_time')
    def _compute_display_name(self):
        for record in self:
            if record.sport_id and record.day_of_week_ids:
                days = ', '.join([d.name for d in record.day_of_week_ids])
                start_time_str = self._float_to_time_string(record.start_time)
                end_time_str = self._float_to_time_string(record.end_time)
                record.display_name = f"{record.sport_id.name} - {days} ({start_time_str}-{end_time_str})"
            else:
                record.display_name = "New Schedule"

    @api.depends('student_schedule_ids')
    def _compute_enrolled_count(self):
        for record in self:
            record.enrolled_count = len(record.student_schedule_ids)

    @api.depends('capacity', 'enrolled_count')
    def _compute_available_spots(self):
        for record in self:
            record.available_spots = record.capacity - record.enrolled_count

    def _float_to_time_string(self, float_time):
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    @api.model
    def create_default_days(self):
        days = [
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
            ('sunday', 'Sunday'),
        ]
        for code, name in days:
            self.env['sport.schedule.day'].sudo().create({'name': name, 'code': code})

class ProductProduct(models.Model):
    _inherit = 'product.product'
    schedule_ids = fields.One2many('sport.schedule', 'sport_id', string='Schedules')

