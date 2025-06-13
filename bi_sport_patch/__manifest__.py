# -*- coding: utf-8 -*-
{
    'name': 'Sport Patch',
    'version': '17.0.1.0',
    'summary': 'All you need to manage your sport center',
    'description': 'Whatever you need to manage your sport center',
    'author': 'Learnovia',
    'depends': ['bi_sport_center_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_patch_views.xml',
        'wizard/student_id_print_wizard_views.xml',
        'views/student_admission_patch_views.xml',
        'report/student_id_card_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
} 