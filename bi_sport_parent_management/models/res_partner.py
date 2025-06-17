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
    
    # Invoice related fields
    invoice_ids = fields.One2many('account.move', 'partner_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')
    
    # Payment status field
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], string='Payment Status', compute='_compute_payment_state', store=True, readonly=True)
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)
    
    @api.depends('invoice_ids.payment_state')
    def _compute_payment_state(self):
        """Compute payment state based on related invoices"""
        for record in self:
            if not record.invoice_ids:
                record.payment_state = 'not_paid'
            else:
                # Filter posted invoices only
                posted_invoices = record.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                
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
        invoices = self.invoice_ids
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
        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoices.id,
                'views': [(False, 'form')],
            })
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