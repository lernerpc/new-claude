# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StudentAdmission(models.Model):
    _name = "student.admission"
    _description = "Student Admission"

    name = fields.Char('الاسم', required=True, readonly=True, default=lambda self: _('New'))
    student_id = fields.Many2one('res.partner', string='اسم الطالب', required=True, domain=[('is_student', '=', True)])
    student_national_id = fields.Char('الرقم القومي للطالب', related='student_id.student_national_id', store=True, readonly=False)
    mobile = fields.Char('رقم هاتف الطالب', related='student_id.mobile', store=True, readonly=False)
    p_name = fields.Char('اسم ولي الأمر', related='student_id.p_name', store=True, readonly=False)
    parent_national_id = fields.Char('الرقم القومي لولي الأمر', related='student_id.parent_national_id', store=True, readonly=False)
    parent_mobile = fields.Char('رقم هاتف ولي الأمر', related='student_id.phone', store=True, readonly=False)
    p1_name = fields.Char('Parent Name ', related='inquiry_id.p_name', readonly=False)
    parent1_mobile = fields.Char('Parent Mobile ', related='inquiry_id.parent_mobile', readonly=False)
    email = fields.Char('البريد الإلكتروني', related='student_id.email', store=True, readonly=False)
    birth_date = fields.Date('تاريخ الميلاد', related='student_id.birth_date', store=True, readonly=False)
    gender = fields.Selection([('male', 'ذكر'), ('female', 'أنثى')], string='الجنس', related='student_id.gender', store=True, readonly=False)
    is_disability = fields.Boolean('هل يوجد أي إعاقة', related='student_id.is_disability', store=True, readonly=False)
    disability_description = fields.Text('وصف الإعاقة', related='student_id.disability_description', store=True, readonly=False)
    
    # Add member_type field with proper labels
    member_type = fields.Selection([
        ('regular', 'عضو رياضي'),
        ('academic', 'عضو أكاديمي')
    ], string='نوع العضوية', default='regular', required=True)

    academic_subtype = fields.Selection([
        ('7star', '7 ستار'),
        ('academic', 'أكاديمية')
    ], string='نوع العضوية الأكاديمية', help="نوع العضوية الأكاديمية المختارة")
    
    # Activities field - optional for academic members
    activity_ids = fields.Many2many('product.product', string="الأنشطة الرياضية", domain=[('is_sportname', '=', True)])
    
    trainer_id = fields.Many2one(comodel_name='res.partner', domain=[('is_coach', '=', True)], string='المدرب')
    state = fields.Selection([
        ('new', 'New'),
        ('enrolled', 'Enrolled'),
        ('student', 'Student'),
        ('cancel', 'Cancelled')], string='State', copy=False, default="new", store=True)
    is_invoiced = fields.Boolean()
    inquiry_id = fields.Many2one('student.inquiry', string='Inquiry')
    check_parent = fields.Boolean('Check Parent', related='inquiry_id.check_parent')
    check_register = fields.Boolean('Check Register')
    property = fields.Boolean('Property', default=False)
    is_guardian = fields.Boolean('هل ولي الأمر مرافق', default=False)
    is_parking = fields.Boolean('هل يحتاج إلى موقف سيارة؟', default=False)
    student_photo = fields.Binary('صورة الطالب', attachment=True)
    parent_photo = fields.Binary('صورة ولي الأمر', attachment=True)
    
    # Pricelist field - optional for academic members  
    pricelist_id = fields.Many2one('product.pricelist', string='جهة الانتماء')
    # Add parent reference
    parent_id = fields.Many2one('res.partner', string='ولي الأمر', domain=[('is_parent', '=', True)])

    # Payment state fields
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

    @api.depends('student_id')
    def _compute_invoice_ids(self):
        """Compute related invoices for the student"""
        for record in self:
            if record.student_id:
                # Find invoices related to this student admission
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', record.student_id.id),
                    ('invoice_origin', '=', record.name),
                    ('move_type', 'in', ['out_invoice', 'out_refund'])
                ])
                record.invoice_ids = invoices
                record.invoice_count = len(invoices)
            else:
                record.invoice_ids = False
                record.invoice_count = 0

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

    @api.constrains('student_national_id', 'parent_national_id', 'mobile', 'parent_mobile')
    def _check_national_id_and_mobile(self):
        for record in self:
            # Validate student_national_id (required)
            if record.student_national_id and (not record.student_national_id.isdigit() or len(record.student_national_id) != 14):
                raise ValidationError(_('الرقم القومي للطالب يجب أن يكون 14 رقمًا.'))
            
            # Validate parent_national_id (required)
            if record.parent_national_id and (not record.parent_national_id.isdigit() or len(record.parent_national_id) != 14):
                raise ValidationError(_('الرقم القومي لولي الأمر يجب أن يكون 14 رقمًا.'))
            
            # Validate mobile (optional - only validate if provided)
            if record.mobile and record.mobile.strip():  # Only validate if mobile is not empty
                if not record.mobile.startswith('0') or not record.mobile.isdigit() or len(record.mobile) != 11:
                    raise ValidationError(_('رقم الجوال يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'))
            
            # Validate parent_mobile (required for parent contact)
            if record.parent_mobile and (not record.parent_mobile.startswith('0') or not record.parent_mobile.isdigit() or len(record.parent_mobile) != 11):
                raise ValidationError(_('رقم جوال ولي الأمر يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'))

    @api.constrains('member_type', 'activity_ids', 'pricelist_id')
    def _check_member_type_requirements(self):
        """Validate requirements based on member type"""
        for record in self:
            if record.member_type == 'regular':
                # Regular members must have activities and pricelist
                if not record.activity_ids:
                    raise ValidationError(_('العضوية الرياضية تتطلب اختيار نشاط واحد على الأقل.'))
                if not record.pricelist_id:
                    raise ValidationError(_('العضوية الرياضية تتطلب اختيار جهة الانتماء.'))
                    
                # Check if academic product is included (shouldn't be for regular members)
                academic_product = self.env['product.product'].search([
                    ('name', '=', 'أكاديمية'),
                    ('is_sportname', '=', True)
                ], limit=1)
                if academic_product and academic_product in record.activity_ids:
                    raise ValidationError(_('لا يمكن للعضوية الرياضية أن تشمل المنتج الأكاديمي.'))
                    
            elif record.member_type == 'academic':
                # Academic members should have the academic product
                academic_product = self.env['product.product'].search([
                    ('name', '=', 'أكاديمية'),
                    ('is_sportname', '=', True)
                ], limit=1)
                
                if academic_product and academic_product not in record.activity_ids:
                    # Auto-assign academic product if missing
                    record.activity_ids = [(4, academic_product.id)]
                
                # Academic members should not have sports activities (only academic product)
                if record.activity_ids:
                    non_academic_activities = record.activity_ids.filtered(lambda p: p.name != 'أكاديمية')
                    if non_academic_activities:
                        raise ValidationError(_('العضوية الأكاديمية لا يمكن أن تشمل أنشطة رياضية.'))

    @api.model_create_multi  
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('student.admission') or _('New')
        res = super(StudentAdmission, self).create(vals_list)
        
        # Handle multiple records if created in batch
        for record in res:
            # Only create portal access if email is provided
            if record.email and record.email.strip():
                portal_wizard_obj = self.env['portal.wizard']
                created_portal_wizard = portal_wizard_obj.create({})
                if created_portal_wizard:
                    portal_wizard_user_obj = self.env['portal.wizard.user']
                    wiz_user_vals = {
                        'wizard_id': created_portal_wizard.id,
                        'partner_id': record.student_id.id,
                        'email': record.student_id.email,
                    }
                    created_portal_wizard_user = portal_wizard_user_obj.create(wiz_user_vals)
                    if created_portal_wizard_user:
                        created_portal_wizard_user.action_grant_access()
        return res
    
    def action_enroll(self):
        """Override to handle different member types"""
        self.state = 'enrolled'
        self.student_id.update({'is_student': False})
        
        # Only send email if email address is provided
        if self.email and self.email.strip():
            template = self.env.ref('bi_sport_center_management.student_admission_enroll_email_template')
            if template:
                template.send_mail(self.id, force_send=True)
        
        return {
            'name': 'Create Invoice',
            'view_mode': 'form',
            'res_model': 'create.invoice',
            'type': 'ir.actions.act_window',
            'context': self._context,
            'target': 'new',
        }

    def action_make_student(self):
        """Override to handle different member types"""
        if not self.is_invoiced:
            return {
                'name': 'Create Invoice',
                'view_mode': 'form',
                'res_model': 'create.invoice',
                'type': 'ir.actions.act_window',
                'context': self._context,
                'target': 'new',
            }
        if self.is_invoiced:
            self.state = 'student'

            if self.parent_id and self.parent_photo:
                self.parent_id.write({
                    'parent_image_1920': self.parent_photo,
                    'image_1920': self.parent_photo,
                })

            student_vals = {
                'is_student': True,
            }
            
            # Only add sports for regular members or if activities exist
            if self.member_type == 'regular' and self.activity_ids:
                # Filter out academic products for regular members
                sports_activities = self.activity_ids.filtered(lambda p: p.name != 'أكاديمية')
                if sports_activities:
                    student_vals['sport_id'] = [(6, 0, sports_activities.ids)]
            elif self.member_type == 'academic':
                # Academic members don't get sport assignments
                student_vals['sport_id'] = [(6, 0, [])]

            # Sync student photo if present
            if hasattr(self, 'student_photo') and self.student_photo:
                student_vals['image_1920'] = self.student_photo

            self.student_id.update(student_vals)

    def action_cancel(self):
        self.state = 'cancel'

    def action_view_invoice(self):
        self.ensure_one()
        if self.invoice_count == 1:
            return {
                'name': _("Student Invoice"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.invoice_ids[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'name': _("Student Invoices"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.invoice_ids.ids)],
                'target': 'current',
            }

    def action_print_registration(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/print/registration/%s' % self.id,
            'target': 'new',
        }

    @api.onchange('member_type')
    def _onchange_member_type(self):
        """Handle member type changes in the UI"""
        if self.member_type == 'academic':
            # Find or suggest academic product
            academic_product = self.env['product.product'].search([
                ('name', '=', 'أكاديمية'),
                ('is_sportname', '=', True)
            ], limit=1)
            if academic_product:
                self.activity_ids = [(6, 0, [academic_product.id])]
        elif self.member_type == 'regular':
            # Clear academic product if switching from academic
            academic_product = self.env['product.product'].search([
                ('name', '=', 'أكاديمية'),
                ('is_sportname', '=', True)
            ], limit=1)
            if academic_product and academic_product in self.activity_ids:
                self.activity_ids = [(3, academic_product.id)]

    def get_total_price(self):
        """Calculate total price based on member type"""
        total = 0
        
        # Base fees
        if self.member_type == 'academic':
            total += 50  # Academic card fee
        else:
            total += 50  # ID card fee
            total += 50  # Form fee
        
        # Guardian fee
        if self.is_guardian:
            total += 50
            
        # Activity fees (only for regular members)
        if self.member_type == 'regular' and self.activity_ids and self.pricelist_id:
            for activity in self.activity_ids:
                if activity.name != 'أكاديمية':  # Exclude academic product
                    price = self.pricelist_id._get_product_price(activity, 1)
                    total += price
                    
        return total

    def get_member_type_display(self):
        """Get display name for member type"""
        member_type_dict = dict(self._fields['member_type'].selection)
        return member_type_dict.get(self.member_type, self.member_type)