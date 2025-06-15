import logging
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from datetime import date

_logger = logging.getLogger(__name__)

class StudentAdmission(models.Model):
    _inherit = 'student.admission'

    # Override the invoice_ids field to use proper One2many relationship
    invoice_ids = fields.One2many('account.move', 'student_admission_id', string='Invoices')

    # Override invoice_count to use the One2many relationship
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        """Compute invoice count using the One2many relationship"""
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    def action_view_invoice(self):
        """Action to view invoices related to this student admission"""
        self.ensure_one()

        # Use the One2many relationship directly
        invoices = self.invoice_ids

        action = {
            'name': _('Student Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', invoices.ids)],
            'context': {
                'default_move_type': 'out_invoice',
                'default_partner_id': self.student_id.id,
                'search_default_open': 1,
            }
        }

        # If there's only one invoice, open it directly in form view
        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoices.id,
                'views': [(False, 'form')],
            })

        return action

    def _ensure_fiscal_parent_setup(self):
        """Ensure proper fiscal parent relationship is set up"""
        self.ensure_one()
        
        if self.parent_id and self.student_id:
            # Ensure parent is marked as company
            if not self.parent_id.is_company:
                self.parent_id.write({'is_company': True})
                _logger.info(f"Set {self.parent_id.name} as company for proper parent-child relationship")
            
            # Ensure student is NOT a company
            if self.student_id.is_company:
                self.student_id.write({'is_company': False})
                _logger.info(f"Set {self.student_id.name} as individual (not company)")
            
            # Set fiscal parent relationship
            if self.student_id.parent_id != self.parent_id:
                old_parent = self.student_id.parent_id.name if self.student_id.parent_id else 'None'
                self.student_id.write({'parent_id': self.parent_id.id})
                _logger.info(f"Set fiscal parent for {self.student_id.name}: {old_parent} → {self.parent_id.name}")
                
                # Add a note on the student partner
                self.student_id.message_post(
                    body=f"Fiscal parent set to {self.parent_id.name} for consolidated billing and portal access."
                )

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

            # IMPORTANT: Set up fiscal parent relationship before creating invoices
            self._ensure_fiscal_parent_setup()

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

                # ALWAYS create invoice on student account
                invoice_vals = {
                    'invoice_origin': self.name or '',
                    'move_type': 'out_invoice',
                    'ref': f"Invoice for {fee.name} - {self.name}",
                    'journal_id': sale_journals.id,
                    'partner_id': self.student_id.id,  # ✅ ALWAYS use student as invoice partner
                    'invoice_date': today,
                    'invoice_date_due': fee.start_date,
                    'currency_id': self.student_id.currency_id.id or self.env.company.currency_id.id,
                    'company_id': self.env.company.id,
                    'student_admission_id': self.id,
                    # Don't set name here - let Odoo handle it in create()
                }
                
                # Add a note about parent if exists
                if self.parent_id:
                    invoice_vals['narration'] = f"Student: {self.student_id.name}\nParent/Guardian: {self.parent_id.name}"
                
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

                    # Apply pricelist for sport products - use student for pricing
                    price = pricelist_to_use._get_product_price(
                        product=sport_product,
                        quantity=1.0,
                        partner=self.student_id,  # Use student for pricing
                        date=today,
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

                        # Apply pricelist for fee-specific products - use student for pricing
                        price = pricelist_to_use._get_product_price(
                            product=product,
                            quantity=1.0,
                            partner=self.student_id,  # Use student for pricing
                            date=today,
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
                    _logger.info("Created invoice: %s (ID: %s) for fee %s and admission %s on student %s", 
                                invoice.name, invoice.id, fee.name, self.name, self.student_id.name)
                    
                    # Add a message to the invoice about the parent
                    if self.parent_id:
                        invoice.message_post(
                            body=f"This invoice is for student {self.student_id.name}. "
                                 f"Parent/Guardian: {self.parent_id.name} (has portal access through fiscal parent relationship)."
                        )
                else:
                    _logger.warning(f"No invoice lines generated for fee {fee.name} for admission {self.name}. Skipping invoice creation for this fee.")

            if not created_invoices:
                raise ValidationError(_('No invoices were created. Please ensure there are activities selected and/or fees with products.'))

            self.is_invoiced = True
            _logger.info(f"Successfully created {len(created_invoices)} invoices for admission {self.name}")

            # Send notification to parent if exists
            if self.parent_id and self.parent_id.email:
                # Log that parent will be notified
                _logger.info(f"Parent {self.parent_id.name} will be notified about invoices for their child {self.student_id.name}")

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
