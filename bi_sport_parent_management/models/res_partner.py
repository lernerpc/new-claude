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
    
    # Invoice related fields - Hybrid approach for better reliability
    invoice_ids = fields.One2many('account.move', 'partner_id', string='Direct Invoices')
    all_invoice_ids = fields.Many2many('account.move', compute='_compute_all_invoice_ids', string='All Invoices')
    invoice_count = fields.Integer(compute='_compute_all_invoice_ids', string='Invoice Count')
    
    # Payment status field
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], string='Payment Status', compute='_compute_payment_state', store=True, readonly=True)
    
    @api.depends('invoice_ids', 'is_student')
    def _compute_all_invoice_ids(self):
        """Compute all related invoices for the partner"""
        for record in self:
            # Start with direct invoices
            all_invoices = record.invoice_ids.filtered(lambda inv: inv.move_type in ['out_invoice', 'out_refund'])
            
            # Additional search for student admission invoices if this partner is a student
            if record.is_student:
                admission_invoices = self.env['account.move'].search([
                    ('student_admission_id.student_id', '=', record.id),
                    ('move_type', 'in', ['out_invoice', 'out_refund'])
                ])
                all_invoices |= admission_invoices
            
            record.all_invoice_ids = all_invoices
            record.invoice_count = len(all_invoices)
    
    @api.depends('all_invoice_ids.payment_state', 'all_invoice_ids.state')
    def _compute_payment_state(self):
        """Compute payment state based on all related invoices"""
        for record in self:
            # Trigger computation of all_invoice_ids first
            record._compute_all_invoice_ids()
            
            if not record.all_invoice_ids:
                record.payment_state = 'not_paid'
            else:
                # Filter posted invoices only
                posted_invoices = record.all_invoice_ids.filtered(lambda inv: inv.state == 'posted')
                
                if not posted_invoices:
                    record.payment_state = 'not_paid'
                else:
                    # Filter invoices with valid invoice_date and sort by date
                    invoices_with_date = posted_invoices.filtered(lambda inv: inv.invoice_date)
                    
                    if invoices_with_date:
                        # Get the latest posted invoice payment state
                        latest_invoice = invoices_with_date.sorted('invoice_date', reverse=True)
                        record.payment_state = latest_invoice[0].payment_state
                    else:
                        # If no invoices have dates, just take the first posted invoice
                        record.payment_state = posted_invoices[0].payment_state
            
    def action_view_invoice(self):
        self.ensure_one()
        
        # Use the computed all_invoice_ids field
        invoices = self.all_invoice_ids
        
        if len(invoices) == 1:
            # Single invoice - open in form view
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoices[0].id,
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
                'domain': [('id', 'in', invoices.ids)],
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