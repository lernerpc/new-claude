# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    booking_id = fields.Many2one('center.booking', string='Booking')
