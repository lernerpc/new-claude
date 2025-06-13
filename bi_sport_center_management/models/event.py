# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Event(models.Model):
    _inherit = 'event.event'

    sport_id = fields.Many2one('product.product', string='Sport Name', domain=[('is_sportname','=', True)])
    center_id = fields.Many2one('res.partner', string='Sport Center')
    ground_id = fields.Many2one('product.product', string='Ground / Court', domain=[('is_space','=', True)])
