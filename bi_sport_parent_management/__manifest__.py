{
    'name': 'BI Sport Parent Management',
    'version': '1.0',
    'depends': ['base', 'web', 'bi_sport_center_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/res_partner_views.xml',
        'wizard/parent_id_print_wizard_views.xml',
        'report/parent_id_card_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bi_sport_parent_management/static/src/js/dashboard.js',
            'bi_sport_parent_management/static/src/js/dashboard_action.js',
            'bi_sport_parent_management/static/src/xml/dashboard.xml',
            'bi_sport_parent_management/static/src/xml/parent_dashboard.xml',
            'bi_sport_parent_management/static/src/css/dashboard.css',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
        ],
    },
    'demo': [],  # Empty or remove this line completely

    'installable': True,
    'auto_install': False,
}