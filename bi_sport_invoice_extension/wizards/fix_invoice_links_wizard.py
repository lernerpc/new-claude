from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class FixInvoiceLinksWizard(models.TransientModel):
    _name = 'fix.invoice.links.wizard'
    _description = 'Fix Invoice Links Wizard'

    fix_type = fields.Selection([
        ('invoices', 'Fix Invoices'),
        ('registrations', 'Fix Registrations'),
        ('both', 'Fix Both')
    ], string='What to Fix', required=True, default='both')
    
    fix_all = fields.Boolean('Fix All Records', default=False)
    selected_invoice_ids = fields.Many2many('account.move', string='Selected Invoices')
    selected_registration_ids = fields.Many2many('student.admission', string='Selected Registrations')
    
    def action_fix(self):
        self.ensure_one()
        fixed_invoices = 0
        fixed_registrations = 0
        
        try:
            if self.fix_type in ['invoices', 'both']:
                # Fix invoices
                if self.fix_all:
                    invoices = self.env['account.move'].search([
                        '|',
                        ('invoice_origin', '!=', False),
                        ('ref', 'like', '%Registration%'),
                        ('student_admission_id', '=', False),
                        ('move_type', '=', 'out_invoice')
                    ])
                else:
                    invoices = self.selected_invoice_ids.filtered(lambda i: not i.student_admission_id)
                
                for invoice in invoices:
                    # Try to find matching student admission
                    admission = self.env['student.admission'].search([
                        '|',
                        ('name', '=', invoice.invoice_origin),
                        ('name', 'in', invoice.ref.split(' - '))
                    ], limit=1)
                    
                    if admission:
                        # Update the invoice with the admission link
                        invoice.write({
                            'student_admission_id': admission.id,
                            'pricelist_id': admission.pricelist_id.id if admission.pricelist_id else False
                        })
                        fixed_invoices += 1
                        _logger.info(f"Fixed invoice {invoice.name} -> linked to admission {admission.name}")
                
                # Trigger recomputation of invoice counts
                if fixed_invoices > 0:
                    admissions = self.env['student.admission'].search([
                        ('id', 'in', invoices.mapped('student_admission_id').ids)
                    ])
                    admissions._compute_invoice_count()
            
            if self.fix_type in ['registrations', 'both']:
                # Fix registrations
                if self.fix_all:
                    registrations = self.env['student.admission'].search([
                        '|',
                        ('state', '=', 'new'),
                        ('state', '=', 'enrolled')
                    ])
                else:
                    registrations = self.selected_registration_ids
                
                for registration in registrations:
                    # First fix the registration itself
                    registration_updates = {}
                    
                    # Set pricelist if missing
                    if not registration.pricelist_id:
                        default_pricelist = self.env['product.pricelist'].search([], limit=1)
                        if default_pricelist:
                            registration_updates['pricelist_id'] = default_pricelist.id
                    
                    # Convert old sport_id to activity_ids if needed
                    if not registration.activity_ids and registration.sport_id:
                        registration_updates['activity_ids'] = [(4, registration.sport_id.id)]
                    
                    # Apply registration updates if any
                    if registration_updates:
                        registration.write(registration_updates)
                        fixed_registrations += 1
                        _logger.info(f"Fixed registration {registration.name}")
                    
                    # Now fix any existing invoices
                    invoices = self.env['account.move'].search([
                        '|',
                        ('invoice_origin', '=', registration.name),
                        ('ref', 'like', f'%{registration.name}%'),
                        ('student_admission_id', '=', False),
                        ('move_type', '=', 'out_invoice')
                    ])
                    
                    for invoice in invoices:
                        # Update the invoice with the admission link
                        update_vals = {
                            'student_admission_id': registration.id,
                            'pricelist_id': registration.pricelist_id.id if registration.pricelist_id else False
                        }
                        
                        # Try to extract membership fee name from ref if not already set
                        if not invoice.membership_fee_name and invoice.ref:
                            try:
                                # Try different patterns for fee name extraction
                                fee_name = None
                                
                                # Pattern 1: "Invoice for FEE_NAME - REG_NAME"
                                if invoice.ref.startswith('Invoice for ') and ' - ' in invoice.ref:
                                    fee_name = invoice.ref.replace('Invoice for ', '').split(' - ')[0]
                                
                                # Pattern 2: "FEE_NAME - REG_NAME"
                                elif ' - ' in invoice.ref:
                                    fee_name = invoice.ref.split(' - ')[0]
                                
                                # Pattern 3: Just the fee name
                                else:
                                    fee_name = invoice.ref
                                
                                if fee_name:
                                    membership_fee = self.env['sport.membership.fees'].search([
                                        ('name', '=', fee_name)
                                    ], limit=1)
                                    
                                    if membership_fee:
                                        update_vals['membership_fee_name'] = membership_fee.name
                                        # Update ref to be cleaner
                                        update_vals['ref'] = f"{membership_fee.name} - {registration.name}"
                            
                            except Exception as e:
                                _logger.warning(f"Error processing ref for invoice {invoice.name}: {e}")
                        
                        # Apply the updates
                        invoice.write(update_vals)
                        fixed_invoices += 1
                        _logger.info(f"Fixed invoice {invoice.name} -> linked to registration {registration.name}")
                
                # Trigger recomputation of invoice counts
                if fixed_registrations > 0:
                    registrations._compute_invoice_count()
            
            # Show success message
            message = []
            if fixed_invoices > 0:
                message.append(f"Fixed {fixed_invoices} invoices")
            if fixed_registrations > 0:
                message.append(f"Fixed {fixed_registrations} registrations")
            
            if message:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': " and ".join(message) + "!",
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "No records needed fixing.",
                        'type': 'info',
                        'sticky': False,
                    }
                }
                
        except Exception as e:
            _logger.error(f"Error in fix wizard: {str(e)}")
            raise UserError(f"Error during fixing process: {str(e)}") 
