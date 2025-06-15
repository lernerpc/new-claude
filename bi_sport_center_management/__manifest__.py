# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sport Center Management",
    'version': "17.0.0.2",
    'summary': "Manage Sport Club Fitness Center Management Sports Operations Sports Industry Sports Club Activities Sports Management Services Custom Sports Solution Sports Management Agency Student Sport Registrations Sports Inquiry Sports Trainers Booking Sports Center",
    'description': """The Sports Club Management Odoo App empowers sports clubs or center to streamline their administrative tasks. Registered or Guests users can submit inquiries and registration requests from the portal view. Admin can manage inquiries, membership registrations, process invoice payment, and event registrations. Sports center dashboard can help users with handling and oversee of sports activities to enhance user experience. User can set trainer and manage sports equipment. Additionally, users can generate sports center certificates in PDF format, This invaluable tool offering a complete solution for managing various aspects of sports center operations.""",
    "author": "BROWSEINFO",
    "website" : "https://www.browseinfo.com/demo-request?app=bi_sport_center_management&version=17&edition=Community",
    "price": 99,
    "currency": 'EUR',
    'depends': ['base', 'mail', 'account', 'product', 'website', 'contacts', 'event','website_event_sale','stock','purchase', 'base_address_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/admission_data.xml',
        'demo/product_demo.xml',
        'data/admission_enroll_email.xml',
        'data/student_inquiry_mail.xml',
        'data/booking_mail_template.xml',
        'data/web_menu.xml',
        'report/center_certificate_report.xml',
        'views/templates.xml',
        'wizard/create_invoice_views.xml',
        'views/res_partner_views.xml',
        'views/student_admission_views.xml',
        'data/center_sport_dashboard_views.xml',
        'views/student_inquiry_views.xml',
        'views/center_booking_views.xml',
        'views/product_views.xml',
        'views/event_views.xml',
        'views/center_certificate_views.xml',
        'views/purchase_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bi_sport_center_management/static/src/js/sport_center_frontend.js',
            'bi_sport_center_management/static/src/js/jquery_datetimepicker_full_min.js',
            'bi_sport_center_management/static/src/css/jquery_datetimepicker.css',
        ],
        'web.assets_backend': [
            'bi_sport_center_management/static/src/css/dashboard.css',
            'bi_sport_center_management/static/src/js/dashboard_action.js',
            'bi_sport_center_management/static/src/xml/dashboard.xml',
        ],
    },
    'demo': [],  # Empty or remove this line completely

    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://www.browseinfo.com/demo-request?app=bi_sport_center_management&version=17&edition=Community',
    "images":['static/description/Banner.gif'],
}
