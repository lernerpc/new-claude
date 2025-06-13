# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api


class StudentInquiry(models.Model):
    _name = "student.inquiry"
    _description = "Student Inquiry"

    name = fields.Char('Name', required=True,
                       readonly=True, default=lambda self: _('New'))
    first_name = fields.Char('First Name', required=True)
    last_name = fields.Char('Last Name', required=True)
    mobile = fields.Char('Mobile', required=True)
    email = fields.Char('Email', required=True)
    level_id = fields.Many2one('res.partner', string="Sport Center", domain=[
                               ('is_sport', '=', True)])
    sport_id = fields.Many2many(
        'product.product', string="Sport Name", domain=[('is_sportname', '=', True)])
    p_name = fields.Char('Parent Name', required=True)
    parent_mobile = fields.Char('Parent Mobile', required=True)
    duration = fields.Float("Duration(Days)")
    query = fields.Text('Query')
    state = fields.Selection([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled')], string='State',
        copy=False, default="new")
    is_admission = fields.Boolean('Admission')
    check_parent = fields.Boolean('Check Parent')

    def remove(self, string):
        return string.replace(" ", "")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'student.inquiry') or _('New')
        res = super(StudentInquiry, self).create(vals_list)
        template = self.env.ref(
            'bi_sport_center_management.student_inquiry_email_template')
        if template:
            template.send_mail(res.id, force_send=True)
        return res

    def action_admission(self):
        admission = False
        name = self.remove(self.first_name) + ' ' + self.remove(self.last_name)
        partner = self.env['res.partner'].create({'name': name,
                                                  'mobile': self.remove(self.mobile),
                                                  'email': self.remove(self.email),
                                                  'p_name': self.remove(self.p_name),
                                                  'phone': self.remove(self.parent_mobile),
                                                  })
        if partner:
            values = {'student_id': partner.id,
                      'sport_id': self.sport_id.id,
                      'level_id': self.level_id.id,
                      'inquiry_id': self.id,
                      'duration': self.duration,
                      }
            if values:
                admission = self.env['student.admission'].create(values)
        if admission:
            self.is_admission = True
            self.check_parent = True
            self.state = 'confirmed'
        return admission

    def action_cancel(self):
        self.state = 'cancel'

    def action_open_admission(self):
        self.ensure_one()
        admissions = self.env['student.admission'].search(
            [('inquiry_id', '=', self.id)])
        if admissions:
            action = {
                'name': _("Admissions"),
                'type': 'ir.actions.act_window',
                'res_model': 'student.admission',
                'target': 'current',
            }
            if len(admissions.ids) == 1:
                res_id = admissions.ids[0]
                action['res_id'] = res_id
                action['view_mode'] = 'form'
            else:
                action['view_mode'] = 'tree,form'
                action['domain'] = [('id', 'in', admissions.ids)]
            return action

    def action_send_ans(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        template = self.env.ref(
            'bi_sport_center_management.student_inquiry_ans_email_template')
        if template:
            template.body_html = f"""
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                    <tr>
                        <td valign="top">
                            <div style="font-size: 13px; margin: 0px; padding: 0px;">
                                Hello <t t-out="object.first_name or ''">Visitor</t>,<br/>
                                <br/>
                                Thank you for your interest.
                                <br/>
                                Your inquiry application <t t-out="object.name or ''"></t> is registered.
                                <br/>
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
            ctx = {
                'default_model': 'student.inquiry',
                'default_res_ids': self.ids,
                'default_use_template': bool(template),
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'proforma': self.env.context.get('proforma', True),
                'force_email': True,
            }

            return{
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }
         
    def _get_customer_information(self):
        """ Get customer information that can be extracted from the records by
        normalized email.

        The goal of this method is to offer an extension point to subclasses
        for retrieving initial values from a record to populate related
        customers record (res_partner).

        :return dict: normalized email -> dict of initial res_partner values
        """
        return {}