from odoo import models, fields, api
import base64
import qrcode
from io import BytesIO

class ResPartner(models.Model):
    _inherit = 'res.partner'

    qr_code = fields.Binary("QR Code", readonly=True)

    def _generate_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/web#id={self.id}&model=res.partner&view_type=form"
        qr = qrcode.make(url)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue())

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.qr_code = record._generate_qr_code()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for record in self:
                record.qr_code = record._generate_qr_code()
        return res 
