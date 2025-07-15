# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _  # Added _ import here
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
        'product.product', 'res_partner_product_sport_rel', 'partner_id', 'product_id',
        string="Sport Name", domain=[('is_sportname', '=', True)])
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

    # Computed fields for student schedule information
    current_admission_id = fields.Many2one('student.admission', string='Current Admission', compute='_compute_current_admission', store=False)
    enrolled_sports = fields.Text('Enrolled Sports', compute='_compute_enrolled_sports', store=False)
    selected_schedules = fields.Text('Selected Schedules', compute='_compute_selected_schedules', store=False)
    schedule_summary = fields.Html('Schedule Summary', compute='_compute_schedule_summary', store=False)
    sports_count = fields.Integer('Sports Count', compute='_compute_sports_count', store=False)
    schedules_count = fields.Integer('Schedules Count', compute='_compute_schedules_count', store=False)

    # _sql_constraints = [
    #     ('student_national_id_unique', 'UNIQUE(student_national_id)', 'الرقم القومي للطالب يجب أن يكون فريدًا.'),
    #     ('parent_national_id_unique', 'UNIQUE(parent_national_id)', 'الرقم القومي لولي الأمر يجب أن يكون فريدًا.')
    # ]

    @api.constrains('student_national_id', 'parent_national_id', 'mobile', 'phone')
    def _check_national_id_and_mobile(self):
        for record in self:
            # Validate student_national_id (optional - only validate if provided)
            if record.student_national_id and record.student_national_id.strip():
                if not record.student_national_id.isdigit() or len(record.student_national_id) != 14:
                    raise ValidationError(_('الرقم القومي للطالب يجب أن يكون 14 رقمًا.'))
            
            # Validate parent_national_id (optional - only validate if provided)
            if record.parent_national_id and record.parent_national_id.strip():
                if not record.parent_national_id.isdigit() or len(record.parent_national_id) != 14:
                    raise ValidationError(_('الرقم القومي لولي الأمر يجب أن يكون 14 رقمًا.'))
            
            # Validate mobile (optional - only validate if provided)
            if record.mobile and record.mobile.strip():
                if not record.mobile.startswith('0') or not record.mobile.isdigit() or len(record.mobile) != 11:
                    raise ValidationError(_('رقم الجوال يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'))
            
            # Validate phone/parent_mobile (optional - only validate if provided)
            if record.phone and record.phone.strip():
                if not record.phone.startswith('0') or not record.phone.isdigit() or len(record.phone) != 11:
                    raise ValidationError(_('رقم جوال ولي الأمر يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'))

    def update_parent_privileges_or_logic(self, child_guardian, child_parking):
        """
        Update parent privileges using OR logic based on all children's privileges.
        This method should be called whenever a child's privileges change.
        """
        self.ensure_one()
        
        if not self.is_parent:
            return
        
        # Get all children of this parent
        all_children_admissions = self.env['student.admission'].search([
            ('parent_national_id', '=', self.parent_national_id),
            ('state', 'in', ['new', 'enrolled', 'student'])
        ])
        
        # Calculate OR logic: parent should have privilege if ANY child has it
        should_have_guardian = any(admission.is_guardian for admission in all_children_admissions)
        should_have_parking = any(admission.is_parking for admission in all_children_admissions)
        
        # Update parent privileges
        self.write({
            'is_guardian': should_have_guardian,
            'is_parking': should_have_parking,
        })

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

    @api.depends('is_student', 'student_national_id')
    def _compute_current_admission(self):
        """Get the most recent admission for this student"""
        for record in self:
            if record.is_student and record.student_national_id:
                admission = self.env['student.admission'].search([
                    ('student_id', '=', record.id)
                ], order='id desc', limit=1)
                record.current_admission_id = admission.id if admission else False
            else:
                record.current_admission_id = False

    @api.depends('current_admission_id', 'current_admission_id.activity_ids')
    def _compute_enrolled_sports(self):
        """Get the sports this student is enrolled in"""
        for record in self:
            if record.current_admission_id and record.current_admission_id.activity_ids:
                sports = []
                for activity in record.current_admission_id.activity_ids:
                    sports.append(activity.name)
                record.enrolled_sports = ', '.join(sports) if sports else 'No sports enrolled'
            else:
                record.enrolled_sports = 'No sports enrolled'

    @api.depends('current_admission_id')
    def _compute_selected_schedules(self):
        """Get the selected schedules for this student"""
        for record in self:
            if record.current_admission_id and record.current_admission_id.schedule_selection_ids:
                schedules = []
                for selection in record.current_admission_id.schedule_selection_ids:
                    if selection.schedule_id:
                        schedule = selection.schedule_id
                        days = ', '.join([d.name for d in schedule.day_of_week_ids])
                        start_time = self._float_to_time_string(schedule.start_time)
                        end_time = self._float_to_time_string(schedule.end_time)
                        schedules.append(f"{selection.activity_id.name}: {days} ({start_time}-{end_time})")
                record.selected_schedules = '\n'.join(schedules) if schedules else 'No schedules selected'
            else:
                record.selected_schedules = 'No schedules selected'

    @api.depends('current_admission_id', 'current_admission_id.schedule_selection_ids', 'current_admission_id.schedule_selection_ids.schedule_id')
    def _compute_schedule_summary(self):
        """Create a formatted HTML summary of the student's sports and schedules"""
        for record in self:
            if record.current_admission_id and record.current_admission_id.schedule_selection_ids:
                html_content = '<div style="margin: 10px 0;">'
                html_content += '<h4 style="color: #2E86AB; margin-bottom: 15px;">📅 Student Schedule Summary</h4>'
                
                # Group by sport activity
                sport_schedules = {}
                for selection in record.current_admission_id.schedule_selection_ids:
                    if selection.schedule_id:
                        sport_name = selection.activity_id.name
                        if sport_name not in sport_schedules:
                            sport_schedules[sport_name] = []
                        
                        schedule = selection.schedule_id
                        days = ', '.join([d.name for d in schedule.day_of_week_ids])
                        start_time = self._float_to_time_string(schedule.start_time)
                        end_time = self._float_to_time_string(schedule.end_time)
                        
                        sport_schedules[sport_name].append({
                            'days': days,
                            'time': f"{start_time} - {end_time}",
                            'capacity': schedule.capacity,
                            'available': schedule.available_spots
                        })
                
                # Create HTML for each sport
                for sport_name, schedules in sport_schedules.items():
                    html_content += f'<div style="margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9;">'
                    html_content += f'<h5 style="color: #2E86AB; margin: 0 0 10px 0;">🏃 {sport_name}</h5>'
                    
                    for schedule in schedules:
                        html_content += '<div style="margin: 5px 0; padding: 8px; background-color: white; border-radius: 4px; border-left: 4px solid #2E86AB;">'
                        html_content += f'<strong>📅 Days:</strong> {schedule["days"]}<br>'
                        html_content += f'<strong>⏰ Time:</strong> {schedule["time"]}<br>'

                        html_content += '</div>'
                    
                    html_content += '</div>'
                
                html_content += '</div>'
                record.schedule_summary = html_content
            else:
                record.schedule_summary = '<div style="margin: 10px 0; padding: 15px; background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; color: #856404;">'
                record.schedule_summary += '⚠️ No schedules selected for this student.'
                record.schedule_summary += '</div>'

    def _float_to_time_string(self, float_time):
        """Convert float time to readable string format"""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def get_schedule_summary_display(self):
        """Get a formatted summary of the student's schedules for display"""
        if not self.is_student or not self.current_admission_id:
            return "No schedule information available"
        
        admission = self.current_admission_id
        if not admission.schedule_selection_ids:
            return "No schedules selected"
        
        summary_parts = []
        for selection in admission.schedule_selection_ids:
            if selection.schedule_id:
                schedule = selection.schedule_id
                days = ', '.join([d.name for d in schedule.day_of_week_ids])
                start_time = self._float_to_time_string(schedule.start_time)
                end_time = self._float_to_time_string(schedule.end_time)
                summary_parts.append(f"• {selection.activity_id.name}: {days} ({start_time}-{end_time})")
        
        return '\n'.join(summary_parts) if summary_parts else "No schedules selected"

    def get_sports_count(self):
        """Get the number of sports this student is enrolled in"""
        if self.current_admission_id and self.current_admission_id.activity_ids:
            return len(self.current_admission_id.activity_ids)
        return 0

    def get_schedules_count(self):
        """Get the number of schedules this student has selected"""
        if self.current_admission_id and self.current_admission_id.schedule_selection_ids:
            return len(self.current_admission_id.schedule_selection_ids)
        return 0

    @api.depends('current_admission_id', 'current_admission_id.activity_ids')
    def _compute_sports_count(self):
        """Compute the number of sports this student is enrolled in"""
        for record in self:
            record.sports_count = record.get_sports_count()

    @api.depends('current_admission_id', 'current_admission_id.schedule_selection_ids')
    def _compute_schedules_count(self):
        """Compute the number of schedules this student has selected"""
        for record in self:
            record.schedules_count = record.get_schedules_count()