from odoo import models, fields

class StudentAdmissionTag(models.Model):
    _name = 'student.admission.tag'
    _description = 'Student Admission Tag'

    name = fields.Char('Tag Name', required=True, translate=True) 