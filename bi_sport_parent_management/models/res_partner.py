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
    

        # Add this temporary method to your res_partner.py
    def force_recompute_invoices(self):
        """Temporary method to force recompute invoice fields"""
        partners = self.search([])
        partners._compute_invoice_ids()
        partners._compute_payment_state()
        return True

    @api.depends('name', 'student_national_id')  # Changed dependency
    def _compute_invoice_ids(self):
        """Compute related invoices for the student"""
        for record in self:
            invoices = self.env['account.move']
        
            # Only compute for students
            if record.is_parent:
                # Primary method: Search by student_admission_id (for new invoices)
                invoices = self.env['account.move'].search([
                ('partner_id', '=', record.id),
                ('move_type', 'in', ['out_invoice', 'out_refund'])
                ])
            
                # Fallback method: Search by invoice_origin (for old invoices)
                if not invoices and record.name:
                    invoices = self.env['account.move'].search([
                    ('invoice_origin', '=', record.name),
                    ('move_type', 'in', ['out_invoice', 'out_refund'])
                   ])
        
            record.invoice_ids = invoices
            record.invoice_count = len(invoices)

    @api.depends('invoice_ids.payment_state')
    def _compute_payment_state(self):
        """Compute payment state based on related invoices"""
        for record in self:
            if not record.invoice_ids:
                record.payment_state = 'not_paid'
            else:
                # Get the latest invoice payment state
                latest_invoice = record.invoice_ids.filtered(lambda inv: inv.state == 'posted').sorted('invoice_date', reverse=True)
                if latest_invoice:
                    record.payment_state = latest_invoice[0].payment_state
                else:
                    record.payment_state = 'not_paid'