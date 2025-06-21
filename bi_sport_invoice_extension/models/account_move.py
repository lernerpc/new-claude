# /victory/custom/addons/bi_sport_invoice_extension/models/account_move.py
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Add the pricelist_id field to the invoice model
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        help="Pricelist used for this invoice. Can be automatically set from the partner or admission."
    )

    # Add field to store membership fee name for display purposes
    membership_fee_name = fields.Char(
        string='Membership Fee',
        readonly=True,
        help="Name of the membership fee used for this invoice"
    )

    # Add computed field for display name that combines invoice number with fee name
    display_name_with_fee = fields.Char(
        string='Invoice Reference',
        compute='_compute_display_name_with_fee',
        store=True
    )

    # Add the inverse field for the One2many relationship
    student_admission_id = fields.Many2one(
        'student.admission',
        string='Student Admission',
        help="Related student admission record"
    )

    @api.depends('name', 'membership_fee_name')
    def _compute_display_name_with_fee(self):
        for record in self:
            if record.name and record.membership_fee_name:
                record.display_name_with_fee = f"{record.membership_fee_name} - {record.name}"
            else:
                record.display_name_with_fee = record.name or '/'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            _logger.info(f"🔍 Creating invoice with vals: invoice_origin={vals.get('invoice_origin')}, ref={vals.get('ref')}, move_type={vals.get('move_type')}")

            # Check if this invoice is from student admission and has a reference containing fee info
            if vals.get('invoice_origin') and vals.get('ref'):
                _logger.info(f"🔍 Found invoice_origin and ref, searching for admission...")

                # Find the student admission record by name/origin
                admission = self.env['student.admission'].search([
                    ('name', '=', vals.get('invoice_origin'))
                ], limit=1)

                _logger.info(f"🔍 Found admission: {admission.name if admission else 'None'}")

                if admission:
                    # Set the student_admission_id for the inverse relationship
                    vals['student_admission_id'] = admission.id

                    # Extract fee name from ref (format: "Invoice for {fee_name} - {admission_name}")
                    ref = vals.get('ref', '')
                    _logger.info(f"🔍 Processing ref: {ref}")

                    if ref.startswith('Invoice for ') and ' - ' in ref:
                        _logger.info(f"🔍 Found invoice pattern in ref")

                        try:
                            # Extract fee name from "Invoice for {fee_name} - {admission_name}"
                            fee_part = ref.replace('Invoice for ', '').split(' - ')[0]
                            _logger.info(f"🔍 Extracted fee_part: {fee_part}")

                            # Find membership fee by name
                            membership_fee = self.env['sport.membership.fees'].search([
                                ('name', '=', fee_part)
                            ], limit=1)

                            _logger.info(f"🔍 Found membership fee: {membership_fee.name if membership_fee else 'None'}")

                            if membership_fee:
                                # Store membership fee name for display
                                vals['membership_fee_name'] = membership_fee.name
                                _logger.info(f"🔍 Set membership_fee_name: {membership_fee.name}")

                                # Update the ref to be cleaner (this is the reference field, not the number)
                                vals['ref'] = f"{membership_fee.name} - {admission.name}"
                                _logger.info(f"🔍 Updated ref to: {vals['ref']}")

                            else:
                                _logger.warning(f"❌ No membership fee found with name: {fee_part}")

                        except (ValueError, IndexError) as e:
                            _logger.error(f"❌ Error parsing ref: {ref}. Error: {e}")
                    else:
                        _logger.info(f"❌ Invoice pattern not found in ref: {ref}")
                else:
                    _logger.info(f"❌ No admission found with name: {vals.get('invoice_origin')}")
            else:
                _logger.info(f"❌ Missing invoice_origin or ref")

        # Create the invoices and let Odoo handle naming naturally
        invoices = super().create(vals_list)

        # Log what was created
        for invoice in invoices:
            if invoice.membership_fee_name:
                _logger.info(f"✅ Created invoice: {invoice.name} for fee: {invoice.membership_fee_name}")

        return invoices

    def _get_sequence(self):
        """Override to ensure proper sequence handling for invoices"""
        self.ensure_one()
        # For customer invoices, ensure we use the correct sequence
        if self.move_type == 'out_invoice':
            journal = self.journal_id
            if journal.sequence_id:
                return journal.sequence_id
            # Fallback to the default invoice sequence
            return self.env['ir.sequence'].search([
                ('code', '=', 'account.move'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        return super()._get_sequence()

    def action_recompute_prices_from_pricelist(self):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_("Prices can only be recomputed on draft invoices."))

        if not self.pricelist_id:
            raise ValidationError(_("No pricelist found on this invoice to recompute prices."))

        _logger.info("Recalculating prices for invoice %s using pricelist %s", self.name, self.pricelist_id.name)

        for line in self.invoice_line_ids:
            if line.product_id:
                # Get the new price from the pricelist
                new_price = self.pricelist_id._get_product_price(
                    product=line.product_id,
                    quantity=line.quantity,
                    partner=self.partner_id,
                    date=self.invoice_date or fields.Date.today(),
                )
                # Apply the new price if it's different and valid
                if new_price is not False and new_price != line.price_unit:
                    _logger.debug("Updating price for product %s from %s to %s on invoice %s",
                                 line.product_id.name, line.price_unit, new_price, self.name)
                    line.write({'price_unit': new_price})
                elif new_price is False:
                    _logger.warning("Pricelist %s returned no specific price for product %s on invoice %s. Keeping original price %s.",
                                    self.pricelist_id.name, line.product_id.name, self.name, line.price_unit)

        _logger.info("Finished recalculating prices for invoice %s", self.name)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Prices recomputed successfully!"),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def fix_existing_invoice_links(self):
        """
        Method to fix existing invoices that were created before the student_admission_id link was implemented.
        This will search for invoices with invoice_origin matching student admissions and link them.
        """
        _logger.info("🔧 Starting to fix existing invoice links...")
        
        # Find all invoices that have invoice_origin but no student_admission_id
        unlinked_invoices = self.search([
            ('invoice_origin', '!=', False),
            ('student_admission_id', '=', False),
            ('move_type', '=', 'out_invoice')
        ])
        
        _logger.info(f"🔧 Found {len(unlinked_invoices)} unlinked invoices to process")
        
        fixed_count = 0
        for invoice in unlinked_invoices:
            # Try to find matching student admission
            admission = self.env['student.admission'].search([
                ('name', '=', invoice.invoice_origin)
            ], limit=1)
            
            if admission:
                # Update the invoice with the admission link
                update_vals = {'student_admission_id': admission.id}
                
                # Also try to extract membership fee name from ref if not already set
                if not invoice.membership_fee_name and invoice.ref:
                    try:
                        if invoice.ref.startswith('Invoice for ') and ' - ' in invoice.ref:
                            fee_part = invoice.ref.replace('Invoice for ', '').split(' - ')[0]
                            membership_fee = self.env['sport.membership.fees'].search([
                                ('name', '=', fee_part)
                            ], limit=1)
                            
                            if membership_fee:
                                update_vals['membership_fee_name'] = membership_fee.name
                                # Also update ref to be cleaner
                                update_vals['ref'] = f"{membership_fee.name} - {admission.name}"
                        
                        # If ref doesn't follow the pattern but contains a fee name, try to match it
                        elif ' - ' in invoice.ref:
                            potential_fee_name = invoice.ref.split(' - ')[0]
                            membership_fee = self.env['sport.membership.fees'].search([
                                ('name', '=', potential_fee_name)
                            ], limit=1)
                            
                            if membership_fee:
                                update_vals['membership_fee_name'] = membership_fee.name
                    
                    except Exception as e:
                        _logger.warning(f"🔧 Error processing ref for invoice {invoice.name}: {e}")
                
                # Apply the updates
                invoice.write(update_vals)
                fixed_count += 1
                
                _logger.info(f"🔧 Fixed invoice {invoice.name} -> linked to admission {admission.name}")
            else:
                _logger.warning(f"🔧 No admission found for invoice {invoice.name} with origin {invoice.invoice_origin}")
        
        _logger.info(f"🔧 Fixed {fixed_count} invoices successfully!")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Fixed {fixed_count} existing invoices! They are now properly linked to their student admissions.",
                'type': 'success',
                'sticky': True,
            }
        }

    def action_fix_invoice_link(self):
        """
        Action to fix a single invoice's link to student admission
        """
        self.ensure_one()
        
        if self.student_admission_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "This invoice is already linked to a student admission.",
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        if not self.invoice_origin:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "No invoice origin found. Cannot link to student admission.",
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Try to find matching student admission
        admission = self.env['student.admission'].search([
            ('name', '=', self.invoice_origin)
        ], limit=1)
        
        if admission:
            update_vals = {'student_admission_id': admission.id}
            
            # Also try to extract membership fee name from ref if not already set
            if not self.membership_fee_name and self.ref:
                try:
                    if self.ref.startswith('Invoice for ') and ' - ' in self.ref:
                        fee_part = self.ref.replace('Invoice for ', '').split(' - ')[0]
                        membership_fee = self.env['sport.membership.fees'].search([
                            ('name', '=', fee_part)
                        ], limit=1)
                        
                        if membership_fee:
                            update_vals['membership_fee_name'] = membership_fee.name
                            update_vals['ref'] = f"{membership_fee.name} - {admission.name}"
                    
                    elif ' - ' in self.ref:
                        potential_fee_name = self.ref.split(' - ')[0]
                        membership_fee = self.env['sport.membership.fees'].search([
                            ('name', '=', potential_fee_name)
                        ], limit=1)
                        
                        if membership_fee:
                            update_vals['membership_fee_name'] = membership_fee.name
                
                except Exception as e:
                    _logger.warning(f"Error processing ref for invoice {self.name}: {e}")
            
            self.write(update_vals)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"Successfully linked invoice to student admission {admission.name}!",
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"No student admission found with name: {self.invoice_origin}",
                    'type': 'warning',
                    'sticky': False,
                }
            }




    def _compute_payments_widget_reconciled_info(self):
        """Override to trigger student admission payment date update"""
        result = super()._compute_payments_widget_reconciled_info()
        
        # Update payment dates for related student admissions when payment state changes
        for move in self:
            if move.invoice_origin and move.move_type == 'out_invoice':
                # Find related student admission by invoice_origin
                admission = self.env['student.admission'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                if admission:
                    # Trigger recomputation of payment state and date
                    admission._compute_payment_state()
        
        return result
    
    def _reconcile_payments(self, writeoff_acc_id=False, writeoff_journal_id=False):
        """Override to update student admission payment date when reconciliation occurs"""
        result = super()._reconcile_payments(writeoff_acc_id, writeoff_journal_id)
        
        # Update payment dates for related student admissions
        for move in self:
            if move.invoice_origin and move.move_type == 'out_invoice':
                admission = self.env['student.admission'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                if admission:
                    admission._compute_payment_state()
        
        return result

    def js_assign_outstanding_line(self, line_id):
        """Override to update payment date when outstanding line is assigned"""
        result = super().js_assign_outstanding_line(line_id)
        
        # Update payment date for related student admission
        if self.invoice_origin and self.move_type == 'out_invoice':
            admission = self.env['student.admission'].search([
                ('name', '=', self.invoice_origin)
            ], limit=1)
            if admission:
                admission._compute_payment_state()
        
        return result

    def js_remove_outstanding_partial(self, partial_id):
        """Override to update payment date when outstanding partial is removed"""
        result = super().js_remove_outstanding_partial(partial_id)
        
        # Update payment date for related student admission
        if self.invoice_origin and self.move_type == 'out_invoice':
            admission = self.env['student.admission'].search([
                ('name', '=', self.invoice_origin)
            ], limit=1)
            if admission:
                admission._compute_payment_state()
        
        return result

    def action_post(self):
        """Override to update admission payment state when invoice is posted"""
        result = super().action_post()
        
        # Update payment state for related admissions when invoice is posted
        for move in self:
            if move.invoice_origin and move.move_type == 'out_invoice':
                admission = self.env['student.admission'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                if admission:
                    admission._compute_payment_state()
        
        return result

    def write(self, vals):
        """Override write to trigger payment date update when payment state changes"""
        result = super().write(vals)
        
        # If payment_state or reconciliation changed, update student admission
        if 'payment_state' in vals or any('reconciled' in str(k) for k in vals.keys()):
            for move in self:
                if move.invoice_origin and move.move_type == 'out_invoice':
                    admission = self.env['student.admission'].search([
                        ('name', '=', move.invoice_origin)
                    ], limit=1)
                    if admission:
                        # Use sudo to avoid access issues and force recomputation
                        admission.sudo()._compute_payment_state()
        
        return result


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        """Override to update student admission payment dates when payment is posted"""
        result = super().action_post()
        
        # Update student admissions when payment is reconciled with invoices
        for payment in self:
            if payment.reconciled_invoice_ids:
                for invoice in payment.reconciled_invoice_ids:
                    if invoice.invoice_origin and invoice.move_type == 'out_invoice':
                        admission = self.env['student.admission'].search([
                            ('name', '=', invoice.invoice_origin)
                        ], limit=1)
                        if admission:
                            admission.sudo()._compute_payment_state()
        
        return result