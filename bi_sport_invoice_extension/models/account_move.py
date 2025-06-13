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

            # IMPORTANT: Do NOT set 'name' field - let Odoo handle it
            if 'name' in vals:
                vals.pop('name')

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

    def action_post(self):
        """Override to ensure proper sequence is set before posting"""
        # For invoices, ensure they use the INV sequence
        for move in self:
            if move.move_type == 'out_invoice' and move.state == 'draft':
                if not move.name or move.name == '/' or 'TEMP' in str(move.name):
                    # Get the INV sequence
                    sequence = self.env['ir.sequence'].search([
                        ('code', '=', 'account.move.INV')
                    ], limit=1)
                    
                    if sequence:
                        # Generate the next number
                        move.name = sequence.next_by_id(sequence_date=move.date)
                    else:
                        # Fallback to default behavior
                        move.name = '/'
                        
        return super().action_post()

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
