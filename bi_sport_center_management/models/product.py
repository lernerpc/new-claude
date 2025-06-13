# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.osv import expression
import re


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_equipment = fields.Boolean('Sport Equipment')
    is_space = fields.Boolean('Space Center')
    is_sportname = fields.Boolean('Sport Product')
    sport_id = fields.Many2many('product.template','product_sports_id','products_id','sports', string = "Sport Name", domain=[('is_sportname', '=', True)])



class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_equipment = fields.Boolean('Sport Equipment')
    is_space = fields.Boolean('Space Center')
    is_sportname = fields.Boolean('Sport Product')
    sport_id = fields.Many2many('product.product','product_sport_id','product_id','sport', string = "Sport Name", domain=[('is_sportname', '=', True)])

   