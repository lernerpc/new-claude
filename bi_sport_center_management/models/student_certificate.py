# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StudentCertificate(models.Model):
    _name = "student.certificate"
    _description = "Student Certificate"

    name = fields.Char('Name', required=True)
    appraisal = fields.Char('Appraisal', required=True)
    description = fields.Text("Description")
