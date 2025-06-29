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

    # Invoice related fields
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

    # Simple fee details field
    fee_details = fields.Html('Fee Details', compute='_compute_fee_details', store=False)

# Corrected partner fee details methods - replace in your res_partner.py



# Add this field to your ResPartner class after the existing computed fields
    
    fees_count = fields.Integer(compute='_compute_fees_count', string='Fees Count',
                               help="Number of membership fee invoices")

    @api.depends('invoice_ids', 'child_ids.invoice_ids')
    def _compute_fees_count(self):
        """Compute fees count for partners"""
        for record in self:
            try:
                if record.is_parent:
                    # For parents: count their own + all children's fee invoices
                    all_invoices = record._get_all_family_invoices(record)
                else:
                    # For students/regular partners: only their own invoices
                    all_invoices = record.invoice_ids.filtered(
                        lambda inv: inv.state == 'posted' and 
                                    inv.move_type in ['out_invoice', 'out_refund']
                    )
                
                # Get fee invoices - those that HAVE membership_fee_name
                fee_invoices = all_invoices.filtered(
                    lambda inv: hasattr(inv, 'membership_fee_name') and getattr(inv, 'membership_fee_name', False)
                )
                
                record.fees_count = len(fee_invoices)
                
            except Exception:
                record.fees_count = 0

    @api.depends('invoice_ids', 'child_ids.invoice_ids')
    def _compute_fee_details(self):
        """Corrected fee details for partners - show ONLY fees"""
        for record in self:
            try:
                if record.is_parent:
                    # For parents: show children's fees
                    html_content = record._build_parent_fee_html()
                elif record.is_student:
                    # For students: show their own fees
                    html_content = record._build_student_fee_html()
                else:
                    html_content = '<p style="text-align: center; color: #6c757d;">No fee information available</p>'
                
                record.fee_details = html_content
            except Exception as e:
                record.fee_details = f'<p style="color: #dc3545;">Error: {str(e)}</p>'

    def _build_parent_fee_html(self):
        """Corrected: Build fee HTML for parents showing children's fees ONLY"""
        html_content = '''
        <div style="margin: 10px 0;">
            <h4 style="color: #875A7B; margin-bottom: 15px;">👨‍👩‍👧‍👦 Children's Fees</h4>
        '''
        
        if not self.child_ids:
            return html_content + '<p style="text-align: center; color: #6c757d;">No children found</p></div>'
        
        for child in self.child_ids:
            # Get child's invoices
            child_invoices = child.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'out_refund'] and inv.state == 'posted'
            )
            
            # CORRECTED: Get ONLY fee invoices - those that HAVE membership_fee_name
            fee_invoices = child_invoices.filtered(
                lambda inv: hasattr(inv, 'membership_fee_name') and getattr(inv, 'membership_fee_name', False)
            )
            
            if fee_invoices:
                paid_count = len(fee_invoices.filtered(lambda inv: inv.payment_state == 'paid'))
                total_amount = sum(fee_invoices.mapped('amount_total'))
                
                html_content += f'''
                <div style="background: white; border: 1px solid #dee2e6; border-radius: 6px; margin-bottom: 15px; overflow: hidden;">
                    <div style="background: #f8f9fa; padding: 10px; border-bottom: 1px solid #dee2e6;">
                        <strong style="color: #875A7B;">👤 {child.name}</strong>
                        <span style="float: right; color: #6c757d; font-size: 12px;">
                            {paid_count}/{len(fee_invoices)} paid • {total_amount:.0f} EGP
                        </span>
                        <br><small style="color: #6c757d;">Showing {len(fee_invoices)} fees out of {len(child_invoices)} total invoices</small>
                    </div>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead style="background: #f8f9fa;">
                            <tr>
                                <th style="padding: 6px; border-bottom: 1px solid #dee2e6; text-align: left; font-size: 12px;">Fee Name</th>
                                <th style="padding: 6px; border-bottom: 1px solid #dee2e6; text-align: center; font-size: 12px;">Date</th>
                                <th style="padding: 6px; border-bottom: 1px solid #dee2e6; text-align: right; font-size: 12px;">Amount</th>
                                <th style="padding: 6px; border-bottom: 1px solid #dee2e6; text-align: center; font-size: 12px;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                '''
                
                for invoice in fee_invoices:
                    # Use membership_fee_name for fee invoices
                    fee_name = getattr(invoice, 'membership_fee_name', 'Unknown Fee')
                    invoice_date = invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else 'N/A'
                    
                    status_color = {
                        'paid': '#28a745', 'partial': '#ffc107', 'in_payment': '#17a2b8',
                        'not_paid': '#dc3545', 'reversed': '#6c757d'
                    }.get(invoice.payment_state, '#6c757d')
                    
                    status_text = {
                        'paid': 'Paid', 'partial': 'Partial', 'in_payment': 'Processing',
                        'not_paid': 'Unpaid', 'reversed': 'Reversed'
                    }.get(invoice.payment_state, invoice.payment_state)
                    
                    html_content += f'''
                    <tr>
                        <td style="padding: 6px; border-bottom: 1px solid #dee2e6; font-size: 12px; font-weight: bold;">{fee_name}</td>
                        <td style="padding: 6px; border-bottom: 1px solid #dee2e6; text-align: center; font-size: 12px;">{invoice_date}</td>
                        <td style="padding: 6px; border-bottom: 1px solid #dee2e6; text-align: right; font-size: 12px; font-weight: bold;">{invoice.amount_total:.0f} EGP</td>
                        <td style="padding: 6px; border-bottom: 1px solid #dee2e6; text-align: center;">
                            <span style="background-color: {status_color}; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px; font-weight: bold;">
                                {status_text}
                            </span>
                        </td>
                    </tr>
                    '''
                
                html_content += '''
                        </tbody>
                    </table>
                </div>
                '''
            else:
                # Child has invoices but no fees
                total_invoices = len(child_invoices)
                html_content += f'''
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 10px; margin-bottom: 10px;">
                    <strong>{child.name}</strong> - No membership fees found
                    <br><small style="color: #6c757d;">(Has {total_invoices} total invoices, but none are marked as fees)</small>
                </div>
                '''
        
        html_content += '</div>'
        return html_content

    def _build_student_fee_html(self):
        """Corrected: Build fee HTML for students showing ONLY their fees"""
        # Get student's invoices
        student_invoices = self.invoice_ids.filtered(
            lambda inv: inv.move_type in ['out_invoice', 'out_refund'] and inv.state == 'posted'
        )
        
        # CORRECTED: Get ONLY fee invoices - those that HAVE membership_fee_name
        fee_invoices = student_invoices.filtered(
            lambda inv: hasattr(inv, 'membership_fee_name') and getattr(inv, 'membership_fee_name', False)
        )
        
        if not fee_invoices:
            total_invoices = len(student_invoices)
            return f'''
            <div style="margin: 10px 0;">
                <h4 style="color: #875A7B; margin-bottom: 15px;">💳 My Fees</h4>
                <p style="text-align: center; color: #6c757d;">No membership fees found</p>
                <p style="text-align: center; color: #6c757d; font-size: 12px;">
                    (Found {total_invoices} total invoices, but none are marked as fees)
                </p>
            </div>
            '''
        
        paid_count = len(fee_invoices.filtered(lambda inv: inv.payment_state == 'paid'))
        total_amount = sum(fee_invoices.mapped('amount_total'))
        total_invoices = len(student_invoices)
        
        html_content = f'''
        <div style="margin: 10px 0;">
            <h4 style="color: #875A7B; margin-bottom: 15px;">💳 My Fees</h4>
            <div style="background: #e9ecef; padding: 10px; border-radius: 6px; margin-bottom: 15px; text-align: center;">
                <strong>{paid_count}/{len(fee_invoices)} Paid • {total_amount:.0f} EGP Total</strong>
                <br><small style="color: #6c757d;">Showing {len(fee_invoices)} fees out of {total_invoices} total invoices</small>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; background: white; border: 1px solid #dee2e6; border-radius: 6px; overflow: hidden;">
                <thead style="background: #875A7B; color: white;">
                    <tr>
                        <th style="padding: 8px; text-align: left;">#</th>
                        <th style="padding: 8px; text-align: left;">Fee Name</th>
                        <th style="padding: 8px; text-align: center;">Date</th>
                        <th style="padding: 8px; text-align: right;">Amount</th>
                        <th style="padding: 8px; text-align: center;">Status</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for index, invoice in enumerate(fee_invoices, 1):
            # Use membership_fee_name for fee invoices
            fee_name = getattr(invoice, 'membership_fee_name', 'Unknown Fee')
            invoice_date = invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else 'N/A'
            
            status_color = {
                'paid': '#28a745', 'partial': '#ffc107', 'in_payment': '#17a2b8',
                'not_paid': '#dc3545', 'reversed': '#6c757d'
            }.get(invoice.payment_state, '#6c757d')
            
            status_text = {
                'paid': 'Paid', 'partial': 'Partial', 'in_payment': 'Processing',
                'not_paid': 'Unpaid', 'reversed': 'Reversed'
            }.get(invoice.payment_state, invoice.payment_state)
            
            row_bg = '#f8f9fa' if index % 2 == 0 else 'white'
            
            html_content += f'''
            <tr style="background-color: {row_bg};">
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">{index}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">{fee_name}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{invoice_date}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right; font-weight: bold;">{invoice.amount_total:.0f} EGP</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: center;">
                    <span style="background-color: {status_color}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;">
                        {status_text}
                    </span>
                </td>
            </tr>
            '''
        
        html_content += '''
                </tbody>
            </table>
        </div>
        '''
        return html_content

    def update_parent_privileges_or_logic(self, new_guardian, new_parking):
        """Update parent privileges using OR logic"""
        self.ensure_one()
        if not self.is_parent:
            _logger.warning("Attempted to update parent privileges on non-parent record: %s", self.name)
            return

        current_guardian = self.is_guardian or False
        current_parking = self.is_parking or False

        final_guardian = current_guardian or new_guardian
        final_parking = current_parking or new_parking

        _logger.info("Parent privilege update for %s (ID: %s):", self.name, self.id)
        _logger.info("  Current: Guardian=%s, Parking=%s", current_guardian, current_parking)
        _logger.info("  New child: Guardian=%s, Parking=%s", new_guardian, new_parking)
        _logger.info("  Final (OR logic): Guardian=%s, Parking=%s", final_guardian, final_parking)

        try:
            self.env.cr.execute("""
                UPDATE res_partner
                SET is_guardian = %s, is_parking = %s
                WHERE id = %s
            """, (final_guardian, final_parking, self.id))

            self.env.cr.commit()

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

        except Exception as e:
            _logger.error("Error updating parent privileges: %s", str(e))
            try:
                self.write({
                    'is_guardian': final_guardian,
                    'is_parking': final_parking,
                })
                _logger.info("Fallback ORM update completed")
            except Exception as orm_error:
                _logger.error("ORM update also failed: %s", str(orm_error))

    @api.depends('invoice_ids', 'child_ids.invoice_ids')
    def _compute_invoice_count(self):
        """Compute invoice count - include children's invoices for parents"""
        for record in self:
            if record.is_parent:
                parent_invoices = record.invoice_ids.filtered(
                    lambda inv: inv.move_type in ['out_invoice', 'out_refund']
                )

                children_invoices = self.env['account.move']
                for child in record.child_ids:
                    child_customer_invoices = child.invoice_ids.filtered(
                        lambda inv: inv.move_type in ['out_invoice', 'out_refund']
                    )
                    children_invoices |= child_customer_invoices

                all_invoices = parent_invoices | children_invoices
                record.invoice_count = len(all_invoices)

            else:
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
        """Compute payment state for partners and parents"""
        for record in self:
            if record.is_parent:
                all_invoices = self._get_all_family_invoices(record)
                
                if not all_invoices:
                    record.payment_state = 'not_paid'
                    record.payment_date = False
                    continue
                
                latest_invoice = sorted(
                    all_invoices,
                    key=lambda inv: inv.invoice_date or inv.create_date,
                    reverse=True
                )[0]
                
                record.payment_state = latest_invoice.payment_state
                payment_date = self._get_actual_payment_date(latest_invoice)
                
                if not payment_date and latest_invoice.payment_state in ['in_payment', 'partial']:
                    payment_date = latest_invoice.invoice_date
                    
                record.payment_date = payment_date
            else:
                posted_invoices = record.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted' and 
                                inv.move_type in ['out_invoice', 'out_refund']
                )
                
                if not posted_invoices:
                    record.payment_state = 'not_paid'
                    record.payment_date = False
                    continue
                
                latest_invoice = sorted(
                    posted_invoices,
                    key=lambda inv: inv.invoice_date or inv.create_date,
                    reverse=True
                )[0]
                
                record.payment_state = latest_invoice.payment_state
                payment_date = self._get_actual_payment_date(latest_invoice)
                
                if not payment_date and latest_invoice.payment_state in ['in_payment', 'partial']:
                    payment_date = latest_invoice.invoice_date
                    
                record.payment_date = payment_date

    def _get_all_family_invoices(self, parent):
        """Helper method to get all invoices for a family"""
        parent_invoices = parent.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and 
                        inv.move_type in ['out_invoice', 'out_refund']
        )
        
        all_invoices = parent_invoices
        for child in parent.child_ids:
            child_invoices = child.invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and 
                            inv.move_type in ['out_invoice', 'out_refund']
            )
            all_invoices |= child_invoices
            
        return all_invoices

    def _get_actual_payment_date(self, invoice):
        """Helper method to find actual payment date"""
        payment_date = False
        
        if invoice.payment_state in ['paid', 'in_payment', 'partial']:
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
            parent_invoices = self.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'out_refund']
            )

            all_invoices = parent_invoices
            for child in self.child_ids:
                child_invoices = child.invoice_ids.filtered(
                    lambda inv: inv.move_type in ['out_invoice', 'out_refund']
                )
                all_invoices |= child_invoices

        else:
            all_invoices = self.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'out_refund']
            )

        if len(all_invoices) == 1:
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': all_invoices[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
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