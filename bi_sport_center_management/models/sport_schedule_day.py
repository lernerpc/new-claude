# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SportScheduleDay(models.Model):
    _name = 'sport.schedule.day'
    _description = 'Sport Schedule Day'

    name = fields.Char('Day', required=True)
    code = fields.Char('Code', required=True)
    
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Day code must be unique'),
    ]
