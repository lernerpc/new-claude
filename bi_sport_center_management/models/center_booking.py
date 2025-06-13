# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class CenterBooking(models.Model):
    _name = "center.booking"
    _description = "Center Booking"

    name = fields.Char('Name', required=True,
                       readonly=True, default=lambda self: _('New'))
    user_id = fields.Many2one('res.users', string='User')
    student_id = fields.Many2one('res.partner', related='user_id.partner_id')
    mobile = fields.Char(
        'Mobile', related='student_id.mobile', store=True, readonly=False)
    email = fields.Char('Email', related='student_id.email',
                        store=True, readonly=False)
    sport_id = fields.Many2one(
        'product.product', string="Sport Name", domain=[('is_sportname', '=', True)])
    space_id = fields.Many2one('product.product', string="Ground/Court", domain=[
                               ('is_space', '=', True)])
    start_date = fields.Datetime('Start Time')
    end_date = fields.Datetime('End Time')
    state = fields.Selection([
        ('new', 'New'),
        ('confirmed', 'Confirmed')], string='State',
        copy=False, default="new")
    is_paid = fields.Boolean('Paid', compute="_compute_sale_order_paid_status")
    duration = fields.Float(string="Spend Time (Hours)",
                            compute="_compute_spend_time")
    sale_order = fields.Boolean('Sale Order')
    desc = fields.Text("Description")

    def _compute_sale_order_paid_status(self):
        for record in self:
            record.is_paid = False
            if record.sale_order:
                orders = self.env['sale.order'].search([('booking_id', '=', record.id)])
                if orders:
                    invoices = orders.invoice_ids.filtered(lambda l:l.state == 'posted')
                    if invoices and all(item == 'paid' for item in invoices.mapped('payment_state')):
                        record.is_paid = True


    @api.depends('start_date', 'end_date')
    def _compute_spend_time(self):
        for record in self:
            if record.start_date and record.end_date:
                record.duration = (
                    (record.end_date - record.start_date).total_seconds())/3600
            else:
                record.duration = 0.0

    @api.constrains('end_date', 'start_date')
    def check_end_date(self):
        if self.start_date and self.start_date < fields.Datetime.now():
            raise ValidationError(
                _('Start Time must be after the Current Time!!'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'center.booking') or _('New')
        res = super(CenterBooking, self).create(vals_list)
        template = self.env.ref(
            'bi_sport_center_management.center_booking_email_template')
        if template:
            template.body_html = f"""
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                    <tr>
                        <td valign="top">
                            <div style="font-size: 13px; margin: 0px; padding: 0px;">
                                Hello <t t-out="object.student_id.name or ''">Visitor</t>,<br/>
                                <br/>
                                Congrats!
                                <br/>
                                Your Booking application <t t-out="object.name or ''"></t> is registered.
                                <br/>
                                <br/>
                                Application will be confirm after complete payment.
                                <br/>
                                <br/>
                                Best regards,
                                <t t-if="not is_html_empty(user.signature)">
                                    <br/><br/>
                                    <t t-out="user.signature or ''">--<br/>Mitchell Admin</t>
                                </t>
                            </div>
                        </td>
                    </tr>
                </table>
            """
            template.send_mail(res.id, force_send=True)
        return res

    def action_make_payment(self):
        if not self.student_id or not self.space_id or not self.start_date or not self.end_date:
            raise ValidationError('Please complete all the details.')
        sale_order = self.env['sale.order'].create({
            'partner_id': self.student_id.id,
            'company_id': self.env.user.company_id.id,
            'booking_id': self.id,
            'date_order': fields.Date.today(),
            'order_line': [(0, 0, {
                'product_id': self.space_id.id,
                'product_uom_qty': self.duration or 1,
            })],
        })
        if sale_order:
            self.sale_order = True
            action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
            action['views'] = [(False, 'form')]
            action['res_id'] = sale_order.id
            return action

    def action_confirm(self):
        if not self.is_paid:
            raise ValidationError("You can't confirm booking without payment.")
        self.state = 'confirmed'


    def action_view_sale_order(self):
        self.ensure_one()
        if self.sale_order:
            orders = self.env['sale.order'].search(
                [('booking_id', '=', self.id)])
            if orders:
                action = {
                    'name': _("Booking Orders"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.order',
                    'target': 'current',
                }
                if len(orders.ids) == 1:
                    invoice = orders.ids[0]
                    action['res_id'] = invoice
                    action['view_mode'] = 'form'
                    action['views'] = [
                        (self.env.ref('sale.view_order_form').id, 'form')]
                else:
                    action['view_mode'] = 'tree,form'
                    action['domain'] = [('id', 'in', orders.ids)]
                return action
