from odoo import models, fields, _
from odoo.exceptions import ValidationError

class CreateInvoice(models.Model):
    _inherit = 'create.invoice'

    pricelist_id = fields.Many2one('product.pricelist', string='قائمة الأسعار', required=True)

    def action_create_invoice(self):
        admission_id = self.env['student.admission'].browse(self._context.get('active_id'))
        if not admission_id:
            raise ValidationError('Admission Registration not found!')

        sale_journals = self.env['account.journal'].sudo().search([('type', '=', 'sale')])
        invoice = self.env['account.move'].create({
            'invoice_origin': admission_id.name or '',
            'move_type': 'out_invoice',
            'ref': admission_id.name or '',
            'journal_id': sale_journals and sale_journals[0].id or False,
            'partner_id': admission_id.student_id.id,
            'invoice_date': fields.date.today(),
            'currency_id': admission_id.student_id.currency_id.id or self.env.user.currency_id.id,
            'company_id': self.env.user.company_id.id or False,
            'pricelist_id': self.pricelist_id.id,
        })

        # Create invoice lines using pricelist prices
        invoice_lines = []
        for activity in admission_id.activity_ids:
            price = self.pricelist_id._get_product_price(
                activity, 1, admission_id.student_id)
            invoice_lines.append((0, 0, {
                'product_id': activity.id,
                'name': activity.display_name or '',
                'product_uom_id': activity.uom_id.id,
                'price_unit': price,
                'move_name': admission_id.name or '',
            }))

        if invoice_lines:
            invoice.write({'invoice_line_ids': invoice_lines})
            admission_id.is_invoiced = True 