# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
from collections import defaultdict
from datetime import timedelta

_logger = logging.getLogger(__name__)

class StudentAdmission(models.Model):
    _name = "student.admission"
    _description = "Student Admission"

    name = fields.Char('رقم العضوية', required=True, readonly=True, default=lambda self: _('New'))

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
    is_disability = fields.Boolean('هل يوجد أي مرض', related='student_id.is_disability', store=True, readonly=False)
    disability_description = fields.Text('وصف المرض', related='student_id.disability_description', store=True, readonly=False)

    # Add member_type field with proper labels
    member_type = fields.Selection([
        ('regular', 'عضو رياضي'),
        ('academic', 'عضو أكاديمي')
    ], string='نوع العضوية', default='regular', required=True)

    academic_subtype = fields.Selection([
        ('7star', '7 ستار'),
        ('academic', 'أكاديمية')
    ], string='نوع العضوية الأكاديمية', help="نوع العضوية الأكاديمية المختارة")
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

    # Add pricelist field for price calculations
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

    payment_date = fields.Date(
        string='Payment Date',
        compute='_compute_payment_state',
        store=True,
        readonly=True,
        help="Date of the latest payment for this student"
    )

    invoice_ids = fields.One2many('account.move', compute='_compute_invoice_ids', string='Invoices', search=True)
    invoice_count = fields.Integer(compute='_compute_invoice_ids', string='Invoice Count')
    fees_count = fields.Integer(compute='_compute_invoice_ids', string='Fees Count', help="Number of invoices that are membership fees")

    # Computed field to show fee details
    fee_details = fields.Html('Fee Details', compute='_compute_fee_details', store=False, 
                             help="Details of membership fees assigned to this student")
    
    # One2many field to show fee invoices in a tree view
    fee_invoice_ids = fields.One2many('account.move', compute='_compute_fee_invoice_ids', 
                                     string='Fee Invoices', store=False,
                                     help="Invoices that are membership fees")

    membership_number = fields.Char('رقم الاستمارة')

    schedule_selection_ids = fields.One2many('admission.schedule.selection', 'admission_id', string='Schedule Selections')

    previous_activities_schedule_ids = fields.Json(string='Previous Activities and Schedules', compute='_compute_previous_activities_schedule_ids', store=False)

    @api.onchange('student_photo')
    def _onchange_student_photo(self):
        """Sync student photo to res.partner when changed in admission"""
        if self.student_photo and self.student_id:
            self.student_id.image_1920 = self.student_photo

    @api.onchange('student_id')
    def _onchange_student_id(self):
        """Load student photo from res.partner when student is selected"""
        if self.student_id and self.student_id.image_1920:
            self.student_photo = self.student_id.image_1920

    @api.onchange('student_national_id')
    def _onchange_student_national_id(self):
        if self.student_national_id:
            student = self.env['res.partner'].search([('student_national_id', '=', self.student_national_id)], limit=1)
            if student:
                self.student_id = student.id
                self.mobile = student.mobile
                self.p_name = student.p_name
                self.parent_national_id = student.parent_national_id
                self.parent_mobile = student.phone
                self.email = student.email
                self.birth_date = student.birth_date
                self.gender = student.gender
                self.is_disability = student.is_disability

    def write(self, vals):
        """Override write to maintain photo synchronization"""
        result = super(StudentAdmission, self).write(vals)

        # Sync student photo to res.partner
        if 'student_photo' in vals:
            for record in self:
                if record.student_id and record.student_photo:
                    record.student_id.write({'image_1920': record.student_photo})

        # Handle parent privilege updates
        if 'is_guardian' in vals or 'is_parking' in vals:
            for record in self:
                if record.parent_id:
                    _logger.info("=== WRITE: UPDATING PARENT PRIVILEGES ===")
                    _logger.info("Current admission: Guardian=%s, Parking=%s", record.is_guardian, record.is_parking)
                    record.parent_id.update_parent_privileges_or_logic(record.is_guardian, record.is_parking)
                    _logger.info("✅ WRITE: Parent privileges updated using OR logic")

        return result

    def _ensure_parent_privileges_or_logic(self):
        """
        Ensure parent privileges follow OR logic across all children.
        This should be called whenever a student's privileges change.
        """
        for record in self:
            if not record.parent_id:
                continue

            parent = record.parent_id

            # Get all children (students) of this parent
            all_children = self.env['res.partner'].search([
                ('parent_id', '=', parent.id),
                ('is_student', '=', True)
            ])

            # Calculate what parent should have based on ALL children
            should_have_guardian = any(child.is_guardian for child in all_children)
            should_have_parking = any(child.is_parking for child in all_children)

            _logger.info("=== PARENT PRIVILEGE CHECK ===")
            _logger.info("Parent: %s (ID: %s)", parent.name, parent.id)
            _logger.info("Found %d children", len(all_children))
            _logger.info("Current parent: Guardian=%s, Parking=%s", parent.is_guardian, parent.is_parking)
            _logger.info("Should be: Guardian=%s, Parking=%s", should_have_guardian, should_have_parking)

            # Update parent if needed
            if parent.is_guardian != should_have_guardian or parent.is_parking != should_have_parking:
                _logger.info("Updating parent privileges...")
                parent.write({
                    'is_guardian': should_have_guardian,
                    'is_parking': should_have_parking,
                })
                _logger.info("✅ Parent privileges updated successfully")
            else:
                _logger.info("✅ Parent privileges already correct")

    @api.constrains('membership_number', 'state')
    def _check_membership_number_unique(self):
        """Validate membership number uniqueness only during enrollment or student creation"""
        for record in self:
            if record.membership_number and record.state in ['enrolled', 'student']:
                # Check if another record with the same membership_number exists
                existing_record = self.search([
                    ('membership_number', '=', record.membership_number),
                    ('id', '!=', record.id),
                    ('state', 'in', ['enrolled', 'student'])
                ])
                if existing_record:
                    raise ValidationError(_('Membership number must be unique for enrolled/student records.'))

    @api.depends('student_id', 'name')
    def _compute_invoice_ids(self):
        """Compute related invoices for the student - Enhanced version with auto-detection"""
        for record in self:
            invoices = self.env['account.move']
            if record.name:
                # Method 1: Search by invoice_origin (existing invoices)
                invoices_by_origin = self.env['account.move'].search([
                    ('invoice_origin', '=', record.name),
                    ('move_type', 'in', ['out_invoice', 'out_refund'])
                ])
                
                # Method 2: Search by student_admission_id (new field from account_move extension)
                invoices_by_admission = self.env['account.move']
                if record.id:  # Check if record has an ID (is saved)
                    invoices_by_admission = self.env['account.move'].search([
                        ('student_admission_id', '=', record.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund'])
                    ])
                
                # Method 3: Auto-link unlinked invoices for this student (fallback)
                invoices_by_partner = self.env['account.move']
                if record.student_id and record.id:
                    # Find invoices for this student that aren't linked to any admission
                    unlinked_invoices = self.env['account.move'].search([
                        ('partner_id', '=', record.student_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('invoice_origin', '=', False),
                        ('student_admission_id', '=', False)
                    ])
                    
                    # Auto-link them to this admission if it's the most recent for this student
                    if unlinked_invoices:
                        most_recent_admission = self.env['student.admission'].search([
                            ('student_id', '=', record.student_id.id)
                        ], order='id desc', limit=1)
                        
                        if most_recent_admission and most_recent_admission.id == record.id:
                            # This is the most recent admission, auto-link the unlinked invoices
                            unlinked_invoices.write({'student_admission_id': record.id})
                            invoices_by_partner = unlinked_invoices
                
                # Combine all methods and remove duplicates
                invoices = (invoices_by_origin | invoices_by_admission | invoices_by_partner)

            record.invoice_ids = invoices
            record.invoice_count = len(invoices)
            
            # Count only invoices that have membership_fee_name set (fee invoices)
            fee_invoices = invoices.filtered(lambda inv: inv.membership_fee_name)
            record.fees_count = len(fee_invoices)

    @api.depends('invoice_ids.payment_state', 'invoice_ids.invoice_date', 'invoice_ids.line_ids.reconciled')
    def _compute_payment_state(self):
        """Improved computation of payment state and date based on actual payment transactions"""
        for record in self:
            if not record.invoice_ids:
                record.payment_state = 'not_paid'
                record.payment_date = False
                continue

            # Get all posted invoices, sorted by invoice_date (descending) to get the latest
            posted_invoices = record.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            if not posted_invoices:
                record.payment_state = 'not_paid'
                record.payment_date = False
                continue

            # Get the most recent invoice based on invoice_date or create_date
            latest_invoice = sorted(
                posted_invoices, 
                key=lambda inv: inv.invoice_date or inv.create_date,
                reverse=True
            )[0]

            # Set payment_state based on the latest invoice
            record.payment_state = latest_invoice.payment_state

            # Find the payment date for the latest invoice if paid, in_payment, or partial
            payment_date = False
            
            if latest_invoice.payment_state in ['paid', 'in_payment', 'partial']:
                # Use direct SQL to find actual payment dates through reconciliations
                self.env.cr.execute("""
                    SELECT MAX(payment_move.date) 
                    FROM account_move_line invoice_line
                    JOIN account_partial_reconcile apr ON 
                        apr.debit_move_id = invoice_line.id OR 
                        apr.credit_move_id = invoice_line.id
                    JOIN account_move_line payment_line ON 
                        (apr.credit_move_id = payment_line.id AND apr.debit_move_id = invoice_line.id) OR
                        (apr.debit_move_id = payment_line.id AND apr.credit_move_id = invoice_line.id)
                    JOIN account_move payment_move ON payment_line.move_id = payment_move.id
                    WHERE 
                        invoice_line.move_id = %s AND
                        payment_move.id != %s AND
                        payment_move.state = 'posted'
                """, (latest_invoice.id, latest_invoice.id))
                
                result = self.env.cr.fetchone()
                if result and result[0]:
                    payment_date = result[0]
                
                # For partial payments with no payment date, use invoice date as fallback
                # but ONLY if no actual payment date was found
                if not payment_date and latest_invoice.payment_state in ['in_payment', 'partial']:
                    payment_date = latest_invoice.invoice_date
            
            record.payment_date = payment_date

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

        # Sync student photo to res.partner after creation
        for record in res:
            if record.student_photo and record.student_id:
                record.student_id.write({'image_1920': record.student_photo})

        # Only create portal access if email is provided
        if res.email and res.email.strip():
            portal_wizard_obj = self.env['portal.wizard']
            created_portal_wizard = portal_wizard_obj.create({})
            if created_portal_wizard:
                portal_wizard_user_obj = self.env['portal.wizard.user']
                wiz_user_vals = {
                    'wizard_id': created_portal_wizard.id,
                    'partner_id': res.student_id.id,
                    'email': res.student_id.email,
                }
                created_portal_wizard_user = portal_wizard_user_obj.create(wiz_user_vals)
                if created_portal_wizard_user:
                    created_portal_wizard_user.action_grant_access()
        return res

    def action_enroll(self):
      """Enhanced enroll method to create/update student and parent like registration form"""
      self.state = 'enrolled'
      
      # =================================================================
      # PARENT CREATION/UPDATE LOGIC - Same as registration form
      # =================================================================
      
      parent_partner = None
      
      # Try to find existing parent by national ID first
      if self.parent_national_id:
          parent_partner = self.env['res.partner'].search([
              ('parent_national_id', '=', self.parent_national_id),
              ('is_parent', '=', True)
          ], limit=1)
      
      # If not found by national ID, try by mobile
      if not parent_partner and self.parent_mobile:
          parent_partner = self.env['res.partner'].search([
              ('mobile', '=', self.parent_mobile),
              ('is_parent', '=', True)
          ], limit=1)

      _logger.info("=== ENROLL PARENT UPDATE START ===")
      _logger.info("Current admission: Guardian=%s, Parking=%s", self.is_guardian, self.is_parking)

      # Prepare parent values
      parent_vals = {
          'name': self.p_name,
          'mobile': self.parent_mobile,
          'parent_national_id': self.parent_national_id,
          'is_parent': True,
          'academic_subtype': self.academic_subtype if hasattr(self, 'academic_subtype') else '',
      }

      if parent_partner:
          # EXISTING PARENT - Update basic info first, then calculate privileges from ALL children
          _logger.info("Found existing parent: %s (ID: %s)", parent_partner.name, parent_partner.id)
          
          # Update basic parent information first
          parent_partner.write(parent_vals)
          
          # Get ALL student admissions for this parent (including current one)
          all_admissions = self.env['student.admission'].search([
              ('parent_national_id', '=', self.parent_national_id),
              ('state', 'in', ['enrolled', 'student'])
          ])
          
          # Calculate what parent should have based on ALL children using OR logic
          should_have_guardian = any(admission.is_guardian for admission in all_admissions)
          should_have_parking = any(admission.is_parking for admission in all_admissions)
          
          _logger.info("Found %d admissions for parent", len(all_admissions))
          _logger.info("Current parent privileges: Guardian=%s, Parking=%s", parent_partner.is_guardian, parent_partner.is_parking)
          _logger.info("Should have privileges: Guardian=%s, Parking=%s", should_have_guardian, should_have_parking)
          
          # Update parent privileges based on ALL children
          parent_partner.write({
              'is_guardian': should_have_guardian,
              'is_parking': should_have_parking,
          })
          
          _logger.info("✅ EXISTING PARENT UPDATED with OR logic from ALL children")
          
      else:
          # NEW PARENT - Use current child's values since it's the first child
          parent_vals.update({
              'is_guardian': self.is_guardian,
              'is_parking': self.is_parking,
          })
          
          parent_partner = self.env['res.partner'].create(parent_vals)
          
          _logger.info("✅ NEW PARENT CREATED: Guardian=%s, Parking=%s", self.is_guardian, self.is_parking)

      _logger.info("=== ENROLL PARENT UPDATE END ===")

      # =================================================================
      # STUDENT UPDATE LOGIC - Enhanced version
      # =================================================================
      
      # Update student record with complete information
      student_vals = {
          'is_student': True,  # Make sure student flag is True, not False
          'mobile': self.mobile,
          'student_national_id': self.student_national_id,
          'p_name': self.p_name,
          'parent_national_id': self.parent_national_id,
          'phone': self.parent_mobile,
          'birth_date': self.birth_date,
          'gender': self.gender,
          'is_disability': self.is_disability,
          'disability_description': self.disability_description,
          'is_guardian': self.is_guardian,
          'is_parking': self.is_parking,
          'parent_id': parent_partner.id,  # Set the parent relationship
      }

      # Handle sports assignment based on member type
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

      # Update the student record
      self.student_id.write(student_vals)

      # Update the admission record with parent reference
      self.write({'parent_id': parent_partner.id})

      # Update parent photo if provided
      if self.parent_photo:
          parent_partner.write({
              'parent_image_1920': self.parent_photo,
              'image_1920': self.parent_photo,
          })

      # =================================================================
      # FINAL SAFETY NET - ENSURE PARENT PRIVILEGES ARE CORRECT FROM ALL CHILDREN
      # =================================================================
      _logger.info("ENROLL FINAL SAFETY NET: Ensuring parent privileges are correct from ALL children")
      
      # Get ALL student admissions for this parent to recalculate privileges
      all_admissions = self.env['student.admission'].search([
          ('parent_national_id', '=', self.parent_national_id),
          ('state', 'in', ['enrolled', 'student'])
      ])
      
      # Calculate what parent should have based on ALL children using OR logic
      final_should_have_guardian = any(admission.is_guardian for admission in all_admissions)
      final_should_have_parking = any(admission.is_parking for admission in all_admissions)
      
      _logger.info("FINAL CHECK: Found %d total admissions for parent", len(all_admissions))
      _logger.info("FINAL CHECK: Should have privileges: Guardian=%s, Parking=%s", final_should_have_guardian, final_should_have_parking)
      
      # Update parent with final calculated privileges
      parent_partner.write({
          'is_guardian': final_should_have_guardian,
          'is_parking': final_should_have_parking,
      })
      
      _logger.info("ENROLL FINAL SAFETY NET: Parent privileges confirmed from ALL children")

      # Send enrollment email only if email address is provided
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

    def action_sync_changes(self):
        """Sync all admission changes to parent, student records, and invoices"""
        
        # =================================================================
        # PARENT CREATION/UPDATE LOGIC - Same as enroll
        # =================================================================
        
        parent_partner = None
        
        # Try to find existing parent by national ID first
        if self.parent_national_id:
            parent_partner = self.env['res.partner'].search([
                ('parent_national_id', '=', self.parent_national_id),
                ('is_parent', '=', True)
            ], limit=1)
        
        # If not found by national ID, try by mobile
        if not parent_partner and self.parent_mobile:
            parent_partner = self.env['res.partner'].search([
                ('mobile', '=', self.parent_mobile),
                ('is_parent', '=', True)
            ], limit=1)

        _logger.info("=== SYNC CHANGES PARENT UPDATE START ===")
        _logger.info("Current admission: Guardian=%s, Parking=%s", self.is_guardian, self.is_parking)

        # Prepare parent values
        parent_vals = {
            'name': self.p_name,
            'mobile': self.parent_mobile,
            'parent_national_id': self.parent_national_id,
            'is_parent': True,
            'academic_subtype': self.academic_subtype if hasattr(self, 'academic_subtype') else '',
            'email': self.email,  # Sync email to parent
        }

        if parent_partner:
            # EXISTING PARENT - Update basic info first, then calculate privileges from ALL children
            _logger.info("Found existing parent: %s (ID: %s)", parent_partner.name, parent_partner.id)
            
            # Update basic parent information first
            parent_partner.write(parent_vals)
            
            # Get ALL student admissions for this parent (including current one)
            all_admissions = self.env['student.admission'].search([
                ('parent_national_id', '=', self.parent_national_id),
                ('state', 'in', ['new', 'enrolled', 'student'])  # Include all active states
            ])
            
            # Calculate what parent should have based on ALL children using OR logic
            should_have_guardian = any(admission.is_guardian for admission in all_admissions)
            should_have_parking = any(admission.is_parking for admission in all_admissions)
            
            _logger.info("Found %d admissions for parent", len(all_admissions))
            _logger.info("Current parent privileges: Guardian=%s, Parking=%s", parent_partner.is_guardian, parent_partner.is_parking)
            _logger.info("Should have privileges: Guardian=%s, Parking=%s", should_have_guardian, should_have_parking)
            
            # Update parent privileges based on ALL children
            parent_partner.write({
                'is_guardian': should_have_guardian,
                'is_parking': should_have_parking,
            })
            
            _logger.info("✅ EXISTING PARENT UPDATED with OR logic from ALL children")
            
        else:
            # NEW PARENT - Use current child's values since it's the first child
            parent_vals.update({
                'is_guardian': self.is_guardian,
                'is_parking': self.is_parking,
            })
            
            parent_partner = self.env['res.partner'].create(parent_vals)
            
            _logger.info("✅ NEW PARENT CREATED: Guardian=%s, Parking=%s", self.is_guardian, self.is_parking)

        _logger.info("=== SYNC CHANGES PARENT UPDATE END ===")

        # =================================================================
        # STUDENT UPDATE LOGIC - Enhanced version with all fields
        # =================================================================
        
        # Update student record with complete information
        student_vals = {
            'name': self.student_id.name,  # Keep the student name or update it
            'mobile': self.mobile,
            'email': self.email,  # Sync email
            'student_national_id': self.student_national_id,
            'p_name': self.p_name,
            'parent_national_id': self.parent_national_id,
            'phone': self.parent_mobile,
            'birth_date': self.birth_date,
            'gender': self.gender,
            'is_disability': self.is_disability,
            'disability_description': self.disability_description,
            'is_guardian': self.is_guardian,
            'is_parking': self.is_parking,
            'parent_id': parent_partner.id,  # Set the parent relationship
        }

        # Handle sports assignment based on member type and state
        if self.member_type == 'regular' and self.activity_ids:
            # Filter out academic products for regular members
            sports_activities = self.activity_ids.filtered(lambda p: p.name != 'أكاديمية')
            if sports_activities:
                student_vals['sport_id'] = [(6, 0, sports_activities.ids)]
            else:
                student_vals['sport_id'] = [(6, 0, [])]
        elif self.member_type == 'academic':
            # Academic members don't get sport assignments
            student_vals['sport_id'] = [(6, 0, [])]
        else:
            # Clear sports if no member type or activities
            student_vals['sport_id'] = [(6, 0, [])]

        # Sync student photo if present
        if hasattr(self, 'student_photo') and self.student_photo:
            student_vals['image_1920'] = self.student_photo

        # Update the student record
        self.student_id.update(student_vals)

        # Update the admission record with parent reference
        self.write({'parent_id': parent_partner.id})

        # Update parent photo if provided
        if self.parent_photo:
            parent_partner.write({
                'parent_image_1920': self.parent_photo,
                'image_1920': self.parent_photo,
            })

        # =================================================================
        # INVOICE SYNC LOGIC - ONLY UPDATE SPORTS ACTIVITIES (NOT FEES)
        # =================================================================
        _logger.info("=== SYNC CHANGES INVOICE UPDATE START ===")
        
        if self.invoice_ids:
            for invoice in self.invoice_ids.filtered(lambda inv: inv.state == 'draft'):
                _logger.info("Updating draft invoice: %s", invoice.name)
                
                # Update invoice partner information
                invoice.write({
                    'partner_id': self.student_id.id,
                    'invoice_origin': self.name,
                })
                
                # ONLY update activity-related invoice lines, keep existing fees
                existing_lines = invoice.invoice_line_ids
                
                # Remove only activity/sport related lines (products with is_sportname=True)
                activity_lines = existing_lines.filtered(lambda line: line.product_id and line.product_id.is_sportname)
                activity_lines.unlink()
                
                # Add current activity fees for regular members ONLY
                new_activity_lines = []
                if self.member_type == 'regular' and self.activity_ids and self.pricelist_id:
                    # Get a default income account
                    default_income_account = self.env['account.account'].search([
                        ('account_type', '=', 'income')
                    ], limit=1)
                    
                    if not default_income_account:
                        default_income_account = self.env['account.account'].search([
                            ('code', 'like', '4%')
                        ], limit=1)
                    
                    if not default_income_account:
                        default_income_account = self.env['account.account'].search([], limit=1)
                    
                    for activity in self.activity_ids:
                        if activity.name != 'أكاديمية':  # Exclude academic product
                            try:
                                price = self.pricelist_id._get_product_price(activity, 1)
                            except:
                                price = activity.list_price or 0
                            
                            # Use product's income account or default
                            account_id = default_income_account.id
                            if hasattr(activity, 'property_account_income_id') and activity.property_account_income_id:
                                account_id = activity.property_account_income_id.id
                            
                            new_activity_lines.append((0, 0, {
                                'product_id': activity.id,
                                'name': activity.name,
                                'quantity': 1,
                                'price_unit': price,
                                'account_id': account_id,
                            }))
                
                # Add new activity lines to invoice (keeping existing fee lines)
                if new_activity_lines:
                    invoice.write({'invoice_line_ids': new_activity_lines})
                    _logger.info("✅ Invoice %s updated with %d activity lines", invoice.name, len(new_activity_lines))
                else:
                    _logger.info("ℹ️ No activity lines to add for invoice %s", invoice.name)
                
            _logger.info("=== SYNC CHANGES INVOICE UPDATE END ===")
        else:
            _logger.info("No invoices found to update")
        
        # =================================================================
        # TRAINER/COACH SYNC - Update if trainer is assigned (with field checking)
        # =================================================================
        if hasattr(self, 'trainer_id') and self.trainer_id:
            # Check if student record has coach-related fields before updating
            coach_vals = {}
            
            # Check for various possible coach field names
            if hasattr(self.student_id, 'coach_id'):
                coach_vals['coach_id'] = self.trainer_id.id
            elif hasattr(self.student_id, 'trainer_id'):
                coach_vals['trainer_id'] = self.trainer_id.id
            elif hasattr(self.student_id, 'instructor_id'):
                coach_vals['instructor_id'] = self.trainer_id.id
            
            # Only update if we found a valid coach field
            if coach_vals:
                self.student_id.update(coach_vals)
                _logger.info("✅ Trainer/Coach synced to student record: %s", list(coach_vals.keys())[0])
            else:
                _logger.info("ℹ️ No coach field found on student record - skipping coach sync")

        # =================================================================
        # MEMBERSHIP NUMBER SYNC (with field checking)
        # =================================================================
        if hasattr(self, 'membership_number') and self.membership_number:
            # Check if student record has membership_number field
            if hasattr(self.student_id, 'membership_number'):
                self.student_id.update({
                    'membership_number': self.membership_number
                })
                _logger.info("✅ Membership number synced to student record")
            else:
                _logger.info("ℹ️ No membership_number field found on student record - skipping membership sync")

        # =================================================================
        # FINAL SAFETY NET - ENSURE PARENT PRIVILEGES ARE CORRECT FROM ALL CHILDREN
        # =================================================================
        _logger.info("SYNC CHANGES FINAL SAFETY NET: Ensuring parent privileges are correct from ALL children")
        
        # Get ALL student admissions for this parent to recalculate privileges
        all_admissions = self.env['student.admission'].search([
            ('parent_national_id', '=', self.parent_national_id),
            ('state', 'in', ['new', 'enrolled', 'student'])  # Include all active states
        ])
        
        # Calculate what parent should have based on ALL children using OR logic
        final_should_have_guardian = any(admission.is_guardian for admission in all_admissions)
        final_should_have_parking = any(admission.is_parking for admission in all_admissions)
        
        _logger.info("FINAL CHECK: Found %d total admissions for parent", len(all_admissions))
        _logger.info("FINAL CHECK: Should have privileges: Guardian=%s, Parking=%s", final_should_have_guardian, final_should_have_parking)
        
        # Update parent with final calculated privileges
        parent_partner.write({
            'is_guardian': final_should_have_guardian,
            'is_parking': final_should_have_parking,
        })
        
        _logger.info("SYNC CHANGES FINAL SAFETY NET: Parent privileges confirmed from ALL children")

        # Show comprehensive success message
        synced_items = [
            "✅ Parent record updated",
            "✅ Student record updated", 
            "✅ Parent privileges calculated with OR logic",
            "✅ Photos synchronized"
        ]
        
        if self.invoice_ids and any(inv.state == 'draft' for inv in self.invoice_ids):
            synced_items.append("✅ Draft invoices updated")
        
        # Only add trainer sync message if we actually found and updated coach fields
        if hasattr(self, 'trainer_id') and self.trainer_id:
            coach_field_exists = any(hasattr(self.student_id, field) for field in ['coach_id', 'trainer_id', 'instructor_id'])
            if coach_field_exists:
                synced_items.append("✅ Trainer/Coach information synced")
        
        # Only add membership sync message if field exists
        if hasattr(self, 'membership_number') and self.membership_number and hasattr(self.student_id, 'membership_number'):
            synced_items.append("✅ Membership number synced")
            
        if self.activity_ids:
            synced_items.append("✅ Sports activities synchronized")
        
        success_message = "All changes synced successfully!\n\n" + "\n".join(synced_items)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': success_message,
                'type': 'success',
                'sticky': True,  # Make it sticky so user can read all items
            }
        }

    def action_make_student(self):
        """Override to handle different member types - FIXED VERSION"""
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

            # Update parent photo if provided
            if self.parent_id and self.parent_photo:
                self.parent_id.write({
                'parent_image_1920': self.parent_photo,
                'image_1920': self.parent_photo,
                })

        # Update student record
            student_vals = {
            'is_student': True,
            # CRITICAL: Update student's individual privileges (NOT parent's)
            'is_guardian': self.is_guardian,
            'is_parking': self.is_parking,
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

        # Update the student record
            self.student_id.update(student_vals)

        # CRITICAL FIX: Use OR logic method instead of _ensure_parent_privileges_or_logic
            if self.parent_id:
                _logger.info("=== MAKE STUDENT: UPDATING PARENT PRIVILEGES ===")
                _logger.info("Current admission: Guardian=%s, Parking=%s", self.is_guardian, self.is_parking)

            # Use the OR logic method to properly update parent privileges
                self.parent_id.update_parent_privileges_or_logic(self.is_guardian, self.is_parking)

                _logger.info("✅ MAKE STUDENT: Parent privileges updated using OR logic")

    def action_cancel(self):
        for record in self:
            if record.state == 'new':
                record.state = 'cancel'

                # CRITICAL: After cancelling, recalculate parent privileges
                record._ensure_parent_privileges_or_logic()
            else:
                raise ValidationError(_("Only new registrations can be cancelled"))

    def reset_to_new(self):
        """Reset cancelled registration back to new state"""
        for record in self:
            if record.state == 'cancel':
                # Reset all related records to draft
                if record.invoice_ids:
                    record.invoice_ids.write({'state': 'draft'})

                # Reset the registration to new
                record.write({
                    'state': 'new'
                })

                # CRITICAL: After resetting, recalculate parent privileges
                record._ensure_parent_privileges_or_logic()
            else:
                raise ValidationError(_("Only cancelled registrations can be reset to new"))

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

    @api.onchange('activity_ids')
    def _onchange_activity_ids(self):
        """Reset schedule selections when activities change"""
        if self.schedule_selection_ids:
            self.schedule_selection_ids = [(5, 0, 0)]  # Clear all schedule selections

    def get_total_price(self):
        """Calculate total price based on member type and registration date"""
        total = 0

        # Get registration date for comparison with fee end dates
        registration_date = self.create_date.date() if self.create_date else fields.Date.today()
        
        # Check if this is a late registration by checking all fees
        fees = self.env['sport.membership.fees'].search([], order='sequence_id asc')
        is_late_registration = False
        
        if fees:
            # Check if registration is after any fee end date
            for fee in fees:
                if fee.end_date and registration_date > fee.end_date:
                    is_late_registration = True
                    break

        # Base fees (always included)
        if self.member_type == 'academic':
            total += 50  # Academic card fee
        else:
            total += 50  # ID card fee
            total += 50  # Form fee

        # Guardian fee (always included if guardian is selected)
        if self.is_guardian:
            total += 50

        # Activity fees (only for regular members and only if not late registration)
        if not is_late_registration and self.member_type == 'regular' and self.activity_ids and self.pricelist_id:
            for activity in self.activity_ids:
                if activity.name != 'أكاديمية':  # Exclude academic product
                    price = self.pricelist_id._get_product_price(activity, 1)
                    total += price

        return total

    def get_member_type_display(self):
        """Get display name for member type"""
        member_type_dict = dict(self._fields['member_type'].selection)
        return member_type_dict.get(self.member_type, self.member_type)

    def get_schedules_for_sport(self, sport_id):
        return self.env['sport.schedule'].search([('sport_id', '=', sport_id)])

    @api.depends('invoice_ids')
    def _compute_fee_invoice_ids(self):
        """Compute fee invoices for display in One2many field"""
        for record in self:
            try:
                # Ensure invoice_ids is computed and available
                if not record.invoice_ids:
                    record.fee_invoice_ids = [(5, 0, 0)]  # Clear the field if no invoices
                    continue

                # Get only invoices that have membership_fee_name set (fee invoices)
                fee_invoices = record.invoice_ids.filtered(
                    lambda inv: hasattr(inv, 'membership_fee_name') and getattr(inv, 'membership_fee_name', False)
                )
                
                # Assign the list of invoice IDs or an empty list if none found
                record.fee_invoice_ids = [(6, 0, fee_invoices.ids)] if fee_invoices else [(5, 0, 0)]
                
            except Exception as e:
                _logger.error("Error computing fee_invoice_ids for admission %s: %s", record.id, str(e))
                record.fee_invoice_ids = [(5, 0, 0)]  # Clear the field in case of error

    @api.depends('invoice_ids')
    def _compute_fee_details(self):
        """Compute fee details to display in the form"""
        for record in self:
            if not record.invoice_ids:
                record.fee_details = '<p>No fees assigned</p>'
                continue
            
            # Get fee invoices - safely check if membership_fee_name exists
            fee_invoices = record.invoice_ids.filtered(
                lambda inv: hasattr(inv, 'membership_fee_name') and getattr(inv, 'membership_fee_name', False)
            )
            
            if not fee_invoices:
                record.fee_details = '<p>No membership fees found</p>'
                continue
            
            # Build simple HTML table
            html_content = '''
            <div style="margin: 10px 0;">
                <h4 style="color: #875A7B; margin-bottom: 15px;">💳 Membership Fees</h4>
                <table class="table table-striped" style="width: 100%; border-collapse: collapse;">
                    <thead style="background-color: #875A7B; color: white;">
                        <tr>
                            <th style="padding: 8px; border: 1px solid #ddd;">#</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Fee Name</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Start Date</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">End Date</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Amount</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Status</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Invoice</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            
            # Add fee rows
            for index, invoice in enumerate(fee_invoices, 1):
                # Safely get membership_fee_name
                fee_name = getattr(invoice, 'membership_fee_name', 'Unknown Fee')
                
                # Try to find the actual membership fee record
                fee_record = None
                if fee_name and fee_name != 'Unknown Fee':
                    fee_record = self.env['sport.membership.fees'].search([
                        ('name', '=', fee_name)
                    ], limit=1)
                
                start_date = fee_record.start_date.strftime('%Y-%m-%d') if fee_record and fee_record.start_date else 'N/A'
                end_date = fee_record.end_date.strftime('%Y-%m-%d') if fee_record and fee_record.end_date else 'N/A'
                
                # Payment status styling
                status_color = {
                    'paid': '#28a745',
                    'partial': '#ffc107', 
                    'in_payment': '#17a2b8',
                    'not_paid': '#dc3545',
                    'reversed': '#6c757d'
                }.get(invoice.payment_state, '#6c757d')
                
                status_text = {
                    'paid': 'Paid',
                    'partial': 'Partial',
                    'in_payment': 'In Payment', 
                    'not_paid': 'Not Paid',
                    'reversed': 'Reversed'
                }.get(invoice.payment_state, invoice.payment_state)
                
                html_content += f'''
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{index}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{fee_name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{start_date}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{end_date}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: bold;">{invoice.amount_total:.2f} EGP</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">
                        <span style="background-color: {status_color}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">
                            {status_text}
                        </span>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #875A7B; font-weight: bold;">{invoice.name or 'Draft'}</td>
                </tr>
                '''
            
            html_content += '''
                    </tbody>
                </table>
            </div>
            '''
            
            record.fee_details = html_content

    @api.depends('student_id')
    def _compute_previous_activities_schedule_ids(self):
        for rec in self:
            result = defaultdict(list)
            if rec.student_id:
                admissions = self.env['student.admission'].search([
                    ('student_id', '=', rec.student_id.id),
                    ('id', '!=', rec.id)
                ])
                for admission in admissions:
                    for activity in admission.activity_ids:
                        schedules = self.env['sport.schedule'].search([
                            ('sport_id', '=', activity.id)
                        ])
                        result[activity.name].extend([s.display_name for s in schedules])
            rec.previous_activities_schedule_ids = dict(result)

class AdmissionScheduleSelection(models.Model):
    _name = 'admission.schedule.selection'
    _description = 'Admission Schedule Selection'

    admission_id = fields.Many2one('student.admission', string='Admission', required=True, ondelete='cascade')
    activity_id = fields.Many2one('product.product', string='Sport Activity', required=True)
    schedule_id = fields.Many2one('sport.schedule', string='Selected Schedule', required=True)

    _sql_constraints = [
        ('admission_activity_unique', 'unique(admission_id, activity_id)', 'You can only select one schedule per activity per admission.')
    ]