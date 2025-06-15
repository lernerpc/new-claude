{
    'name': 'Sport Center Pricelist Extension',
    'version': '1.0',
    'category': 'Sports',
    'summary': 'Extends sport center with pricelist functionality',
    'description': """
        This module extends the sport center management module by:
        - Replacing the affiliation section with pricelists in the registration form
        - Applying pricelist prices to invoices for selected activities
        - Supporting different pricing for student categories
        - Compatible with Odoo 17 Community Edition
    """,
    'depends': ['bi_sport_center_management', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/student_admission_views.xml',
    ],
    'demo': [],  # Empty or remove this line completely

    'installable': True,
    'application': False,
    'auto_install': False,
}
