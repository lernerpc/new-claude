import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.bi_sport_center_management.controllers.main import StudentRegistration as BaseStudentRegistration

_logger = logging.getLogger(__name__)

class StudentRegistration(BaseStudentRegistration):

    @http.route('/registration/', auth='public', website=True, methods=['GET'])
    def registration(self, **kw):
        _logger.debug("Rendering registration form with pricelist extension")
        
        # Set session data
        request.session['is_data'] = True
        
        # Get all the base data that the template needs
        states = request.env['res.country.state'].sudo().search([])
        centers = request.env['res.partner'].sudo().search([('is_sport', '=', True)])
        all_activities = request.env['product.product'].sudo().search([('is_sportname', '=', True)])
        
        # Group activities by category (this was missing!)
        activities_by_category = {}
        for act in all_activities:
            cat_name = act.categ_id.name if act.categ_id else _('Uncategorized')
            if cat_name not in activities_by_category:
                activities_by_category[cat_name] = []
            activities_by_category[cat_name].append(act)
        
        # Get pricelists (enhanced functionality from this extension)
        pricelists = request.env['product.pricelist'].sudo().search([('active', '=', True)])
        default_pricelist_id = pricelists[0].id if pricelists else None
        
        _logger.info("Fetched pricelists count: %s", len(pricelists))
        _logger.info("Fetched pricelists names: %s", pricelists.mapped('name'))
        _logger.info("Activities by category: %s", list(activities_by_category.keys()))
        
        # Complete values dictionary with all required data
        values = {
            'states': states,
            'activities_by_category': activities_by_category,
            'centers': centers,
            'pricelists': pricelists,
            'pricelist_id': default_pricelist_id,
        }
        
        return request.render('bi_sport_center_management.registration', values)

    @http.route('/registration/create', auth='public', website=True, methods=['POST'])
    def registration_create(self, **kw):
        _logger.info("Form submission data: %s", kw)
        _logger.info("Received pricelist_id: %s", kw.get('pricelist_id'))
        
        # Process pricelist_id properly
        if kw.get('pricelist_id') and kw.get('pricelist_id').isdigit():
            kw['pricelist_id'] = int(kw.get('pricelist_id'))
        else:
            kw['pricelist_id'] = False
            
        # Call the parent's registration_create method
        # Note: Fix the super() call
        return super().registration_create(**kw)