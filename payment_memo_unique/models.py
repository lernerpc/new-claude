from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    # Completely override the ref field with Arabic label
    ref = fields.Char(
        string='رقم الايصال',
        help='رقم الايصال - يجب أن يكون فريد لكل دفعة جديدة',
        copy=False
    )
    
    @api.constrains('ref')
    def _check_unique_memo(self):
        for record in self:
            if record.ref and record.ref.strip():
                is_new_or_modified = (
                    not record.create_date or
                    record.create_date >= (datetime.now() - timedelta(minutes=5)) or
                    (record.write_date and record.write_date >= (datetime.now() - timedelta(minutes=5)))
                )
                
                if is_new_or_modified:
                    existing_payments = self.search([
                        ('ref', '=', record.ref.strip()),
                        ('id', '!=', record.id),
                        ('state', '!=', 'cancel')
                    ])
                    
                    if existing_payments:
                        conflicting_payment = existing_payments[0]
                        error_msg = _(
                            'رقم الايصال "%s" مستخدم من قبل!\n'
                            'الدفعة المتضاربة: %s (التاريخ: %s)\n'
                            'يرجى استخدام رقم ايصال مختلف.'
                        ) % (
                            record.ref,
                            conflicting_payment.name or 'غير محدد',
                            conflicting_payment.date.strftime('%Y-%m-%d') if conflicting_payment.date else 'غير محدد'
                        )
                        raise ValidationError(error_msg)
    
    @api.model
    def create(self, vals):
        if vals.get('ref'):
            vals['ref'] = vals['ref'].strip()
        return super().create(vals)
    
    def write(self, vals):
        if vals.get('ref'):
            vals['ref'] = vals['ref'].strip()
        return super().write(vals)
    
    @api.onchange('ref')
    def _onchange_ref(self):
        if self.ref:
            self.ref = self.ref.strip()
            if self.ref:
                existing = self.search([
                    ('ref', '=', self.ref),
                    ('id', '!=', self.id or 0),
                    ('state', '!=', 'cancel')
                ], limit=1)
                
                if existing:
                    return {
                        'warning': {
                            'title': _('تحذير - رقم ايصال مكرر'),
                            'message': _(
                                'رقم الايصال "%s" مستخدم من قبل في الدفعة: %s\n'
                                'يرجى استخدام رقم مختلف.'
                            ) % (self.ref, existing.name or 'غير محدد')
                        }
                    }
