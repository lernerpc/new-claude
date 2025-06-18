from odoo import models, fields, api

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
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        """Compute invoice count - only count out_invoice and out_refund"""
        for record in self:
            # Count only customer invoices and refunds
            customer_invoices = record.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'out_refund']
            )
            record.invoice_count = len(customer_invoices)
    
    @api.depends('child_ids')
    def _compute_children_count(self):
        """Compute children count"""
        for record in self:
            record.children_count = len(record.child_ids)
    
    @api.depends('invoice_ids.payment_state', 'invoice_ids.state', 'invoice_ids.move_type', 'invoice_ids.invoice_date')
    def _compute_payment_state(self):
        """Compute payment state and payment date based on customer invoices only"""
        for record in self:
            # Filter only customer invoices (out_invoice, out_refund) that are posted
            customer_invoices = record.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'out_refund'] and inv.state == 'posted'
            )
            
            if not customer_invoices:
                record.payment_state = 'not_paid'
                record.payment_date = False
            else:
                # Filter invoices with valid invoice_date and sort by date
                invoices_with_date = customer_invoices.filtered(lambda inv: inv.invoice_date)
                
                if invoices_with_date:
                    # Get the latest posted customer invoice
                    latest_invoice = invoices_with_date.sorted('invoice_date', reverse=True)[0]
                    record.payment_state = latest_invoice.payment_state
                    record.payment_date = latest_invoice.invoice_date
                else:
                    # If no invoices have dates, just take the first posted customer invoice
                    latest_invoice = customer_invoices[0]
                    record.payment_state = latest_invoice.payment_state
                    record.payment_date = False
            
    def action_view_invoice(self):
        self.ensure_one()
        
        # Get only customer invoices
        customer_invoices = self.invoice_ids.filtered(
            lambda inv: inv.move_type in ['out_invoice', 'out_refund']
        )
        
        if len(customer_invoices) == 1:
            # Single invoice - open in form view
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': customer_invoices[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Multiple invoices - open in tree view
            action = {
                'name': 'Invoices',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'target': 'current',
                'domain': [('id', 'in', customer_invoices.ids)],
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