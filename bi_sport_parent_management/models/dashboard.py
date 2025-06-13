from odoo import fields, models, api

class SportDashboard(models.TransientModel):
    _name = 'sport.dashboard'
    _description = 'Sports Dashboard'

    @api.model
    def get_dashboard_data(self):
        return {
            'total_inquiries': self.env['student.inquiry'].search_count([]),  # Updated to bi_sport_center_management model
            'total_students': self.env['res.partner'].search_count([('is_student', '=', True)]),
            'total_trainers': self.env['res.partner'].search_count([('is_coach', '=', True)]),
            'total_center_events': self.env['event.event'].search_count([]),  # Updated to Odoo core model
            'total_center_spaces': self.env['product.product'].search_count([('is_space', '=', True)]),
            'total_sports': self.env['product.product'].search_count([('is_sportname', '=', True)]),
            'total_bookings': self.env['center.booking'].search_count([]),
            'total_confirm_admissions': self.env['student.admission'].search_count([('state', '=', 'student')]),  # Adjusted state
            'total_equipment': self.env['product.product'].search_count([('is_equipment', '=', True)]),
        }
