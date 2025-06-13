import logging
from odoo import models, api, fields, _ 
from odoo.exceptions import ValidationError
from datetime import date

_logger = logging.getLogger(__name__)

class StudentAdmission(models.Model):
    _inherit = 'student.admission'

    # Use proper One2many with inverse field - this is FAST for 1000+ students
    invoice_ids = fields.One2many('account.move', 'student_admission_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count', store=True)

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        """Compute invoice count - this is fast because invoice_ids is stored"""
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    def action_make_invoice(self):
        self.ensure_one()
        _logger.info("Starting action_make_invoice to create multiple invoices (one per fee) with pricelist for admission: %s", self.name)

        try:
            if not self.student_id:
                raise ValidationError(_('Student not found for this admission!'))

            pricelist_to_use = self.pricelist_id
            if not pricelist_to_use:
                _logger.error("No pricelist found on student admission record %s. Cannot create invoice.", self.name)
                raise ValidationError(_('No pricelist found on the student admission record!'))

            _logger.info("Using pricelist: %s (ID: %s) for admission %s", pricelist_to_use.name, pricelist_to_use.id, self.name)

            # Fetch membership fees, sorted by sequence_id
            fees = self.env['sport.membership.fees'].search([], order='sequence_id asc')
            _logger.info(f"Found {len(fees)} fees: {fees.mapped('name')}")

            if not fees:
                _logger.info("No membership fees found, cannot proceed with invoice creation")
                raise ValidationError(_("No membership fees configured. Please contact administrator."))

            if not self.activity_ids:
                _logger.error(f"No sports assigned to admission {self.name}")
                raise ValidationError(_("Student has no sports assigned. Please select at least one sport before creating an invoice."))

            sale_journals = self.env['account.journal'].sudo().search([('type', '=', 'sale')], limit=1)
            if not sale_journals:
                raise ValidationError(_('No sale journal found!'))

            created_invoices = self.env['account.move']

            # Create one invoice per fee
            for fee in fees:
                # Use today's date for invoice_date to avoid sequence mismatch, but keep due date as fee start date
                today = date.today()
                
                # Prepare invoice values with proper date handling
                invoice_vals = {
                    'invoice_origin': self.name or '',
                    'move_type': 'out_invoice',
                    'ref': f"Invoice for {fee.name} - {self.name}",
                    'journal_id': sale_journals.id,
                    'partner_id': self.parent_id.id if self.parent_id else self.student_id.id,
                    'invoice_date': today,  # ✅ Use today to match sequence numbering
                    'invoice_date_due': fee.start_date,  # ✅ Use membership fee start date for due date
                    'currency_id': self.student_id.currency_id.id or self.env.company.currency_id.id,
                    'company_id': self.env.company.id,
                    'student_admission_id': self.id,  # ✅ Set the inverse relationship
                    # Don't set name here - let Odoo handle it in create()
                }
                _logger.debug("Invoice header values for fee %s: %s", fee.name, invoice_vals)

                invoice_lines = []

                # Add lines for all sports/activities (activity_ids)
                for sport_product in self.activity_ids:
                    if not sport_product.is_sportname:
                        _logger.warning(f"Skipping non-sport product in activities for fee {fee.name}: {sport_product.name}")
                        continue

                    # Check if product has is_guardian tag and skip if guardian is not true
                    if self._should_skip_product_based_on_guardian(sport_product):
                        _logger.info(f"Skipping sport product '{sport_product.name}' for fee {fee.name} due to guardian requirement not met")
                        continue

                    # Apply pricelist for sport products using today's date for consistency
                    price = pricelist_to_use._get_product_price(
                        product=sport_product,
                        quantity=1.0,
                        partner=invoice_vals['partner_id'],
                        date=today,  # ✅ Use today for pricing consistency
                    )
                    final_price_unit_sport = price if price else sport_product.lst_price
                    _logger.info("Price for sport '%s' (Fee: %s): %s (Pricelist: %s, List: %s)",
                                 sport_product.name, fee.name, final_price_unit_sport, price, sport_product.lst_price)

                    invoice_lines.append((0, 0, {
                        'product_id': sport_product.id,
                        'name': f"{sport_product.name} - {fee.name}",
                        'product_uom_id': sport_product.uom_id.id,
                        'price_unit': final_price_unit_sport,
                        'quantity': 1.0,
                    }))

                # Add lines for the fee's specific products (if any)
                if fee.product_ids:
                    for product in fee.product_ids:
                        # Check if product has is_guardian tag and skip if guardian is not true
                        if self._should_skip_product_based_on_guardian(product):
                            _logger.info(f"Skipping fee product '{product.name}' for fee {fee.name} due to guardian requirement not met")
                            continue

                        # Apply pricelist for fee-specific products using today's date
                        price = pricelist_to_use._get_product_price(
                            product=product,
                            quantity=1.0,
                            partner=invoice_vals['partner_id'],
                            date=today,  # ✅ Use today for pricing consistency
                        )
                        final_price_unit_fee_product = price if price else product.lst_price
                        _logger.info("Price for fee product '%s' (Fee: %s): %s (Pricelist: %s, List: %s)",
                                     product.name, fee.name, final_price_unit_fee_product, price, product.lst_price)

                        invoice_lines.append((0, 0, {
                            'product_id': product.id,
                            'name': f"{product.name} - {fee.name}",
                            'product_uom_id': product.uom_id.id,
                            'price_unit': final_price_unit_fee_product,
                            'quantity': 1,
                        }))
                else:
                    _logger.info(f"No specific products configured for fee {fee.name}")

                # Create the invoice only if there are lines to add
                if invoice_lines:
                    invoice_vals['invoice_line_ids'] = invoice_lines
                    
                    # Add pricelist_id to the invoice for our extension
                    invoice_vals['pricelist_id'] = pricelist_to_use.id
                    
                    invoice = self.env['account.move'].sudo().create(invoice_vals)
                    created_invoices += invoice
                    _logger.info("Created invoice: %s (ID: %s) for fee %s and admission %s", invoice.name, invoice.id, fee.name, self.name)
                else:
                    _logger.warning(f"No invoice lines generated for fee {fee.name} for admission {self.name}. Skipping invoice creation for this fee.")

            if not created_invoices:
                raise ValidationError(_('No invoices were created. Please ensure there are activities selected and/or fees with products.'))

            self.is_invoiced = True
            _logger.info(f"Successfully created {len(created_invoices)} invoices for admission {self.name}")

            # Return action to view all created invoices
            return {
                'name': 'Created Invoices',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_invoices.ids)],
                'target': 'current',
            }

        except ValidationError:
            # Re-raise ValidationError directly
            raise
        except Exception as e:
            _logger.error("An unexpected error occurred while creating invoices for admission %s: %s", self.name, str(e))
            raise ValidationError(f"An unexpected error occurred: {str(e)}. Please contact your administrator.")

    def _should_skip_product_based_on_guardian(self, product):
        """
        Check if a product should be skipped based on guardian requirements.
        Returns True if the product should be skipped, False otherwise.
        """
        # Check if the product has the 'is_guardian' tag
        guardian_tag = self.env['product.tag'].search([('name', '=', 'is_guardian')], limit=1)
        
        if guardian_tag and guardian_tag in product.product_tag_ids:
            # Product has is_guardian tag - only include if student admission has is_guardian = True
            if not getattr(self, 'is_guardian', False):
                _logger.info(f"Product '{product.name}' has 'is_guardian' tag but student admission is_guardian is False. Skipping product.")
                return True
        
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('activity_ids'):
                raise ValidationError("Sport/Activity is required. Please select at least one sport before proceeding.")
        return super(StudentAdmission, self).create(vals_list)

# This CreateInvoice class is part of bi_sport_invoice_extension,
# and it's the one that gets called by the button.
class CreateInvoice(models.Model):
    _inherit = 'create.invoice'

    def action_create_invoice(self):
        try:
            admission_id = self.env['student.admission'].browse(self._context.get('active_id'))
            if not admission_id:
                raise ValidationError('Admission Registration not found!')

            _logger.info(f"Wizard 'create.invoice' triggering action_make_invoice for admission {admission_id.name}")
            return admission_id.action_make_invoice()
        except ValidationError:
            raise
        except Exception as e:
            _logger.error(f"Error in create invoice wizard: {str(e)}")
            raise ValidationError(f"Error creating invoice: {str(e)}")
