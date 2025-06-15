# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_student = fields.Boolean('Student', readonly=True)
    is_coach = fields.Boolean('Coach', readonly=True)
    p_name = fields.Char('اسم ولي الأمر')
    parent_national_id = fields.Char('الرقم القومي لولي الأمر')
    student_national_id = fields.Char('الرقم القومي للطالب')
    short_name = fields.Char('Short Name')
    birth_date = fields.Date('تاريخ الميلاد')
    gender = fields.Selection([('male', 'ذكر'), ('female', 'أنثى')], string='الجنس')
    # affiliation = fields.Selection([
    #     ('college_children', 'أبناء الكلية'),
    #     ('national_institutes', 'أبناء معاهد قومية'),
    #     ('college_workers', 'أبناء عاملي الكلية'),
    #     ('outside_college', 'خارج الكلية')
    # ], string='جهة الإنتماء')
    # emergency_contact_name = fields.Char('اسم جهة الإتصال في حالة الطوارئ')
    # emergency_contact_phone = fields.Char('رقم هاتف جهة الإتصال في حالة الطوارئ')
    is_disability = fields.Boolean('هل يوجد أي إعاقة', default=False)
    disability_description = fields.Text('وصف الإعاقة')    
    trainer_id = fields.Many2one(string='Current Coach', comodel_name='res.partner', domain=[('is_coach', '=', True)])
    is_sport = fields.Boolean('Sport Product')
    sport_id = fields.Many2many(
        'product.product', string="Sport Name", domain=[('is_sportname', '=', True)])
    is_parent = fields.Boolean(string="Is Parent", help="Indicates if this partner is a parent")
    is_guardian = fields.Boolean(string="Is Guardian", help="Indicates if this parent is a guardian")
    academic_subtype = fields.Selection([
        ('7star', '7 ستار'),
        ('academic', 'أكاديمية')
    ], string='نوع العضوية الأكاديمية', help="نوع العضوية الأكاديمية المختارة") 
    is_parking = fields.Boolean(string="Has Parking", help="Indicates if this parent has parking privileges")
    child_ids = fields.One2many('res.partner', 'parent_id', string="Children", help="Student accounts linked to this parent")
    parent_id = fields.Many2one('res.partner', string="Parent", help="Parent account for this student")
    x_parent_image = fields.Binary(string="Parent Photo", help="Temporary storage for parent photo")


    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], string='Payment Status', compute='_compute_payment_state', store=True, readonly=True)

    invoice_ids = fields.One2many('account.move', compute='_compute_invoice_ids', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_ids', string='Invoice Count')

    # _sql_constraints = [
    #     ('student_national_id_unique', 'UNIQUE(student_national_id)', 'الرقم القومي للطالب يجب أن يكون فريدًا.'),
    #     ('parent_national_id_unique', 'UNIQUE(parent_national_id)', 'الرقم القومي لولي الأمر يجب أن يكون فريدًا.')
    # ]

    @api.depends('name', 'student_national_id')  # Changed dependency
    def _compute_invoice_ids(self):
        """Compute related invoices for the student"""
        for record in self:
            invoices = self.env['account.move']
        
            # Only compute for students
            if record.is_parent:
                # Primary method: Search by student_admission_id (for new invoices)
                invoices = self.env['account.move'].search([
                ('partner_id', '=', record.id),
                ('move_type', 'in', ['out_invoice', 'out_refund'])
                ])
            
                # Fallback method: Search by invoice_origin (for old invoices)
                if not invoices and record.name:
                    invoices = self.env['account.move'].search([
                    ('invoice_origin', '=', record.name),
                    ('move_type', 'in', ['out_invoice', 'out_refund'])
                   ])
        
            record.invoice_ids = invoices
            record.invoice_count = len(invoices)

    @api.depends('invoice_ids.payment_state')
    def _compute_payment_state(self):
        """Compute payment state based on related invoices"""
        for record in self:
            if not record.invoice_ids:
                record.payment_state = 'not_paid'
            else:
                # Get the latest invoice payment state
                latest_invoice = record.invoice_ids.filtered(lambda inv: inv.state == 'posted').sorted('invoice_date', reverse=True)
                if latest_invoice:
                    record.payment_state = latest_invoice[0].payment_state
                else:
                    record.payment_state = 'not_paid'




    @api.constrains('student_national_id', 'parent_national_id', 'mobile', 'phone')
    def _check_national_id_and_mobile(self):
        for record in self:
            # Validate student_national_id
            if record.student_national_id and (not record.student_national_id.isdigit() or len(record.student_national_id) != 14):
                raise ValidationError(_('الرقم القومي للطالب يجب أن يكون 14 رقمًا.'))
            # Validate parent_national_id
            if record.parent_national_id and (not record.parent_national_id.isdigit() or len(record.parent_national_id) != 14):
                raise ValidationError(_('الرقم القومي لولي الأمر يجب أن يكون 14 رقمًا.'))
            # Validate mobile
            if record.mobile and (not record.mobile.startswith('0') or not record.mobile.isdigit() or len(record.mobile) != 11):
                raise ValidationError(_('رقم الجوال يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'))
            # Validate phone (parent_mobile)
            if record.phone and (not record.phone.startswith('0') or not record.phone.isdigit() or len(record.phone) != 11):
                raise ValidationError(_('رقم جوال ولي الأمر يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'))

    @api.model
    def get_data(self):
        students = self.search([('is_student', '=', True)])
        trainers = self.search([('is_coach', '=', True)])
        inquiries = self.env['student.inquiry'].search([('state', '=', 'new')])
        admissions = self.env['student.admission'].search([])
        enroll_admissions = self.env['student.admission'].search([('state', '=', 'enrolled')])
        bookings = self.env['center.booking'].search([])
        center_spaces = self.env['product.product'].search([('is_space', '=', True)])
        center_event = self.env['event.event'].search([])
        total_sports = self.env['res.partner'].search([('is_sport', '=', True)])
        total_equipment = self.env['product.product'].search([('is_equipment', '=', True)])
        data = {
            'total_inquiries': len(inquiries),
            'total_center_events': len(center_event),
            'total_bookings': len(bookings),
            'total_sports': len(total_sports),
            'total_equipment': len(total_equipment),
            'total_center_spaces': len(center_spaces),
            'total_trainers': len(trainers),
            'total_students': len(students),
            'total_confirm_admissions': len(admissions),
            'total_enroll_admissions': len(enroll_admissions)
        }
        return data

    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        context = self._context
        params = context.get('params')
        
        if context.get('default_is_student') and not params:
            res.update({'is_student': True})
        elif context.get('default_is_student'):
            res.update({'is_student': True})
        elif context.get('default_name') and not params:
            res.update({'is_student': False})
        elif context.get('default_is_sport') and not params:
            res.update({'is_student': False})
        elif context.get('default_is_coach') and not params:
            res.update({'is_student': False})
        elif (params and params.get('model') == 'student.admission'):
            res.update({'is_student': False})
        return res

    def action_open_student_id_print_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Student ID',
            'res_model': 'student.id.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_ids': self.ids},
        }