# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo import _, fields, http
from dateutil.relativedelta import relativedelta
from odoo.http import request, content_disposition
from operator import itemgetter
from odoo.tools.translate import _
from odoo.tools import groupby as groupbyelem
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers.portal import CustomerPortal
import pytz
import logging
import base64

_logger = logging.getLogger(__name__)

class StudentRegistration(http.Controller):
    
    def remove(self, string):
        return string.replace(" ", "") if string else ""
    
    def remove2(self, string):
        return " ".join(string.split()) if string else ""
    
    def _get_pricelist_id(self, pricelist_value):
        """
        Helper method to handle pricelist_id whether it comes as string or int
        from the pricelist extension or directly from form
        """
        if isinstance(pricelist_value, int):
            return pricelist_value if pricelist_value else False
        elif isinstance(pricelist_value, str) and pricelist_value.isdigit():
            return int(pricelist_value)
        else:
            return False

    @http.route('/registration/create', auth='public', website=True, methods=['POST'], csrf=False)
    def registration_create(self, **kw):
        admission = False
        massage = 'عذرًا، بعض القيم مفقودة! الرجاء ملء الحقول أولاً'
        
        # Add logging for debugging
        _logger.info("Received member_type: %s", kw.get('member_type'))
        _logger.info("Received form data keys: %s", list(kw.keys()))
        
        if request.session.get('is_data') and kw.get('check_data'):
            if kw.get('fname') and kw.get('lname'):
                name = self.remove2(kw.get('fname')) + ' ' + self.remove2(kw.get('lname'))
                mobile = self.remove(kw.get('mobile'))
                parent_mobile = self.remove(kw.get('parent_mobile'))
                student_national_id = self.remove(kw.get('student_national_id'))
                parent_national_id = self.remove(kw.get('parent_national_id'))
                member_type = kw.get('member_type', 'regular')  # Get member type
                academic_subtype = kw.get('academic_subtype', '')  # Get academic subtype

                # Validate member type
                if not member_type or member_type not in ['regular', 'academic']:
                    massage = 'يرجى اختيار نوع العضوية.'
                    return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})

                # Validate national IDs
                if student_national_id and (not student_national_id.isdigit() or len(student_national_id) != 14):
                    massage = 'الرقم القومي للطالب يجب أن يكون 14 رقمًا.'
                    return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})
                if parent_national_id and (not parent_national_id.isdigit() or len(parent_national_id) != 14):
                    massage = 'الرقم القومي لولي الأمر يجب أن يكون 14 رقمًا.'
                    return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})

                # Validate mobile numbers
                if mobile and (not mobile.startswith('0') or not mobile.isdigit() or len(mobile) != 11):
                    massage = 'رقم الهاتف يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'
                    return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})
                if parent_mobile and (not parent_mobile.startswith('0') or not parent_mobile.isdigit() or len(parent_mobile) != 11):
                    massage = 'رقم هاتف ولي الأمر يجب أن يبدأ بـ 0 ويتكون من 11 رقمًا.'
                    return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})

                # Check for duplicates - only check student records with the same national ID
                old_student = request.env['res.partner'].sudo().search([
                    ('student_national_id', '=', student_national_id),
                    ('is_student', '=', True)
                ])
                if old_student:
                    massage = 'السجل موجود بالفعل بنفس الرقم القومي للطالب.'
                    return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})

                # Handle file uploads
                student_photo_data = False
                student_photo = request.httprequest.files.get('student_photo')
                if student_photo and student_photo.filename:
                    try:
                        student_photo_data = base64.b64encode(student_photo.read())
                    except Exception as e:
                        _logger.error("Error processing student photo: %s", str(e))

                # =================================================================
                # PARENT CREATION/UPDATE LOGIC - ENHANCED VERSION WITH OR LOGIC
                # =================================================================
                
                parent_partner = None
                if parent_national_id:
                    parent_partner = request.env['res.partner'].sudo().search([
                        ('parent_national_id', '=', parent_national_id),
                        ('is_parent', '=', True)
                    ], limit=1)
                if not parent_partner:
                    parent_partner = request.env['res.partner'].sudo().search([
                        ('mobile', '=', parent_mobile),
                        ('is_parent', '=', True)
                    ], limit=1)

                # Get current child's guardian and parking status
                current_is_guardian = kw.get('is_guardian') == 'on'
                current_is_parking = kw.get('is_parking') == 'on'

                _logger.info("=== PARENT UPDATE START ===")
                _logger.info("Current child: Guardian=%s, Parking=%s", current_is_guardian, current_is_parking)

                # Prepare parent values
                parent_vals = {
                    'name': self.remove2(kw.get('parent_fullname')),
                    'mobile': parent_mobile,
                    'parent_national_id': parent_national_id,
                    'is_parent': True,
                    'academic_subtype': academic_subtype,
                }

                if parent_partner:
                    # EXISTING PARENT - Use the update_parent_privileges_or_logic method
                    _logger.info("Found existing parent: %s (ID: %s)", parent_partner.name, parent_partner.id)
                    
                    # Update basic parent information first
                    parent_partner.write(parent_vals)
                    
                    # Then update privileges using OR logic
                    parent_partner.update_parent_privileges_or_logic(current_is_guardian, current_is_parking)
                    
                    _logger.info("✅ EXISTING PARENT UPDATED with OR logic")
                    
                else:
                    # NEW PARENT - Use current child's values
                    parent_vals['is_guardian'] = current_is_guardian
                    parent_vals['is_parking'] = current_is_parking
                    
                    parent_partner = request.env['res.partner'].sudo().create(parent_vals)
                    
                    _logger.info("✅ NEW PARENT CREATED: Guardian=%s, Parking=%s", current_is_guardian, current_is_parking)

                _logger.info("=== PARENT UPDATE END ===")

                # =================================================================
                # STUDENT CREATION LOGIC
                # =================================================================

                # Create student partner with parent relationship
                partner_vals = {
                    'name': name,
                    'mobile': mobile,
                    'student_national_id': student_national_id,
                    'p_name': self.remove2(kw.get('parent_fullname')),
                    'parent_national_id': parent_national_id,
                    'phone': parent_mobile,
                    'birth_date': kw.get('birth_date'),
                    'gender': kw.get('gender'),
                    'is_disability': kw.get('is_disability') == 'on',
                    'disability_description': kw.get('disability_description'),
                    'is_student': True,
                    'is_guardian': current_is_guardian,
                    'is_parking': current_is_parking,
                    'parent_id': parent_partner.id,  # Set the parent relationship
                }
                if student_photo_data:
                    partner_vals['image_1920'] = student_photo_data

                student_partner = request.env['res.partner'].sudo().create(partner_vals)

                if student_partner:
                    # Handle activities and pricelist based on member type
                    if member_type == 'academic':
                        # For academic members: automatically assign academic product and default pricelist
                        
                        # Find the academic product by name
                        academic_product = request.env['product.product'].sudo().search([
                            ('name', '=', 'أكاديمية'),
                            ('is_sportname', '=', True)
                        ], limit=1)
                        
                        if not academic_product:
                            # If academic product doesn't exist, create it
                            academic_product = request.env['product.product'].sudo().create({
                                'name': 'أكاديمية',
                                'is_sportname': True,
                                'list_price': 0.0,  # Set a base price
                                'type': 'service',
                                'categ_id': request.env.ref('product.product_category_all').id,
                            })
                            _logger.info("Created academic product: %s", academic_product.name)
                        
                        # Get the first available pricelist (default pricelist)
                        default_pricelist = request.env['product.pricelist'].sudo().search([
                            ('name', '=', 'academic')
                        ], limit=1)
                        
                        if not default_pricelist:
                            # If no pricelist exists, create a default one
                            default_pricelist = request.env['product.pricelist'].sudo().create({
                                'name': 'academic',
                                'active': True,
                            })
                            _logger.info("Created default pricelist: %s", default_pricelist.name)
                        
                        activity_ids = [(6, 0, [academic_product.id])]
                        pricelist_id = default_pricelist.id
                        
                        _logger.info("Academic member - Product: %s, Pricelist: %s", academic_product.name, default_pricelist.name)
                        
                    else:
                        # For regular members: must have activities and pricelist from form
                        activity_ids_raw = request.httprequest.form.getlist('activity_ids[]')
                        activity_ids = [(6, 0, list(map(int, activity_ids_raw)))] if activity_ids_raw else []
                        pricelist_id = self._get_pricelist_id(kw.get('pricelist_id'))
                        academic_subtype = ''  # Clear academic subtype for regular members
                        
                        # Validate that regular members have activities
                        if not activity_ids_raw:
                            student_partner.sudo().unlink()
                            massage = 'عذرًا، يجب اختيار نشاط واحد على الأقل للعضوية الرياضية.'
                            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})
                        
                        # Validate pricelist for regular members
                        if not pricelist_id:
                            student_partner.sudo().unlink()
                            massage = 'عذرًا، يجب اختيار جهة الانتماء للعضوية الرياضية.'
                            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})

                    admission_vals = {
                        'student_id': student_partner.id,
                        'parent_id': parent_partner.id,
                        'activity_ids': activity_ids,
                        'check_register': kw.get('check_data') == 'on',
                        'pricelist_id': pricelist_id,
                        'is_guardian': current_is_guardian,
                        'is_parking': current_is_parking,
                        'student_photo': student_photo_data,
                        'member_type': member_type,
                        'academic_subtype': academic_subtype,
                    }

                    request.session['is_data'] = False
                    admission = request.env['student.admission'].sudo().create(admission_vals)

                    # =================================================================
                    # FINAL SAFETY NET - ENSURE PARENT PRIVILEGES ARE CORRECT
                    # =================================================================
                    if admission and admission.parent_id:
                        _logger.info("FINAL SAFETY NET: Ensuring parent privileges are correct")
                        
                        # Use the proven OR logic update method one more time
                        admission.parent_id.update_parent_privileges_or_logic(
                            admission.is_guardian, 
                            admission.is_parking
                        )
                        
                        _logger.info("FINAL SAFETY NET: Parent privileges confirmed")
                    
                    if member_type == 'academic':
                        message = 'تم التسجيل بنجاح كعضو أكاديمي'
                    else:
                        message = 'تم التسجيل بنجاح كعضو رياضي'
                        
                    return request.render('bi_sport_center_management.registration_create_massage', {
                        'massage': message, 
                        'admission': admission
                    })

        # Error handling
        if admission:
            massage = f'تم إنشاء طلب التسجيل الخاص بك {admission.name} بنجاح.'
            return request.render('bi_sport_center_management.registration_create_massage', {
                'massage': massage, 
                'admission': admission,
                'admission_name': admission.name
            })
        else:
            if not (kw.get('fname') and kw.get('lname')):
                massage = 'عذرًا، الإسم الأول واسم العائلة مطلوبان.'
            elif not request.session.get('is_data'):
                massage = 'خطأ في الجلسة، يرجى المحاولة مرة أخرى.'
            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})

    @http.route('/inquiry/create', auth='public', website=True, methods=['POST'], csrf=False)
    def inquiry_create(self, **kw):
        massage = 'عذرًا، بعض القيم مفقودة! الرجاء ملء الحقول أولاً'
        inquiry = False
        if request.session.get('is_data'):
            if kw.get('fname') and kw.get('lname'):
                name = self.remove2(kw.get('fname')) + ' ' + self.remove2(kw.get('lname'))
                activity_id_val = request.env['product.product'].sudo().browse(int(kw.get('sport_id')))
                values = {
                    'first_name': self.remove2(kw.get('fname')),
                    'last_name': self.remove2(kw.get('lname')),
                    'mobile': self.remove(kw.get('mobile')),
                    'email': self.remove(kw.get('email')),
                    'parent_mobile': self.remove(kw.get('parent_mobile')),
                    'p_name': self.remove2(kw.get('parent_fullname')),
                    'sport_id': activity_id_val.id,
                    'level_id': kw.get('level_id'),
                    'duration': kw.get('duration'),
                    'query': kw.get('query'),
                }
                if values:
                    inquiry = request.env['student.inquiry'].sudo().create(values)
                    request.session['is_data'] = False
            if inquiry:
                massage = f'تم إنشاء طلب الاستفسار الخاص بك {inquiry.name} بنجاح.'
                return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': inquiry})
            else:
                return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': inquiry})
        else:
            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': inquiry})
        
    @http.route('/registration/', type='http', auth='public', website=True, sitemap=False)
    def registration(self, **kw):
        request.session['is_data'] = True
        states = request.env['res.country.state'].sudo().search([])
        centers = request.env['res.partner'].sudo().search([('is_sport', '=', True)])
        all_activities = request.env['product.product'].sudo().search([('is_sportname', '=', True)])

        _logger.info("All Activities: %s", all_activities)

        # Group activities by category
        activities_by_category = {}
        for act in all_activities:
            cat_name = act.categ_id.name if act.categ_id else _('Uncategorized')
            activities_by_category.setdefault(cat_name, []).append(act)

        # Add pricelist fetching logic
        pricelists = request.env['product.pricelist'].sudo().search([('active', '=', True)])
        _logger.info("Fetched pricelists count in base controller: %s", len(pricelists))
        _logger.info("Fetched pricelists names in base controller: %s", pricelists.mapped('name'))

        values = {
            'states': states,
            'activities_by_category': activities_by_category,
            'centers': centers,
            'pricelists': pricelists,  # Add pricelists to the values dictionary
        }

        return request.render('bi_sport_center_management.registration', values)

    @http.route('/inquiry/', type='http', auth='public', website=True, sitemap=False)
    def inquiry(self, **kw):
        request.session['is_data'] = True
        centers = request.env['res.partner'].sudo().search([('is_sport', '=', True)])
        studies = request.env['product.product'].sudo().search([('is_sportname', '=', True)])
        return request.render('bi_sport_center_management.inquiry', {'centers': centers, 'studies': studies})

    @http.route('/confirm/<int:id>/registration', type='http', auth='public', website=True)
    def confirm_registration(self, id, **kw):
        inquiry = request.env['student.inquiry'].sudo().browse(id)
        massage = 'عذرًا، بعض القيم مفقودة! الرجاء ملء الحقول أولاً'
        admission = False
        if inquiry and not inquiry.is_admission:
            admission = inquiry.action_admission()
        if admission:
            massage = f'تم إنشاء طلب القبول الخاص بك {admission.name} بنجاح.'
            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': admission})
        else:
            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': admission})

    @http.route('/book_ground/confirm', auth='public', website=True, methods=['POST'], csrf=False)
    def book_ground_confirm(self, **kw):
        massage = 'عذرًا، بعض القيم مفقودة! الرجاء ملء الحقول أولاً'
        tz = pytz.timezone(request.env.user.tz) or pytz.utc
        start_date = datetime.strptime(kw.get('model_start_date'), '%Y/%m/%d %H:%M')
        end_date = datetime.strptime(kw.get('model_end_date'), '%Y/%m/%d %H:%M')
        start_date = tz.localize(start_date)
        end_date = tz.localize(end_date)
        start_date_utc = start_date.astimezone(pytz.utc)
        end_date_utc = end_date.astimezone(pytz.utc)
        start_date_naive = start_date_utc.replace(tzinfo=None)
        end_date_naive = end_date_utc.replace(tzinfo=None)
        space_id = int(kw.get('model_ground_id'))
        sport_id = int(kw.get('model_sportname_id'))
        booking = request.env['center.booking'].sudo().create({
            'user_id': request.env.user.id,
            'email': kw.get('model_user_email'),
            'mobile': kw.get('model_user_mobile'),
            'space_id': space_id,
            'sport_id': sport_id,
            'start_date': start_date_naive,
            'end_date': end_date_naive,
            'desc': str(kw.get('model_user_mobile')) + ',' + str(kw.get('model_user_email')),
        })
        if booking:
            booking.sudo().action_make_payment()
            sale_order = request.env['sale.order'].sudo().search([('booking_id', '=', booking.id)], limit=1)
            if sale_order:
                request.session['sale_order_id'] = sale_order.id
                return request.redirect("/shop/cart")
        else:
            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage})

    @http.route('/check_book/availability', type='json', auth='public', website=True, csrf=False)
    def check_book_availability(self, **kw):
        data = {}
        tz = pytz.timezone(request.env.user.tz) or pytz.utc
        start_date = datetime.strptime(kw.get('start_date'), '%Y/%m/%d %H:%M')
        end_date = datetime.strptime(kw.get('end_date'), '%Y/%m/%d %H:%M')
        ground_id = int(kw.get('ground_id'))
        sportname_id = int(kw.get('sportname_id'))
        res = request.env['center.booking'].sudo().search([('sport_id', '=', sportname_id), ('space_id', '=', ground_id)])
        date_format = request.env['res.lang']._lang_get(request.env.user.lang).date_format + ' %H:%M:%S'
        start_date = start_date.strftime(date_format)
        end_date = end_date.strftime(date_format)
        if res.filtered(lambda l: l.start_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) < start_date and l.end_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) > end_date):
            data = {'status': 'unavailable'}
        elif res.filtered(lambda l: l.start_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) > start_date and l.end_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) > end_date and l.start_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) < end_date):
            data = {'status': 'unavailable'}
        elif res.filtered(lambda l: l.start_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) < start_date and l.end_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) < end_date and l.end_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) > start_date):
            data = {'status': 'unavailable'}
        elif res.filtered(lambda l: l.start_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) > start_date and l.end_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) < end_date):
            data = {'status': 'unavailable'}
        elif res.filtered(lambda l: l.start_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) == start_date or l.end_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) == end_date or l.end_date.replace(tzinfo=pytz.utc).astimezone(tz).strftime(date_format) == start_date):
            data = {'status': 'unavailable'}
        else:
            data = {'status': 'available', 'id': request.env.user.id, 'email': request.env.user.email, 'user': request.env.user.name, 'mobile': request.env.user.partner_id.mobile or ''}
        return data

    @http.route('/book_ground/', type='http', auth='user', website=True)
    def book_ground(self, **kw):
        request.session['is_data'] = True
        grounds = request.env['product.product'].sudo().search([('is_space', '=', True)])
        sports = request.env['product.product'].sudo().search([('is_sportname', '=', True)])
        return request.render('bi_sport_center_management.booking', {'grounds': grounds, 'sports': sports})

    @http.route('/get_sports', type='json', auth='user')
    def get_sports(self, ground_id):
        if ground_id:
            ground = request.env['product.product'].sudo().browse(int(ground_id))
            sports_data = [{'id': sport.id, 'name': sport.name} for sport in ground.sport_id]
        else:
            sports_data = []
        return sports_data

    @http.route('/get_sports_by_center', type='json', auth='public', website=True, csrf=False)
    def get_sports_by_center(self, center_id=None, **kw):
        sports_data = []
        if center_id:
            center = request.env['res.partner'].sudo().browse(int(center_id))
            if center and center.exists() and center.sport_id:
                sports_data = [{'id': sport.id, 'name': sport.name} for sport in center.sport_id if sport.is_sportname]
        return sports_data

    @http.route('/get_activity_price', type='json', auth='public', website=True, csrf=False)
    def get_activity_price(self, activity_id, pricelist_id, **kw):
        try:
            if not activity_id or not pricelist_id:
                return {'price': 0}
            activity = request.env['product.product'].sudo().browse(int(activity_id))
            pricelist = request.env['product.pricelist'].sudo().browse(int(pricelist_id))
            if activity and pricelist:
                price = pricelist._get_product_price(activity, 1)
                return {'price': price}
            else:
                return {'price': 0}
        except Exception as e:
            _logger.error("Error getting activity price: %s", str(e))
            return {'price': 0}

    @http.route('/print/registration/<int:registration_id>', type='http', auth='user')
    def print_registration(self, registration_id):
        registration = request.env['student.admission'].browse(registration_id)
        if not registration:
            return request.not_found()
        return request.render('bi_sport_center_management.registration_print', {'registration': registration})


class EventPortal(CustomerPortal):
    
    def get_domain_my_event(self, user):
        return [
            ('partner_id.id', '=', user.partner_id.id)
        ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user  = request.env.user
        if 'event_count' in counters:
            values['event_count'] = request.env['event.registration'].search_count(self.get_domain_my_event(request.env.user))
        return values

    def _event_get_page_view_values(self, event, access_token, **kwargs):
        values = {
            'page_name': 'events',
            'event': event,
        }
        return self._get_page_view_values(event, access_token, values, 'my_event_history', False, **kwargs)

    def _get_searchbar_inputs(self):
        return {
            'all': {'input': 'all', 'label': _('Search in All')},
            'name': {'input': 'name', 'label': _('Search by Attendee')},
            'event': {'input': 'event', 'label': _('Search by Event')},
        }

    @http.route(['/my/events', '/my/events/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_events(self, page=1, date_begin=None, date_end=None, search=None, search_in='all', sortby=None, filterby=None, groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        EventRegistration = request.env['event.registration']
        domain = self.get_domain_my_event(request.env.user)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today'), 'domain': []},
            'this week': {'label': _('This Week'), 'domain': []},
            'last week': {'label': _('Last Week'), 'domain': []},
            'this month': {'label': _('This Month'), 'domain': []},
            'last month': {'label': _('Last Month'), 'domain': []},
            'this year': {'label': _('This Year'), 'domain': []},
            'last year': {'label': _('Last Year'), 'domain': []},
        }

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'event': {'input': 'event_id', 'label': _('Event')},
        }

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'}
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        format_str = '%d%m%Y'

        if not filterby:
            filterby = 'all'

        if filterby == 'today':
            my_datetime_field = datetime.now()
            start_of_day = my_datetime_field.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = my_datetime_field.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_of_day_str = start_of_day.strftime('%Y-%m-%d %H:%M:%S')
            end_of_day_str = end_of_day.strftime('%Y-%m-%d %H:%M:%S')
            start = fields.Datetime.to_datetime(start_of_day_str)
            end = fields.Datetime.to_datetime(end_of_day_str)
            domain += [('create_date','>=',start), ('create_date','<=', end)]

        if filterby == 'this week':
            domain+=[('create_date','<=', ((date.today() - relativedelta(days=1, weeks=-1)).strftime('%Y-%m-%d'))),
            ('create_date','>=', ((date.today() - relativedelta(days=7, weeks=-1)).strftime('%Y-%m-%d')))]

        if filterby == 'last week':
            domain+=[('create_date','>=', ((date.today()  + relativedelta(days=0, weeks=-1)).strftime('%Y-%m-%d'))),
            ('create_date','<=', ((date.today()  + relativedelta(days=6, weeks=-1)).strftime('%Y-%m-%d')))]

        if filterby == 'this month':
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('create_date','>=',from_date),('create_date','<=',to_date)]

        if filterby == 'last month':
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month-1)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            if month == '02':
                to_month.append('28')
            else:
                to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('create_date','>=',from_date),('create_date','<=',to_date)]

        if filterby == 'this year':
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('create_date','>=',from_date),('create_date','<=',to_date)]

        if filterby == 'last year':
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year-1))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year-1))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('create_date','>=',from_date),('create_date','<=',to_date)]

        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        if search and search_in:
            search_domain = []
            if search_in in ('all'):
                search_domain = OR([search_domain, [('email', 'ilike', search),('name', 'ilike', search),('event_id.name', 'ilike', search)]])
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('event', 'all'):
                search_domain = OR([search_domain, [('event_id.name', 'ilike', search)]])
            domain += search_domain

        # pager
        event_count = EventRegistration.search_count(domain)
        pager = portal_pager(
            url='/my/events',
            url_args={'date_begin': date_begin, 'date_end': date_end,'sortby': sortby, 'search_in': search_in, 'search': search},
            total=event_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        events = EventRegistration.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        if groupby == 'event':
            grouped_events = [request.env['event.registration'].concat(*g) for k, g in groupbyelem(events, itemgetter('event_id'))]
        else:
            grouped_events = [events]

        searchbar_inputs = self._get_searchbar_inputs()

        values.update({
            'date': date_begin,
            'grouped_events': grouped_events,
            'page_name': 'events',
            'default_url': '/my/events',
            'pager': pager,
            'searchbar_filters': searchbar_filters,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'groupby': groupby,
            'search_in': search_in,
            'search': search,
            'filterby': filterby,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("bi_sport_center_management.portal_my_events", values)
    
    @http.route([
    "/event/<int:event_id>",
    "/event/<int:event_id>/<access_token>",
    '/my/event/<int:event_id>',
    '/my/event/<int:event_id>/<access_token>'
    ], type='http', auth="public", website=True)
    def event_followup(self, event_id=None, report_type=None, download=False, access_token=None, **kw):
        try:
            event_sudo = self._document_check_access('event.registration', event_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        request.session['event_id'] = True
        values = self._event_get_page_view_values(event_sudo, access_token, **kw)
        return request.render("bi_sport_center_management.event_followup", values)

    @http.route('/event/ticket/report/<int:event_id>', type='http', auth='user')
    def download_qweb_report(self, event_id=None, access_token=None, **kw):
        try:
            event_sudo = self._document_check_access('event.registration', event_id, access_token)
        except (AccessError, MissingError): 
            return request.redirect('/my')

        pdf = request.env["ir.actions.report"].sudo()._render_qweb_pdf('event.action_report_event_registration_full_page_ticket', event_sudo.id)[0]
        report_name = event_sudo.name + '.pdf'
        return request.sresponse(pdf, headers=[('Content-Type', 'application/pdf'), ('Content-Disposition', content_disposition(report_name))])