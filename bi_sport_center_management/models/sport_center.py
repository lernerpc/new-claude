# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SportCenter(models.Model):
    _name = "sport.center"
    _description = "Sport Center"

    name = fields.Char(string="Name", required=True)

class SportName(models.Model):
    _name = "sport.name"
    _description = "Sport Name"

    name = fields.Char(string="Sport Name", required=True)
