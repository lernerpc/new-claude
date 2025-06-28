from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_parent = fields.Boolean(string="Is Parent")
    is_student = fields.Boolean(string="Is Student")
    is_guardian = fields.Boolean(string="Is Guardian")
    is_parking = fields.Boolean(string="Has Parking")
    printed = fields.Boolean(string="Printed")
    first_print_date = fields.Datetime(string="First Print Date")
    last_print_date = fields.Datetime(string="Last Print Date")
    tag_ids = fields.Many2many('partner.tag', string="Partner Tags")
    parent_image_1920 = fields.Image(string="Parent Image")
    trainer_id = fields.Many2one('res.partner', string="Current Trainer")
    is_coach = fields.Boolean(string="Is Coach")
    sport_id = fields.Many2many('product.product', string="Sports", domain=[('is_sportname', '=', True)])
    is_disability = fields.Boolean(string="Has Disability")
    disability_description = fields.Text(string="Disability Description")
    is_sport = fields.Boolean(string="Is Sport", readonly=True)

    # Invoice related fields - Keep original One2many but fix the count and payment state logic
    invoice_ids = fields.One2many('account.move', 'partner_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')

    # Children count field
    children_count = fields.Integer(compute='_compute_children_count', string='Children Count')

    # Payment status field
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
        help="Date of the latest payment for this partner"
    )

    def update_parent_privileges_or_logic(self, new_guardian, new_parking):
        """
        Update parent privileges using OR logic to never downgrade privileges.
        If parent currently has a privilege OR the new child has it, keep it True.
        """
        self.ensure_one()
        if not self.is_parent:
            _logger.warning("Attempted to update parent privileges on non-parent record: %s", self.name)
            return

        # Get current values
        current_guardian = self.is_guardian or False
        current_parking = self.is_parking or False

        # Apply OR logic (True if current OR new is True)
        final_guardian = current_guardian or new_guardian
        final_parking = current_parking or new_parking

        _logger.info("Parent privilege update for %s (ID: %s):", self.name, self.id)
        _logger.info("  Current: Guardian=%s, Parking=%s", current_guardian, current_parking)
        _logger.info("  New child: Guardian=%s, Parking=%s", new_guardian, new_parking)
        _logger.info("  Final (OR logic): Guardian=%s, Parking=%s", final_guardian, final_parking)

        # Use SQL update directly to ensure it works
        try:
            self.env.cr.execute("""
                UPDATE res_partner
                SET is_guardian = %s, is_parking = %s
                WHERE id = %s
            """, (final_guardian, final_parking, self.id))

            self.env.cr.commit()

            # Verify with SQL query
            self.env.cr.execute("""
                SELECT is_guardian, is_parking
                FROM res_partner
                WHERE id = %s
            """, (self.id,))

            result = self.env.cr.fetchone()
            if result:
                actual_guardian, actual_parking = result
                if actual_guardian == final_guardian and actual_parking == final_parking:
                    _logger.info("✅ Parent privilege update SUCCESS: Guardian=%s, Parking=%s",
                                actual_guardian, actual_parking)
                else:
                    _logger.error("❌ Parent privilege update FAILED!")
                    _logger.error("  Expected: Guardian=%s, Parking=%s", final_guardian, final_parking)
                    _logger.error("  Actual: Guardian=%s, Parking=%s", actual_guardian, actual_parking)

        except Exception as e:
            _logger.error("Error updating parent privileges: %s", str(e))
            # Fallback to ORM write
            try:
                self.write({
                    'is_guardian': final_guardian,
                    'is_parking': final_parking,
                })
                _logger.info("Fallback ORM update completed")
            except Exception as orm_error:
                _logger.error("ORM update also failed: %s", str(orm_error))

    def _sql_update_privileges(self, guardian, parking):
        """Direct SQL update method (legacy - kept for compatibility)"""
        _logger.info("Direct SQL update for parent %s", self.name)

        self.env.cr.execute("""
            UPDATE res_partner
            SET is_guardian = %s, is_parking = %s
            WHERE id = %s
        """, (guardian, parking, self.id))

        self.env.cr.commit()

        # Verify SQL update
        self.env.cr.execute("""
            SELECT is_guardian, is_parking
            FROM res_partner
            WHERE id = %s
        """, (self.id,))

        result = self.env.cr.fetchone()
        if result:
            _logger.info("SQL update result: Guardian=%s, Parking=%s", result[0], result[1])

    def get_all_children_privileges(self):
        """
        Get the combined privileges from all children of this parent.
        Returns tuple (any_guardian, any_parking)
        """
        self.ensure_one()
        if not self.is_parent:
            return (False, False)

        # Get all children
        children = self.env['res.partner'].search([('parent_id', '=', self.id)])

        # Check if any child has guardian or parking privileges
        any_guardian = any(child.is_guardian for child in children)
        any_parking = any(child.is_parking for child in children)

        _logger.info("Parent %s has %d children. Combined privileges: Guardian=%s, Parking=%s",
                    self.name, len(children), any_guardian, any_parking)

        return (any_guardian, any_parking)

    def recalculate_parent_privileges(self):
        """
        Recalculate parent privileges based on all children.
        Useful for fixing any inconsistencies.
        """
        self.ensure_one()
        if not self.is_parent:
            return

        any_guardian, any_parking = self.get_all_children_privileges()

        _logger.info("Recalculating privileges for parent %s: Guardian=%s, Parking=%s",
                    self.name, any_guardian, any_parking)

        self.write({
            'is_guardian': any_guardian,
            'is_parking': any_parking,
        })

        self.env.cr.commit()

    @api.depends('invoice_ids', 'child_ids.invoice_ids')
    def _compute_invoice_count(self):
        """Compute invoice count - include children's invoices for parents"""
        for record in self:
            if record.is_parent:
                # For parents: count their own invoices + all children's invoices
                parent_invoices = record.invoice_ids.filtered(
                    lambda inv: inv.move_type in ['out_invoice', 'out_refund']
                )

                # Get all children's invoices
                children_invoices = self.env['account.move']
                for child in record.child_ids:
                    child_customer_invoices = child.invoice_ids.filtered(
                        lambda inv: inv.move_type in ['out_invoice', 'out_refund']
                    )
                    children_invoices |= child_customer_invoices

                # Combine parent and children invoices
                all_invoices = parent_invoices | children_invoices
                record.invoice_count = len(all_invoices)

            else:
                # For non-parents: only count their own invoices
                customer_invoices = record.invoice_ids.filtered(
                    lambda inv: inv.move_type in ['out_invoice', 'out_refund']
                )
                record.invoice_count = len(customer_invoices)

    @api.depends('child_ids')
    def _compute_children_count(self):
        """Compute children count"""
        for record in self:
            record.children_count = len(record.child_ids)

    @api.depends('invoice_ids.payment_state', 'invoice_ids.state', 'invoice_ids.move_type',
                 'invoice_ids.invoice_date', 'invoice_ids.line_ids.reconciled',
                 'child_ids.invoice_ids.payment_state', 'child_ids.invoice_ids.state', 
                 'child_ids.invoice_ids.move_type', 'child_ids.invoice_ids.invoice_date',
                 'child_ids.invoice_ids.line_ids.reconciled')
    def _compute_payment_state(self):
        """Improved computation of payment state and date for partners and parents"""
        for record in self:
            if record.is_parent:
                # For parents: consider their own + children's invoices
                all_invoices = self._get_all_family_invoices(record)
                
                if not all_invoices:
                    record.payment_state = 'not_paid'
                    record.payment_date = False
                    continue
                
                # Get the most recent invoice by invoice_date or create_date
                latest_invoice = sorted(
                    all_invoices,
                    key=lambda inv: inv.invoice_date or inv.create_date,
                    reverse=True
                )[0]
                
                # Set payment_state based on the latest invoice
                record.payment_state = latest_invoice.payment_state
                
                # Find the payment date for this invoice
                payment_date = self._get_actual_payment_date(latest_invoice)
                
                # Use invoice date as fallback for partial payments with no payment date
                if not payment_date and latest_invoice.payment_state in ['in_payment', 'partial']:
                    payment_date = latest_invoice.invoice_date
                    
                record.payment_date = payment_date
            else:
                # For regular partners: only consider their own invoices
                posted_invoices = record.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted' and 
                                inv.move_type in ['out_invoice', 'out_refund']
                )
                
                if not posted_invoices:
                    record.payment_state = 'not_paid'
                    record.payment_date = False
                    continue
                
                # Get the most recent invoice by invoice_date or create_date
                latest_invoice = sorted(
                    posted_invoices,
                    key=lambda inv: inv.invoice_date or inv.create_date,
                    reverse=True
                )[0]
                
                # Set payment_state based on the latest invoice
                record.payment_state = latest_invoice.payment_state
                
                # Find the payment date for this invoice
                payment_date = self._get_actual_payment_date(latest_invoice)
                
                # Use invoice date as fallback for partial payments with no payment date
                if not payment_date and latest_invoice.payment_state in ['in_payment', 'partial']:
                    payment_date = latest_invoice.invoice_date
                    
                record.payment_date = payment_date

    def _get_all_family_invoices(self, parent):
        """Helper method to get all invoices for a family (parent + children)"""
        parent_invoices = parent.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and 
                        inv.move_type in ['out_invoice', 'out_refund']
        )
        
        # Add children's posted invoices
        all_invoices = parent_invoices
        for child in parent.child_ids:
            child_invoices = child.invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and 
                            inv.move_type in ['out_invoice', 'out_refund']
            )
            all_invoices |= child_invoices
            
        return all_invoices

    def _get_actual_payment_date(self, invoice):
        """Helper method to find the actual payment date for an invoice"""
        payment_date = False
        
        if invoice.payment_state in ['paid', 'in_payment', 'partial']:
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
            """, (invoice.id, invoice.id))
            
            result = self.env.cr.fetchone()
            if result and result[0]:
                payment_date = result[0]
                
        return payment_date

    def action_view_invoice(self):
        """View invoices - include children's invoices for parents"""
        self.ensure_one()

        if self.is_parent:
            # For parents: show their own + children's invoices
            parent_invoices = self.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'out_refund']
            )

            # Add children's invoices
            all_invoices = parent_invoices
            for child in self.child_ids:
                child_invoices = child.invoice_ids.filtered(
                    lambda inv: inv.move_type in ['out_invoice', 'out_refund']
                )
                all_invoices |= child_invoices

        else:
            # For non-parents: only their own invoices
            all_invoices = self.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'out_refund']
            )

        if len(all_invoices) == 1:
            # Single invoice - open in form view
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': all_invoices[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Multiple invoices - open in tree view
            action = {
                'name': 'Family Invoices' if self.is_parent else 'Invoices',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'target': 'current',
                'domain': [('id', 'in', all_invoices.ids)],
                'context': {
                    'default_move_type': 'out_invoice',
                    'default_partner_id': self.id,
                    'search_default_open': 1,
                }
            }
            return action

    def open_print_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Parent ID Card',
            'res_model': 'parent.id.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_parent_ids': [(6, 0, [self.id])]},
        }

    def action_print_and_mark(self):
        return self.open_print_wizard()
