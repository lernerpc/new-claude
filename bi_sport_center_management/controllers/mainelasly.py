# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo import _, fields
from dateutil.relativedelta import relativedelta
from odoo import http
from odoo.osv.expression import OR
from odoo.http import request, content_disposition
from operator import itemgetter
from odoo.tools.translate import _
from odoo.tools import groupby as groupbyelem
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers.portal import CustomerPortal
import pytz

class StudentRegistration(http.Controller):
    
    def remove(self, string):
        return string.replace(" ", "") if string else ""

    @http.route('/registration/create', auth='public', website=True, methods=['POST'], csrf=False)
    def registration_create(self, **kw):
        admission = False
        massage = 'عذرًا، بعض القيم مفقودة! الرجاء ملء الحقول أولاً'
        if request.session.get('is_data') and kw.get('check_data'):
            if kw.get('fname') and kw.get('lname'):
                name = self.remove(kw.get('fname')) + ' ' + self.remove(kw.get('lname'))
                mobile = self.remove(kw.get('mobile'))
                # Duplicate check for name or mobile
                old_partner = request.env['res.partner'].sudo().search(
                    ['|', ('name', '=', name), ('mobile', '=', mobile)]
                )
                if old_partner:
                    massage = 'السجل موجود بالفعل بنفس الاسم أو رقم الهاتف.'
                    return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': admission})
                
                partner_vals = {
                    'name': name,
                    'email': self.remove(kw.get('email')),
                    'mobile': mobile,
                    'street': kw.get('address'),
                    'city': kw.get('city'),
                    'state_id': int(kw.get('state')) if kw.get('state') else False,
                    'zip': kw.get('zip'),
                    # Parent Info
                    'p_name': self.remove(kw.get('parent_fullname')),
                    'parent_national_id': self.remove(kw.get('parent_national_id')),
                    'phone': self.remove(kw.get('parent_mobile')), # Mapped to phone in res.partner
                    # Other Student Info
                    'birth_date': kw.get('birth_date'),
                    'gender': kw.get('gender'),
                    'affiliation': kw.get('affiliation'),
                    'is_disability': kw.get('is_disability') == 'on',
                    'disability_description': kw.get('disability_description'),
                    'emergency_contact_name': self.remove(kw.get('emergency_contact_name')),
                    'emergency_contact_phone': self.remove(kw.get('emergency_contact_phone')),
                    'is_student': True, # Set is_student to True for new registrations
                }
                partner = request.env['res.partner'].sudo().create(partner_vals)
                if partner:

                    # Group activities by category
                    all_activities = request.env['product.product'].sudo().search([('is_sportname', '=', True)])
                    categ_activities = {}
                    for act in all_activities:
                        cat_name = act.categ_id.name if act.categ_id else _('Uncategorized')
                        categ_activities.setdefault(cat_name, []).append(act)

                    activity_ids_raw = request.httprequest.form.getlist('activity_ids[]')
                    activity_ids = [(6, 0, list(map(int, activity_ids_raw)))] if activity_ids_raw else []

                    admission_vals = {
                        'student_id': partner.id,
                        'activity_ids': activity_ids,
                        'check_register': kw.get('check_data') == 'on',
                    }
                    if admission_vals.get('activity_ids'):
                        request.session['is_data'] = False
                        admission = request.env['student.admission'].sudo().create(admission_vals)
                    else:
                        partner.sudo().unlink()
                        massage = 'عذرًا، بيانات النشاط مفقودة. لا يمكن إنشاء القبول.'
                        return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': False})

           
        if admission:
            massage = f'تم إنشاء طلب التسجيل الخاص بك {admission.name} بنجاح.'
            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': admission})
        else:
            # Ensure a message is displayed even if initial checks (is_data, check_data, fname, lname) fail
            if not (kw.get('fname') and kw.get('lname')) and request.session.get('is_data') and kw.get('check_data'):
                 massage = 'عذرًا، الإسم الأول واسم العائلة مطلوبان.'
            elif not request.session.get('is_data'):
                 massage = 'خطأ في الجلسة، يرجى المحاولة مرة أخرى.' 
            return request.render('bi_sport_center_management.registration_create_massage', {'massage': massage, 'admission': admission})

    @http.route('/inquiry/create', auth='public', website=True, methods=['POST'], csrf=False)
    def inquiry_create(self, **kw):
        massage = 'عذرًا، بعض القيم مفقودة! الرجاء ملء الحقول أولاً'
        inquiry = False
        if request.session.get('is_data'):
            if kw.get('fname') and kw.get('lname'):
                name = self.remove(kw.get('fname')) + ' ' + self.remove(kw.get('lname'))
                activity_id_val = request.env['product.product'].sudo().browse(int(kw.get('sport_id')))
                values = {
                    'first_name': self.remove(kw.get('fname')),
                    'last_name': self.remove(kw.get('lname')),
                    'mobile': self.remove(kw.get('mobile')),
                    'email': self.remove(kw.get('email')),
                    'parent_mobile': self.remove(kw.get('parent_mobile')),
                    'p_name': self.remove(kw.get('parent_fullname')),
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

        # Group activities by category
        activities_by_category = {}
        for act in all_activities:
            cat_name = act.categ_id.name if act.categ_id else _('Uncategorized')
            activities_by_category.setdefault(cat_name, []).append(act)

        return request.render('bi_sport_center_management.registration', {
            'states': states,
            'activities_by_category': activities_by_category,
            'centers': centers
        })

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
        return request.make_response(pdf, headers=[('Content-Type', 'application/pdf'), ('Content-Disposition', content_disposition(report_name))])

