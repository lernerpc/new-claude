# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class PartnerSuspension(models.Model):
    """Model to track partner suspensions"""
    _name = 'partner.suspension'
    _description = 'Partner Suspension'
    _order = 'start_date desc'

    name = fields.Char('Suspension Reference', required=True, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    start_date = fields.Date('Suspension Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date('Suspension End Date', required=True)
    reason = fields.Text('Suspension Reason', required=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='active', readonly=True)
    
    # Computed fields
    is_current = fields.Boolean('Currently Suspended', compute='_compute_is_current', store=True)
    suspension_type = fields.Selection([
        ('student', 'Student Suspension'),
        ('parent', 'Parent Suspension')
    ], string='Type', compute='_compute_suspension_type', store=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('partner.suspension') or _('New')
        return super(PartnerSuspension, self).create(vals_list)
    
    @api.depends('partner_id.is_student', 'partner_id.is_parent')
    def _compute_suspension_type(self):
        for record in self:
            if record.partner_id.is_student:
                record.suspension_type = 'student'
            elif record.partner_id.is_parent:
                record.suspension_type = 'parent'
            else:
                record.suspension_type = 'student'  # default
    
    @api.depends('start_date', 'end_date', 'state')
    def _compute_is_current(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_current = (
                record.state == 'active' and 
                record.start_date <= today <= record.end_date
            )
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date >= record.end_date:
                raise ValidationError(_('End date must be after start date.'))
    
    def action_cancel_suspension(self):
        """Cancel the suspension"""
        self.state = 'cancelled'
        # Recompute partner suspension status
        self.partner_id._compute_suspension_status()
    
    @api.model
    def check_expired_suspensions(self):
        """Cron job to automatically expire suspensions"""
        today = fields.Date.context_today(self)
        expired_suspensions = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        
        for suspension in expired_suspensions:
            suspension.state = 'expired'
            # Recompute partner suspension status
            suspension.partner_id._compute_suspension_status()
            
            _logger.info("Suspension %s for partner %s has expired", 
                        suspension.name, suspension.partner_id.name)


class ResPartnerSuspension(models.Model):
    """Extend res.partner with suspension functionality"""
    _inherit = 'res.partner'
    
    # Suspension fields
    is_suspended = fields.Boolean('Currently Suspended', compute='_compute_suspension_status', store=True)
    suspension_count = fields.Integer('Suspension Count', compute='_compute_suspension_count', store=True)
    suspension_ids = fields.One2many('partner.suspension', 'partner_id', string='Suspensions')
    current_suspension_id = fields.Many2one('partner.suspension', string='Current Suspension', 
                                          compute='_compute_suspension_status', store=True)
    suspension_reason = fields.Text('Current Suspension Reason', 
                                   related='current_suspension_id.reason', readonly=True)
    suspension_end_date = fields.Date('Suspension End Date', 
                                     related='current_suspension_id.end_date', readonly=True)
    
    # HTML field for displaying suspension status in tree view
    suspension_status_display = fields.Html('Suspension Status', compute='_compute_suspension_status_display', store=False)
    
    @api.depends('is_suspended', 'suspension_end_date', 'suspension_reason')
    def _compute_suspension_status_display(self):
        """Compute HTML display for suspension status in tree view"""
        for record in self:
            if record.is_suspended:
                # Create red suspension tag
                end_date = record.suspension_end_date.strftime('%d/%m/%Y') if record.suspension_end_date else 'N/A'
                reason = record.suspension_reason[:30] + '...' if record.suspension_reason and len(record.suspension_reason) > 30 else (record.suspension_reason or 'No reason')
                
                record.suspension_status_display = f'''
                <span style="display: inline-block; background-color: #dc3545; color: white; padding: 4px 8px; 
                            border-radius: 12px; font-size: 11px; font-weight: bold; margin: 2px;">
                    🚫 SUSPENDED
                </span>
                <br/>
                <small style="color: #6c757d;">Until: {end_date}</small>
                '''
            else:
                # Show green "Active" tag
                record.suspension_status_display = '''
                <span style="display: inline-block; background-color: #28a745; color: white; padding: 4px 8px; 
                            border-radius: 12px; font-size: 11px; font-weight: bold; margin: 2px;">
                    ✅ ACTIVE
                </span>
                '''
    
    @api.depends('suspension_ids.is_current', 'suspension_ids.state')
    def _compute_suspension_status(self):
        for record in self:
            current_suspension = record.suspension_ids.filtered(
                lambda s: s.state == 'active' and s.is_current
            )
            
            if current_suspension:
                record.is_suspended = True
                record.current_suspension_id = current_suspension[0]
            else:
                record.is_suspended = False
                record.current_suspension_id = False
    
    @api.depends('suspension_ids')
    def _compute_suspension_count(self):
        for record in self:
            record.suspension_count = len(record.suspension_ids)
    
    def action_suspend_partner(self):
        """Open suspension wizard"""
        return {
            'name': 'Suspend Partner',
            'type': 'ir.actions.act_window',
            'res_model': 'partner.suspension.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_suspension_type': 'student' if self.is_student else 'parent'
            }
        }
    
    def action_view_suspensions(self):
        """View all suspensions for this partner"""
        return {
            'name': f'Suspensions - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'partner.suspension',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }


class StudentAdmissionSuspension(models.Model):
    """Extend student.admission with suspension functionality"""
    _inherit = 'student.admission'
    
    # Suspension fields
    is_suspended = fields.Boolean('Currently Suspended', 
                                 related='student_id.is_suspended', readonly=True)
    suspension_count = fields.Integer('Suspension Count', 
                                     related='student_id.suspension_count', readonly=True)
    suspension_reason = fields.Text('Current Suspension Reason', 
                                   related='student_id.suspension_reason', readonly=True)
    suspension_end_date = fields.Date('Suspension End Date', 
                                     related='student_id.suspension_end_date', readonly=True)
    
    # HTML field for displaying suspension status in tree view
    suspension_status_display = fields.Html('Suspension Status', compute='_compute_suspension_status_display', store=False)
    
    @api.depends('is_suspended', 'suspension_end_date', 'suspension_reason')
    def _compute_suspension_status_display(self):
        """Compute HTML display for suspension status in tree view"""
        for record in self:
            if record.is_suspended:
                # Create red suspension tag
                end_date = record.suspension_end_date.strftime('%d/%m/%Y') if record.suspension_end_date else 'N/A'
                reason = record.suspension_reason[:30] + '...' if record.suspension_reason and len(record.suspension_reason) > 30 else (record.suspension_reason or 'No reason')
                
                record.suspension_status_display = f'''
                <span style="display: inline-block; background-color: #dc3545; color: white; padding: 4px 8px; 
                            border-radius: 12px; font-size: 11px; font-weight: bold; margin: 2px;">
                    🚫 SUSPENDED
                </span>
                <br/>
                <small style="color: #6c757d;">Until: {end_date}</small>
                '''
            else:
                # Show green "Active" tag
                record.suspension_status_display = '''
                <span style="display: inline-block; background-color: #28a745; color: white; padding: 4px 8px; 
                            border-radius: 12px; font-size: 11px; font-weight: bold; margin: 2px;">
                    ✅ ACTIVE
                </span>
                '''
    
    def action_suspend_student(self):
        """Suspend the student"""
        return self.student_id.action_suspend_partner()
    
    def action_view_suspensions(self):
        """View suspensions for this student"""
        return self.student_id.action_view_suspensions()


class PartnerSuspensionWizard(models.TransientModel):
    """Wizard to create suspensions"""
    _name = 'partner.suspension.wizard'
    _description = 'Partner Suspension Wizard'
    
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    start_date = fields.Date('Suspension Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date('Suspension End Date', required=True)
    reason = fields.Text('Suspension Reason', required=True, 
                        placeholder="Enter the reason for suspension...")
    suspension_type = fields.Selection([
        ('student', 'Student Suspension'),
        ('parent', 'Parent Suspension')
    ], string='Type', default='student')
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date >= record.end_date:
                raise ValidationError(_('End date must be after start date.'))
    
    def action_confirm_suspension(self):
        """Create the suspension"""
        suspension = self.env['partner.suspension'].create({
            'partner_id': self.partner_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'reason': self.reason,
        })
        
        # Show success message and close wizard
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Suspension Created',
                'message': f'{self.partner_id.name} has been suspended until {self.end_date}',
                'type': 'success',
            }
        }


# Data file content for sequences and cron job
DATA_XML = '''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Sequence for suspension references -->
    <record id="sequence_partner_suspension" model="ir.sequence">
        <field name="name">Partner Suspension</field>
        <field name="code">partner.suspension</field>
        <field name="prefix">SUSP</field>
        <field name="padding">4</field>
        <field name="number_next">1</field>
        <field name="number_increment">1</field>
    </record>
    
    <!-- Cron job to check expired suspensions -->
    <record id="cron_check_expired_suspensions" model="ir.cron">
        <field name="name">Check Expired Suspensions</field>
        <field name="model_id" ref="model_partner_suspension"/>
        <field name="state">code</field>
        <field name="code">model.check_expired_suspensions()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">days</field>
        <field name="numbercall">-1</field>
        <field name="active" eval="True"/>
    </record>
</odoo>
'''